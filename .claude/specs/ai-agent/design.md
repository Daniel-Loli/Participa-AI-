# Design — Módulo: ai-agent
**Proyecto:** Participa AI  
**Módulo:** `services/ai-agent/` — Backend IA (Python + FastAPI + LangGraph)  
**Fecha:** 2026-05-24  
**Estado:** BORRADOR — pendiente revisión humana  
**Depende de:** `requirements.md` (aprobado)

---

## 1. Estructura de Archivos

```
services/ai-agent/
├── src/
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── message.py              # Entidad Message (from_hash, type, contenido)
│   │   │   ├── agent_response.py       # Entidad AgentResponse (type, text, audio)
│   │   │   └── user_profile.py         # Entidad UserProfile (name, district, issue)
│   │   ├── ports/
│   │   │   ├── i_llm_client.py         # Port ILlmClient
│   │   │   ├── i_rag_client.py         # Port IRagClient
│   │   │   ├── i_stt_client.py         # Port ISttClient
│   │   │   ├── i_tts_client.py         # Port ITtsClient
│   │   │   └── i_session_store.py      # Port ISessionStore
│   │   └── value_objects/
│   │       ├── message_type.py         # Enum: TEXT | AUDIO
│   │       ├── agent_intent.py         # Enum: ONBOARDING | LEGAL | ESTRATEGA |
│   │       │                           #       OPORTUNIDADES | RED | REDACTOR | GENERAL
│   │       └── rag_collection.py       # Enum: LEGAL | ODS | PROCEDIMIENTOS | CASOS_EXITO
│   │
│   ├── application/
│   │   └── use_cases/
│   │       └── process_message.py      # ProcessMessageUseCase
│   │
│   └── adapters/
│       ├── inbound/
│       │   └── agent_router.py         # FastAPI router: POST /agent, GET /health
│       └── outbound/
│           ├── openai_llm_adapter.py   # ILlmClient → OpenAI gpt-4o-mini (LangChain)
│           ├── openai_stt_adapter.py   # ISttClient → OpenAI Whisper whisper-1
│           ├── openai_tts_adapter.py   # ITtsClient → OpenAI TTS tts-1
│           ├── qdrant_rag_adapter.py   # IRagClient → Qdrant Cloud (langchain-qdrant)
│           └── redis_session_adapter.py # ISessionStore → Redis Cloud (langgraph-redis)
│
├── agents/
│   ├── state.py                        # AgentState TypedDict (estado compartido del grafo)
│   ├── orchestrator.py                 # Grafo LangGraph principal + classify_intent
│   ├── onboarding_node.py              # Nodo ONBOARDING
│   ├── legal_node.py                   # Nodo LEGAL (RAG colección legal)
│   ├── estratega_node.py               # Nodo ESTRATEGA (RAG procedimientos + calendar)
│   ├── oportunidades_node.py           # Nodo OPORTUNIDADES (calendar.json + RAG)
│   ├── red_node.py                     # Nodo RED (directorio.json + casos_exito)
│   ├── redactor_node.py                # Nodo REDACTOR (generación de documentos)
│   └── general_node.py                 # Nodo GENERAL (ODS + glosario + fallback)
│
├── config.py                           # Carga y validación de variables de entorno
├── dependencies.py                     # Contenedor de dependencias (DI manual)
├── main.py                             # FastAPI app factory + lifespan
│
├── tests/
│   ├── unit/
│   │   ├── test_message_entity.py
│   │   ├── test_agent_response_entity.py
│   │   ├── test_process_message_use_case.py
│   │   ├── test_openai_llm_adapter.py
│   │   ├── test_openai_stt_adapter.py
│   │   ├── test_openai_tts_adapter.py
│   │   ├── test_qdrant_rag_adapter.py
│   │   ├── test_redis_session_adapter.py
│   │   ├── test_orchestrator.py
│   │   ├── test_legal_node.py
│   │   ├── test_estratega_node.py
│   │   ├── test_oportunidades_node.py
│   │   ├── test_red_node.py
│   │   ├── test_redactor_node.py
│   │   └── test_general_node.py
│   └── integration/
│       └── test_agent_router.py
│
├── Dockerfile
├── requirements.txt
├── .env.example
└── pytest.ini
```

---

## 2. Domain Layer

### 2.1 Value Objects

