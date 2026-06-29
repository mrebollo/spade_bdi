import asyncio
import os
import spade
from loguru import logger
from spade_bdi.bdi import BDIAgent
from spade_bdi.bdi_artifact import ArtifactBDIMixin
from spade_artifact import OperableArtifact, operation

# Modelo del entorno: una puerta operable
class Door(OperableArtifact):
    @operation
    async def lock(self):
        print("[door] lock operation invoked")
        await self.publish("door(locked)")

    @operation
    async def unlock(self):
        print("[door] unlock operation invoked")
        await self.publish("door(unlocked)")


# Agente que percibe la puerta de forma situada
class SituatedAgent(ArtifactBDIMixin, BDIAgent):
    def __init__(self, *args, artifact_jid: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.artifact_jid = artifact_jid

    async def setup(self):
        await super().setup()
        # Enfocar el artefacto. El mixin ArtifactBDIMixin se encarga automáticamente
        # de puentear las publicaciones a las creencias del motor BDI.
        await self.artifacts.focus(self.artifact_jid)
        logger.info(f"{self.name} situated agent ready")


# Agente con capacidad de manejar la puerta usando acciones dinámicas nativas.
# No necesita registrar manualmente add_custom_actions ni mantener referencias directas
# a los objetos del entorno en Python; todo se delega en tiempo de ejecución.
class RoomAgent(SituatedAgent):
    pass


async def main():
    asl_dir = os.path.dirname(__file__)
    
    paranoid = SituatedAgent(jid="paranoid@localhost", password="1234", asl=os.path.join(asl_dir, "paranoid.asl"), artifact_jid="door@localhost")
    claust = SituatedAgent(jid="claustrophobic@localhost", password="1234", asl=os.path.join(asl_dir, "claust.asl"), artifact_jid="door@localhost")
    porter = RoomAgent(jid="porter@localhost", password="1234", asl=os.path.join(asl_dir, "porter.asl"), artifact_jid="door@localhost")
    theDoor = Door("door@localhost", "1234")

    print("Start agents")
    await theDoor.start()
    await porter.start()
    await paranoid.start()
    await claust.start()

    # Estado inicial: door locked
    await asyncio.sleep(2)
    await theDoor.lock()

    await asyncio.sleep(5)

    # Imprimir las creencias finales de los agentes
    print("**porter final beliefs")
    porter.bdi.print_beliefs(source=True)
    print("**claustr final beliefs")
    claust.bdi.print_beliefs(source=True)
    print("**paranoid final beliefs")
    paranoid.bdi.print_beliefs(source=True)
    
    print("Stopping agents...")
    await paranoid.stop()
    await claust.stop()
    await porter.stop()
    await theDoor.stop()


if __name__ == "__main__":
    spade.run(main())