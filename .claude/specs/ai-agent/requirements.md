# Requirements — Módulo: ai-agent
**Proyecto:** Participa AI  
**Módulo:** `services/ai-agent/` — Backend IA (Python + FastAPI + LangGraph)  
**Fecha:** 2026-05-24  
**Estado:** BORRADOR — pendiente revisión humana  

---

## 1. Contexto

El módulo `ai-agent` es el cerebro del sistema. Recibe mensajes del webhook NestJS
(texto o audio en base64), los procesa a través de un grafo de agentes LangGraph y
devuelve una respuesta estructurada en texto o audio.

Este módulo encapsula toda la inteligencia de Participa AI:
- Clasificación de intención ciudadana
- Búsqueda semántica (RAG) sobre leyes, procedimientos y datos gubernamentales
- Transcripción de notas de voz (STT) y síntesis de respuestas (TTS)
- Memoria conversacional persistente en Redis
- Conexión con directorios de organizaciones juveniles y calendarios municipales

Sin este módulo, el webhook solo puede recibir mensajes pero no puede guiar al usuario.

---

## 2. Functional Requirements

### FR-01 — Endpoint principal POST /agent
**When** el servicio NestJS envía una solicitud POST a `/agent`  
**The system shall** aceptar el payload con:
- `from` (identificador del usuario), `session_id`, `timestamp`, `type` (`"text"` o `"audio"`)
- Si `type === "text"`: campo `message` con el texto del usuario
- Si `type === "audio"`: campos `audio_base64` y `audio_mime_type`

**And** procesar el mensaje a través del orquestador LangGraph  
**And** retornar dentro del tiempo de respuesta definido (NFR-01) una respuesta con:
- `response_type`: `"text"` o `"audio"`
- `response_text`: texto de respuesta (si `response_type === "text"`)
- `response_audio_base64`: audio sintetizado en base64 (si `response_type === "audio"`)

### FR-02 — Health check GET /health
**When** cualquier servicio llama a `GET /health`  
**The system shall** responder HTTP 200 con:
```json
{ "status": "ok", "service": "ai-agent", "timestamp": "<iso_datetime>" }
```

### FR-03 — Pipeline STT: transcripción de audio
**When** el tipo de mensaje recibido es `"audio"`  
**The system shall** transcribir el audio a texto usando OpenAI Whisper API (`whisper-1`)  
antes de enviarlo al orquestador LangGraph  
**With** idioma forzado a español (`language: "es"`)  
**Within** un timeout de 20 segundos  
**Otherwise** (si Whisper falla) devolver respuesta de error amigable al usuario

### FR-04 — Orquestador LangGraph: clasificación de intención
**When** el orquestador recibe el texto del usuario (transcrito o directo)  
**The system shall** clasificar la intención en una de las siguientes categorías:
- `ONBOARDING` — primer contacto, recolección de nombre y distrito
- `LEGAL` — consultas sobre leyes, derechos, mecanismos legales
- `ESTRATEGA` — planificación de ruta de incidencia
- `OPORTUNIDADES` — calendarios municipales, plazos PP, ventanas de acción
- `RED` — conexión con organizaciones RENOJ/SENAJU
- `REDACTOR` — generación de cartas, solicitudes, propuestas
- `GENERAL` — consultas generales, glosario, ODS, casos de éxito

**And** enrutar al nodo de agente correspondiente  
**With** uso de LLM (gpt-4o-mini) para la clasificación

### FR-05 — Nodo ONBOARDING: bienvenida y perfil de usuario
**When** la intención es `ONBOARDING` o no existe perfil previo del usuario  
**The system shall** guiar al usuario para recolectar:
- Nombre (o cómo prefiere que lo llamen)
- Distrito de residencia
- Problemática o preocupación ciudadana principal

**And** almacenar este perfil en el estado de sesión Redis  
**And** transicionar automáticamente al nodo `ESTRATEGA` al completar el onboarding

### FR-06 — Nodo LEGAL: consultas normativas
**When** la intención es `LEGAL`  
**The system shall** realizar búsqueda semántica (RAG) en la colección `legal` de Qdrant  
sobre las leyes: Ley 26300, Ley 28056 (Presupuesto Participativo), Ley 27783  
**And** generar una respuesta en lenguaje simple, sin jerga burocrática  
**With** citas de los artículos específicos encontrados  
**And** máximo top-5 chunks relevantes del índice vectorial

