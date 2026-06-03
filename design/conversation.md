# Historial de Conversación: Integración de spade_artifact y spade_bdi

Este documento registra detalladamente la discusión, decisiones de diseño y acciones tomadas durante la sesión del 22 de mayo de 2026 para la extensión de `spade_artifact` y su futura integración con `spade_bdi`.

---

## 1. Contexto Inicial y Rama Activa
* **Pregunta:** Cuando este proyecto está añadido con `uv add --editable` en otro repositorio, ¿qué rama tiene activa por defecto y se está usando actualmente?
* **Respuesta:**
  Al usar `--editable`, `uv` crea un enlace directo (a través de un archivo `.site-packages` o enlace simbólico) al directorio local de desarrollo del proyecto. Por tanto, la rama y el código que se están ejecutando en los proyectos dependientes son siempre los que estén activos en ese momento en `/Users/mrebollo/devel/spade_artifact`.
  En ese momento, la rama activa por defecto en el repositorio local era `master`.
* **Identificación de repositorios dependientes:** Se detectaron referencias en `spade413` y `spd`.

---

## 2. Creación de Rama de Funcionalidad (`feat/operations`)
* El usuario consultó sobre la implicación de nombrar una rama como `feat/operations` (si es una carpeta o solo una marca en el nombre).
* **Concepto:** En Git, los nombres de rama con barra `/` no son carpetas reales en el espacio de trabajo, sino referencias jerárquicas dentro de `.git/refs/heads/`. Esto ayuda a que los clientes visuales de Git (como VS Code, GitKraken o Sourcetree) agrupen las ramas bajo directorios visuales para mantener un orden organizativo.
* **Acción:** Se creó la rama `feat/operations` partiendo de `master`.

---

## 3. Integración de `spade_artifact_ext` (Copiado Limpio)
El usuario tenía desarrollos de operaciones y directorios en el repositorio `/Users/mrebollo/devel/ain25-26/spade_artifact_ext`.
Para traerlos a este repositorio sin alterar el núcleo existente:
* Se copiaron los archivos de código (`artifact_ext.py`, ejemplos en `examples/examples_operations/` y documentación en `design/`).
* **Resolución de Importaciones Circulares (Muy Importante):**
  Originalmente, `artifact_ext.py` importaba componentes usando:
  ```python
  from spade_artifact import Artifact, ArtifactMixin
  ```
  Al integrarlo dentro de `spade_artifact`, si el archivo `__init__.py` del paquete raíz intenta importar de `artifact_ext` y este a su vez importa de la raíz `spade_artifact`, se produce un error de importación circular en Python.
  **Solución implementada:** Se cambiaron las importaciones en `spade_artifact/artifact_ext.py` a importaciones relativas locales:
  ```python
  from .artifact import Artifact
  from .agent import ArtifactMixin
  ```
* Se actualizaron las exportaciones en `spade_artifact/spade_artifact/__init__.py` para incluir todos los elementos de la extensión:
  ```python
  from .artifact import Artifact
  from .agent import ArtifactMixin
  from .artifact_ext import (
      operation,
      OperableArtifact,
      ArtifactActuatorMixin,
      AgentDirectoryMixin,
      DirectoryArtifact,
  )
  ```
* Se eliminó el archivo `__init__.py` sobrante y huérfano que había quedado en la raíz del proyecto.
* Se verificó que el repositorio quedara limpio de modificaciones intrusivas y que todo funcionara correctamente.

---

## 4. Diseño de la Integración con `spade_bdi`
El objetivo final es poder usar los artefactos de forma nativa desde las reglas en AgentSpeak (como en JaCaMo/CArtAgO), en lugar de usar acciones internas verbosas.

### Análisis de Alternativas:
1. **`python-agentspeak`**: Es el motor BDI e intérprete puro de AgentSpeak. No debe contener ninguna referencia a XMPP, red o SPADE para mantener su generalidad.
2. **`spade_bdi`**: Es el pegamento perfecto. Une el motor BDI puro con SPADE, por lo que es el lugar idóneo para mapear artefactos a creencias y acciones.

### Propuesta del Mixin (`ArtifactBDIMixin`):
Para evitar estropear cosas en `spade_bdi` (que es un proyecto activo), se propuso encapsular toda la lógica de integración en un Mixin independiente que se ubicará en `spade_bdi/spade_bdi/artifact_integration.py`. Así, la compatibilidad con el resto del framework es del 100% y el archivo central `bdi.py` no sufre cambios disruptivos.

El plan incremental estructurado consta de tres fases:
1. **Fase 1 (Creencias):** Mapear de forma automática las notificaciones de PubSub de los artefactos enfocados en creencias de AgentSpeak (usando trigger de adición/remoción en el ciclo de razonamiento BDI).
2. **Fase 2 (Acción Genérica `.use`):** Definir una acción interna `.use(jid, operacion, args)` en AgentSpeak para interactuar con los artefactos de forma explícita.
3. **Fase 3 (Acciones Dinámicas):** Registrar de forma dinámica las operaciones de los artefactos enfocados como acciones internas disponibles en el agente BDI (estilo JaCaMo, donde se llama directamente a `unlock;` o `open;` en el `.asl` sin necesidad de envolverlo en un `.use`).

---

## 5. Preparación de la Rama en `spade_bdi`
* Se comprobó el estado de `spade_bdi`.
* Se cambió la rama activa a **`feat/bdi_artifacts`** partiendo del commit de la versión estable de `master`.
* Se creó la carpeta `design/` en `spade_bdi` para albergar este histórico y el plan de acción asociado.
