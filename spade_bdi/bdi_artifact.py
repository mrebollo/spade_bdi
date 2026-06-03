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


class ArtifactBDIMixin(ArtifactActuatorMixin, ArtifactMixin):
    """
    Mixin that mirrors artifact publications into BDI beliefs and
    provides the .use internal action to interact with artifacts.

    Use it before `BDIAgent` in the MRO:
        class MyAgent(ArtifactBDIMixin, BDIAgent):
            ...
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

        original_focus = self.artifacts.focus
        agent = self

        async def _focus_with_bridge(artifact_jid, callback=None):
            def _wrapped(jid, payload):
                agent._on_artifact_publication(jid, payload)

                if callback is None:
                    return

                callback(jid, payload)

            await original_focus(artifact_jid, _wrapped)

        self.artifacts.focus = _focus_with_bridge
        self._bdi_artifact_focus_wrapped = True

    def add_custom_actions(self, actions):
        super().add_custom_actions(actions)

        @actions.add(".use", None)
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
                    # Fallback for sync contexts (like old tests)
                    asyncio.ensure_future(coro)
            yield

    def _on_artifact_publication(self, artifact_jid, payload):
        """Default callback that converts payloads to BDI beliefs."""
        del artifact_jid  # Reserved for future source-aware mappings.

        if not hasattr(self, "bdi") or self.bdi is None:
            logger.warning("[ArtifactBDIMixin] BDI behaviour is not ready yet.")
            return

        parsed_json = self._parse_json_payload(payload)
        if parsed_json is not None:
            self._inject_json_beliefs(parsed_json)
            return

        literal = self._parse_literal_payload(payload)
        if literal is not None:
            functor, args = literal
            self.bdi.set_belief(functor, *args)
            return

        logger.debug(f"[ArtifactBDIMixin] Ignored payload: {payload!r}")

    def _inject_json_beliefs(self, payload_dict):
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
            values = literal_eval(f"[{raw_args}]")
        except (ValueError, SyntaxError):
            values = [raw_args]

        if not isinstance(values, list):
            values = [values]

        return functor, tuple(values)