### FR-07 — Nodo ESTRATEGA: ruta de incidencia
**When** la intención es `ESTRATEGA`  
**The system shall** generar una ruta de acción ciudadana personalizada considerando:
- El distrito del usuario (desde el perfil de sesión)
- La problemática identificada
- Los mecanismos legales disponibles (desde RAG en colección `procedimientos`)
- Las oportunidades actuales (desde `data/calendar.json`)

**And** presentar la ruta como pasos concretos y numerados

### FR-08 — Nodo OPORTUNIDADES: calendarios y plazos
**When** la intención es `OPORTUNIDADES`  
**The system shall** consultar `data/calendar.json` (herramienta local)  
**And** buscar en Qdrant colección `procedimientos` sobre plazos de PP  
**And** devolver las próximas 3 oportunidades más relevantes  
con fecha, tipo de evento y acción requerida del usuario

### FR-09 — Nodo RED: directorio de organizaciones
**When** la intención es `RED`  
**The system shall** consultar `data/directorio.json` (generado desde el Excel RENOJ)  
filtrando por distrito del usuario si está disponible  
**And** buscar en Qdrant colección `casos_exito` por similaridad con la problemática  
**And** devolver máximo 3 organizaciones relevantes con nombre, contacto y área de trabajo

### FR-10 — Nodo REDACTOR: generación de documentos ciudadanos
**When** la intención es `REDACTOR`  
**The system shall** generar documentos formales según el tipo solicitado:
- Carta dirigida a funcionario municipal
- Solicitud de información pública (Ley 27806)
- Propuesta para Presupuesto Participativo
- Inscripción a mesa de concertación

**And** personalizar el documento con nombre, distrito y problemática del usuario  
**And** incluir fecha, destinatario correcto (desde `data/municipios.json`) y firma

### FR-11 — Nodo GENERAL: guía y glosario ciudadano
**When** la intención es `GENERAL`  
**The system shall** responder usando RAG sobre colecciones `ods` y `procedimientos`  
**And** incluir casos de éxito similares desde la colección `casos_exito`  
**And** explicar términos burocráticos en lenguaje accesible para jóvenes de 15-29 años

### FR-12 — Pipeline TTS: síntesis de respuesta por voz
**When** el mensaje entrante fue de tipo `"audio"` (nota de voz)  
**The system shall** sintetizar la respuesta de texto a audio usando OpenAI TTS API  
(`tts-1`, voz `alloy`, formato MP3)  
**And** retornar el audio como base64 en el campo `response_audio_base64`  
**Within** un timeout de 30 segundos  
**Otherwise** (si TTS falla) devolver la respuesta en texto como fallback

### FR-13 — Memoria de sesión: persistencia en Redis
**When** el orquestador LangGraph procesa cualquier mensaje  
**The system shall** cargar el estado de conversación previo desde Redis  
usando `session_id` como clave (`session:{session_id}`)  
**And** guardar el estado actualizado al finalizar el nodo activo  
**With** TTL de 24 horas por sesión  
**And** si no existe sesión previa, inicializar con estado vacío

### FR-14 — Guardrails: límites temáticos
**When** el usuario realiza consultas fuera del ámbito de participación ciudadana  
(p. ej., contenido político-partidario, violencia, consultas médicas)  
**The system shall** rechazar amablemente la consulta  
**And** redirigir al usuario hacia las funcionalidades disponibles  
**Never** emitir opiniones políticas, electorales ni partidarias  
**Only** referenciar el marco legal peruano vigente

### FR-15 — Trazabilidad con LangSmith
**When** el orquestador ejecuta cualquier nodo de agente  
**The system shall** enviar trazas completas a LangSmith  
incluyendo: session_id hasheado, nodo ejecutado, tokens usados, latencia  
**When** `LANGCHAIN_TRACING_V2=true` en las variables de entorno

---

## 3. Non-Functional Requirements

### NFR-01 — Tiempos de respuesta
- POST `/agent` (texto): respuesta completa en < **10 segundos**
- POST `/agent` (audio, incluye STT): respuesta completa en < **15 segundos**
- OpenAI LLM (gpt-4o-mini): timeout máximo **30 segundos**
- OpenAI Whisper: timeout máximo **20 segundos**
- OpenAI TTS: timeout máximo **30 segundos**
- Qdrant (por consulta): timeout máximo **5 segundos**
- Redis (lectura/escritura): timeout máximo **2 segundos**

### NFR-02 — Disponibilidad y resiliencia
- Si Qdrant no responde → el nodo sigue con contexto vacío y responde con LLM puro
- Si Redis no responde → el nodo sigue sin estado previo (stateless degradado)
- Si TTS falla → devolver respuesta en texto como fallback transparente
- Si Whisper falla → retornar error 422 al webhook con mensaje de error amigable

