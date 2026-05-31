# tech.md — Participa AI

## Stack tecnológico

### Canal
- **WhatsApp Business API (Meta)** — canal único del MVP
- Webhook en NestJS: GET /webhook (verificación) + POST /webhook (mensajes)
- Soporta mensajes de texto y notas de voz (OGG/OPUS)

### Backend de negocio
- **Node.js + NestJS (TypeScript)** — orquestación de mensajes, webhooks
- Arquitectura hexagonal: domain → application → adapters
- Sin framework de bots; lógica propia de enrutamiento en `MessageDispatcher`

### Backend de IA
- **Python + FastAPI** — microservicio de agentes, expone `POST /agent`
- **LangGraph** — orquestación de agentes como grafo de estados
- **LangChain** — RAG, tools, memory wrappers
- **OpenAI API gpt-4o-mini** — generación de respuestas
- **OpenAI text-embedding-3-small** — embeddings para RAG
- **Qdrant Cloud** — base de datos vectorial para búsqueda semántica
- **LangSmith** — trazabilidad y observabilidad de agentes

### Voz
- **OpenAI Whisper API (whisper-1)** — transcripción OGG → texto (español)
- **OpenAI TTS API (tts-1, voz alloy)** — síntesis texto → audio para respuestas por voz

### Sesiones y Memoria Conversacional
- **Redis Cloud (free tier)** — tres capas de persistencia:
  1. `UserProfile` vía `RedisSessionAdapter` — nombre, distrito, etapa, `awaiting_doc_confirmation`, `awaiting_next_action` (TTL 24h)
  2. `conversation_history` vía `AsyncRedisSaver` (LangGraph checkpointer) — historial acumulativo de mensajes
  3. `last_activity:{session_id}` y `warning_sent:{session_id}` — gestionados por NestJS para session-timeout
- En cada turno: `process_message.py` añade `HumanMessage` al historial antes de invocar; cada nodo añade `AIMessage` al responder
- `ILlmClient.generate_with_history(system_prompt, messages)` pasa el historial completo al LLM en cada llamada
- Sin base de datos relacional ni documental para el MVP
- **CRÍTICO:** `_save_profile` en `process_message.py` debe persistir `awaiting_doc_confirmation` y `awaiting_next_action` — de lo contrario se pierden entre turnos al recargar el perfil desde Redis

### Datos en tiempo real
- **Scraper Python diario 8AM** (GCP Cloud Scheduler, cron `0 13 * * *` UTC = 8AM Lima)
- Fuentes: juventud.gob.pe, munlima.gob.pe, observatorio-juventud.minedu.gob.pe
- Pipeline: scrape → chunk → embed (OpenAI) → Qdrant

### Documentos fuente
- PDFs almacenados en `knowledge-base/` en el repositorio
- Procesados localmente con `pypdf` + `langchain.text_splitter`
- Solo los chunks + vectores se suben a Qdrant (no los PDFs completos)
- Colección `legal`: Ley 26300, Ley 28056 (PP), Ley 27972 (Municipalidades), Ley 27783
- Colección `procedimientos`: Manual SENAJU, Glosario Presupuesto Público
- Colección `ods`: Agenda 2030, Glosario ODS

### Infraestructura
- **Docker** — un Dockerfile multi-stage por servicio
- **GCP Cloud Run** — dos servicios: `participa-whatsapp` (512Mi) y `participa-ai-agent` (1Gi), región us-central1
- **GCP Artifact Registry** — repositorio `participa-ai` para imágenes Docker
- **GCP Secret Manager** — todas las variables secretas (nunca en env vars planas)
- **GCP Cloud Build** — CI/CD automático desde GitHub (`cloudbuild.yaml` en raíz)

## Decisiones de arquitectura

### ¿Por qué arquitectura hexagonal?
La lógica de incidencia ciudadana (el dominio) debe poder probarse sin OpenAI,
sin WhatsApp y sin NestJS. Si el día de mañana el canal cambia de WhatsApp a
Telegram, solo se cambia el adapter, no el dominio. Los ports son contratos;
las implementaciones son intercambiables.

### ¿Por qué dos microservicios separados (Node.js y Python)?
- Node.js es superior para manejar webhooks, I/O concurrente
- Python es el ecosistema natural para IA, LangChain, LangGraph y embeddings
- Separarlos permite escalar el backend de IA independientemente
- Comunicación interna via HTTP (REST), no event bus (simplicidad para hackathon)

### ¿Por qué LangGraph y no implementación propia de agentes?
- Grafo de estados explícito → flujo de agentes auditable y debuggeable
- Integración nativa con LangSmith para trazas end-to-end
- Checkpointing de estado en Redis sin código adicional
- Menos boilerplate que implementar un orquestador desde cero

### ¿Por qué OpenAI directo y no Azure OpenAI?
- Sin pasos de aprobación ni deployments previos — API key funciona al instante
- Mismos modelos (gpt-4o-mini, whisper-1, tts-1, text-embedding-3-small) en una sola cuenta
- Facturación unificada y más predecible
- Sin dependencia de región ni disponibilidad de Azure

