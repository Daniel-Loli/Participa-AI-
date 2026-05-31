# Tasks — Módulo: webhook
**Proyecto:** Participa AI  
**Módulo:** `services/whatsapp/` — Webhook WhatsApp Business API  
**Fecha:** 2025  
**Estado:** ✅ COMPLETO — 12/12 tareas implementadas  
**Depende de:** `design.md` (aprobado)

---

## Resumen de tareas

| ID | Tarea | Estimado | Dependencias |
|---|---|---|---|
| TASK-001 | Scaffolding del proyecto NestJS | 30 min | ninguna | ✅ |
| TASK-002 | Domain layer — entidades, VOs y ports | 45 min | TASK-001 | ✅ |
| TASK-003 | VerifyWebhookUseCase + test | 30 min | TASK-002 | ✅ |
| TASK-004 | HmacSignatureGuard + test | 30 min | TASK-002 | ✅ |
| TASK-005 | MessageDispatcher + test | 45 min | TASK-002 | ✅ |
| TASK-006 | HandleTextMessageUseCase + test | 45 min | TASK-002 | ✅ |
| TASK-007 | HandleAudioMessageUseCase + test | 45 min | TASK-002 | ✅ |
| TASK-008 | WhatsAppController + test integración | 45 min | TASK-003/004/005/006/007 | ✅ |
| TASK-009 | WhatsAppApiAdapter (outbound) + test | 60 min | TASK-002 | ✅ |
| TASK-010 | AiAgentHttpAdapter (outbound) + test | 45 min | TASK-002 | ✅ |
| TASK-011 | Wiring NestJS (módulo completo) | 30 min | TASK-008/009/010 | ✅ |
| TASK-012 | Dockerfile + .env.example | 20 min | TASK-011 | ✅ |

**Total estimado: ~7 horas**

---

## Detalle de Tareas

---

### TASK-001 — Scaffolding del proyecto NestJS
**Estimado:** 30 min  
**Dependencias:** ninguna

**Archivos a crear:**
- `services/whatsapp/package.json`
- `services/whatsapp/tsconfig.json`
- `services/whatsapp/tsconfig.build.json`
- `services/whatsapp/nest-cli.json`
- `services/whatsapp/src/main.ts`
- `services/whatsapp/src/app.module.ts`
- `services/whatsapp/.env.example`

**Acciones:**
1. Inicializar proyecto NestJS con `@nestjs/cli` o manualmente
2. Configurar `tsconfig.json` con `strict: true`, `experimentalDecorators: true`
3. Instalar dependencias: `@nestjs/common`, `@nestjs/core`, `@nestjs/platform-express`,
   `axios`, `class-validator`, `class-transformer`
4. Instalar devDependencies: `@nestjs/testing`, `jest`, `ts-jest`, `supertest`, `@types/node`
5. Configurar Jest en `package.json` con `ts-jest` y coverage mínimo 80%
6. `main.ts` debe: activar `ValidationPipe` global, escuchar en `PORT` env var (default 3000),
   activar `rawBody: true` en express (necesario para validar firma HMAC)

**Criterio de done:**
- `npm run start:dev` levanta sin errores
- `npm test` corre sin errores (aunque no haya tests aún)
- `npm run build` compila sin errores TypeScript

---

### TASK-002 — Domain layer: entidades, value objects y ports
**Estimado:** 45 min  
**Dependencias:** TASK-001

**Archivos a crear:**
- `src/domain/entities/message.entity.ts`
- `src/domain/value-objects/message-type.vo.ts`
- `src/domain/value-objects/whatsapp-number.vo.ts`
- `src/domain/ports/message-sender.port.ts`
- `src/domain/ports/ai-agent.port.ts`
- `src/domain/ports/media-downloader.port.ts`

**Acciones:**
1. Crear `MessageType` enum con valores `TEXT`, `AUDIO`, `UNSUPPORTED` y función `parseMessageType()`
2. Crear `WhatsAppNumber` value object que valide formato E.164 (empieza con `+`, solo dígitos)
3. Crear clase `Message` con campos del design, métodos `isText()` e `isAudio()`
4. Crear interfaces `IMessageSender`, `IAiAgentClient`, `IMediaDownloader` exactamente
   como están definidas en el design
