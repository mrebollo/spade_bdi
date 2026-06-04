import asyncio

from spade_bdi.bdi_artifact import ArtifactBDIMixin


class _DummyBDI:
    def __init__(self):
        self.calls = []

    def set_belief(self, name, *args):
        self.calls.append((name, args))


class _DummyArtifacts:
    def __init__(self):
        self.callbacks = {}
        self.use_calls = []

    async def focus(self, artifact_jid, callback):
        self.callbacks[artifact_jid] = callback

    async def use(self, jid, op, *args):
        self.use_calls.append((jid, op, args))


class _BaseAgent:
    async def setup(self):
        return None

    def add_custom_actions(self, actions):
        pass


class _DummyAgent(ArtifactBDIMixin, _BaseAgent):
    def __init__(self):
        self.artifacts = _DummyArtifacts()
        self.bdi = _DummyBDI()


def test_literal_payload_is_injected_as_belief():
    agent = _DummyAgent()
    asyncio.run(agent.setup())

    callback = agent.artifacts.callbacks.setdefault("sensor@localhost", None)
    assert callback is None

    asyncio.run(agent.artifacts.focus("sensor@localhost"))
    callback = agent.artifacts.callbacks["sensor@localhost"]
    callback("sensor@localhost", "temperature(22)")

    assert ("temperature", (22,)) in agent.bdi.calls


def test_json_payload_is_injected_as_belief():
    agent = _DummyAgent()
    asyncio.run(agent.setup())

    asyncio.run(agent.artifacts.focus("sensor@localhost"))
    callback = agent.artifacts.callbacks["sensor@localhost"]
    callback("sensor@localhost", '{"status": "locked"}')

    assert ("status", ("locked",)) in agent.bdi.calls


def test_use_action_invokes_artifact_operation():
    import agentspeak as asp

    async def _run_test():
        agent = _DummyAgent()

        actions = asp.Actions()
        agent.add_custom_actions(actions)

        use_action = agent.bdi_actions.lookup(".use", 2)
        term = asp.Literal(".use", (asp.Literal("sensor@localhost"), asp.Literal("lock")))
        intention = asp.runtime.Intention()

        gen = use_action(agent, term, intention)
        list(gen)

        await asyncio.sleep(0.01)

        assert ("sensor@localhost", "lock", ()) in agent.artifacts.use_calls

    asyncio.run(_run_test())


def test_dynamic_action_invocation_without_params():
    import agentspeak as asp

    async def _run_test():
        agent = _DummyAgent()
        actions = asp.Actions()
        agent.add_custom_actions(actions)

        await agent.artifacts.focus("door@localhost", lambda j, p: None)

        unlock_action = agent.bdi_actions.lookup(".unlock", 0)
        term = asp.Literal(".unlock", ())
        intention = asp.runtime.Intention()

        gen = unlock_action(agent, term, intention)
        list(gen)

        await asyncio.sleep(0.01)

        assert ("door@localhost", "unlock", ()) in agent.artifacts.use_calls

    asyncio.run(_run_test())


def test_dynamic_action_invocation_with_params():
    import agentspeak as asp

    async def _run_test():
        agent = _DummyAgent()
        actions = asp.Actions()
        agent.add_custom_actions(actions)

        await agent.artifacts.focus("door@localhost", lambda j, p: None)

        unlock_action = agent.bdi_actions.lookup(".unlock", 1)
        term = asp.Literal(".unlock", (asp.Literal("master_key_123"),))
        intention = asp.runtime.Intention()

        gen = unlock_action(agent, term, intention)
        list(gen)

        await asyncio.sleep(0.01)

        assert ("door@localhost", "unlock", (asp.Literal("master_key_123"),)) in agent.artifacts.use_calls

    asyncio.run(_run_test())


def test_dynamic_action_invocation_with_directory_resolution():
    import agentspeak as asp

    async def _run_test():
        agent = _DummyAgent()
        actions = asp.Actions()
        agent.add_custom_actions(actions)

        # Focus two dummy JIDs
        await agent.artifacts.focus("door1@localhost", lambda j, p: None)
        await agent.artifacts.focus("door2@localhost", lambda j, p: None)

        # Set up Directory cache and search method
        agent.artifacts._dir_cache = {
            "door1@localhost": {"type": "Door", "operations": ["lock"]},
            "door2@localhost": {"type": "Door", "operations": ["unlock"]}
        }
        def _find_by_op(op):
            return [jid for jid, info in agent.artifacts._dir_cache.items() if op in info["operations"]]
        agent.artifacts.find_by_op = _find_by_op

        # Look up and execute the action
        unlock_action = agent.bdi_actions.lookup(".unlock", 0)
        term = asp.Literal(".unlock", ())
        intention = asp.runtime.Intention()

        gen = unlock_action(agent, term, intention)
        list(gen)

        await asyncio.sleep(0.01)

        # Should target door2@localhost since it exposes unlock
        assert ("door2@localhost", "unlock", ()) in agent.artifacts.use_calls

    asyncio.run(_run_test())

