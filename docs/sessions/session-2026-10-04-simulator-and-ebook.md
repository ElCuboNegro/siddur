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
