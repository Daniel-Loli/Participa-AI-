# Requirements — Módulo: webhook
**Proyecto:** Participa AI  
**Módulo:** `services/whatsapp/` — Webhook WhatsApp Business API  
**Fecha:** 2025  
**Estado:** BORRADOR — pendiente revisión humana  

---

## 1. Contexto

El webhook es el punto de entrada de todo el sistema. Es el único componente que
se comunica directamente con la API de WhatsApp Business (Meta). Recibe mensajes
de texto y notas de voz de los jóvenes peruanos, los pre-procesa y los enruta al
backend de IA (Python/FastAPI) para su procesamiento por los agentes.

Sin este módulo, ningún otro componente del sistema puede funcionar.

---

## 2. Functional Requirements

### FR-01 — Verificación del webhook (Meta handshake)
**When** Meta for Developers envía una solicitud GET a `/webhook`  
**The system shall** responder con el valor de `hub.challenge` incluido en la query  
**siempre que** `hub.mode === "subscribe"` Y `hub.verify_token` coincida con la  
variable de entorno `WHATSAPP_VERIFY_TOKEN`  
**Otherwise** responder con HTTP 403 Forbidden  

### FR-02 — Recepción de mensajes entrantes
**When** WhatsApp Business API envía un evento POST a `/webhook`  
**The system shall** responder con HTTP 200 OK **inmediatamente** antes de procesar  
el payload, para evitar reintentos de Meta (timeout: 20 segundos)

### FR-03 — Detección de tipo de mensaje
**When** el sistema recibe un payload POST válido de WhatsApp  
**The system shall** identificar el tipo de mensaje del campo `messages[0].type`:  
- `"text"` → extraer `messages[0].text.body` y enrutar a procesamiento de texto  
- `"audio"` → extraer `messages[0].audio.id` y enrutar a pipeline STT  
- Cualquier otro tipo (`image`, `video`, `document`, `sticker`, etc.) → responder  
  al usuario con mensaje de tipo no soportado (ver FR-07)

### FR-04 — Procesamiento de mensaje de texto
**When** el tipo de mensaje es `"text"`  
**The system shall** enviar al backend de IA (POST `/agent`) el payload:  
```json
{
  "from": "<número_whatsapp>",
  "message": "<texto_del_usuario>",
  "type": "text",
  "session_id": "<from>",
  "timestamp": "<unix_timestamp>"
}
```

### FR-05 — Procesamiento de nota de voz
**When** el tipo de mensaje es `"audio"`  
**The system shall**:  
1. Descargar el archivo de audio usando el `media_id` vía la API de Meta  
   (`GET https://graph.facebook.com/v18.0/{media_id}`)  
2. Obtener la URL de descarga del archivo OGG/OPUS  
3. Descargar el binario del audio  
4. Enviar al backend de IA (POST `/agent`) el payload con el audio en base64:  
```json
{
  "from": "<número_whatsapp>",
  "audio_base64": "<base64_del_audio>",
  "audio_mime_type": "audio/ogg",
  "type": "audio",
  "session_id": "<from>",
  "timestamp": "<unix_timestamp>"
}
```

### FR-06 — Envío de respuesta de texto al usuario
**When** el backend de IA devuelve una respuesta en texto  
**The system shall** enviarla al usuario vía WhatsApp Business API:  
`POST https://graph.facebook.com/v18.0/{phone_number_id}/messages`  
con `type: "text"` y el cuerpo de la respuesta

### FR-07 — Envío de respuesta de audio al usuario
**When** el backend de IA devuelve una respuesta en audio (base64)  
**The system shall**:  
1. Decodificar el base64 a buffer MP3/OGG  
2. Subir el audio a la API de Meta (Media Upload)  
3. Enviar al usuario el `media_id` resultante como mensaje de tipo `"audio"`

### FR-08 — Manejo de tipo de mensaje no soportado
**When** el mensaje entrante no es de tipo `"text"` ni `"audio"`  
**The system shall** responder al usuario en WhatsApp:  
> "Hola, por ahora solo puedo recibir mensajes de texto o notas de voz. 
> ¿Cuéntame en qué te puedo ayudar?"

### FR-09 — Validación de payload de Meta
**When** el sistema recibe un POST en `/webhook`  
**The system shall** verificar la firma HMAC-SHA256 del header `X-Hub-Signature-256`  
usando `WHATSAPP_APP_SECRET` para confirmar que el mensaje proviene de Meta  
**If** la firma no coincide → responder HTTP 401 y no procesar el mensaje

### FR-10 — Health check
**When** cualquier servicio llama a `GET /health`  
**The system shall** responder HTTP 200 con:  
```json
{ "status": "ok", "service": "whatsapp-webhook", "timestamp": "<iso_datetime>" }
```

---

## 3. Non-Functional Requirements

### NFR-01 — Tiempo de respuesta al webhook (crítico)
- El endpoint POST `/webhook` DEBE responder HTTP 200 en menos de **1 segundo**
- El procesamiento del mensaje ocurre de forma asíncrona después del 200 OK
- Si Meta no recibe 200 en 20 segundos, reintentará el mensaje (duplicados)

### NFR-02 — Disponibilidad
- El servicio debe tener una disponibilidad mínima de 99.5% en horario 6AM-11PM Lima
- Render Starter plan (always-on) — mínimo 1 instancia activa en todo momento

