# ADR-0001: Arquitectura del Monorepo Siddur y Motor Litúrgico Embebido

**Status:** accepted  
**Deciders:** ElCuboNegro (Lead Architect)  
**Date:** 2026-10-04  

---

## Context and Problem Statement

El proyecto **Siddur** busca convertir el dispositivo de tinta electrónica **Xteink X4 Pro** (ESP32-S3) en un libro de rezos judío dinámico, inteligente (*time-aware*) y completamente offline. La arqueología y retroingeniería de los sistemas existentes ([CrossPoint Reader](https://github.com/crosspoint-reader/crosspoint-reader), [FreeInk SDK](https://github.com/Free-Ink/freeink-sdk), [libhdate](https://github.com/Boruch-Baum/libhdate) y `xtcloud.xteink.cc`) evidenció que:
1. El hardware Xteink X4 Pro está completamente soportado en hardware HAL (ESP32-S3, EPD 800×480, RTC BM8563 en I²C `0x51`, SDMMC nativo y touch GT911).
2. Sin embargo, no existe en el ecosistema e-reader abierto un motor embebido que vincule el reloj de tiempo real (RTC) con el calendario hebreo y los horarios halájicos (*Zmanim*) para resolver dinámicamente qué inserciones litúrgicas corresponden en cada momento (ej. *Mashiv HaRuaj*, *Tal UMatar*, *Al HaNisim*, *Yaalé VeYavó*, omisiones de *Tajanún*).
3. Los lectores convencionales carecen de soporte interactivo para textos litúrgicos interlineales y despliegue de traducciones/comentarios versículo a versículo mediante ventanas emergentes (modales).

Se requería definir la arquitectura de repositorio, el modelo de datos litúrgico y la estrategia de integración del firmware.

---

## Decision Drivers

- **Operación 100% Offline y Confiable:** El dispositivo debe calcular las fechas hebreas, zmanim e inserciones litúrgicas en Shabat y festividades sin ninguna conexión a Internet ni APIs externas, aprovechando el RTC BM8563 respaldado por batería.
- **Eficiencia y Huella de Memoria Embebida:** El código del motor astronómico y halájico debe ser C/C++ puro, sin dependencias pesadas de POSIX o bibliotecas de alto nivel, apto para ejecutarse en microcontroladores ESP32-S3.
- **Separación de Responsabilidades en Monorepo:** Centralizar firmware, corpus de contenido estructurado y herramientas auxiliares en un único repositorio con trazabilidad integral.
- **Tipografía Hebrea con Nikud y UX Táctil:** Resolver el renderizado de puntos vocálicos (*nikud*) y la interacción de selección/tap en frase para desplegar un modal contextual sin romper el flujo de lectura.

---

## Considered Options

- **Opción 1 (Arquitectura Multi-repositorio):** Mantener un repositorio para el firmware fork, otro para los textos litúrgicos y otro para scripts de conversión.
- **Opción 2 (Porte completo de HarfBuzz y KosherJava en Java/C#):** Integrar motores completos de shaping OpenType y wrappers pesados de calendarios.
- **Opción 3 (Monorepo Consolidado con Motor Embebido C/C++ y Esquema JSON Validado):**
  - **Monorepo:** Organización en `firmware/` (C/C++), `content/` (esquema JSON y textos validados) y `tools/` (validadores, suites matemáticas y empaquetadores).
  - **Motor C/C++ Embebido:** Algoritmos matemáticos derivados de `libhdate` (Meeus/NOAA y reglas talmúdicas de Molad) en `libhdate_core` y `HebrewCalendarEngine`.
  - **UI Modal:** `VerseModalActivity` montada sobre la pila de actividades (`ActivityManager`) de CrossPoint Reader.
  - **Nikud:** Tratamiento de marcas diacríticas como glifos de avance cero con alineación vertical sobre la consonante base.

---

## Decision Outcome

**Opción elegida:** **Opción 3**, porque proporciona el balance óptimo entre autonomía técnica, rendimiento en tiempo real en microcontrolador ESP32-S3, facilidad de prueba en CI/entorno local y simplicidad de mantenimiento.

### Estructura Arquitectónica del Monorepo

```
siddur/
├── content/               # Corpus litúrgico estructurado
│   ├── schema/            # JSON Schema formal (liturgical-text.json)
│   └── samples/           # Textos litúrgicos validados (Kiddush Shabbat, Shema, etc.)
├── firmware/              # Código fuente de firmware embebido C/C++
│   ├── zmanim/            # Motor de calendario hebreo, zmanim e inserciones (libhdate_core + HebrewCalendarEngine)
│   └── activities/        # Componentes de interfaz (VerseModalActivity)
├── tools/                 # Scripts auxiliares y validación
│   ├── content/           # Validador de esquemas (validate_schema.py)
│   └── zmanim/            # Suite de verificación matemática y astronómica (verify_engine.py)
├── input/                 # Fuentes legadas bajo auditoría arqueológica (cuarentena)
│   ├── crosspoint-reader/ # Firmware base open-source
│   └── libhdate/          # Algoritmos astronómicos de referencia
└── docs/                  # Documentación arquitectónica, PRD-Lite y hallazgos
    ├── adr/               # Architecture Decision Records
    ├── knowledge/         # Bitácora arqueológica (FINDINGS.md, learning_log.md)
    └── prd-lite.md        # Documento de requisitos confirmado (Catalyst)
```

### Consecuencias Positivas

1. **Cálculo Determinista de Zmanim:** Pruebas automatizadas validan que los horarios solares (Amanecer, Shemá, Tefilá, Jatzot, Puesta de sol, Anochecer) y las inserciones litúrgicas son exactos y ordenados monotónicamente.
2. **Contrato de Datos Estricto:** Cualquier adición al corpus de rezos se valida automáticamente contra `liturgical-text.json`, previniendo errores de formateo o pérdida de campos interlineales.
3. **UX Intuitiva:** El patrón de modal desacoplado permite tocar cualquier versículo y leer la traducción detallada, fonética y comentarios sin abandonar la página del libro de rezos.
4. **Cumplimiento de Gobernanza:** Respeta las reglas de Cornerstone (ADR-First, Gitflow, Semver, cuarentena de `input/` y registro de hallazgos).

### Consecuencias Negativas / Retos

- Requiere mantener la suite de pruebas cruzadas entre C++ y Python para garantizar consistencia entre las herramientas de escritorio y el binario final del firmware.

---

## Links

- [PRD-Lite: Siddur e-Ink](../prd-lite.md)
- [FINDINGS.md (F-001 a F-005)](../knowledge/FINDINGS.md)
- [CrossPoint Reader Archaeology Report](../knowledge/CROSSPOINT_ARCHAEOLOGY.md)
- [CrossPoint Reader Repository](https://github.com/crosspoint-reader/crosspoint-reader)
- [FreeInk SDK X4 Pro Support Guide](../../input/crosspoint-reader/freeink-sdk/docs/xteink-x4pro-support.md)
