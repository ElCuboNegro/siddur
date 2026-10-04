# PRD-Lite: Siddur e-Ink (Smart Liturgical Reader)

**Iniciativa:** `siddur`  
**Área:** Personal / Open Source  
**Proceso:** Lectura y navegación de textos litúrgicos en e-ink  
**Fecha de Confirmación:** 2026-10-04  
**ID de Sesión Catalyst:** `50f6553895704a0782b02b47fb9ed630`  
**Estado:** Confirmado (v1)

---

## 1. Definición del Problema

### Problem Statement
Las festividades y rezos diarios del judaísmo requieren material litúrgico altamente especializado y dinámico según el calendario hebreo (zmanim, festividades, Shabat, Rosh Jodesh, inserciones estacionales como *Mashiv HaRuaj* o *Tal UMatar*). Durante los rezos y reuniones, buscar el texto exacto con traducción interlineal en el idioma de la comunidad (español/hebreo) genera fricción, distracciones e interrupciones molestas si no se cuenta con los tomos físicos precisos.

Los lectores de libros electrónicos actuales carecen de sincronización temporal (*time-awareness*) para presentar dinámicamente las variaciones litúrgicas exactas según fecha, hora y ubicación geográfica. Esto obliga a búsquedas manuales complejas o al acceso limitado a bibliotecas impresas voluminosas y costosas.

### Frecuencia
Ocurre de forma continua:
- Varias veces al día (rezos cotidianos: Shajarit, Minjá, Arvit, y bendiciones antes/después de comer).
- Semanalmente (víspera y día de Shabat, Kidush, Havdalá).
- En cada festividad a lo largo del año (Pésaj, Shavuot, Sucot, Rosh Hashaná, Yom Kipur, Janucá, Purim).
- Ciclos plurianuales: Años bisiestos/embolísmicos del calendario hebreo y años sabáticos (Shemitá).

### Impacto Actual
- **Pérdida de concentración (*kavaná*)**: Interrupciones constantes hojeando tomos o buscando la inserción correspondiente.
- **Costos económicos prohibitivos**: Adquirir una biblioteca litúrgica completa con traducción e interlineal cuesta miles de dólares.
- **Fricciones en el uso de móviles**: El uso de smartphones en días sagrados o en la sinagoga genera distracciones y desaprobación comunitaria.
- **Tiempos muertos**: Entre 5 y 15 minutos perdidos por servicio en búsquedas manuales o consultas previas de zmanim.

---

## 2. Usuario Objetivo

- **Rol Principal:** Cualquier persona judía (tanto miembros regulares de la comunidad como quienes siguen rezos con apoyo interlineal) o aspirantes a conversión que requieren una guía litúrgica accesible, precisa y adaptable para rezar y estudiar.
- **Contexto de Uso:** 
  - Sinagoga durante servicios comunitarios.
  - Hogar (mesa de Shabat, Kidush, festividades familiares).
  - Viajes y desplazamientos.
  - Estudio personal.
  - Dispositivos de tinta electrónica (e-ink) de alta autonomía, operando 100% offline, sin retroiluminación agresiva ni distracciones.
- **Población Afectada:**
  - **Fase Piloto:** 1 usuario directo (validación en hardware e-ink Xteink X4 Pro).
  - **Corto-Mediano Plazo:** Comunidad local (decenas a cientos de miembros).
  - **Largo Plazo:** Comunidad judía internacional en la diáspora y personas en proceso de conversión (cientos de miles de usuarios).

---

## 3. Ecosistema Técnico y Sistemas Involucrados

