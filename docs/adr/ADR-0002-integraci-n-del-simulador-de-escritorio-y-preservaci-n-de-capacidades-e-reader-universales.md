# ADR-0002: Integración del Simulador de Escritorio y Preservación de Capacidades E-Reader Universales

**Status:** accepted  
**Deciders:** ElCuboNegro (Lead Architect)  
**Date:** 2026-10-04  

---

## Context and Problem Statement

El desarrollo del proyecto **Siddur** requiere validar y depurar frecuentemente el renderizado tipográfico con *nikud*, la alineación interlineal en español y la interacción táctil con versículos para desplegar modales explicativos. Depender exclusivamente de flashear el microcontrolador físico (ESP32-S3 en el Xteink X4 Pro) a través de USB ralentiza el ciclo de desarrollo (*inner loop*).

Asimismo, surgió la directiva fundamental de producto: **el dispositivo debe preservar íntegramente sus capacidades para leer cualquier tipo de libro electrónico** (EPUB 2/3, TXT, XTC, cómics, etc.) y no convertirse en un dispositivo cerrado o bloqueado (*single-purpose kiosk*).

Se evaluó la integración del simulador oficial de escritorio [CrossPoint Simulator](https://github.com/crosspoint-reader/crosspoint-simulator) y la coexistencia arquitectónica entre el lector de libros general y el portal litúrgico de Siddur.

---

## Decision Drivers

- **Velocidad de Iteración (Inner Loop):** Poder compilar, ejecutar y verificar el comportamiento visual e interactivo del lector en la máquina host (Linux/WSL/macOS) en una ventana gráfica SDL2 nativa de 800×480 píxeles, con emulación de toques, gestos, botones físicos y RTC.
- **Lector de Libros Electrónicos Universal:** No eliminar ni degradar el soporte nativo de CrossPoint Reader para formatos de libros estándar (`.epub`, `.txt`, `.xtc`), gestión de biblioteca (`LibraryActivity`), explorador de archivos (`FileBrowserActivity`), sincronización KOReader y catálogos OPDS.
- **Arquitectura No Invasiva:** El motor litúrgico (`HebrewCalendarEngine`), el esquema de datos (`liturgical-text.json`) y la actividad modal (`VerseModalActivity`) deben desacoplarse del hardware subyacente de forma que compilen tanto en el hardware real (`[env:x4pro]`) como en el simulador de escritorio (`[env:simulator_x4_pro]`).

---

## Considered Options

- **Opción 1: Kiosco Litúrgico Dedicado (Appliance Mode).** Eliminar la biblioteca de libros generales, el explorador y la sincronización, dedicando el dispositivo únicamente a rezos. (Rechazada: limita severamente la utilidad del dispositivo e incumple el mandato del usuario).
- **Opción 2: Solo Libros EPUB Estándar para Liturgia.** Compilar los rezos como archivos `.epub` regulares sin lógica embebida ni interactividad. (Rechazada: no permite el dinamismo *time-aware* de festividades y zmanim, ni la UX fluida de modal al pulsar versículos).
- **Opción 3: Arquitectura de Doble Propósito con Soporte de Simulador SDL2.**
  - **Soporte de Simulador:** Integrar `crosspoint-simulator` mediante la variable `-DSIMULATOR_DEVICE_X4_PRO` para emular pantalla, touch GT911, botones y RTC en escritorio.
  - **Lector Universal Completo:** Conservar todos los componentes de lectura existentes (`EpubReaderActivity`, `TxtReaderActivity`, `XtcReaderActivity`, `FileBrowserActivity`, `LibraryActivity`, `KOReaderSyncActivity`).
  - **Portal Litúrgico Siddur:** Añadir `SiddurActivity` como módulo especializado accesible desde la pantalla principal (`HomeActivity`), permitiendo cargar automáticamente la plegaria del momento según el reloj/zmanim o navegar cualquier libro litúrgico de la biblioteca, manteniendo simultáneamente la capacidad de abrir cualquier libro general.

---

## Decision Outcome

**Opción elegida:** **Opción 3**, porque proporciona una experiencia de usuario integral (lector de libros de propósito general + libro de rezos inteligente) y dota al equipo de un entorno de simulación rápida en escritorio.

### Puntos de Integración en el Sistema

1. **Simulador de Escritorio (`crosspoint-simulator`):**
   - Configuración en PlatformIO con entorno `[env:simulator_x4_pro]`.
   - Se compila de forma nativa contra SDL2 en la máquina anfitriona.
   - Emula la geometría de 800×480 del Xteink X4 Pro, mapeando clics del ratón a eventos táctiles y pulsaciones de teclado a los botones Left (GPIO0), Right (GPIO7), Power (GPIO3) y tecla Home.
2. **Coexistencia en la Interfaz (`HomeActivity`):**
   - La pantalla principal mantiene el carrusel de libros recientes, explorador de archivos, biblioteca y configuración.
   - Se añade un punto de acceso directo (*Siddur / Rezo del Día*) que consulta el `HebrewCalendarEngine` para sugerir y abrir la plegaria actual en menos de 15 segundos.
3. **Compatibilidad de Formatos:**
   - La tarjeta SD puede albergar carpetas con libros literarios generales (`/books/*.epub`, `/books/*.txt`) junto con el corpus litúrgico estructurado (`/siddur/*.json` o `/siddur/*.epub`).
   - El motor de lectura detecta el tipo de contenido y despacha la actividad adecuada.

### Consecuencias Positivas

- **Cero Regresiones:** El usuario puede llevar toda su biblioteca literaria, novelas, ensayos y textos de estudio además de los textos litúrgicos.
- **Desarrollo Acelerado:** Todo el flujo de navegación, selección de versículos y despliegue del modal de traducción puede probarse localmente en segundos con `run_simulator.py` sin cables ni flasheos continuos.
- **Alta Flexibilidad:** La liturgia puede consumirse de manera asistida (*time-aware*) o como lectura regular por capítulos.

---

## Links

- [CrossPoint Simulator Repository](https://github.com/crosspoint-reader/crosspoint-simulator)
- [CrossPoint Reader Repository](https://github.com/crosspoint-reader/crosspoint-reader)
- [ADR-0001: Arquitectura del Monorepo Siddur y Motor Litúrgico Embebido](ADR-0001-arquitectura-del-monorepo-siddur-y-motor-lit-rgico-embebido.md)
- [FINDINGS.md (F-006)](../knowledge/FINDINGS.md#L62)
- [PRD-Lite: Siddur e-Ink](../prd-lite.md)