```python
# src/domain/value_objects/message_type.py
from enum import Enum

class MessageType(str, Enum):
    TEXT  = "text"
    AUDIO = "audio"

# src/domain/value_objects/agent_intent.py
from enum import Enum

class AgentIntent(str, Enum):
    ONBOARDING   = "onboarding"
    LEGAL        = "legal"
    ESTRATEGA    = "estratega"
    OPORTUNIDADES = "oportunidades"
    RED          = "red"
    REDACTOR     = "redactor"
    GENERAL      = "general"

# src/domain/value_objects/rag_collection.py
from enum import Enum

class RagCollection(str, Enum):
    LEGAL          = "legal"
    ODS            = "ods"
    PROCEDIMIENTOS = "procedimientos"
    CASOS_EXITO    = "casos_exito"
```

### 2.2 Entidades

```python
# src/domain/entities/message.py
from dataclasses import dataclass
from src.domain.value_objects.message_type import MessageType

@dataclass(frozen=True)
class Message:
    from_hash: str        # SHA256 del número de teléfono — nunca el número real
    type: MessageType
    session_id: str       # igual a from_hash (por ahora)
    timestamp: int        # unix timestamp
    text_content: str | None = None   # poblado si type == TEXT
    audio_base64: str | None = None   # poblado si type == AUDIO
    audio_mime_type: str | None = None

    def is_text(self) -> bool:
        return self.type == MessageType.TEXT

    def is_audio(self) -> bool:
        return self.type == MessageType.AUDIO

# src/domain/entities/agent_response.py
from dataclasses import dataclass

@dataclass(frozen=True)
class AgentResponse:
    response_type: str          # "text" | "audio"
    response_text: str | None = None
    response_audio_base64: str | None = None

# src/domain/entities/user_profile.py
from dataclasses import dataclass, field

@dataclass
class UserProfile:
    user_id: str               # session_id / from_hash
    name: str | None = None
    district: str | None = None
    issue: str | None = None
    conversation_stage: str = "ONBOARDING"   # ONBOARDING | ACTIVE

    def is_complete(self) -> bool:
        return bool(self.name and self.district)
```

### 2.3 Ports (interfaces del dominio)

```python
# src/domain/ports/i_llm_client.py
from abc import ABC, abstractmethod

class ILlmClient(ABC):
    @abstractmethod
    async def generate(self, system_prompt: str, user_message: str) -> str:
        """Genera texto usando el LLM configurado."""

# src/domain/ports/i_rag_client.py
from abc import ABC, abstractmethod
from src.domain.value_objects.rag_collection import RagCollection

class RagDocument:
    content: str
    metadata: dict

class IRagClient(ABC):
    @abstractmethod
    async def search(
        self,
        query: str,
        collection: RagCollection,
        top_k: int = 5,
    ) -> list[RagDocument]:
        """Busca en Qdrant por similitud semántica."""

# src/domain/ports/i_stt_client.py
from abc import ABC, abstractmethod

class ISttClient(ABC):
    @abstractmethod
    async def transcribe(self, audio_base64: str, mime_type: str) -> str:
        """Transcribe audio a texto en español."""

# src/domain/ports/i_tts_client.py
from abc import ABC, abstractmethod

class ITtsClient(ABC):
    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """Sintetiza texto a audio MP3. Retorna bytes."""

# src/domain/ports/i_session_store.py
from abc import ABC, abstractmethod
from src.domain.entities.user_profile import UserProfile

class ISessionStore(ABC):
    @abstractmethod
    async def get_profile(self, session_id: str) -> UserProfile | None:
        """Recupera el perfil del usuario desde Redis."""

    @abstractmethod
    async def save_profile(self, profile: UserProfile) -> None:
        """Persiste el perfil del usuario en Redis (TTL 24h)."""
```

**Regla crítica:** Ningún archivo de `src/domain/` puede importar FastAPI, LangChain,
OpenAI SDK, Qdrant SDK, Redis ni ningún framework externo. Solo librerías estándar de Python.

---

## 3. Application Layer

### 3.1 ProcessMessageUseCase

```python
# src/application/use_cases/process_message.py
import base64
from src.domain.entities.message import Message
from src.domain.entities.agent_response import AgentResponse
from src.domain.value_objects.message_type import MessageType
from src.domain.ports.i_stt_client import ISttClient
from src.domain.ports.i_tts_client import ITtsClient
from src.domain.ports.i_session_store import ISessionStore

class ProcessMessageUseCase:
    def __init__(
        self,
        stt_client: ISttClient,
        tts_client: ITtsClient,
        session_store: ISessionStore,
        orchestrator,       # LangGraph compiled graph (importado desde agents/)
    ):
        ...

    async def execute(self, message: Message) -> AgentResponse:
        # 1. Si es audio → transcribir a texto (STT)
        # 2. Cargar perfil de sesión desde Redis
        # 3. Ejecutar grafo LangGraph con estado cargado
        # 4. Si entrada fue audio → sintetizar respuesta con TTS
        # 5. Retornar AgentResponse
```