5. Crear tipos `TextAgentPayload`, `AudioAgentPayload`, `AgentResponse`

**Regla crítica:** Ningún archivo de esta carpeta puede importar desde NestJS, Axios
ni ningún framework externo. Solo TypeScript puro.

**Criterio de done:**
- `tsc --noEmit` sin errores en la carpeta `domain/`
- Ningún import externo en archivos de `domain/`
- Todos los tipos exportados correctamente

---

### TASK-003 — VerifyWebhookUseCase + test unitario
**Estimado:** 30 min  
**Dependencias:** TASK-002

**Archivos a crear:**
- `src/application/use-cases/verify-webhook.use-case.ts`
- `test/unit/verify-webhook.use-case.spec.ts`

**Acciones:**
1. Implementar `VerifyWebhookUseCase.execute(mode, token, challenge)` según el design
2. El token se lee de `process.env.WHATSAPP_VERIFY_TOKEN`
3. Escribir tests para:
   - Token correcto + mode subscribe → retorna challenge ✓
   - Token incorrecto → retorna null ✓
   - Mode distinto a subscribe → retorna null ✓
   - Token vacío → retorna null ✓

**Criterio de done:**
- `npm test -- verify-webhook` pasa al 100%
- Cobertura del use case: 100%

---

### TASK-004 — HmacSignatureGuard + test unitario
**Estimado:** 30 min  
**Dependencias:** TASK-002

**Archivos a crear:**
- `src/adapters/guards/hmac-signature.guard.ts`
- `test/unit/hmac-signature.guard.spec.ts`

**Acciones:**
1. Implementar guard usando `crypto.createHmac('sha256', APP_SECRET)`
2. Usar `crypto.timingSafeEqual` para comparar (evitar timing attacks)
3. Leer body como raw buffer (requiere `rawBody: true` en main.ts — TASK-001)
4. Si el header `x-hub-signature-256` no existe → retornar false
5. Escribir tests para:
   - Firma válida → `canActivate()` retorna true ✓
   - Firma inválida → retorna false ✓
   - Header ausente → retorna false ✓
   - APP_SECRET vacío → retorna false ✓

**Criterio de done:**
- `npm test -- hmac-signature` pasa al 100%
- No usar comparación con `===` para las firmas (debe ser `timingSafeEqual`)

---

### TASK-005 — MessageDispatcher + test unitario
**Estimado:** 45 min  
**Dependencias:** TASK-002

**Archivos a crear:**
- `src/adapters/inbound/message.dispatcher.ts`
- `test/unit/message.dispatcher.spec.ts`

**Acciones:**
1. Implementar `MessageDispatcher.dispatch(body)` que:
   - Extrae `messages[0]` del payload de Meta (con optional chaining)
   - Verifica idempotencia con Map + TTL 5 minutos
   - Construye entidad `Message` con `parseMessageType()`
   - Delega al use case correcto según tipo
2. Implementar limpieza del cache (purgar entradas expiradas al insertar nuevas)
3. Escribir tests con mocks de los use cases para:
   - Mensaje de texto → llama `HandleTextMessageUseCase.execute()` ✓
   - Mensaje de audio → llama `HandleAudioMessageUseCase.execute()` ✓
   - Tipo no soportado → llama `IMessageSender.sendText()` con texto amigable ✓
   - `message_id` duplicado → no llama ningún use case ✓
   - Payload sin messages → retorna sin error ✓
   - `message_id` duplicado expirado (>5min) → sí procesa ✓

**Criterio de done:**
- `npm test -- message.dispatcher` pasa al 100%
- Cobertura: 100% de ramas del switch y del cache

---

### TASK-006 — HandleTextMessageUseCase + test unitario
**Estimado:** 45 min  
**Dependencias:** TASK-002

**Archivos a crear:**
- `src/application/use-cases/handle-text-message.use-case.ts`
- `test/unit/handle-text-message.use-case.spec.ts`

**Acciones:**
1. Implementar use case según el design: llama `IAiAgentClient.processText()`,
   luego según `response_type` llama `sendText()` o `sendAudio()`
2. Si `IAiAgentClient` lanza error de timeout → loguear WARNING, llamar
   `sender.sendText()` con mensaje de espera definido en constante
