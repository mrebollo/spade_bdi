import asyncio
import random
from spade_artifact import Artifact

class Beer(Artifact):
    """Artefacto cerveza."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = "full"

    async def setup(self):
        await self.publish(self.state)

    def sip(self):
        """Acción de beber."""
        if self.state == "full":
            if random.random() < 0.25:
                self.state = "empty"
                print(f"[beer(A)] Empty!")
                asyncio.create_task(self.publish(self.state))
            else:
                print(f"[beer(A)] Slurp... still some left.")

class Table(Artifact):
    """Artefacto mediador tipo mesa para dejar/recoger bebidas."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = "empty"
        self.slot = None

    async def put_on(self, beer):
        """Colocar un `Beer` en la mesa (placeholder)."""
        self.slot = beer
        self.state = "occupied"
        print(f"[table(A)] Beer {beer.jid} placed on the table.")
        await self.publish(self.state)
        pass

    async def take_off(self):
        """Tomar la `Beer` de la mesa (placeholder)."""
        if self.slot:
            beer = self.slot
            self.slot = None
            self.state = "empty"
            print(f"[table(A)] Beer {beer.jid} taken from the table.")
            await self.publish(self.state)
            return beer
        print("[table(A)] No beer on the table to take.")
        return None


class Fridge(Artifact):
    """La nevera es un contenedor de objetos Beer."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.beers = []

    def set_stock(self, instances):
        print(f"[fridge(A)] adding {len(instances)} beers")
        self.beers = instances

    async def setup(self):
        state = "available" if len(self.beers) > 0 else "empty"
        print(f"[fridge(A)] ready")
        await self.publish(state)

    def open(self):
        print(f"[fridge(A)] open: send stock:{len(self.beers)}")
        asyncio.create_task(self.publish(f"stock: {len(self.beers)}"))

    def take(self):
        if self.beers:
            beer = self.beers.pop(0)
            print(f"[fridge(A)] take: beer {beer.name} taken, {len(self.beers)} left")
            asyncio.create_task(self.publish(f"stock:{len(self.beers)}"))
            return beer
        print("[fridge(A)] take: no beers left")
        return None

    def restock(self, new_beers):
        print(f"[fridge(A)] restock: adding {len(new_beers)} beers")
        self.beers.extend(new_beers)
        state = "available" if len(self.beers) > 0 else "empty"
        print(f"[fridge(A)] availability: '{state}'")
        asyncio.create_task(self.publish(state))