### ¿Por qué Qdrant Cloud y no Pinecone o ChromaDB?
- Free tier generoso (1GB) — suficiente para los documentos del hackathon
- API REST nativa — fácil integración sin SDK obligatorio
- LangChain tiene integración oficial `langchain-qdrant`
- Soporte de filtros de metadatos para RAG por colección

### ¿Por qué Redis Cloud y no Cosmos DB o PostgreSQL?
- Sesiones conversacionales son datos efímeros (TTL natural)
- Redis es la solución canónica para estado de sesión en tiempo real
- Free tier (30MB) suficiente para cientos de sesiones activas simultáneas
- LangGraph tiene `RedisSaver` como checkpoint saver oficial

### ¿Por qué GPT-4o-mini y no GPT-4o?
- Costo 10x menor — crítico para un piloto con jóvenes a escala
- Latencia menor — respuestas más rápidas en WhatsApp
- Suficiente para RAG + respuestas conversacionales en español
- GPT-4o queda disponible si se necesita para casos complejos

### ¿Por qué GCP Cloud Run y no Render?
- 2 meses de créditos GCP gratuitos disponibles — costo cero para el hackathon
- Cloud Run escala a cero cuando no hay tráfico (créditos duran más)
- Artifact Registry + Secret Manager + Cloud Build integrados en el mismo ecosistema
- CI/CD automático desde GitHub con `cloudbuild.yaml` sin configuración extra
- Cold starts aceptables para ai-agent porque el webhook de NestJS responde 200 async

## Comunicación entre servicios

```
WhatsApp API
    ↕ webhook HTTPS
Node.js (NestJS) :3000          [GCP Cloud Run — participa-whatsapp, 512Mi]
    ↕ HTTP POST /agent
Python (FastAPI)  :8000          [GCP Cloud Run — participa-ai-agent, 1Gi]
    ↕
OpenAI API + Qdrant Cloud + Redis Cloud
```

## Variables de entorno requeridas
Ver sección 9 del CLAUDE.md para el listado completo.
Nunca hardcodear secrets. Nunca commitear `.env`.

## Timeouts definidos
- POST /webhook → responde 200 a Meta en < 1 segundo
- Node.js → Python /agent: 10s para texto, 15s para audio
- Python → OpenAI LLM: 30s máximo
- Python → OpenAI Whisper: 20s máximo
- Python → Qdrant: 5s máximo
- Python → Redis: 2s máximo

### Exportación de documentos ciudadanos (PDF)
- Cuando el nodo Redactor genera una carta/solicitud/propuesta, `pdf_generator.py` crea un PDF con `reportlab`
- El PDF se devuelve como `response_type: "document"` con `response_pdf_base64` y `response_pdf_filename`
- NestJS lo recibe, sube a Meta `/media`, y envía primero el texto de la carta y luego el PDF como adjunto descargable
- Dependencia: `reportlab==4.*` en `services/ai-agent/requirements.txt`

### UX Conversacional WhatsApp
- `agents/wa_format.py` — dos responsabilidades:
  1. `WA_RULES` — instrucciones de formato inyectadas en todos los system prompts
  2. `clean(text)` — post-procesador que elimina markdown roto (`###`, `**`) antes de enviar
- Reglas de formato: `*negrita*` (un asterisco), listas con `-` o números, sin headers `#`
- Límite de 4 puntos por respuesta; cada respuesta termina con una pregunta para guiar el siguiente paso
- Emojis: máximo 1-2 por mensaje, solo en posición natural
- **Mensajes en partes:** `services/whatsapp/src/application/utils/message-splitter.ts` — `sendInParts()` divide el texto por `\n\n` (mínimo 80 chars por parte) y envía cada parte con 400 ms de delay. Todos los use-cases de texto usan `sendInParts` en lugar de `sendText` directo.

### Mejoras UX (implementadas)
- **Onboarding:** `classify_intent` fuerza onboarding hasta tener nombre Y distrito (no solo nombre). El nodo de onboarding extrae ambos de un solo mensaje.
- **Intención compuesta legal+redactor:** `AgentIntent.LEGAL_REDACTOR` activa `legal_redactor_node.py`, que resuelve ley + solicita confirmación de carta en un mismo turno. Se detecta cuando el mensaje contiene términos legales Y términos de documento simultáneamente.
- **Confirmación antes de PDF:** `redactor_node.py` verifica `state["doc_confirmed"]` antes de generar. Si no hay confirmación, responde con pregunta y activa `profile["awaiting_doc_confirmation"]=True`. El siguiente turno con respuesta afirmativa redirige al redactor con `doc_confirmed=True`.

## Testing
- Node.js: Jest + Supertest. Cobertura mínima 80%
- Python: pytest + httpx. Cobertura mínima 80%
- Mocks para todos los servicios externos (OpenAI, Qdrant, Redis, Meta Graph API)
- Tests de integración con mocks, no con servicios reales
