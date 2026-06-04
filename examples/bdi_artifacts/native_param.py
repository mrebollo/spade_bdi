import asyncio
import os
import spade
from spade_artifact import OperableArtifact, operation
from spade_bdi.bdi_artifact import ArtifactBDIMixin
from spade_bdi.bdi import BDIAgent


class DoorArtifact(OperableArtifact):
    @operation
    async def lock(self):
        print("[door] lock operation invoked!")
        await self.publish("status(locked)")

    @operation
    async def unlock(self, key):
        print(f"[door] unlock operation invoked with key: {key}!")
        await self.publish(f"status(unlocked_by('{key}'))")


class UserAgent(ArtifactBDIMixin, BDIAgent):
    async def setup(self):
        await super().setup()
        # Focus on the door artifact
        await self.artifacts.focus("door@localhost")


async def main():
    door = DoorArtifact("door@localhost", "1234")
    asl_path = os.path.join(os.path.dirname(__file__), "native_param.asl")
    agent = UserAgent("agent@localhost", "1234", asl_path)

    # Start the artifact and agent
    await door.start()
    await agent.start()

    # Let them interact for 4 seconds
    await asyncio.sleep(4)

    # Stop them
    await agent.stop()
    await door.stop()


if __name__ == "__main__":
    spade.run(main())
