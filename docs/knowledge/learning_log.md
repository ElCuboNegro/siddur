# Log de Aprendizaje

Historial cronológico de lecciones aprendidas, patrones reutilizables y consolidación de conocimientos.

---

## [2026-06-03] Inicialización: Repositorio Inicializado con Cornerstone
- **Trigger**: Generación o sincronización inicial de este proyecto utilizando la CLI de Cornerstone.
- **Acción Tomada**: Configuración del scaffolding básico e integración del protocolo de aprendizaje general.
- **Impacto**: El repositorio ahora cuenta con capacidades unificadas de trazabilidad de hallazgos y auto-documentación para los agentes en cada sesión de desarrollo.

## [2026-10-04] Arqueología de Firmware: Xteink X4 Pro & FreeInk SDK
- **Trigger**: Excavación y retroingeniería de `input/crosspoint-reader` y `freeink-sdk` para validar soporte de hardware de Xteink X4 Pro.
- **Acción Tomada**: Análisis del árbol de llamadas, documentación técnica `xteink-x4pro-support.md` y perfil `[env:x4pro]`. Se documentó el hallazgo F-003 en `FINDINGS.md`.
- **Impacto**: Se confirmó que el hardware (ESP32-S3, 800×480 EPD, touch GT911, RTC BM8563, SDMMC, CW2017) está 100% caracterizado y soportado. El proyecto puede enfocarse directamente en el motor litúrgico de Zmanim en C++, tipografía hebrea con Nikud y la UI de interacción versículo/modal sin bloqueos de controladores de hardware.

## [2026-10-04] Simulación de Escritorio y Preservación de Capacidades E-Reader
- **Trigger**: Requerimiento de integración del simulador oficial `crosspoint-simulator` y preservación íntegra de capacidades e-reader universales.
- **Acción Tomada**: Análisis de la arquitectura del simulador (`crosspoint-simulator`), evaluación del desacoplamiento HAL vs App, y definición de la coexistencia de `SiddurActivity` con los lectores nativos de EPUB, TXT y XTC. Se documentó el hallazgo F-006 y se redactó el ADR-0002.
- **Impacto**: El dispositivo mantiene el 100% de sus funcionalidades como lector de libros electrónicos universal, incorporando el portal litúrgico como una capacidad superior sin canibalizar el ecosistema de lectura general.