**Flujo de errores:**
- Si STT falla → lanzar `SttTranscriptionError` (el router devuelve 422)
- Si LangGraph falla → lanzar `OrchestratorError` (el router devuelve 500)
- Si TTS falla → loguear WARNING y devolver respuesta en texto (fallback, sin error HTTP)

---

## 4. Adapters Layer

### 4.1 Inbound — agent_router.py (FastAPI)

```python
# src/adapters/inbound/agent_router.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter()

class AgentRequest(BaseModel):
    from_: str = Field(alias="from")   # número hasheado
    type: str                           # "text" | "audio"
    session_id: str
    timestamp: int
    message: str | None = None
    audio_base64: str | None = None
    audio_mime_type: str | None = None

class AgentResponseDTO(BaseModel):
    response_type: str
    response_text: str | None = None
    response_audio_base64: str | None = None

@router.post("/agent", response_model=AgentResponseDTO)
async def process_message(
    body: AgentRequest,
    use_case: ProcessMessageUseCase = Depends(get_process_message_use_case),
) -> AgentResponseDTO:
    # Construye entidad Message del dominio
    # Llama use_case.execute()
    # Mapea AgentResponse → AgentResponseDTO
    ...

@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "ai-agent", "timestamp": datetime.utcnow().isoformat()}
```

**Validación de entrada:**
- Si `type == "text"` y `message` es None → 422 Unprocessable Entity
- Si `type == "audio"` y `audio_base64` es None → 422 Unprocessable Entity
- Si `type` no es `"text"` ni `"audio"` → 422 Unprocessable Entity

### 4.2 Outbound — openai_llm_adapter.py

```python
# src/adapters/outbound/openai_llm_adapter.py
# Implementa ILlmClient
# - Usa langchain_openai.ChatOpenAI con model=OPENAI_MODEL
# - temperature=0.3 para respuestas consistentes
# - timeout=30s via request_timeout
# - Si timeout → lanza LlmTimeoutError
# - Si error de API (4xx/5xx) → lanza LlmApiError
```

### 4.3 Outbound — openai_stt_adapter.py

```python
# src/adapters/outbound/openai_stt_adapter.py
# Implementa ISttClient
# - Decodifica audio_base64 → bytes
# - Sube a openai.Audio.transcriptions.create(model="whisper-1", language="es")
# - timeout=20s
# - Si timeout → lanza SttTimeoutError
# - Si audio inválido (error 400 de OpenAI) → lanza SttInvalidAudioError
```

### 4.4 Outbound — openai_tts_adapter.py

```python
# src/adapters/outbound/openai_tts_adapter.py
# Implementa ITtsClient
# - Llama openai.audio.speech.create(model="tts-1", voice="alloy", input=text)
# - Retorna bytes del audio MP3
# - timeout=30s
# - Si texto excede 4096 caracteres → truncar con aviso en log
# - Si error de API → lanza TtsApiError
```

### 4.5 Outbound — qdrant_rag_adapter.py

```python
# src/adapters/outbound/qdrant_rag_adapter.py
# Implementa IRagClient
# - Usa langchain_qdrant.QdrantVectorStore
# - Embeddings: langchain_openai.OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL)
# - Colección se mapea desde RagCollection enum → nombre de colección en Qdrant
# - timeout=5s en el cliente httpx de Qdrant
# - Si colección no existe → retornar lista vacía (no crash)
# - Si timeout → retornar lista vacía y loguear WARN
```

### 4.6 Outbound — redis_session_adapter.py

```python
# src/adapters/outbound/redis_session_adapter.py
# Implementa ISessionStore
# - Usa redis.asyncio para operaciones async
# - get_profile(): GET session:{session_id} → deserializa JSON → UserProfile
# - save_profile(): SET session:{session_id} JSON(profile) EX 86400 (TTL 24h)
# - timeout=2s en el cliente Redis
# - Si Redis no disponible → loguear WARN y retornar None (degraded mode)
```

---

