# Sesión: 2026-10-04 — Scaffold del Monorepo, PRD-Lite, Motor Zmanim Embebido y Esquema Litúrgico

- **Fecha:** 2026-10-04
- **Objetivo:** Inicialización de arquitectura Monorepo para Siddur e-ink en Xteink X4 Pro, redacción del PRD-Lite, implementación y verificación de algoritmos astronómicos de Zmanim en C/C++, y definición del esquema JSON para textos litúrgicos con Nikud y modales interactivos.
- **Repositorio:** `ElCuboNegro/siddur` (Personal)
- **Branch:** `feature/init-monorepo-and-prd` -> `staging` (Commit `8f56b01`)

## Resumen de Acciones y Decisiones
1. **Definición de Requerimientos y PRD-Lite:**
   - Formalización de especificaciones en `docs/prd-lite.md` cubriendo hardware (ESP32-S3, 800×480 EPD, RTC BM8563, Touch GT911), necesidades litúrgicas, Zmanim dinámicos y experiencia de usuario.
2. **Arquitectura Monorepo y ADR-0001:**
   - Creación y adopción de `ADR-0001-arquitectura-del-monorepo-siddur-y-motor-lit-rgico-embebido.md`.
   - Estructuración de carpetas: `firmware/` (C/C++), `content/` (JSON de rezos y esquemas), `tools/` (validadores y pruebas).
3. **Motor Litúrgico y Zmanim Embebido (`firmware/zmanim`):**
   - Adaptación de algoritmos Meeus/NOAA y calendario hebreo (`libhdate_core.c` / `.h`) sin dependencias POSIX.
   - Implementación de la clase `HebrewCalendarEngine` para cómputo de Zmanim solares (Alot HaShajar, Netzarim, Shema, Tefilá, Jatzot, Minjá, Shkiá, Tzeit) e inserciones litúrgicas (*Mashiv HaRuach*, *Morid HaTal*, *Tal UMatar*, *Al HaNissim*, *Yaaleh VeYavo*, omisión de *Tachanun*).
   - Verificación con suite de pruebas: `tools/zmanim/verify_engine.py` y `tests/test_zmanim_engine.cpp` (100% aprobado).
4. **Esquema de Contenido y Modales:**
   - Diseño de `content/schema/liturgical-text.json` soportando versículos en hebreo con nikud, traducción frase a frase, notas y reglas de inserción.
   - Muestras validadas: `kiddush_shabbat.json` y `shema_yisrael.json`.
   - Implementación del presentador de modales `VerseModalActivity.cpp` / `.h` con word-wrap y paginación en pantalla 800×480.
5. **Hallazgos Arqueológicos:**
   - Registro de F-001 a F-005 en `docs/knowledge/FINDINGS.md`.