### NFR-03 — Seguridad
- Nunca loguear el contenido de los mensajes de los usuarios (PII)
- Solo loguear: `from_hash` (SHA256 del número), `message_type`, `timestamp`, `status`
- El `WHATSAPP_ACCESS_TOKEN` y `WHATSAPP_APP_SECRET` solo en variables de entorno
- Validar firma HMAC en cada POST (FR-09) sin excepción

### NFR-04 — Manejo de errores
- Si el backend de IA no responde en 10 segundos → enviar al usuario:  
  "Estoy procesando tu mensaje, en un momento te respondo 🙏"
- Si falla la descarga del audio → responder al usuario que intente reenviar la nota
- Todos los errores deben loguearse con nivel ERROR (visible en Render logs)

### NFR-05 — Escalabilidad
- El servicio debe soportar al menos 100 mensajes simultáneos sin degradación
- Usar procesamiento asíncrono (NestJS + async/await) para no bloquear el event loop

### NFR-06 — Idempotencia
- Si Meta reenvía el mismo mensaje (mismo `message_id`), el sistema no debe
  procesarlo dos veces
- Implementar cache de `message_id` procesados (TTL: 5 minutos) en memoria

---

## 4. Casos de Uso Principales

### CU-01: Joven envía mensaje de texto
```
Actor: Usuario (joven peruano vía WhatsApp)
Flujo principal:
  1. Usuario escribe "quiero participar en el presupuesto participativo"
  2. WhatsApp API → POST /webhook con payload tipo "text"
  3. Sistema responde 200 OK a Meta
  4. Sistema extrae texto y número del usuario
  5. Sistema envía al backend de IA con session_id
  6. Backend de IA procesa y devuelve respuesta en texto
  7. Sistema envía respuesta al usuario vía WhatsApp
Flujo alternativo:
  - Si backend de IA tarda >10s → enviar mensaje de espera (NFR-04)
```

### CU-02: Joven envía nota de voz
```
Actor: Usuario (joven peruano vía WhatsApp)
Flujo principal:
  1. Usuario graba y envía nota de voz describiendo su problema
  2. WhatsApp API → POST /webhook con payload tipo "audio"
  3. Sistema responde 200 OK a Meta
  4. Sistema descarga el archivo OGG usando el media_id
  5. Sistema envía audio en base64 al backend de IA
  6. Backend de IA transcribe (OpenAI Whisper API) y procesa con agentes LangGraph
  7. Backend devuelve respuesta (texto o audio según preferencia)
  8. Sistema envía respuesta al usuario
Flujo alternativo:
  - Si falla descarga del audio → pedir al usuario que reenvíe la nota
```

### CU-03: Meta verifica el webhook al registrarlo
```
Actor: Desarrollador (configurando Meta for Developers)
Flujo principal:
  1. Desarrollador registra URL en panel de Meta
  2. Meta → GET /webhook?hub.mode=subscribe&hub.verify_token=XXX&hub.challenge=YYY
  3. Sistema valida que hub.verify_token === WHATSAPP_VERIFY_TOKEN
  4. Sistema responde con hub.challenge
  5. Meta confirma el webhook como verificado
Flujo alternativo:
  - Si token no coincide → 403, Meta rechaza el registro
```

---

## 5. Criterios de Aceptación

| ID | Criterio | Verificación |
|---|---|---|
| AC-01 | GET /webhook con token correcto → responde con hub.challenge | Test unitario + prueba manual en Meta |
| AC-02 | GET /webhook con token incorrecto → responde 403 | Test unitario |
| AC-03 | POST /webhook responde 200 en menos de 500ms | Test de performance con Jest |
| AC-04 | Mensaje de texto llega correctamente al backend de IA | Test de integración con mock del backend |
| AC-05 | Nota de voz se descarga y llega en base64 al backend de IA | Test de integración con audio de prueba |
| AC-06 | Firma HMAC inválida → rechaza con 401 | Test unitario de seguridad |
| AC-07 | Mensaje duplicado (mismo message_id) → no se procesa dos veces | Test unitario de idempotencia |
| AC-08 | Tipo de mensaje no soportado → usuario recibe mensaje amigable | Test E2E con mock de WhatsApp |
| AC-09 | GET /health → responde 200 con JSON de estado | Test unitario |
| AC-10 | Ningún log contiene el texto completo del mensaje del usuario | Revisión manual de logs |

---

## 6. Fuera de Alcance (este módulo)

- Transcripción STT del audio → módulo `stt-pipeline` (módulo 2)
- Síntesis TTS de la respuesta → módulo `tts-response` (módulo 5)
- Lógica de agentes y RAG → módulo `agent-orchestrator` (módulo 3)
- Guardado de sesión en Cosmos DB → módulo `session-memory` (módulo 6)
- Envío de documentos PDF generados → módulo `document-writer` (módulo 7)

---

## 7. Dependencias Externas

| Dependencia | Uso | Credencial requerida |
|---|---|---|
| WhatsApp Business API (Meta) | Recepción y envío de mensajes | `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` |
| Meta Graph API v18.0 | Descarga de archivos de audio | `WHATSAPP_ACCESS_TOKEN` |
| Backend IA (Python/FastAPI + LangGraph) | Procesamiento de mensajes por agentes | `AI_AGENT_SERVICE_URL` (internal) |

---