## 5. Agents Layer (LangGraph)

### 5.1 Estado compartido del grafo

```python
# agents/state.py
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    session_id: str
    user_message: str                    # texto final (ya transcrito si era audio)
    intent: str | None                   # AgentIntent value
    user_profile: dict                   # UserProfile serializado
    rag_context: list[str]               # chunks recuperados de Qdrant
    tool_data: dict                      # datos de JSONs locales (calendar, directorio, etc.)
    response: str                        # respuesta generada por el nodo activo
    conversation_history: Annotated[list, add_messages]  # historial LangChain messages
```

### 5.2 Orquestador (grafo principal)

```python
# agents/orchestrator.py
# Construcción del StateGraph de LangGraph

# Nodos del grafo:
# - classify_intent: usa LLM para clasificar el mensaje en AgentIntent
# - onboarding_node, legal_node, estratega_node,
#   oportunidades_node, red_node, redactor_node, general_node

# Edges condicionales (desde classify_intent):
# intent == ONBOARDING   → onboarding_node
# intent == LEGAL        → legal_node
# intent == ESTRATEGA    → estratega_node
# intent == OPORTUNIDADES → oportunidades_node
# intent == RED          → red_node
# intent == REDACTOR     → redactor_node
# else                   → general_node

# Todos los nodos → END

# Checkpointer: RedisSaver(redis_client)  ← LangGraph memoria de sesión
# El grafo compilado se inyecta en ProcessMessageUseCase

# classify_intent:
# - system_prompt: instrucción de clasificación con las 7 categorías
# - few-shot examples en el prompt
# - Responde SOLO con el nombre del intent (una palabra)
# - Si responde algo inválido → GENERAL como fallback
```

### 5.3 Nodo ONBOARDING

```python
# agents/onboarding_node.py
# Responsabilidad: recolectar nombre y distrito del usuario
#
# Lógica:
# 1. Verificar qué campos del perfil faltan (nombre o distrito)
# 2. Si no hay nombre → preguntar por nombre
# 3. Si hay nombre pero no distrito → preguntar por distrito
# 4. Si hay nombre y distrito → solicitar descripción de la problemática
#    y transicionar conversation_stage → "ACTIVE"
# 5. Intentar extraer nombre/distrito del mensaje actual antes de preguntar
#    (p. ej., "Hola, soy Carlos de Miraflores" → llenar ambos campos directamente)
# 6. Actualizar state["user_profile"] con los campos recolectados
```

### 5.4 Nodo LEGAL

```python
# agents/legal_node.py
# Responsabilidad: responder consultas normativas con RAG
#
# Lógica:
# 1. Buscar en RagCollection.LEGAL (Qdrant) top-5 chunks más relevantes
# 2. Construir prompt con contexto RAG + mensaje del usuario
# 3. system_prompt: "Eres un asistente legal ciudadano para jóvenes peruanos.
#    Usa solo la legislación peruana provista. No opines sobre política.
#    Responde en lenguaje simple, sin jerga burocrática."
# 4. Llamar LLM y guardar respuesta en state["response"]
# 5. Guardar chunks usados en state["rag_context"]
```

### 5.5 Nodo ESTRATEGA

```python
# agents/estratega_node.py
# Responsabilidad: construir ruta de incidencia personalizada
#
# Lógica:
# 1. Buscar en RagCollection.PROCEDIMIENTOS top-5 chunks relevantes
# 2. Leer data/calendar.json → filtrar por distrito del perfil (si existe)
# 3. Construir prompt con: contexto RAG + oportunidades del calendario
#    + nombre y distrito del usuario
# 4. system_prompt: instruir a generar ruta en pasos numerados (1-5 pasos máx)
# 5. Llamar LLM y guardar en state["response"]
```

### 5.6 Nodo OPORTUNIDADES

```python
# agents/oportunidades_node.py
# Responsabilidad: devolver próximas oportunidades de participación
#
# Lógica:
# 1. Leer data/calendar.json → ordenar por fecha, filtrar futuros
# 2. Tomar las 3 más próximas relevantes al distrito/problemática del usuario
# 3. Buscar en RagCollection.PROCEDIMIENTOS para contexto de cada oportunidad
# 4. Formatear respuesta: para cada oportunidad → fecha, tipo, acción requerida
# 5. Guardar en state["tool_data"] el JSON filtrado para trazabilidad
```

### 5.7 Nodo RED