### NFR-03 — Seguridad y privacidad
- Nunca loguear el contenido de mensajes de usuarios (PII)
- Solo loguear: `from_hash` (SHA256 del `from`), `message_type`, `intent`, `timestamp`, `status`
- Todos los secrets solo en variables de entorno; el servicio falla rápido si faltan
- `OPENAI_API_KEY`, `QDRANT_API_KEY`, `LANGCHAIN_API_KEY`, `REDIS_PASSWORD` — nunca hardcodeados

### NFR-04 — Observabilidad
- Logging estructurado con `structlog` (salida JSON para Render logs)
- Niveles: `ERROR` fallos inesperados, `WARN` timeouts y reintentos, `INFO` flujos normales
- Trazas LangSmith activas en producción y opcionales en desarrollo

### NFR-05 — Testing
- Framework: `pytest` + `httpx` (cliente async para FastAPI)
- Cobertura mínima: **80%** sobre código en `src/` y `agents/`
- Mocks obligatorios para: OpenAI API, Qdrant, Redis, archivos `data/*.json`
- Tests de integración con mocks (no con servicios reales)

### NFR-06 — Arquitectura hexagonal
- `domain/` no importa FastAPI, LangChain, OpenAI SDK ni ningún framework externo
- Solo librerías estándar de Python en `domain/`
- `adapters/` implementan los ports; `agents/` puede importar LangChain/LangGraph
- `application/` solo importa entidades y ports del dominio

### NFR-07 — Despliegue
- Un Dockerfile multi-stage por servicio (build + production)
- El servicio debe fallar rápido al arranque si falta una variable de entorno crítica
- Compatible con Render free tier (cold start posible, aceptable porque webhook responde async)

---

## 4. Casos de Uso Principales

### CU-01: Joven consulta sobre una ley
```
Actor: Usuario (joven peruano vía WhatsApp → webhook NestJS → /agent)
Flujo principal:
  1. Usuario escribe: "¿Qué es el presupuesto participativo y cómo puedo participar?"
  2. POST /agent con type: "text", message: "¿Qué es el presupuesto..."
  3. Orquestador clasifica intención → LEGAL (o ESTRATEGA)
  4. Nodo LEGAL ejecuta RAG en colección "legal" (Ley 28056)
  5. LLM genera respuesta en lenguaje simple con pasos concretos
  6. Redis guarda estado de sesión actualizado
  7. Retorno: { response_type: "text", response_text: "El presupuesto participativo es..." }
```

### CU-02: Joven envía nota de voz describiendo su problema
```
Actor: Usuario (audio OGG desde WhatsApp)
Flujo principal:
  1. POST /agent con type: "audio", audio_base64: "<...>"
  2. STT adapter → Whisper API → texto transcrito en español
  3. Orquestador clasifica → ESTRATEGA
  4. Nodo ESTRATEGA busca en "procedimientos" + lee calendar.json
  5. LLM genera ruta de incidencia personalizada por distrito
  6. TTS adapter → OpenAI tts-1 → audio MP3 en base64
  7. Retorno: { response_type: "audio", response_audio_base64: "<...>" }
```

### CU-03: Onboarding de nuevo usuario
```
Actor: Usuario nuevo (sin perfil en Redis)
Flujo principal:
  1. POST /agent con message: "Hola, quiero participar"
  2. Redis: no existe session → estado vacío (sin perfil)
  3. Orquestador detecta ausencia de perfil → ONBOARDING
  4. Nodo ONBOARDING solicita nombre y distrito
  5. Respuesta: "¡Hola! Soy Participa AI. ¿Cómo te llamas y de qué distrito eres?"
  6. Estado guardado en Redis con conversation_stage: ONBOARDING
```

### CU-04: Usuario pide que le redacten una carta
```
Actor: Usuario con perfil y problemática identificada
Flujo principal:
  1. POST /agent con message: "Ayúdame a redactar una carta para la municipalidad"
  2. Orquestador clasifica → REDACTOR
  3. Nodo REDACTOR carga perfil (nombre, distrito) desde estado Redis
  4. Consulta municipios.json para obtener funcionario y mesa de partes correcta
  5. LLM genera carta formal personalizada
  6. Retorno: carta completa como texto estructurado
```

