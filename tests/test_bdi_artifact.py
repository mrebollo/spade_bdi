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

    async def focus(self, artifact_jid, callback):
        self.callbacks[artifact_jid] = callback


class _BaseAgent:
    async def setup(self):
        return None


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
