import logging
logging.basicConfig(level=logging.INFO) #, format='%(asctime)s %(levelname)s %(name)s:%(lineno)d %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger('slixmpp').setLevel(logging.WARNING)


import random
import agentspeak
import asyncio
from abc import ABC, abstractmethod
from spade_bdi.bdi import BDIAgent
from spade_bdi.bdi_artifact import ArtifactBDIMixin
from artifacts import Fridge, Beer


# --- Base para agentes que usan la mesa ──────────────────────────────────────
class TableUserAgent(ArtifactBDIMixin, BDIAgent, ABC):
    def __init__(self, *args, table_jid: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.table_jid = table_jid
        self.table = None

    
    def controls(self, table):
        self.table = table

    async def setup(self):
        await super().setup()
        await self.artifacts.focus(self.table_jid, self.table_callback)

    @abstractmethod
    def table_callback(self, artifact_jid, state):
        """Handle table state updates. Implemented by concrete agents."""
        raise NotImplementedError()

    @abstractmethod
    def add_custom_actions(self, actions):
        pass


# ── Base para agentes que usan la nevera ──────────────────────────────────────
class FridgeUserAgent(ArtifactBDIMixin, BDIAgent, ABC):
    def __init__(self, *args, fridge_jid: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fridge_jid = fridge_jid
        self.fridge = None
        self._known_stock = None

    def fridge_callback(self, artifact_jid, state):
        # logger.info(f"[fridgeag] callback: from {artifact_jid}, state: {state}, id: {id(state)}, type: {type(state)}")
        # Ignore pubsub events if BDI internals are not ready or shutting down.
        if not getattr(self, "bdi", None) or not getattr(self.bdi.agent, "bdi_agent", None):
            print(f"[{self.name}] Callback received but BDI internals not ready. Ignoring.")
            return

        try:
            if state == "available":
                self.bdi.set_belief("available", "beer", "fridge")
            elif state == "empty":
                self.bdi.remove_belief("available", "beer", "fridge")
            elif state.startswith("stock:"):
                self._known_stock = int(state.split(":")[1])
                self.bdi.set_belief("stock", "beer", self._known_stock)
                #logger.debug(f"[fridgeag] payload from {artifact_jid}: {state}")
                #logger.debug(f"[fridgeag] id(payload): {id(state)}, type: {type(state)}")
                if self._known_stock > 0:
                     self.bdi.set_belief("available", "beer", "fridge")
                else:
                     self.bdi.remove_belief("available", "beer", "fridge")
        except AttributeError:
            # A shutdown race can null BDI internals between the guard and set/remove.
            return

    def controls(self, fridge: Fridge):
        self.fridge = fridge

    async def setup(self):
        await super().setup()
        await self.artifacts.focus(self.fridge_jid, self.fridge_callback)

    def _add_fridge_actions(self, actions):
        @actions.add(".open", 1)
        def _m_open(agent, term, intention):
            print(f"[{self.name}] opening fridge")
            self.fridge.open()
            yield
            
        @actions.add(".close", 1)
        def _m_close(agent, term, intention):
            print(f"[{self.name}] closing fridge")
            if self._known_stock is not None:
                self.bdi.remove_belief("stock", "beer", self._known_stock)
                self._known_stock = None
            yield

    @abstractmethod
    def add_custom_actions(self, actions):
        pass


# ── Agente Camarero (Waiter) ──────────────────────────────────────────────────
class WaiterAgent(FridgeUserAgent, TableUserAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = None
        self.held_beer = None 

    def table_callback(self, artifact_jid, state):
        """Waiter reacts to table state by updating local beliefs."""
        try:
            if state == "occupied":
                self.bdi.set_belief("table", "occupied")
            elif state == "empty":
                self.bdi.remove_belief("table", "occupied")
        except Exception:
            # ignore if BDI not ready
            pass

    def set_owner(self, owner):
        self.owner = owner

    def add_custom_actions(self, actions):
        self._add_fridge_actions(actions)

        @actions.add(".get", 1)
        def _m_get(agent, term, intention):
            self.held_beer = self.fridge.take()
            if self.held_beer:
                print(f"[{self.name}] taking {self.held_beer.name}")
                self.bdi.set_belief("holding", "beer")
            yield

        @actions.add(".hand_in", 1)
        def _m_hand_in(agent, term, intention):
            if self.held_beer:
                print(f"[{self.name}] giving beer to owner")
                # If a table is available, place the beer on it (fire-and-forget)
                if getattr(self, "table", None):
                    try:
                        asyncio.create_task(self.table.put_on(self.held_beer))
                    except Exception:
                        pass
                # Notify owner as before
                # self.owner.receive_beer(self.held_beer)
                self.held_beer = None
                self.bdi.remove_belief("holding", "beer")
            yield

        @actions.add(".move_towards", 1)
        def _m_move_towards(agent, term, intention):
            args = agentspeak.grounded(term.args, intention.scope)
            print(f"[{self.name}] moving towards {args[0]}...")
            self.bdi.set_belief("at", "robot", args[0])
            yield


# ── Agente Reponedor (Stocker) ────────────────────────────────────────────────
class StockerAgent(FridgeUserAgent):
    _beer_serial = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spawned_beers = []

    def add_custom_actions(self, actions):
        self._add_fridge_actions(actions)

        @actions.add(".restock", 1)
        def _m_restock(agent, term, intention):
            args = agentspeak.grounded(term.args, intention.scope)
            qty = int(args[0])
            asyncio.create_task(self._do_physical_restock(qty))
            yield

    async def _do_physical_restock(self, qty):
        new_beers = []
        for _ in range(qty):
            jid = f"beer_{StockerAgent._beer_serial}@localhost"
            print(f"[{self.name}] preparing {jid}...")
            b = Beer(jid, "1234")
            await b.start() 
            new_beers.append(b)
            self.spawned_beers.append(b)
            StockerAgent._beer_serial += 1
        
        print(f"[{self.name}] all beers ready. Putting in fridge.")
        self.fridge.restock(new_beers)



# ── Agente Dueño (Owner) ──────────────────────────────────────────────────────
class OwnerAgent(TableUserAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_beer_obj = None
        self.current_beer_jid = None

    def table_callback(self, artifact_jid, state):
        """Owner reacts to table state by updating own beliefs and
        attempting to take the beer from the table (simple, no races).
        """
        print("[owner] table callback: state=", state)
        try:
            if state == "occupied":
                self.bdi.set_belief("table", "occupied")
                # If owner has no beer, try to take from table asynchronously
                if getattr(self, "current_beer_obj", None) is None and getattr(self, "table", None):
                    async def _take_and_receive():
                        try:
                            beer = await self.table.take_off()
                            if beer:
                                # hand it to owner logic
                                self.receive_beer(beer)
                        except Exception:
                            pass

                    asyncio.create_task(_take_and_receive())
            elif state == "empty":
                self.bdi.remove_belief("table", "occupied")
        except Exception:
            # defensive: BDI internals may be shutting down
            pass

    def beer_callback(self, artifact_jid, state):
        if state == "empty":
            print(f"[{self.name}] detected empty beer")
            # Owner removes its own beliefs when the beer becomes empty
            try:
                self.bdi.remove_belief("has", "owner", "beer")
                self.bdi.remove_belief("focused", "beer")
            except Exception:
                # BDI internals may be shutting down
                pass
            self.current_beer_obj = None
            self.current_beer_jid = None

    def receive_beer(self, beer_obj):
        self.current_beer_obj = beer_obj
        self.current_beer_jid = str(beer_obj.jid)
        asyncio.create_task(self.artifacts.focus(self.current_beer_jid, self.beer_callback))
      # Owner sets its own belief that it has a beer
        try:
            self.bdi.set_belief("has", "owner", "beer")
        except Exception:
            # BDI may not be ready yet; belief will be set when focus completes
            pass
        print(f"[{self.name}] ready to sip.")
        # self.bdi.set_belief("focused", "beer")

    def add_custom_actions(self, actions):
        @actions.add(".sip", 1)
        def _m_sip(agent, term, intention):
            if self.current_beer_obj:
                self.current_beer_obj.sip()
            yield

        @actions.add(".take", 0)
        def _m_take(agent, term, intention):
            if self.table:
                async def _do_take():
                    try:
                        beer = await self.table.take_off()
                        if beer:
                            self.receive_beer(beer)
                    except Exception:
                        pass

                try:
                    asyncio.create_task(_do_take())
                except Exception:
                    pass
            yield


# ── Agente Supermercado (Market) ──────────────────────────────────────────────
class MarketAgent(BDIAgent):
    def add_custom_actions(self, actions):
        @actions.add(".deliver", 2)
        def _m_deliver(agent, term, intention):
            args = agentspeak.grounded(term.args, intention.scope)
            print(f"[{self.name}] delivering {args[1]} {args[0]}...")
            yield
