import sys
import os
import asyncio
import spade
from artifacts import Fridge, Beer, Table
from agents import WaiterAgent, StockerAgent, OwnerAgent, MarketAgent


async def main():
    # 1. Instanciar Nevera (Vacía)
    fridge = Fridge("fridge@localhost", "1234")
    fridge.set_stock([])

    # 2. Instanciar Agentes
    asl_dir = os.path.dirname(__file__)
    waiter = WaiterAgent("waiter@localhost", "1234", os.path.join(asl_dir, "waiter.asl"), fridge_jid="fridge@localhost")
    stocker = StockerAgent("stocker@localhost", "1234", os.path.join(asl_dir, "stocker.asl"), fridge_jid="fridge@localhost")
    owner = OwnerAgent("owner@localhost", "1234", os.path.join(asl_dir, "owner.asl"), table_jid="table@localhost")
    market = MarketAgent("market@localhost", "1234", os.path.join(asl_dir, "supermarket.asl"))

    # 3. Cruzar referencias
    waiter.controls(fridge)
    waiter.set_owner(owner)
    stocker.controls(fridge)
    # table mediadora
    table = Table("table@localhost", "1234")
    waiter.table = table
    owner.controls(table)

    # 4. Arrancar Artefactos
    print(">>> Iniciando entorno físico...")
    await fridge.start()
    await table.start()

    # 5. Arrancar Agentes
    print(">>> Iniciando agentes...")
    await market.start()
    await waiter.start()
    await stocker.start()
    await owner.start()

    # 5.1 Debug: Mostrar handlers registrados
    def _count_handlers(observer):
        print(f"\n--- Handlers registrados en {observer.name} ---")
        handlers = getattr(observer.client, "_XMLStream__event_handlers", {})
        print("pubsub_publish handlers:", len(handlers.get("pubsub_publish", [])))
        if hasattr(observer, "artifacts"):  
             print("focus_callbacks:", len(observer.artifacts.focus_callbacks))
             print("focus_callbacks keys:", list(observer.artifacts.focus_callbacks.keys()))    
    _count_handlers(waiter)
    _count_handlers(stocker)
    _count_handlers(owner) 
    _count_handlers(market)

    # 5.2 Debug: Mostrar suscribers de los artefactos
    async def _show_subscribers(artifact):
        print(f"\n--- Suscriptores en {artifact.name} ---")
        if hasattr(artifact, "subscribers"):
            print("Subscribers:", len(artifact.subscribers))
            print("Subscriber JIDs:", [str(jid) for jid in artifact.subscribers])
    await _show_subscribers(fridge)
    

    # 6. Ejecución infinita
    print("--- SISTEMA EN MARCHA (Presiona Ctrl+C para detener) ---")
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        def collect_known_beers():
            known = {}

            for beer in getattr(stocker, "spawned_beers", []):
                known[str(beer.jid)] = beer

            for beer in getattr(fridge, "beers", []):
                known[str(beer.jid)] = beer

            if getattr(waiter, "held_beer", None):
                known[str(waiter.held_beer.jid)] = waiter.held_beer

            if getattr(owner, "current_beer_obj", None):
                known[str(owner.current_beer_obj.jid)] = owner.current_beer_obj

            return known

        def print_beer_snapshot(title):
            print(f"\n--- {title} ---")
            known = collect_known_beers()
            if not known:
                print("No hay artefactos Beer conocidos en memoria.")
                return

            fridge_jids = {str(b.jid) for b in getattr(fridge, "beers", [])}
            held_jid = str(waiter.held_beer.jid) if getattr(waiter, "held_beer", None) else None
            owner_jid = str(owner.current_beer_obj.jid) if getattr(owner, "current_beer_obj", None) else None

            print(f"Total beers conocidas: {len(known)}")
            for jid in sorted(known.keys()):
                beer = known[jid]
                state = getattr(beer, "state", "unknown")
                if jid == owner_jid:
                    location = "owner"
                elif jid == held_jid:
                    location = "waiter"
                elif jid in fridge_jids:
                    location = "fridge"
                else:
                    location = "out_of_fridge"
                print(f"  - {jid}: state={state}, location={location}")

        async def stop_all_known_beers():
            known = collect_known_beers()
            if not known:
                return

            print("Parando artefactos Beer conocidos...")
            for jid in sorted(known.keys()):
                try:
                    await known[jid].stop()
                    print(f"  - stopped {jid}")
                except Exception as exc:
                    print(f"  - error stopping {jid}: {exc}")

        # 7. Parada y Limpieza
        print("\n--- DETENIENDO SISTEMA ---")

        # Paramos agentes primero
        await waiter.stop()
        await stocker.stop()
        await owner.stop()
        await market.stop()

        # Paramos el entorno
        # Paramos cervezas restantes de forma explicita
        await stop_all_known_beers()
        await table.stop()
        await fridge.stop()

        print_beer_snapshot("SNAPSHOT CERVEZAS")

        # 8. Mostrar creencias finales
        print("" + "="*40)
        print(" ESTADO FINAL DE LAS CREENCIAS BDI")
        print("="*40)
        print("** [OWNER]")
        owner.bdi.print_beliefs()
        print("** [WAITER]")
        waiter.bdi.print_beliefs()
        print("** [STOCKER]")
        stocker.bdi.print_beliefs()
        print("** [MARKET]")
        market.bdi.print_beliefs()
        print("="*40)
        print("Cierre finalizado.")

if __name__ == "__main__":
    spade.run(main())