- **Hardware Objetivo:** Dispositivos e-ink basados en ESP32 compatibles con la arquitectura de **CrossPoint Reader** (prioritariamente **Xteink X4 Pro** / X3, con extensibilidad a M5Paper, Seeed reTerminal, LilyGo T5).
- **Firmware Base:** Fork/adaptación del firmware C++/ESP-IDF de [CrossPoint Reader](https://github.com/crosspoint-reader/crosspoint-reader).
- **Monorepo `siddur`:**
  - `firmware/`: Código C++ del firmware con HAL para Xteink X4 Pro y motores específicos.
  - `content/`: Modelos de datos, esquemas litúrgicos y textos en hebreo con interlineal en español.
  - `tools/`: Scripts de build, packaging de fuentes bitmap/truetype con soporte nikud, compiladores de zmanim offline y scrapers/normalizadores.
- **Fuentes de Contenido:** Repositorios abiertos como Sefaria y Open Siddur.
- **Componentes Clave a Desarrollar:**
  1. **Motor astronómico y halájico C++ (Zmanim y Calendario Hebreo)** embebido en ESP32.
  2. **Motor tipográfico e-ink con soporte Nikud y RTL** sin solapamiento de diacríticos.
  3. **Motor interlineal y modal de versículo**: Navegación física y tap/click en frase para desplegar modal con traducción contextual.

---

## 4. Análisis AS-IS vs TO-BE

### Flujo AS-IS (Actual)
1. El usuario consulta calendarios externos, apps móviles o tablas de zmanim para saber qué inserciones aplican hoy (ej. *Al HaNisim*, *Yaalé VeYavó*, *Tajanún*).
2. Selecciona entre varios libros físicos (Siddur diario, Sidur de Shabat, Majzor específico).
3. Hojea manualmente durante el servicio para encontrar la sección correcta.
4. En comunidades de habla hispana, alterna la vista entre columnas hebreas y traducciones no alineadas, perdiendo el ritmo del rezo colectivo.

### Fricciones Principales
- Barrera del idioma hebreo sin alineación visual directa frase a frase.
- Incertidumbre de omitir o incluir erróneamente variaciones litúrgicas temporales.
- Peso, volumen y costo excesivo de los libros físicos.
- Falta de traducciones interlineales fieles y accesibles al español.

### Flujo TO-BE (Propuesto)
1. El usuario enciende el dispositivo e-ink Xteink X4 Pro.
2. El sistema *time-aware* detecta automáticamente la fecha hebrea, la hora actual (RTC) y la geolocalización configurada.
3. El lector carga automáticamente la plegaria o Kidush correspondiente al momento del día con todas las inserciones del calendario ya integradas.
4. Renderiza en e-ink hebreo nítido con *nikud* perfectamente posicionado y alineación interlineal en español.
5. El usuario navega con fluidez usando botones físicos.
6. **Interacción por Frase / Modal:** Al hacer tap o presionar sobre una frase/versículo, se abre un modal contextual en pantalla que despliega la traducción y comentarios del versículo sin perder la posición de lectura.

---

## 5. Métricas e Impacto

| Métrica | Situación Base (AS-IS) | Meta (TO-BE) |
|---|---|---|
| **Costo económico de biblioteca litúrgica** | $1,000 – $3,000 USD por familia (múltiples tomos) | $50 – $90 USD (costo único del hardware e-ink; contenido libre) |
| **Tiempo de acceso al rezo exacto** | 5 – 15 minutos (búsqueda y verificación) | < 15 segundos (carga automática time-aware) |
| **Cobertura litúrgica offline** | Fragmentada en tomos pesados | 100% del ciclo anual y Shemitá en un solo dispositivo offline |
| **Fricción lingüística** | Alta (columnas disjuntas o sin traducción) | Mínima (interlineal continuo + modal por versículo) |

### Impacto de Valor
- **Portabilidad:** Toda la biblioteca litúrgica en el bolsillo con meses de autonomía de batería.
- **Inclusión:** Accesibilidad inmediata para personas de habla hispana en la diáspora y procesos de conversión.
- **Tiempo y Eficiencia:** Cero tiempo perdido buscando qué página corresponde rezar hoy.
- **Economía:** Democratización del acceso a textos sagrados de alta calidad tipográfica.

---

## 6. Brechas Técnicas Identificadas (Gaps)

1. **Motor C++ de Zmanim y Calendario Hebreo:** Portar un algoritmo ligero sin dependencias pesadas que calcule zmanim y fechas hebreas en microcontroladores ESP32 con memoria limitada.
2. **Renderizado de Nikud en e-Ink:** CrossPoint Reader utiliza fuentes bitmap/u8g2 o freetype; se requiere garantizar que los puntos vocálicos (*nikud*) y cantilaciones (*teamim*) se dibujen correctamente sobre las consonantes sin solapamiento (RTL shaping / HarfBuzz lite o fuentes pre-renderizadas).
3. **Esquema de Datos Estructurado:** Definir el formato binario o JSON compacto para almacenar la liturgia con metadatos temporales (reglas de inserción) y traducción frase por frase.
4. **UI Modal Contextual:** Diseñar e implementar el componente de ventana emergente / modal en el firmware de CrossPoint Reader accionado por evento táctil o selección de cursor.
