import asyncio
import json
import os
import spade
from spade_artifact import Artifact
from spade_bdi.bdi_artifact import ArtifactBDIMixin
from spade_bdi.bdi import BDIAgent


class MultiSensorArtifact(Artifact):
    async def run(self):
        # Wait for connections and subscriptions to stabilize
        await asyncio.sleep(1.5)

        # Case 1: Multi-argument literal
        print("[sensor] publishing multi-argument literal: measure(25, 'celsius', 'ok')")
        await self.publish("measure(25, 'celsius', 'ok')")
        await asyncio.sleep(1.5)

        # Case 2: JSON dictionary with simple values
        status = "unlocked"
        battery = 92
        print("[sensor] publishing JSON dict: {'status': 'unlocked', 'battery': 92}")
        await self.publish(json.dumps({"status": status, "battery": battery}))
        await asyncio.sleep(1.5)

        # Case 3: JSON dictionary with lists (multiple values per key)
        print("[sensor] publishing JSON with list: {'sensor_data': [22.5, 'celsius', 'normal']}")
        await self.publish(json.dumps({"sensor_data": [22.5, "celsius", "normal"]}))
        await asyncio.sleep(1.5)


class MultiObserverAgent(ArtifactBDIMixin, BDIAgent):
    async def setup(self):
        await super().setup()
        await self.artifacts.focus("sensor@localhost", self.on_sensor_update)

    def on_sensor_update(self, jid, payload):
        print(f"[observer] received raw payload from {jid}: {payload}")


async def main():
    sensor = MultiSensorArtifact("sensor@localhost", "1234")
    asl_path = os.path.join(os.path.dirname(__file__), "multi_observer.asl")
    observer = MultiObserverAgent("observer@localhost", "1234", asl_path)

    await sensor.start()
    await observer.start()

    # Let the interaction run for 8 seconds
    await asyncio.sleep(8)

    await observer.stop()
    await sensor.stop()


if __name__ == "__main__":
    spade.run(main())
