import json
import re
import asyncio
from ast import literal_eval
from loguru import logger

import agentspeak as asp
from spade_artifact import ArtifactMixin
from spade_artifact.artifact_ext import ArtifactActuatorMixin


_FUNCTOR_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_LITERAL_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:\((.*)\))?\s*$")


class ArtifactActions(asp.Actions):
    """
    Custom Actions registry for python-agentspeak.
    Intercepts lookups of undefined dotted actions (like .unlock) and
    dynamically delegates them as remote operations on focused artifacts.
    """
    def __init__(self, parent=None, agent=None):
        super().__init__(parent)
        self.agent = agent

    def lookup(self, functor, arity):
        try:
            return super().lookup(functor, arity)
        except KeyError:
            # If the compiler/runtime queries an unknown action starting with '.'
            # (e.g. .unlock), we return a dynamic dispatcher wrapper.
            if functor.startswith("."):
                return self._dynamic_dispatch(functor)
            raise

    def _dynamic_dispatch(self, functor):
        """
        Generates a wrapper function executed at runtime when the dynamic
        action is called in an AgentSpeak plan.
        """
        def _wrapper(agent, term, intention):
            op_name = functor[1:]  # strip leading dot to get operation name
            args = tuple(asp.grounded(arg, intention.scope) for arg in term.args)

            # 1. Retrieve JIDs of all currently focused/subscribed artifacts
            if hasattr(self.agent.artifacts, "focus_callbacks"):
                focused_jids = list(self.agent.artifacts.focus_callbacks.keys())
            elif hasattr(self.agent.artifacts, "callbacks"):
                focused_jids = list(self.agent.artifacts.callbacks.keys())
            else:
                focused_jids = []

            if not focused_jids:
                logger.error(f"[ArtifactActions] Cannot execute .{op_name}: No focused artifacts.")
                return

            # 2. Query the Directory cache to find which artifact supports this operation
            target_jid = None
            if hasattr(self.agent.artifacts, "_dir_cache") and self.agent.artifacts._dir_cache:
                try:
                    matching_jids = self.agent.artifacts.find_by_op(op_name)
                    # Limit JIDs to only focused ones
                    focused_matches = [j for j in matching_jids if j in focused_jids]
                    if focused_matches:
                        target_jid = focused_matches[0]
                except Exception as e:
                    logger.debug(f"[ArtifactActions] Directory resolution failed: {e}")

            # 3. Fallback: if not resolved via Directory, target the first focused artifact
            if not target_jid:
                target_jid = focused_jids[0]

            logger.info(f"[ArtifactActions] Invoking .{op_name} on {target_jid} with args {args}")

            # 4. Asynchronously invoke the remote operation via spade_artifact
            coro = self.agent.artifacts.use(target_jid, op_name, *args)
            if hasattr(self.agent, "loop") and self.agent.loop is not None:
                self.agent.loop.create_task(coro)
            else:
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(coro)
                except RuntimeError:
                    asyncio.ensure_future(coro)
            yield
        return _wrapper


