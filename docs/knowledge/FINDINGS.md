# Findings Ledger

Registro acumulativo de hallazgos de investigación, auditorías, descubrimientos técnicos y decisiones operativas de este proyecto.
Cada entrada sigue el protocolo de aprendizaje: Hallazgo → FINDINGS.md → learning_log.md → ADR (si aplica).

## Plantilla para nuevos Hallazgos:
Use este bloque para nuevos hallazgos:
```
### F-XXX: [Título Corto del Hallazgo]
- **Fecha**: YYYY-MM-DD
- **Contexto**: [Archivo/Módulo/Path afectado o estudiado]
- **Hallazgo**: [¿Qué se descubrió o resolvió?]
- **Implicación**: [¿Por qué es importante? ¿Requiere un ADR?]
```

---

### F-001: Arquitectura del ecosistema Xteink Cloud (xtcloud.xteink.cc) y XTEINKBridge
- **Fecha**: 2026-10-04
- **Contexto**: `https://xtcloud.xteink.cc/app`, WebViews y puente nativo
- **Hallazgo**: La plataforma cloud de Xteink (`xtcloud.xteink.cc`) es una SPA en Vue 3 con integración nativa a través del objeto `window.XTEINKBridge` (con fallback a `window.webkit.messageHandlers.xtApp`, `ReactNativeWebView` o `window.Android`). Expone rutas para firmware flashing (`/app/firmware-flash`), actualizaciones de firmware (`/firmware-updates`), gestión de tareas en la nube, visor OPDS, creadores de libros/imágenes, y generador de fuentes personalizadas (`xtFontMaker`, `systemFontMaker`).
- **Implicación**: Permite comprender los contratos de datos entre la nube/app compañera y el dispositivo Xteink X4 Pro, incluyendo el protocolo de flasheo web y las herramientas auxiliares para e-ink.

### F-002: CrossPoint Reader como base de firmware open source para Xteink X4 Pro
- **Fecha**: 2026-10-04
- **Contexto**: `https://crosspointreader.com`, `https://github.com/crosspoint-reader/crosspoint-reader`
- **Hallazgo**: CrossPoint Reader es un firmware de código abierto para dispositivos e-reader basados en ESP32 (incluyendo hardware Xteink X3 y X4). Posee soporte para EPUB 2/3, capa de abstracción de hardware (HAL), renderizado optimizado para pantallas de tinta electrónica, sincronización KOReader y flasheo directo vía USB-C desde el navegador.
- **Implicación**: Constituye la base arquitectónica principal para modificar y desplegar la versión personalizada de "Siddur" en el Xteink X4 Pro.