```python
# agents/red_node.py
# Responsabilidad: conectar al usuario con organizaciones juveniles
#
# Lógica:
# 1. Leer data/directorio.json → filtrar por distrito del perfil (si existe)
# 2. Buscar en RagCollection.CASOS_EXITO por similaridad con la problemática
# 3. Combinar resultados → top-3 organizaciones más relevantes
# 4. Formatear respuesta: nombre, área de trabajo, contacto, caso de éxito relacionado
# 5. Si no hay organizaciones en el distrito → ampliar a nivel Lima/nacional
```

### 5.8 Nodo REDACTOR

```python
# agents/redactor_node.py
# Responsabilidad: generar documentos ciudadanos formales
#
# Lógica:
# 1. Detectar tipo de documento solicitado:
#    - carta → dirigida a funcionario municipal
#    - solicitud → solicitud de información pública (Ley 27806)
#    - propuesta → propuesta de PP
#    - inscripción → inscripción a mesa de concertación
# 2. Cargar datos del funcionario desde data/municipios.json por distrito
# 3. system_prompt: "Genera el documento formal en español peruano estándar.
#    Incluye: lugar, fecha, destinatario, cuerpo, firma."
# 4. Personalizar con nombre y distrito del perfil de sesión
# 5. Llamar LLM → guardar documento completo en state["response"]
```

### 5.9 Nodo GENERAL

```python
# agents/general_node.py
# Responsabilidad: respuestas generales, glosario, ODS, guardrails
#
# Lógica:
# 1. Buscar en RagCollection.ODS y RagCollection.PROCEDIMIENTOS
# 2. Buscar en RagCollection.CASOS_EXITO por contexto
# 3. system_prompt: incluye regla de guardrail explícita:
#    "No emitas opiniones políticas ni sobre candidatos.
#    Solo el marco legal peruano. Si la consulta está fuera del ámbito
#    de participación ciudadana, redirige amablemente."
# 4. Llamar LLM y guardar en state["response"]
```

---

## 6. Configuración y arranque

### 6.1 config.py

```python
# config.py
# Carga todas las variables de entorno al arranque
# Si falta una variable crítica → ValueError con mensaje claro
# Variables críticas (falla si faltan): OPENAI_API_KEY, QDRANT_URL,
#   QDRANT_API_KEY, REDIS_URL
# Variables opcionales con default: OPENAI_MODEL=gpt-4o-mini,
#   OPENAI_TTS_VOICE=alloy, LANGCHAIN_TRACING_V2=false
```

### 6.2 dependencies.py

```python
# dependencies.py
# Contenedor de dependencias (DI manual, sin framework de DI)
# Inicializa una sola vez al arranque de FastAPI (lifespan):
# - OpenAILlmAdapter
# - OpenAISttAdapter
# - OpenAITtsAdapter
# - QdrantRagAdapter
# - RedisSessionAdapter
# - Grafo LangGraph compilado (con RedisSaver)
# - ProcessMessageUseCase (recibe todos los anteriores)
# Expone funciones get_process_message_use_case() para FastAPI Depends()
```

### 6.3 main.py

```python
# main.py
# FastAPI app factory
# lifespan: inicializa dependencies al startup, cierra conexiones al shutdown
# Incluye agent_router con prefix=""
# Configura structlog para logging JSON
# CORS: solo permite origen del servicio whatsapp (AI_AGENT_ALLOWED_ORIGIN)
```

---

## 7. Contratos de API

### Inbound (recibe el servicio)

| Método | Ruta | Request Body | Response Body |
|---|---|---|---|
| `POST` | `/agent` | `AgentRequest` (ver §4.1) | `AgentResponseDTO` |
| `GET` | `/health` | — | `{ "status": "ok", "service": "ai-agent", "timestamp": "..." }` |

### Esquema completo POST /agent

**Request:**
```json
{
  "from": "abc123...sha256",
  "type": "text",
  "session_id": "abc123...sha256",
  "timestamp": 1703000000,
  "message": "¿Cómo puedo participar en el presupuesto participativo?"
}
```

```json
{
  "from": "abc123...sha256",
  "type": "audio",
  "session_id": "abc123...sha256",
  "timestamp": 1703000000,
  "audio_base64": "<base64_del_ogg>",
  "audio_mime_type": "audio/ogg"
}
```

**Response 200:**
```json
{
  "response_type": "text",
  "response_text": "El Presupuesto Participativo es un mecanismo legal..."
}
```