3. Escribir tests con mocks para:
   - Backend IA responde texto → `sendText()` llamado con el texto ✓
   - Backend IA responde audio → `sendAudio()` llamado con base64 ✓
   - Backend IA timeout → `sendText()` llamado con mensaje de espera ✓
   - Backend IA error desconocido → loguear ERROR, no propagar excepción ✓

**Constante a definir:**
```typescript
const WAIT_MESSAGE = 'Estoy procesando tu mensaje, en un momento te respondo 🙏';
```

**Criterio de done:**
- `npm test -- handle-text-message` pasa al 100%
- El use case NUNCA propaga excepciones al caller (las absorbe y logguea)

---

### TASK-007 — HandleAudioMessageUseCase + test unitario
**Estimado:** 45 min  
**Dependencias:** TASK-002

**Archivos a crear:**
- `src/application/use-cases/handle-audio-message.use-case.ts`
- `test/unit/handle-audio-message.use-case.spec.ts`

**Acciones:**
1. Implementar use case según el design: descarga audio, convierte a base64,
   llama `processAudio()`, envía respuesta
2. Si falla la descarga del audio → `sendText()` con:
   `'No pude recibir tu nota de voz. ¿Puedes reenviarla o escribirme tu consulta?'`
3. Escribir tests con mocks para:
   - Descarga OK + respuesta texto → `sendText()` ✓
   - Descarga OK + respuesta audio → `sendAudio()` ✓
   - Falla descarga → mensaje de reintento al usuario ✓
   - Falla backend IA → mensaje de espera al usuario ✓

**Criterio de done:**
- `npm test -- handle-audio-message` pasa al 100%
- El use case NUNCA propaga excepciones al caller

---

### TASK-008 — WhatsAppController + test de integración
**Estimado:** 45 min  
**Dependencias:** TASK-003, TASK-004, TASK-005, TASK-006, TASK-007

**Archivos a crear:**
- `src/adapters/inbound/whatsapp.controller.ts`
- `test/integration/whatsapp.controller.spec.ts`

**Acciones:**
1. Implementar controller con los 3 endpoints según el design:
   - `GET /webhook` → usa `VerifyWebhookUseCase`
   - `POST /webhook` → aplica `HmacSignatureGuard`, responde 200, llama dispatcher async
   - `GET /health` → retorna JSON de estado
2. En `POST /webhook`: el `res.status(200).send('OK')` va ANTES del `await dispatcher.dispatch()`
3. Escribir tests de integración con `@nestjs/testing` y `supertest`:
   - `GET /webhook` token correcto → 200 con challenge ✓
   - `GET /webhook` token incorrecto → 403 ✓
   - `POST /webhook` firma válida → 200 inmediato ✓
   - `POST /webhook` firma inválida → 401 ✓
   - `GET /health` → 200 con `{ status: 'ok' }` ✓

**Criterio de done:**
- `npm test -- whatsapp.controller` pasa al 100%
- El POST responde 200 antes de que el dispatcher termine (verificar con spy de timing)

---

### TASK-009 — WhatsAppApiAdapter + test
**Estimado:** 60 min  
**Dependencias:** TASK-002

**Archivos a crear:**
- `src/adapters/outbound/whatsapp-api.adapter.ts`
- `test/unit/whatsapp-api.adapter.spec.ts`

**Acciones:**
1. Implementar `sendText(to, text)`:
   - POST `https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages`
   - Header: `Authorization: Bearer {ACCESS_TOKEN}`
   - Body: `{ messaging_product: 'whatsapp', to, type: 'text', text: { body: text } }`
2. Implementar `downloadAudio(mediaId)`:
   - GET `https://graph.facebook.com/v18.0/{mediaId}` → obtener `url`
   - GET `{url}` con `Authorization` header → descargar binario
   - Retornar `{ buffer, mimeType }`
3. Implementar `sendAudio(to, audioBase64, mimeType)`:
   - Subir buffer a Media Upload API: POST `.../media` multipart
   - Enviar media_id: POST `.../messages` con `type: 'audio'`
4. Tests con `axios-mock-adapter` o mocks de Jest:
   - `sendText()` construye el payload correcto ✓
   - `downloadAudio()` sigue los dos pasos (metadata → binario) ✓
   - Error 401 de Meta → lanza error descriptivo ✓

