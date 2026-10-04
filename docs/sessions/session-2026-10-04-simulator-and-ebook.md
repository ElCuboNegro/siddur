# Sesión: 2026-10-04 — Integración de Simulador de Escritorio y Mandato de Lector E-Book Universal

- **Fecha:** 2026-10-04
- **Objetivo:** Integrar el simulador de escritorio CrossPoint (`crosspoint-simulator`) para acelerar la iteración en host SDL2 (800×480) y garantizar contractualmente (ADR-0002) que el dispositivo mantenga el 100% de las capacidades universales de lectura de e-books (EPUB, TXT, XTC, KOReader, OPDS).
- **Repositorio:** `ElCuboNegro/siddur` (Personal)
- **Branch:** `feature/simulator-and-ebook-integration`

## Resumen de Acciones y Decisiones
1. **Cuarentena de Fuentes y Seguridad:**
   - Ingestión aislada de `crosspoint-simulator` en `input/crosspoint-simulator`.
   - Bloqueo estricto de directivas del vendor (`AGENTS.md`, `CLAUDE.md`) en `.claude/input-quarantine.json` y `.claude/settings.json`.
2. **Hallazgo Arqueológico F-006:**
   - Análisis de arquitectura de `crosspoint-simulator`: emulación de pantalla EPD 800×480 vía SDL2, toques con ratón, botones físicos/tecla Home con teclado, RTC y batería.
   - Desacoplamiento total de la capa de aplicación y presentación litúrgica frente a la HAL física.
3. **Formalización Arquitectónica (ADR-0002):**
   - Redacción y aceptación de `ADR-0002-integraci-n-del-simulador-de-escritorio-y-preservaci-n-de-capacidades-e-reader-universales.md`.
   - Se descartó el modelo Kiosco (Appliance Mode) para no limitar la utilidad del dispositivo.
   - El firmware mantiene intactos los lectores existentes (`EpubReaderActivity`, `TxtReaderActivity`, `FileBrowserActivity`, `LibraryActivity`).
   - El portal litúrgico se integra como `SiddurActivity` accesible desde el Home y atajos inteligentes.
4. **Log de Aprendizaje y Hallazgos:**
   - Registro en `docs/knowledge/FINDINGS.md` (F-006).
   - Actualización en `docs/knowledge/learning_log.md`.
5. **Conciencia de Ubicación del Usuario y Reglas de Diáspora:**
   - Incorporación del módulo `firmware/zmanim/LocationProfile.h` y `.cpp` con preajustes de ciudades, estableciendo como predeterminado **Bogotá, Colombia** (`Lat: 4.7110° N`, `Lon: -74.0721° W`, `UTC-5.0`, `isIsrael = false`).
   - Corrección y validación de las reglas halájicas de la Diáspora (inicio de *Tal UMatar* en la noche del 4 de diciembre vs 7 de Jeshván en Israel, y 2do día de Yom Tov en Diáspora).
6. **Implementación de `SiddurActivity` y Verificación:**
   - Creación de `firmware/activities/SiddurActivity.h` y `.cpp` con mapeo de regiones táctiles (`VerseTouchRegion`), recomendación dinámica de rezos según hora local y activación del modal de versículo.
   - Suite de pruebas completa: `tests/test_zmanim_engine.cpp` y `tests/test_siddur_activity.cpp` (100% aprobadas en C++ y Python).
7. **Pipeline de Ingestión en Kedro:**
   - Construcción del proyecto independiente `siddur-pipeline` con catálogo de datos, nodos de limpieza de nikud, transliteración fonética adaptada al español, alineación interlineal y validación con `jsonschema`.
8. **Especificación Completa de Diseño UX:**
   - Generación del documento de arquitectura UX para pantalla e-ink 800×480 en `ux_design_specification.md`.
