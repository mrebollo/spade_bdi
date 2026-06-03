# Plan de Acción: Integración SPADE BDI + SPADE Artifact

Este documento detalla el plan de diseño e implementación incremental para conectar el motor BDI (`spade_bdi` / `python-agentspeak`) con el framework de artefactos (`spade_artifact`).

---

## 🎯 Objetivo General
Permitir que un agente BDI observe propiedades de un artefacto como creencias automáticas en su base de conocimiento y ejecute operaciones de artefactos como acciones nativas del plan de AgentSpeak (al estilo de **JaCaMo / CArtAgO**).

---

## 🧩 Patrón de Diseño: `ArtifactBDIMixin`
Para garantizar una retrocompatibilidad y estabilidad del 100% sobre el núcleo activo de `spade_bdi` (`bdi.py`), implementaremos toda la lógica de integración dentro de un **Mixin independiente** ubicado en un nuevo archivo:
`spade_bdi/spade_bdi/bdi_artifact.py`

Cualquier agente BDI que requiera usar artefactos heredará de este Mixin:
```python
from spade_bdi.bdi import BDIAgent
from spade_bdi.bdi_artifact import ArtifactBDIMixin

class MiAgenteBDI(ArtifactBDIMixin, BDIAgent):
    # setup() y comportamiento heredados y enriquecidos automáticamente
```

---

## 🗺️ Plan de Implementación por Fases

### 🚀 Fase 1: El Puente de Creencias (Observación)
* **Meta:** Traducir eventos de publicación de propiedades del artefacto (PubSub) en creencias del motor BDI de forma automática.
* **Detalles Técnicos:**
  1. El `ArtifactBDIMixin` interceptará la llamada a `focus(jid, callback)`.
  2. Registrará un callback por defecto que recibe los payloads de estado del artefacto.
  3. Traducirá el payload en creencias estructuradas para el motor `python-agentspeak`.
     * **Texto Plano / Literal:** Si el payload es una cadena (ej. `temperatura(22)`), se parseará y se añadirá usando `self.bdi.set_belief("temperatura", 22)`.
     * **JSON:** Si es un diccionario JSON (ej. `{"status": "locked"}`), se inyectará como `self.bdi.set_belief("status", "locked")`.
  4. Al cambiar el estado en el artefacto, el mixin llamará a `self.bdi.remove_belief` de la propiedad anterior y añadirá la nueva, disparando los eventos nativos de adición/remoción en el `.asl` (`+temperatura(X)` o `-temperatura(X)`).

### 🛠️ Fase 2: Acción Interna `.use` (Actuación Explícita)
* **Meta:** Proveer una acción interna en AgentSpeak (`.use`) para invocar operaciones en artefactos específicos.
* **Detalles Técnicos:**
  1. Registrar una acción interna en la tabla de acciones del agente BDI durante la inicialización del mixin:
     ```python
     @self.bdi_actions.add(".use", 2)  # .use(jid_del_artefacto, nombre_operacion)
     def _use_op(agent, term, intention):
         # 1. Obtener los argumentos unificados
         jid = grounded(term.args[0])
         op = grounded(term.args[1])
         # 2. Despachar la tarea asíncrona hacia el artefacto
         asyncio.create_task(agent.artifacts.use(jid, op))
         yield
     ```
  2. Ampliar el registro para soportar argumentos dinámicos (ej: `.use(jid, op, arg1, arg2, ...)`).

### 🧙‍♂️ Fase 3: Acciones Dinámicas Nativas (Estilo JaCaMo Completo)
* **Meta:** Permitir que los planes de AgentSpeak llamen a operaciones directamente como acciones nativas (ej. `unlock;` u `open;` en lugar de `.use(...)`).
* **Detalles Técnicos:**
  1. Cuando el agente se conecta al directorio (`connect_directory`) y enfoca artefactos, el mixin lee del caché del directorio qué operaciones expone cada artefacto.
  2. Registra dinámicamente cada operación en la tabla de acciones (`self.bdi_actions`) de forma automatizada en tiempo de ejecución.
  3. Al procesar una acción nativa en el plan (como `unlock;`), el motor resolverá que el agente tiene un enfoque sobre el artefacto que provee la capacidad y ejecutará el `use()` de forma transparente.

---

## 🧪 Estrategia de Pruebas
1. **Test de Creencias (Fase 1):** Crear un artefacto simple de contador y un agente BDI. El agente enfoca el contador. Al incrementarse el contador, verificar que en el plan de AgentSpeak se gatilla una regla `+count(X)` de manera automática.
2. **Test de Acción (Fase 2):** Verificar que un plan del agente que ejecuta `.use` interactúa y modifica de manera efectiva el estado del artefacto remoto.