```json
{
  "response_type": "audio",
  "response_audio_base64": "<base64_mp3>"
}
```

**Response 422:** campo requerido ausente o tipo inválido  
**Response 500:** error interno del orquestador (no debería ocurrir con fallbacks activos)

---

## 8. Gestión de errores — Jerarquía de excepciones

```
AiAgentError (base)
├── SttTranscriptionError        # Whisper falla o audio inválido → 422
├── OrchestratorError            # LangGraph falla → 500
├── LlmTimeoutError              # OpenAI LLM timeout → fallback interno
├── LlmApiError                  # OpenAI API 4xx/5xx → fallback interno
├── RagTimeoutError              # Qdrant timeout → nodo continúa sin contexto
├── RagCollectionError           # Colección inexistente → lista vacía
├── TtsApiError                  # TTS falla → fallback a texto
└── SessionStoreError            # Redis falla → modo stateless degradado
```

Todos los errores de adapters outbound son capturados en los nodos LangGraph.
Solo `SttTranscriptionError` y `OrchestratorError` se propagan al router.

---

## 9. Diagrama de Flujo Principal

```
POST /agent
     │
     ▼
[agent_router] — validación Pydantic
     │ 422 si payload inválido
     ▼
[ProcessMessageUseCase]
     │
     ├─ type == AUDIO ──→ [ISttClient.transcribe()] ──FAIL──→ SttTranscriptionError → 422
     │                         │ texto transcrito
     │                         ▼
     ├─ (always) ──────→ [ISessionStore.get_profile()] ──FAIL──→ None (degradado)
     │                         │ UserProfile (o vacío)
     │                         ▼
     │                  [LangGraph Graph.invoke()]
     │                         │
     │                  [classify_intent] ──→ AgentIntent
     │                         │
     │              ┌──────────┼──────────┐──────────┐──────────┐──────────┐
     │              ▼          ▼          ▼          ▼          ▼          ▼
     │        [ONBOARDING] [LEGAL]  [ESTRATEGA] [OPOR.] [RED]  [REDACTOR] [GENERAL]
     │              │          │          │          │      │       │          │
     │              └──────────┴──────────┴──────────┴──────┴───────┴──────────┘
     │                                    │ state["response"]
     │                         ▼
     │                  [ISessionStore.save_profile()] ──FAIL──→ loguear WARN
     │
     ├─ entrada fue AUDIO ──→ [ITtsClient.synthesize()] ──FAIL──→ fallback texto
     │                              │ bytes MP3
     │                              ▼ base64
     ▼
[AgentResponse] → AgentResponseDTO → HTTP 200
```

---

## 10. Variables de Entorno del Módulo

```bash
# OpenAI
OPENAI_API_KEY=                          # crítica
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_WHISPER_MODEL=whisper-1
OPENAI_TTS_MODEL=tts-1
OPENAI_TTS_VOICE=alloy

# Qdrant Cloud
QDRANT_URL=                              # crítica
QDRANT_API_KEY=                          # crítica
QDRANT_COLLECTION_LEGAL=legal
QDRANT_COLLECTION_ODS=ods
QDRANT_COLLECTION_PROCEDIMIENTOS=procedimientos
QDRANT_COLLECTION_CASOS=casos_exito

# Redis Cloud
REDIS_URL=                               # crítica
REDIS_PASSWORD=

# LangSmith
LANGCHAIN_API_KEY=
LANGCHAIN_TRACING_V2=false
LANGCHAIN_PROJECT=participa-ai

# Servicio
PORT=8000
DATA_DIR=../../data                       # ruta a data/*.json relativa al servicio
```

---

## 11. Dependencias Python (requirements.txt)

```
# Framework
fastapi==0.115.*
uvicorn[standard]==0.32.*
pydantic==2.9.*

# LangChain / LangGraph
langchain==0.3.*
langchain-openai==0.2.*
langchain-qdrant==0.2.*
langgraph==0.2.*
langgraph-checkpoint-redis==0.1.*

# OpenAI directo (STT/TTS no tienen wrapper LangChain)
openai==1.55.*

# Redis
redis[asyncio]==5.2.*

# Logging
structlog==24.*

# Testing
pytest==8.*
pytest-asyncio==0.24.*
httpx==0.27.*

# Dev
python-dotenv==1.0.*
```

---

## 12. Dockerfile (multi-stage)

```dockerfile
# Stage 1: build / instalar dependencias
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: producción
FROM python:3.12-slim AS production
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```
