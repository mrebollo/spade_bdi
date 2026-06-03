import asyncio
import json

import spade
from spade_artifact import Artifact
from spade_bdi.bdi_artifact import ArtifactBDIMixin
from spade_bdi.bdi import BDIAgent


class SensorArtifact(Artifact):
    async def run(self):
        temp = 0
        while True:
            print("[sensor] publishing temperature")
            await self.publish(f"temperature({temp})")
            temp += 1
            await asyncio.sleep(1)
            print("[sensor] publishing status")
            await self.publish(json.dumps({"status": "locked"}))
            await asyncio.sleep(1)


class ObserverAgent(ArtifactMixin, BDIAgent):
    async def setup(self):
        await super().setup()
        await self.artifacts.focus("sensor@localhost", self.on_sensor_update)

    def on_sensor_update(self, jid, payload):
        print(f"[observer] payload from {jid}: {payload}")
        print(f"[observer] id(payload): {id(payload)}, type: {type(payload)}")
        if hasattr(payload, 'metadata'):
            print(f"[observer] payload.metadata: {getattr(payload, 'metadata')}")


async def main():
    sensor = SensorArtifact("sensor@localhost", "1234")
    observer = ObserverAgent("observer@localhost", "1234", "observer.asl")

    await sensor.start()
    await observer.start()
    handlers = getattr(observer.client, "_XMLStream__event_handlers", {})
    print("pubsub_publish handlers:", len(handlers.get("pubsub_publish", [])))
    print("focus_callbacks:", len(observer.artifacts.focus_callbacks))
    print("focus_callbacks keys:", list(observer.artifacts.focus_callbacks.keys()))
    await asyncio.sleep(6)
    await observer.stop()
    await sensor.stop()


if __name__ == "__main__":
    spade.run(main())
