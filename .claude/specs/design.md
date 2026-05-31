# Design — Módulo: webhook
**Proyecto:** Participa AI  
**Módulo:** `services/whatsapp/` — Webhook WhatsApp Business API  
**Fecha:** 2025  
**Estado:** BORRADOR — pendiente revisión humana  
**Depende de:** `requirements-webhook.md` (aprobado)

---

## 1. Estructura de Archivos

```
services/whatsapp/
├── src/
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── message.entity.ts          # Entidad Message (tipo, from, contenido)
│   │   │   └── session.entity.ts          # Entidad Session (session_id, timestamp)
│   │   ├── ports/
│   │   │   ├── message-sender.port.ts     # IMessageSender (interfaz de envío)
│   │   │   ├── ai-agent.port.ts           # IAiAgentClient (interfaz hacia Python)
│   │   │   └── media-downloader.port.ts   # IMediaDownloader (descarga de audio)
│   │   └── value-objects/
│   │       ├── message-type.vo.ts         # Enum: TEXT | AUDIO | UNSUPPORTED
│   │       └── whatsapp-number.vo.ts      # Validación de número E.164
│   │
│   ├── application/
│   │   └── use-cases/
│   │       ├── handle-text-message.use-case.ts   # CU-01
│   │       ├── handle-audio-message.use-case.ts  # CU-02
│   │       ├── verify-webhook.use-case.ts         # CU-03
│   │       └── handle-unsupported.use-case.ts    # FR-08
│   │
│   └── adapters/
│       ├── inbound/
│       │   └── whatsapp.controller.ts     # GET /webhook, POST /webhook, GET /health
│       ├── outbound/
│       │   ├── whatsapp-api.adapter.ts    # Implementa IMessageSender + IMediaDownloader
│       │   └── ai-agent-http.adapter.ts   # Implementa IAiAgentClient (HTTP hacia FastAPI)
│       └── guards/
│           └── hmac-signature.guard.ts    # Valida X-Hub-Signature-256 (FR-09)
│
├── test/
│   ├── unit/
│   │   ├── verify-webhook.use-case.spec.ts
│   │   ├── handle-text-message.use-case.spec.ts
│   │   ├── handle-audio-message.use-case.spec.ts
│   │   └── hmac-signature.guard.spec.ts
│   └── integration/
│       └── whatsapp.controller.spec.ts
│
├── Dockerfile
├── package.json
├── tsconfig.json
└── .env.example
```

---

## 2. Domain Layer

### 2.1 Entidad: Message

```typescript
// src/domain/entities/message.entity.ts
export class Message {
  constructor(
    readonly from: string,           // número WhatsApp E.164
    readonly type: MessageType,      // TEXT | AUDIO | UNSUPPORTED
    readonly sessionId: string,      // igual a from (por ahora)
    readonly timestamp: number,      // unix timestamp
    readonly messageId: string,      // ID único de Meta (para idempotencia)
    readonly textContent?: string,   // solo si type === TEXT
    readonly audioId?: string,       // solo si type === AUDIO (media_id de Meta)
  ) {}

  isText(): boolean { return this.type === MessageType.TEXT; }
  isAudio(): boolean { return this.type === MessageType.AUDIO; }
}
```

### 2.2 Value Object: MessageType

```typescript
// src/domain/value-objects/message-type.vo.ts
export enum MessageType {
  TEXT        = 'text',
  AUDIO       = 'audio',
  UNSUPPORTED = 'unsupported',
}

export function parseMessageType(raw: string): MessageType {
  if (raw === 'text')  return MessageType.TEXT;
  if (raw === 'audio') return MessageType.AUDIO;
  return MessageType.UNSUPPORTED;
}
```

### 2.3 Ports (interfaces del dominio)

```typescript
// src/domain/ports/message-sender.port.ts
export interface IMessageSender {
  sendText(to: string, text: string): Promise<void>;
  sendAudio(to: string, audioBase64: string, mimeType: string): Promise<void>;
}

// src/domain/ports/ai-agent.port.ts
export interface IAiAgentClient {
  processText(payload: TextAgentPayload): Promise<AgentResponse>;
  processAudio(payload: AudioAgentPayload): Promise<AgentResponse>;
}

export interface TextAgentPayload {
  from: string;
  message: string;
  type: 'text';
  session_id: string;
  timestamp: number;
}

export interface AudioAgentPayload {
  from: string;
  audio_base64: string;
  audio_mime_type: string;
  type: 'audio';
  session_id: string;
  timestamp: number;
}

export interface AgentResponse {
  response_text?: string;
  response_audio_base64?: string;
  response_type: 'text' | 'audio';
}

// src/domain/ports/media-downloader.port.ts
export interface IMediaDownloader {
  downloadAudio(mediaId: string): Promise<{ buffer: Buffer; mimeType: string }>;
}
```

---

## 3. Application Layer — Casos de Uso

### 3.1 VerifyWebhookUseCase (CU-03)

```typescript
// src/application/use-cases/verify-webhook.use-case.ts
export class VerifyWebhookUseCase {
  execute(mode: string, token: string, challenge: string): string | null {
    if (mode === 'subscribe' && token === process.env.WHATSAPP_VERIFY_TOKEN) {
      return challenge;
    }
    return null;
  }
}
```