class ArtifactBDIMixin(ArtifactActuatorMixin, ArtifactMixin):
    """
    Mixin that integrates the SPADE BDI agent with SPADE Artifacts.
    
    1. Belief Propagation: Automatically translates PubSub updates received
       from focused artifacts into BDI beliefs (literals or JSON).
    2. Operation Execution: Registers the .use internal action and provides
       the hook to support dynamic native actions (e.g. .unlock).
    """

    async def setup(self):
        await super().setup()
        if not hasattr(self, "artifacts"):
            logger.warning(
                "[ArtifactBDIMixin] self.artifacts not found; ensure ArtifactMixin is in the MRO."
            )
            return

        if getattr(self, "_bdi_artifact_focus_wrapped", False):
            return

        # Intercept and wrap the focus() method to automatically forward
        # all incoming PubSub events to the BDI belief base.
        original_focus = self.artifacts.focus
        agent = self

        async def _focus_with_bridge(artifact_jid, callback=None):
            def _wrapped(jid, payload):
                # First, process the payload and update the BDI belief base
                agent._on_artifact_publication(jid, payload)

                # Then, trigger the original user-defined callback if it exists
                if callback is None:
                    return

                callback(jid, payload)

            await original_focus(artifact_jid, _wrapped)

        self.artifacts.focus = _focus_with_bridge
        self._bdi_artifact_focus_wrapped = True

    def add_custom_actions(self, actions):
        # Wrap the original AgentSpeak actions in our custom ArtifactActions class
        self.bdi_actions = ArtifactActions(parent=actions, agent=self)

        super().add_custom_actions(self.bdi_actions)

        # Register the explicit .use(JID, Op, Args...) internal action
        @self.bdi_actions.add(".use", None)
        def _use(agent, term, intention):
            jid = str(asp.grounded(term.args[0], intention.scope))
            op = str(asp.grounded(term.args[1], intention.scope))
            op_args = tuple(asp.grounded(arg, intention.scope) for arg in term.args[2:])

            coro = self.artifacts.use(jid, op, *op_args)
            if hasattr(self, "loop") and self.loop is not None:
                self.loop.create_task(coro)
            else:
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(coro)
                except RuntimeError:
                    asyncio.ensure_future(coro)
            yield

    def _on_artifact_publication(self, artifact_jid, payload):
        """
        Receives raw PubSub payloads from focused artifacts and parses them
        into the agent's BDI belief base.
        """
        del artifact_jid  # Reserved for future source-aware mappings.

        if not hasattr(self, "bdi") or self.bdi is None:
            logger.warning("[ArtifactBDIMixin] BDI behaviour is not ready yet.")
            return

        # Case A: Try parsing payload as a JSON dictionary
        parsed_json = self._parse_json_payload(payload)
        if parsed_json is not None:
            self._inject_json_beliefs(parsed_json)
            return

        # Case B: Try parsing payload as a literal (e.g. status(unlocked))
        literal = self._parse_literal_payload(payload)
        if literal is not None:
            functor, args = literal
            self.bdi.set_belief(functor, *args)
            return

        logger.debug(f"[ArtifactBDIMixin] Ignored payload: {payload!r}")

    def _inject_json_beliefs(self, payload_dict):
        """
        Maps JSON dictionary keys to BDI belief functors.
        Supports:
        - List/Tuple values -> maps to multi-argument beliefs (e.g. key(arg1, arg2))
        - Scalar values -> maps to single-argument beliefs (e.g. key(value))
        """
        for key, value in payload_dict.items():
            if not isinstance(key, str) or not _FUNCTOR_RE.match(key):
                logger.debug(f"[ArtifactBDIMixin] Ignored JSON key: {key!r}")
                continue

            if value is None:
                continue

            if isinstance(value, (list, tuple)):
                self.bdi.set_belief(key, *tuple(value))
            elif isinstance(value, (str, int, float, bool)):
                self.bdi.set_belief(key, value)
            else:
                logger.debug(f"[ArtifactBDIMixin] Ignored JSON value for {key!r}: {value!r}")

    @staticmethod
    def _parse_json_payload(payload):
        """Decodes JSON payload string and ensures it represents a dictionary."""
        if not isinstance(payload, str):
            return None

        try:
            decoded = json.loads(payload)
        except (TypeError, json.JSONDecodeError):
            return None

        if isinstance(decoded, dict):
            return decoded
        return None

    @staticmethod
    def _parse_literal_payload(payload):
        """
        Parses a Prolog-like string literal (e.g., "temperature(22, celsius)")
        into a tuple of (functor, tuple_of_args).
        """
        if not isinstance(payload, str):
            return None

        match = _LITERAL_RE.match(payload)
        if not match:
            return None

        functor = match.group(1)
        raw_args = match.group(2)

        if raw_args is None or raw_args.strip() == "":
            return functor, tuple()

        try:
            # Wrap in brackets to parse as a Python list using literal_eval safely
            values = literal_eval(f"[{raw_args}]")
        except (ValueError, SyntaxError):
            values = [raw_args]

        if not isinstance(values, list):
            values = [values]

        return functor, tuple(values)