**Criterio de done:**
- `npm test -- whatsapp-api.adapter` pasa al 100%
- Ninguna URL de Meta está hardcodeada fuera de este archivo

---

### TASK-010 — AiAgentHttpAdapter + test
**Estimado:** 45 min  
**Dependencias:** TASK-002

**Archivos a crear:**
- `src/adapters/outbound/ai-agent-http.adapter.ts`
- `test/unit/ai-agent-http.adapter.spec.ts`

**Acciones:**
1. Implementar `processText(payload)`:
   - POST `{AI_AGENT_SERVICE_URL}/agent` con `TextAgentPayload`
   - Timeout: 10 segundos (Axios `timeout` option)
   - Mapear respuesta a `AgentResponse`
2. Implementar `processAudio(payload)`:
   - POST `{AI_AGENT_SERVICE_URL}/agent` con `AudioAgentPayload`
   - Timeout: 15 segundos (el audio requiere STT, tarda más)
3. Tests con mocks para:
   - Respuesta texto exitosa → `AgentResponse` con `response_type: 'text'` ✓
   - Respuesta audio exitosa → `AgentResponse` con `response_type: 'audio'` ✓
   - Timeout → lanza `AgentTimeoutError` (error tipado propio) ✓
   - Error 500 del backend → lanza `AgentUnavailableError` ✓

**Criterio de done:**
- `npm test -- ai-agent-http.adapter` pasa al 100%
- Los errores son tipos propios (no string genérico), para que los use cases los capturen tipados

---

### TASK-011 — Wiring NestJS: módulo completo
**Estimado:** 30 min  
**Dependencias:** TASK-008, TASK-009, TASK-010

**Archivos a crear/modificar:**
- `src/whatsapp/whatsapp.module.ts`
- `src/app.module.ts` (modificar)

**Acciones:**
1. Crear `WhatsAppModule` que provea e inyecte:
   - `VerifyWebhookUseCase`
   - `HandleTextMessageUseCase`
   - `HandleAudioMessageUseCase`
   - `MessageDispatcher`
   - `WhatsAppApiAdapter` como `IMessageSender` y `IMediaDownloader`
   - `AiAgentHttpAdapter` como `IAiAgentClient`
   - `HmacSignatureGuard`
   - `WhatsAppController`
2. Usar tokens de inyección (`Symbol`) para los ports, no las clases concretas
3. Importar `WhatsAppModule` en `AppModule`
4. Verificar que `npm run start:dev` levanta y los endpoints responden

**Criterio de done:**
- `GET /health` responde `{ status: 'ok' }` con el servidor corriendo
- `GET /webhook?hub.mode=subscribe&hub.verify_token=TEST&hub.challenge=123` responde `123`
  (con `WHATSAPP_VERIFY_TOKEN=TEST` en `.env`)
- `npm run build` compila sin errores

---

### TASK-012 — Dockerfile + .env.example
**Estimado:** 20 min  
**Dependencias:** TASK-011

**Archivos a crear:**
- `services/whatsapp/Dockerfile`
- `services/whatsapp/.env.example`

**Acciones:**

1. Crear `Dockerfile` multi-stage:
```dockerfile
# Stage 1: build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: production
FROM node:20-alpine AS production
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY --from=builder /app/dist ./dist
EXPOSE 3000
CMD ["node", "dist/main"]
```

2. Crear `.env.example` con todas las variables del módulo (sin valores reales):
```bash
WHATSAPP_VERIFY_TOKEN=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_APP_SECRET=
AI_AGENT_SERVICE_URL=http://ai-agent:8000
PORT=3000
```

**Criterio de done:**
- `docker build -t participa-ai-whatsapp .` construye sin errores
- `docker run --env-file .env participa-ai-whatsapp` levanta el servicio
- Imagen final pesa menos de 200MB

---

## Orden de ejecución recomendado para Claude Code

```
TASK-001 → TASK-002 → TASK-003 → TASK-004 → TASK-005
                    → TASK-006
                    → TASK-007
                    → TASK-009 (paralelo, no depende de 003-007)
                    → TASK-010 (paralelo, no depende de 003-007)
         → TASK-008 (cuando 003-007 estén listos)
         → TASK-011 (cuando 008-010 estén listos)
         → TASK-012
```

---