### 3.2 HandleTextMessageUseCase (CU-01)

```typescript
// src/application/use-cases/handle-text-message.use-case.ts
export class HandleTextMessageUseCase {
  constructor(
    private readonly aiAgent: IAiAgentClient,
    private readonly sender: IMessageSender,
  ) {}

  async execute(message: Message): Promise<void> {
    const response = await this.aiAgent.processText({
      from: message.from,
      message: message.textContent!,
      type: 'text',
      session_id: message.sessionId,
      timestamp: message.timestamp,
    });
    if (response.response_type === 'audio' && response.response_audio_base64) {
      await this.sender.sendAudio(message.from, response.response_audio_base64, 'audio/ogg');
    } else {
      await this.sender.sendText(message.from, response.response_text!);
    }
  }
}
```

### 3.3 HandleAudioMessageUseCase (CU-02)

```typescript
// src/application/use-cases/handle-audio-message.use-case.ts
export class HandleAudioMessageUseCase {
  constructor(
    private readonly downloader: IMediaDownloader,
    private readonly aiAgent: IAiAgentClient,
    private readonly sender: IMessageSender,
  ) {}

  async execute(message: Message): Promise<void> {
    const { buffer, mimeType } = await this.downloader.downloadAudio(message.audioId!);
    const audioBase64 = buffer.toString('base64');

    const response = await this.aiAgent.processAudio({
      from: message.from,
      audio_base64: audioBase64,
      audio_mime_type: mimeType,
      type: 'audio',
      session_id: message.sessionId,
      timestamp: message.timestamp,
    });

    if (response.response_type === 'audio' && response.response_audio_base64) {
      await this.sender.sendAudio(message.from, response.response_audio_base64, 'audio/ogg');
    } else {
      await this.sender.sendText(message.from, response.response_text!);
    }
  }
}
```

---

## 4. Adapter Layer

### 4.1 Controller (inbound)

```typescript
// src/adapters/inbound/whatsapp.controller.ts
@Controller()
export class WhatsAppController {

  // CU-03 — Meta handshake
  @Get('webhook')
  verifyWebhook(@Query() query: VerifyWebhookDto, @Res() res: Response) {
    const challenge = this.verifyUseCase.execute(
      query['hub.mode'], query['hub.verify_token'], query['hub.challenge']
    );
    if (!challenge) return res.status(403).send('Forbidden');
    return res.status(200).send(challenge);
  }

  // CU-01 / CU-02 — Recepción de mensajes
  @Post('webhook')
  @UseGuards(HmacSignatureGuard)          // FR-09
  async receiveMessage(@Body() body: WhatsAppPayloadDto, @Res() res: Response) {
    res.status(200).send('OK');           // NFR-01: responder inmediatamente
    await this.messageDispatcher.dispatch(body);  // procesar de forma asíncrona
  }

  // FR-10 — Health check
  @Get('health')
  healthCheck() {
    return { status: 'ok', service: 'whatsapp-webhook', timestamp: new Date().toISOString() };
  }
}
```

### 4.2 MessageDispatcher (lógica de enrutamiento)

```typescript
// src/adapters/inbound/message.dispatcher.ts
export class MessageDispatcher {
  private processedIds = new Map<string, number>(); // cache idempotencia (FR-06 / NFR-06)

  async dispatch(body: WhatsAppPayloadDto): Promise<void> {
    const raw = body?.entry?.[0]?.changes?.[0]?.value?.messages?.[0];
    if (!raw) return;

    // Idempotencia: ignorar mensaje_id ya procesado
    if (this.isAlreadyProcessed(raw.id)) return;
    this.markAsProcessed(raw.id);

    const message = this.parseMessage(raw);

    switch (message.type) {
      case MessageType.TEXT:
        await this.handleText.execute(message); break;
      case MessageType.AUDIO:
        await this.handleAudio.execute(message); break;
      default:
        await this.sender.sendText(message.from, UNSUPPORTED_MESSAGE_TEXT);
    }
  }

  private isAlreadyProcessed(messageId: string): boolean {
    const ts = this.processedIds.get(messageId);
    if (!ts) return false;
    if (Date.now() - ts > 5 * 60 * 1000) { // TTL 5 min
      this.processedIds.delete(messageId);
      return false;
    }
    return true;
  }
}

const UNSUPPORTED_MESSAGE_TEXT =
  'Hola, por ahora solo puedo recibir mensajes de texto o notas de voz. ¿Cuéntame en qué te puedo ayudar?';
```

### 4.3 HmacSignatureGuard (seguridad FR-09)

```typescript
// src/adapters/guards/hmac-signature.guard.ts
@Injectable()
export class HmacSignatureGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const req = context.switchToHttp().getRequest();
    const signature = req.headers['x-hub-signature-256'] as string;
    if (!signature) return false;

    const expected = 'sha256=' + createHmac('sha256', process.env.WHATSAPP_APP_SECRET!)
      .update(JSON.stringify(req.body))
      .digest('hex');

    return timingSafeEqual(Buffer.from(signature), Buffer.from(expected));
  }
}
```

