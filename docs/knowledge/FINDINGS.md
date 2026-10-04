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

### F-003: Mapeo de Hardware y HAL de Xteink X4 Pro en FreeInk SDK / CrossPoint Reader
- **Fecha**: 2026-10-04
- **Contexto**: `input/crosspoint-reader/freeink-sdk/docs/xteink-x4pro-support.md` y `platformio.ini` (`[env:x4pro]`)
- **Hallazgo**: El dispositivo Xteink X4 Pro cuenta con un perfil maduro y probado en hardware dentro del ecosistema FreeInk SDK / CrossPoint Reader:
  - **MCU**: ESP32-S3 (16MB Flash, 8MB Octal PSRAM, memoria `dio_opi`).
  - **Pantalla**: 800×480 EPD monocromo (controladores SSD1677, UC8179 o UC8279 con autoprobe mediante `applyXteinkDisplayController()`). Pines: SCLK=12, MOSI=11, CS=13, DC=18, RST=14, BUSY=6 (HIGH).
  - **Touch & Home**: GT911 capacitivo en I²C (0x5D, SDA=39, SCL=38, INT=10, RST=4, Power Enable=GPIO2 activo en BAJO). Home key mapeado a bit capacitivo `0x10`. Orientación `swapXY = true`.
  - **Botones Físicos**: Izquierda = GPIO0, Derecha = GPIO7, Encendido = GPIO3 (digitales, activos en bajo).
  - **RTC Embebido**: BM8563 (compatible PCF8563) en I²C `0x51` (bus 39/38). Esencial para la sincronización "time-aware" y cómputo de zmanim completamente offline.
  - **Almacenamiento**: SDMMC nativo de 1-bit en CLK=41, CMD=42, DAT0=40, Power Enable=GPIO5 (activo en bajo).
  - **Batería**: Medidor de combustible I²C CW2017 en `0x63` y pin de estado de carga en GPIO21 (activo en alto).
  - **Frontlight dual**: Blanco/frío en GPIO8 y cálido en GPIO9 (modulados por PWM/LEDC a 25 kHz, activos en alto).
- **Implicación**: Toda la capa de abstracción de hardware (HAL) requerida para Siddur ya está identificada y validada en hardware real. No se requiere ingeniería inversa a ciegas de los buses periféricos.

### F-004: Motor de Calendario Hebreo y Zmanim Embebido (`libhdate` en C/C++)
- **Fecha**: 2026-10-04
- **Contexto**: `input/libhdate/src/hdate.h`, `hdate_julian.c`, `hdate_sun_time.c`, `hdate_holyday.c`
- **Hallazgo**: `libhdate` es una biblioteca en C puro (sin dependencias POSIX obligatorias ni asignaciones pesadas) que implementa:
  - Conversión biunívoca entre fechas gregorianas, número de día juliano (JD) y fecha hebrea.
  - Detección precisa de años bisiestos/embolísmicos, tipos de año (defectivo, regular, completo) y cómputo de Molad.
  - Identificación de festividades judías (Yom Tov, Jol HaMoed, ayunos, Janucá, Purim), cuenta del Omer y Parashá de la semana.
  - Cómputo solar astronómico de alta precisión para Zmanim halájicos (Alot HaShajar, Netzarim/Sunrise, Shema, Tefilá, Jatzot, Minjá Gedolá/Ketaná, Plag, Shkiá, Tzeit HaKojavim) dados únicamente latitud, longitud y fecha.
- **Implicación**: `libhdate` es el candidato ideal para integrarse en el firmware como componente embebido. Permite al Xteink X4 Pro calcular de forma autónoma y 100% offline (usando su RTC BM8563) qué día litúrgico es y qué inserciones aplican al segundo exacto.

### F-005: Arquitectura de Renderizado Tipográfico con Nikud y Modales de Versículo
- **Fecha**: 2026-10-04
- **Contexto**: `input/crosspoint-reader/lib/EpdFont/`, `freeink-sdk/libs/font/FreeInkFont/include/Gpos.h`, y `src/activities/reader/DictionaryDefinitionActivity.h`
- **Hallazgo**: 
  1. *Nikud y diacríticos*: En `FreeInkFont`, la tabla OpenType GPOS implementa únicamente el ajuste horizontal de pares ('kern'); el soporte de *Mark-to-Base* (attachment de diacríticos) está deliberadamente fuera del alcance para mantener bajo el footprint en microcontroladores. Para renderizar hebreo con nikud sin solapamiento, las marcas vocálicas (Unicode `U+05B0` a `U+05BC`, `U+05C1`-`05C2`) deben procesarse como caracteres de avance cero (`advance = 0`) con desplazamiento vertical relativo a la línea base y centrado horizontal sobre la consonante base precedente.
  2. *Modales Contextuales*: CrossPoint Reader ya posee una arquitectura de pila de actividades (`ActivityManager`), y el patrón de `DictionaryDefinitionActivity` y `EpubReaderFootnoteSelectActivity` demuestra cómo capturar toques de pantalla (`wasScreenTapped`) con regiones interactivas (`linkAtPoint`) para apilar un modal paginado con texto, traducción y navegación por botones físicos o toque.
- **Implicación**: Ambos problemas (soporte de Nikud en pantalla e-ink y visualización de la traducción en modal al pulsar un versículo) tienen una ruta de implementación clara, determinista y alineada con la arquitectura nativa del lector.

### F-006: Simulación de Escritorio (crosspoint-simulator) y Arquitectura de Doble Propósito (E-Reader General + Siddur)
- **Fecha**: 2026-10-04
- **Contexto**: `https://github.com/crosspoint-reader/crosspoint-simulator`, `sample-platformio-linux-wsl.ini` y `src/activities/home/HomeActivity.cpp`
- **Hallazgo**:
  1. *Simulador Nativo de Escritorio*: `crosspoint-simulator` permite compilar y ejecutar todo el firmware de CrossPoint Reader en la máquina host (Linux/WSL/macOS) renderizando el panel e-ink en una ventana SDL2 a resolución nativa 800×480. El perfil `[env:simulator_x4_pro]` (`-DSIMULATOR_DEVICE_X4_PRO`) emula el framebuffer de X4 Pro, toques de pantalla y gestos con el ratón, teclas físicas y Home capacitivo con el teclado, además del RTC y la batería. Reemplaza la capa `lib/hal/` sin modificar la API de alto nivel.
  2. *Preservación Absoluta de Capacidades E-Reader*: El dispositivo debe operar como un lector de libros electrónicos universal (EPUB 2/3, TXT, XTC, cómics/manga, sincronización KOReader, catálogos OPDS y explorador de archivos en tarjeta SD). La funcionalidad de Siddur se integra como un subsistema de lectura enriquecida y portal de oraciones dinámico (accesible desde la pantalla principal, menú de aplicaciones o apertura de archivos litúrgicos), coexistiendo sin alterar ni restringir la lectura de libros comunes.
- **Implicación**: Se acelera drásticamente el ciclo de desarrollo (inner loop) al poder depurar interfaces hebreas y modales interlineales directamente en el simulador SDL2 de escritorio, garantizando que el firmware final preserve el 100% de la funcionalidad de lectura de cualquier libro electrónico.