### CU-05: Usuario pregunta por organizaciones juveniles en su distrito
```
Actor: Usuario con distrito identificado (Miraflores)
Flujo principal:
  1. POST /agent con message: "¿Hay alguna organización juvenil en mi zona?"
  2. Orquestador clasifica → RED
  3. Nodo RED filtra directorio.json por distrito "Miraflores"
  4. Busca en Qdrant "casos_exito" por similaridad
  5. Retorna top-3 organizaciones con nombre, contacto, área de trabajo
```

---

## 5. Criterios de Aceptación

| ID | Criterio | Verificación |
|---|---|---|
| AC-01 | POST /agent con texto → responde en < 10s con `response_type: "text"` | Test de integración + timer |
| AC-02 | POST /agent con audio → transcribe con Whisper y responde en < 15s | Test de integración con audio mock |
| AC-03 | POST /agent sin campo requerido → responde 422 Unprocessable Entity | Test unitario con httpx |
| AC-04 | Usuario nuevo sin perfil → orquestador enruta a ONBOARDING | Test unitario del orquestador |
| AC-05 | Intención LEGAL → nodo ejecuta RAG en colección "legal" | Test con mock de IRagClient |
| AC-06 | Intención REDACTOR → documento generado contiene nombre y distrito del usuario | Test con estado de sesión populado |
| AC-07 | Si Qdrant timeout → nodo sigue y responde con LLM puro (sin crash) | Test con mock de timeout |
| AC-08 | Si Redis timeout → sesión nueva sin historial (no falla el servicio) | Test con mock de timeout |
| AC-09 | Si TTS falla → respuesta cae back a texto | Test con mock de ITtsClient lanzando error |
| AC-10 | Estado de sesión se persiste en Redis tras cada interacción | Test con RedisSessionAdapter mock |
| AC-11 | Ningún log contiene el contenido del mensaje del usuario | Revisión manual de logs con `structlog` |
| AC-12 | GET /health → 200 con `{ "status": "ok", "service": "ai-agent" }` | Test unitario |
| AC-13 | `OPENAI_API_KEY` ausente al arranque → el servicio falla con mensaje claro | Test de configuración |
| AC-14 | LangSmith recibe trazas con `LANGCHAIN_TRACING_V2=true` | Verificación manual en LangSmith UI |
| AC-15 | Consulta político-partidaria → respuesta de guardrail sin opinión | Test del nodo GENERAL con prompt de prueba |

---

## 6. Fuera de Alcance (este módulo)

- Ingestión de PDFs a Qdrant → módulo `data-pipeline` (módulo 6)
- Scraping diario de fuentes gubernamentales → módulo `scraper` (módulo 7)
- Interfaz web / dashboard → mejora futura (no en MVP)
- Notificaciones proactivas al usuario → mejora futura
- Multiidioma (quechua, aymara) → mejora futura

---

## 7. Dependencias Externas

| Dependencia | Uso | Variable de entorno |
|---|---|---|
| OpenAI API (gpt-4o-mini) | Clasificación de intención + generación de respuestas | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| OpenAI Whisper (whisper-1) | Transcripción STT de audios | `OPENAI_API_KEY`, `OPENAI_WHISPER_MODEL` |
| OpenAI TTS (tts-1) | Síntesis de respuestas por voz | `OPENAI_API_KEY`, `OPENAI_TTS_MODEL`, `OPENAI_TTS_VOICE` |
| OpenAI Embeddings (text-embedding-3-small) | Embeddings para RAG | `OPENAI_API_KEY`, `OPENAI_EMBEDDING_MODEL` |
| Qdrant Cloud | Vector DB para búsqueda semántica RAG | `QDRANT_URL`, `QDRANT_API_KEY` |
| Redis Cloud | Persistencia de sesiones LangGraph | `REDIS_URL`, `REDIS_PASSWORD` |
| LangSmith | Observabilidad de agentes | `LANGCHAIN_API_KEY`, `LANGCHAIN_TRACING_V2` |
| JSONs locales (`data/`) | Directorio RENOJ, calendario, municipios | Ruta relativa desde raíz del repo |

---

## 8. Invariantes del Dominio

1. El dominio nunca sabe si la entrada es voz o texto — solo procesa texto (la transcripción es pre-procesamiento)
2. El orquestador siempre devuelve una respuesta aunque todos los servicios externos fallen
3. El `session_id` siempre es idéntico al campo `from` hasheado — nunca el número real
4. Un mensaje no puede ser de tipo distinto a `"text"` o `"audio"` en el dominio
5. La respuesta nunca incluye contenido político-partidario ni opiniones sobre candidatos