### 4.4 WhatsAppApiAdapter (outbound)

```typescript
// src/adapters/outbound/whatsapp-api.adapter.ts
// Implementa IMessageSender + IMediaDownloader
// - sendText(): POST graph.facebook.com/.../messages con type:"text"
// - sendAudio(): sube buffer a Media Upload API, luego envía media_id
// - downloadAudio(): GET graph.facebook.com/{media_id} → URL → descarga binario
```

### 4.5 AiAgentHttpAdapter (outbound)

```typescript
// src/adapters/outbound/ai-agent-http.adapter.ts
// Implementa IAiAgentClient
// - processText(): POST {AI_AGENT_SERVICE_URL}/agent con TextAgentPayload, timeout 10s
// - processAudio(): POST {AI_AGENT_SERVICE_URL}/agent con AudioAgentPayload, timeout 15s
// - El backend destino es Python FastAPI + LangGraph (services/ai-agent)
// - Si timeout (ECONNABORTED) → lanza AgentTimeoutError
// - Si HTTP 5xx → lanza AgentUnavailableError con statusCode
// - AI_AGENT_SERVICE_URL=http://localhost:8000 en dev, URL de Render en producción
```

---

## 5. DTOs de Entrada

```typescript
// VerifyWebhookDto
class VerifyWebhookDto {
  @IsString() 'hub.mode': string;
  @IsString() 'hub.verify_token': string;
  @IsString() 'hub.challenge': string;
}

// WhatsAppPayloadDto — estructura del POST de Meta
class WhatsAppPayloadDto {
  object: string;   // siempre "whatsapp_business_account"
  entry: Array<{
    changes: Array<{
      value: {
        messages?: Array<{
          id: string;
          from: string;
          type: string;
          timestamp: string;
          text?: { body: string };
          audio?: { id: string; mime_type: string };
        }>;
      };
    }>;
  }>;
}
```

---

## 6. Contratos de API

### Inbound (recibe el servicio)

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/webhook` | Verificación Meta handshake |
| `POST` | `/webhook` | Recepción de mensajes WhatsApp |
| `GET` | `/health` | Health check del servicio |

### Outbound (llama el servicio)

| Destino | Método | Ruta | Descripción |
|---|---|---|---|
| Meta Graph API | `GET` | `/v18.0/{media_id}` | Obtener URL de audio |
| Meta Graph API | `GET` | `<url_del_audio>` | Descargar binario del audio |
| Meta Graph API | `POST` | `/v18.0/{phone_id}/messages` | Enviar mensaje al usuario |
| Meta Graph API | `POST` | `/v18.0/{phone_id}/media` | Subir audio de respuesta |
| Backend IA | `POST` | `/agent` | Enviar mensaje a los agentes |

---

## 7. Variables de Entorno del Módulo

```bash
# WhatsApp Business API
WHATSAPP_VERIFY_TOKEN=         # token para handshake con Meta
WHATSAPP_ACCESS_TOKEN=         # Bearer token para Graph API
WHATSAPP_PHONE_NUMBER_ID=      # ID del número de WhatsApp Business
WHATSAPP_APP_SECRET=           # para validar firma HMAC-SHA256

# Backend IA (Python FastAPI + LangGraph)
AI_AGENT_SERVICE_URL=http://localhost:8000  # dev; URL de Render en producción

PORT=3000
NODE_ENV=development
```

---

## 8. Diagrama de Flujo de Decisión

```
POST /webhook
     │
     ▼
[HmacSignatureGuard] ──FAIL──→ 401 Unauthorized
     │ OK
     ▼
res.status(200).send('OK')   ← Meta queda satisfecho aquí
     │
     ▼ (asíncrono)
[MessageDispatcher]
     │
     ├─ ¿message_id ya procesado? ──SI──→ ignorar
     │
     ▼ NO
 detectar tipo
     │
     ├── "text"  ──→ HandleTextMessageUseCase
     │                    │
     │                    ▼
     │              IAiAgentClient.processText()
     │                    │
     │                    ▼
     │              IMessageSender.sendText() o sendAudio()
     │
     ├── "audio" ──→ HandleAudioMessageUseCase
     │                    │
     │                    ▼
     │              IMediaDownloader.downloadAudio()
     │                    │
     │                    ▼
     │              IAiAgentClient.processAudio()
     │                    │
     │                    ▼
     │              IMessageSender.sendText() o sendAudio()
     │
     └── otro   ──→ IMessageSender.sendText(UNSUPPORTED_MESSAGE_TEXT)
```

---

## 9. Dependencias npm

```json
{
  "dependencies": {
    "@nestjs/common": "^10",
    "@nestjs/core": "^10",
    "@nestjs/platform-express": "^10",
    "axios": "^1.6",
    "class-validator": "^0.14",
    "class-transformer": "^0.5"
  },
  "devDependencies": {
    "@nestjs/testing": "^10",
    "jest": "^29",
    "supertest": "^6",
    "ts-jest": "^29",
    "@types/node": "^20"
  }
}
```

---

