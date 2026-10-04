# ADR-0003: Conciencia de Ubicación Geográfica, Perfiles Halájicos y Reglas de la Diáspora

**Status:** accepted  
**Deciders:** ElCuboNegro (Lead Architect)  
**Date:** 2026-10-04  

---

## Context and Problem Statement

El cómputo de los tiempos litúrgicos (*Zmanim*) y las variantes de las plegarias en la ley judía (*Halajá*) dependen críticamente de la ubicación geográfica exacta (latitud, longitud, zona horaria, elevación) y de la condición territorial (*Eretz Yisrael* vs. *Jutz LaAretz* / Diáspora).

El sistema del usuario y su comunidad de referencia operan en la **Diáspora** (específicamente Colombia, zona horaria UTC-05:00). Existen diferencias litúrgicas obligatorias:
1. **Petición de Rocío y Lluvia (*Tal UMatar / Barej Aleinu*):** En la Diáspora se inicia en la noche del 4 de diciembre (o 5 de diciembre en el año previo a un bisiesto civil), mientras que en Israel comienza el 7 de Jeshván.
2. **Segundo Día de Festividades (*Yom Tov Sheni shel Galuyot*):** En la Diáspora se celebran dos días para las festividades mayores bíblicas (Pésaj, Shavuot, Sucot, Sheminí Atzéret / Simjat Torá).
3. **Encendido de Velas (*Hadlakat Nerot*):** La costumbre estándar en la Diáspora es de 18 minutos antes de la puesta del sol (a diferencia de Jerusalén con 40 minutos).

No contar con perfiles de ubicación explícitos o asumir una ubicación fija (como Jerusalén) produce cálculos inválidos para el rezo cotidiano del usuario.

---

## Decision Drivers

- **Exactitud Halájica:** Los rezos sugeridos y las bendiciones de la *Amidá* deben concordar al 100% con la fecha, hora y ubicación en la que se encuentra el usuario.
- **Configuración Autónoma Offline:** El dispositivo e-ink Xteink X4 Pro debe operar 100% sin conexión a internet, almacenando perfiles de ciudades precargadas y permitiendo el ingreso manual de coordenadas GPS en memoria no volátil (NVS).
- **Adaptación a Comunidades Hispanohablantes:** Brindar soporte prioritario a las principales comunidades de la Diáspora en Latinoamérica (Bogotá, Medellín, Cali, Barranquilla, CDMX, Buenos Aires, Santiago, Panamá, Caracas) y Norteamérica (Miami, Nueva York).

---

## Considered Options

- **Opción 1: Coordenadas y Reglas Hardcodeadas a Jerusalén.** (Rechazada: arroja Zmanim desfasados por 7 horas para un usuario en América Latina e inserta *Tal UMatar* prematuramente).
- **Opción 2: Solo Coordenadas GPS Numéricas sin Lógica de Diáspora.** (Rechazada: ignora las diferencias halájicas de festividades e inserciones estacionales entre Israel y el resto del mundo).
- **Opción 3: Módulo Desacoplado `LocationProfile` con Preajustes y Selector de Territorio.**
  - Crear `firmware/zmanim/LocationProfile.h` y `.cpp`.
  - Definir perfil por defecto en **Bogotá, Colombia** (`Lat: 4.7110° N`, `Lon: -74.0721° W`, `UTC: -5.0`, `isIsrael: false`, elevación: 2600m).
  - Incluir catálogo de ciudades de la Diáspora e Israel.
  - Implementar en `HebrewCalendarEngine` el cómputo astronómico solar local y las bifurcaciones halájicas (*Tal UMatar* el 4 de diciembre en Diáspora vs 7 de Jeshván en Israel).

---

## Decision Outcome

**Opción elegida:** **Opción 3**, garantizando cumplimiento halájico riguroso y una experiencia inmediata y precisa para el usuario.

### Consecuencias Positivas

- **Precisión Solar en Tiempo Real:** El usuario en Bogotá u otra ciudad de la Diáspora recibe los Zmanim exactos (Alot 04:41 AM, Netz 05:42 AM, Sof Zman Tefilá 09:44 AM, Shkiá 17:46 PM).
- **Transición Dinámica sin Errores:** La *Amidá* cambia automáticamente entre *Morid HaTal* y *Mashiv HaRuaj*, y no agrega *Tal UMatar* hasta el 4 de diciembre en la Diáspora.
- **Validación Automatizada:** Suite de pruebas en C++ (`tests/test_zmanim_engine.cpp`) y Python (`tools/zmanim/verify_engine.py`) que auditan activamente la consistencia de Diáspora vs. Israel.

---

## Links

- [ADR-0001: Arquitectura del Monorepo Siddur y Motor Litúrgico Embebido](ADR-0001-arquitectura-del-monorepo-siddur-y-motor-lit-rgico-embebido.md)
- [ADR-0002: Integración del Simulador de Escritorio y Preservación de Capacidades E-Reader Universales](ADR-0002-integraci-n-del-simulador-de-escritorio-y-preservaci-n-de-capacidades-e-reader-universales.md)
- [FINDINGS.md](../knowledge/FINDINGS.md)
