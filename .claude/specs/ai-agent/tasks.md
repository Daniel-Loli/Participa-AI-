# Tasks — Módulo: ai-agent
**Proyecto:** Participa AI  
**Módulo:** `services/ai-agent/` — Backend IA (Python + FastAPI + LangGraph)  
**Fecha:** 2026-05-24  
**Estado:** ✅ COMPLETO — 24/24 tareas implementadas  
**Depende de:** `design.md` (aprobado)

---

## Resumen de tareas

| ID | Tarea | Estado |
|---|---|---|
| TASK-001 | Scaffolding del proyecto Python + FastAPI | ✅ |
| TASK-002 | Domain — value objects + tests | ✅ |
| TASK-003 | Domain — entities + tests | ✅ |
| TASK-004 | Domain — ports (5 interfaces ABC) | ✅ |
| TASK-005 | config.py — carga y validación de env vars | ✅ |
| TASK-006 | agents/state.py — AgentState TypedDict | ✅ |
| TASK-007 | OpenAILlmAdapter + tests | ✅ |
| TASK-008 | OpenAISttAdapter + tests | ✅ |
| TASK-009 | OpenAITtsAdapter + tests | ✅ |
| TASK-010 | QdrantRagAdapter + tests | ✅ |
| TASK-011 | RedisSessionAdapter + tests | ✅ |
| TASK-012 | classify_intent (nodo clasificador) + tests | ✅ |
| TASK-013 | Nodo ONBOARDING + tests | ✅ |
| TASK-014 | Nodo LEGAL + tests | ✅ |
| TASK-015 | Nodo ESTRATEGA + tests | ✅ |
| TASK-016 | Nodo OPORTUNIDADES + tests | ✅ |
| TASK-017 | Nodo RED + tests | ✅ |
| TASK-018 | Nodo REDACTOR + tests | ✅ |
| TASK-019 | Nodo GENERAL + guardrails + tests | ✅ |
| TASK-020 | Orchestrator LangGraph (grafo completo) + tests | ✅ |
| TASK-021 | ProcessMessageUseCase + tests | ✅ |
| TASK-022 | agent_router.py (FastAPI) + tests integración | ✅ |
| TASK-023 | dependencies.py + main.py (wiring completo) | ✅ |
| TASK-024 | Dockerfile + requirements.txt + .env.example | ✅ |

**Total: 24/24 tareas completadas**

---

## Orden de ejecución recomendado

```
TASK-001
    └─ TASK-002 → TASK-003 → TASK-004 ─┬─ TASK-007 (paralelo)
    │                                    ├─ TASK-008 (paralelo)
    │                                    ├─ TASK-009 (paralelo)
    │                                    ├─ TASK-010 (paralelo)
    │                                    └─ TASK-011 (paralelo)
    └─ TASK-005 (paralelo desde TASK-001)
    └─ TASK-006 (deps TASK-002) ─┬─ TASK-012 (deps también TASK-007)
                                  ├─ TASK-013 (paralelo)
                                  ├─ TASK-014 (paralelo)
                                  ├─ TASK-015 (paralelo)
                                  ├─ TASK-016 (paralelo)
                                  ├─ TASK-017 (paralelo)
                                  ├─ TASK-018 (paralelo)
                                  └─ TASK-019 (paralelo)
                                      └─ TASK-020 (todos los nodos listos)
                                              └─ TASK-021
                                                     └─ TASK-022
                                                            └─ TASK-023
                                                                   └─ TASK-024
```

---

## Detalle de Tareas

---

### TASK-001 — Scaffolding del proyecto Python + FastAPI
**Estimado:** 45 min  
**Dependencias:** ninguna

**Archivos a crear:**
- `services/ai-agent/main.py` (FastAPI app mínima)
- `services/ai-agent/requirements.txt`
- `services/ai-agent/pytest.ini`
- `services/ai-agent/.env.example` (skeleton vacío)
- `services/ai-agent/src/__init__.py`
- `services/ai-agent/src/domain/__init__.py`
- `services/ai-agent/src/domain/entities/__init__.py`
- `services/ai-agent/src/domain/ports/__init__.py`
- `services/ai-agent/src/domain/value_objects/__init__.py`
- `services/ai-agent/src/application/__init__.py`
- `services/ai-agent/src/application/use_cases/__init__.py`
- `services/ai-agent/src/adapters/__init__.py`
- `services/ai-agent/src/adapters/inbound/__init__.py`
- `services/ai-agent/src/adapters/outbound/__init__.py`
- `services/ai-agent/agents/__init__.py`
- `services/ai-agent/tests/__init__.py`
- `services/ai-agent/tests/unit/__init__.py`
- `services/ai-agent/tests/integration/__init__.py`

**Acciones:**
1. Crear `requirements.txt` con las versiones exactas del design §11
2. Crear `main.py` con:
   ```python
   from fastapi import FastAPI
   app = FastAPI(title="Participa AI — Agent Service")
   @app.get("/health")
   async def health(): return {"status": "ok", "service": "ai-agent"}
   ```
3. Crear `pytest.ini`:
   ```ini
   [pytest]
   asyncio_mode = auto
   testpaths = tests
   ```
4. Crear todos los `__init__.py` de paquetes (pueden estar vacíos)
5. Instalar dependencias: `pip install -r requirements.txt`

**Criterio de done:**
- `uvicorn main:app --reload` arranca sin errores
- `GET /health` responde `{"status": "ok", "service": "ai-agent"}`
- `pytest tests/` corre sin errores (0 tests collected está bien aquí)
- `python -m mypy src/ --ignore-missing-imports` no lanza errores de import

---

### TASK-002 — Domain — value objects + tests
**Estimado:** 45 min  
**Dependencias:** TASK-001

**Archivos a crear:**
- `src/domain/value_objects/message_type.py`
- `src/domain/value_objects/agent_intent.py`
- `src/domain/value_objects/rag_collection.py`
- `tests/unit/test_value_objects.py`

**Acciones:**
1. Implementar `MessageType(str, Enum)` con valores `TEXT = "text"`, `AUDIO = "audio"`
2. Implementar `AgentIntent(str, Enum)` con los 7 valores del design §2.1
3. Implementar `RagCollection(str, Enum)` con los 4 valores del design §2.1
4. Usar `str, Enum` (no solo `Enum`) para que sean serializables a JSON por Pydantic
5. Tests para:
   - `MessageType("text") == MessageType.TEXT` ✓
   - `AgentIntent("legal") == AgentIntent.LEGAL` ✓
   - `AgentIntent("invalido")` → lanza `ValueError` ✓
   - Todos los valores del enum son strings (compatibles con JSON) ✓

**Regla crítica:** Estos archivos no pueden importar nada externo al módulo. Solo `enum`.

**Criterio de done:**
- `pytest tests/unit/test_value_objects.py` pasa al 100%
- Ningún import externo en `src/domain/value_objects/`

---

### TASK-003 — Domain — entities + tests
**Estimado:** 45 min  
**Dependencias:** TASK-002

**Archivos a crear:**
- `src/domain/entities/message.py`
- `src/domain/entities/agent_response.py`
- `src/domain/entities/user_profile.py`
- `tests/unit/test_entities.py`

**Acciones:**
1. Implementar `Message` como `@dataclass(frozen=True)` con campos del design §2.2
   - `from_hash: str` — SHA256 del número (nunca el número real)
   - `type: MessageType`
   - `session_id: str`
   - `timestamp: int`
   - `text_content: str | None = None`
   - `audio_base64: str | None = None`
   - `audio_mime_type: str | None = None`
   - Métodos: `is_text() -> bool`, `is_audio() -> bool`
2. Implementar `AgentResponse` como `@dataclass(frozen=True)` con campos del design §2.2
3. Implementar `UserProfile` como `@dataclass` (mutable) con campos del design §2.2
   - Método `is_complete() -> bool` (True si name Y district están poblados)
4. Tests para:
   - `Message(type=TEXT)` → `is_text()` True, `is_audio()` False ✓
   - `Message` es inmutable (asignar campo → `FrozenInstanceError`) ✓
   - `UserProfile(name=None)` → `is_complete()` False ✓
   - `UserProfile(name="Carlos", district="Miraflores")` → `is_complete()` True ✓
   - `AgentResponse(response_type="text")` con `response_text=None` es válido ✓

**Regla crítica:** Solo imports de `dataclasses`, `__future__`, y los value objects del dominio.

**Criterio de done:**
- `pytest tests/unit/test_entities.py` pasa al 100%
- Ningún import de frameworks en `src/domain/entities/`

---

### TASK-004 — Domain — ports (5 interfaces ABC)
**Estimado:** 30 min  
**Dependencias:** TASK-003

**Archivos a crear:**
- `src/domain/ports/i_llm_client.py`
- `src/domain/ports/i_rag_client.py`
- `src/domain/ports/i_stt_client.py`
- `src/domain/ports/i_tts_client.py`
- `src/domain/ports/i_session_store.py`

**Acciones:**
1. Implementar los 5 ports exactamente como están definidos en el design §2.3
2. Usar `abc.ABC` y `@abstractmethod` para cada interface
3. Incluir en `i_rag_client.py` el dataclass `RagDocument(content: str, metadata: dict)`
4. Todos los métodos abstractos deben ser `async`
5. No hay tests para interfaces puras (no hay lógica que testear)

**Regla crítica:** Solo imports de `abc`, `__future__`, y tipos del dominio propio.
No importar `langchain`, `openai`, `redis` ni ningún framework en esta carpeta.

**Criterio de done:**
- `python -c "from src.domain.ports.i_llm_client import ILlmClient"` funciona sin error
- Ídem para los otros 4 ports
- Ningún import externo en `src/domain/ports/`

---

### TASK-005 — config.py — carga y validación de env vars
**Estimado:** 30 min  
**Dependencias:** TASK-001

**Archivos a crear:**
- `config.py`
- `tests/unit/test_config.py`

**Acciones:**
1. Implementar clase `Config` usando `pydantic_settings.BaseSettings`:
   ```python
   class Config(BaseSettings):
       openai_api_key: str
       openai_model: str = "gpt-4o-mini"
       openai_embedding_model: str = "text-embedding-3-small"
       openai_whisper_model: str = "whisper-1"
       openai_tts_model: str = "tts-1"
       openai_tts_voice: str = "alloy"
       qdrant_url: str
       qdrant_api_key: str
       qdrant_collection_legal: str = "legal"
       qdrant_collection_ods: str = "ods"
       qdrant_collection_procedimientos: str = "procedimientos"
       qdrant_collection_casos: str = "casos_exito"
       redis_url: str
       redis_password: str = ""
       langchain_api_key: str = ""
       langchain_tracing_v2: bool = False
       langchain_project: str = "participa-ai"
       port: int = 8000
       data_dir: str = "../../data"
   ```
2. Exportar instancia singleton: `config = Config()`
3. Si falta `OPENAI_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY` o `REDIS_URL` →
   `pydantic_settings` lanza `ValidationError` con mensaje claro al arranque
4. Tests (usando `monkeypatch` de pytest para simular env vars):
   - Config con todas las vars críticas presentes → instancia correctamente ✓
   - Config sin `OPENAI_API_KEY` → lanza `ValidationError` ✓
   - Config sin `QDRANT_URL` → lanza `ValidationError` ✓
   - Config usa defaults cuando vars opcionales están ausentes ✓

**Criterio de done:**
- `pytest tests/unit/test_config.py` pasa al 100%
- `python -c "from config import config"` falla con mensaje claro si faltan vars

---

### TASK-006 — agents/state.py — AgentState TypedDict
**Estimado:** 20 min  
**Dependencias:** TASK-002

**Archivos a crear:**
- `agents/state.py`
- `tests/unit/test_state.py`

**Acciones:**
1. Implementar `AgentState` como `TypedDict` con los campos del design §5.1:
   ```python
   class AgentState(TypedDict):
       session_id: str
       user_message: str
       intent: str | None          # valor de AgentIntent
       user_profile: dict          # UserProfile serializado como dict
       rag_context: list[str]
       tool_data: dict
       response: str
       conversation_history: Annotated[list, add_messages]
   ```
2. Usar `langgraph.graph.message.add_messages` para el historial
3. Tests:
   - Un dict compatible con `AgentState` pasa type checking ✓
   - `add_messages` acumula mensajes correctamente (test funcional) ✓

**Criterio de done:**
- `python -c "from agents.state import AgentState"` funciona
- `pytest tests/unit/test_state.py` pasa

---

### TASK-007 — OpenAILlmAdapter + tests
**Estimado:** 60 min  
**Dependencias:** TASK-004

**Archivos a crear:**
- `src/adapters/outbound/openai_llm_adapter.py`
- `tests/unit/test_openai_llm_adapter.py`

**Acciones:**
1. Implementar `OpenAILlmAdapter(ILlmClient)`:
   - Usar `langchain_openai.ChatOpenAI` con `model=config.openai_model`, `temperature=0.3`
   - Método `generate(system_prompt, user_message) -> str`
   - Construir `[SystemMessage(system_prompt), HumanMessage(user_message)]`
   - `request_timeout=30`
   - Si `openai.APITimeoutError` → lanzar `LlmTimeoutError` (excepción propia)
   - Si `openai.APIError` → lanzar `LlmApiError` con código de estado
2. Definir `LlmTimeoutError` y `LlmApiError` en un archivo `src/adapters/outbound/errors.py`
3. Tests con `unittest.mock.AsyncMock` (mock del cliente LangChain):
   - Llamada exitosa → retorna string de respuesta ✓
   - `APITimeoutError` → `LlmTimeoutError` ✓
   - `APIError` (status 429) → `LlmApiError` ✓
   - System prompt se pasa como `SystemMessage` ✓

**Criterio de done:**
- `pytest tests/unit/test_openai_llm_adapter.py` pasa al 100%
- El adapter implementa `ILlmClient` (se puede hacer `isinstance(adapter, ILlmClient)`)

---

### TASK-008 — OpenAISttAdapter + tests
**Estimado:** 60 min  
**Dependencias:** TASK-004

**Archivos a crear:**
- `src/adapters/outbound/openai_stt_adapter.py`
- `tests/unit/test_openai_stt_adapter.py`

**Acciones:**
1. Implementar `OpenAISttAdapter(ISttClient)`:
   - Recibe `audio_base64: str` y `mime_type: str`
   - Decodifica base64 → `bytes`
   - Crea `io.BytesIO` con los bytes y le asigna `name = "audio.ogg"`
   - Llama `openai.audio.transcriptions.create(model="whisper-1", file=..., language="es")`
   - Usa cliente `openai.AsyncOpenAI(timeout=20)`
   - Retorna `transcription.text`
   - Si timeout → `SttTimeoutError`
   - Si `openai.BadRequestError` (audio inválido) → `SttInvalidAudioError`
2. Añadir `SttTimeoutError` y `SttInvalidAudioError` a `errors.py`
3. Tests con mock de `openai.AsyncOpenAI`:
   - Audio base64 válido → retorna texto transcrito ✓
   - `AsyncTimeoutError` → `SttTimeoutError` ✓
   - `BadRequestError` → `SttInvalidAudioError` ✓
   - El archivo enviado a Whisper tiene `name = "audio.ogg"` ✓

**Criterio de done:**
- `pytest tests/unit/test_openai_stt_adapter.py` pasa al 100%

---

### TASK-009 — OpenAITtsAdapter + tests
**Estimado:** 45 min  
**Dependencias:** TASK-004

**Archivos a crear:**
- `src/adapters/outbound/openai_tts_adapter.py`
- `tests/unit/test_openai_tts_adapter.py`

**Acciones:**
1. Implementar `OpenAITtsAdapter(ITtsClient)`:
   - `synthesize(text: str) -> bytes`
   - Usar `openai.AsyncOpenAI(timeout=30)`
   - `openai.audio.speech.create(model="tts-1", voice="alloy", input=text, response_format="mp3")`
   - Si `len(text) > 4096` → truncar a 4096 caracteres, loguear WARN
   - Retornar `response.content` (bytes del MP3)
   - Si error de API → `TtsApiError`
2. Añadir `TtsApiError` a `errors.py`
3. Tests:
   - Texto normal → retorna bytes ✓
   - Texto > 4096 chars → trunca y loguea WARN ✓
   - Error de API → `TtsApiError` ✓

**Criterio de done:**
- `pytest tests/unit/test_openai_tts_adapter.py` pasa al 100%

---

### TASK-010 — QdrantRagAdapter + tests
**Estimado:** 60 min  
**Dependencias:** TASK-004

**Archivos a crear:**
- `src/adapters/outbound/qdrant_rag_adapter.py`
- `tests/unit/test_qdrant_rag_adapter.py`

**Acciones:**
1. Implementar `QdrantRagAdapter(IRagClient)`:
   - Constructor recibe `qdrant_url`, `qdrant_api_key`, `openai_api_key`, `embedding_model`
   - Usar `langchain_openai.OpenAIEmbeddings(model=embedding_model)`
   - Método `search(query, collection, top_k=5) -> list[RagDocument]`
   - Crear `langchain_qdrant.QdrantVectorStore` por cada colección (o cachear por nombre)
   - Mapear `RagCollection` enum → nombre de colección en Qdrant usando config
   - Timeout de 5s: configurar `httpx.Timeout(5.0)` en el cliente Qdrant
   - Si colección no existe (error 404) → retornar `[]` y loguear WARN
   - Si timeout → `RagTimeoutError` + retornar `[]`
   - Mapear resultados de LangChain a `RagDocument(content=..., metadata=...)`
2. Añadir `RagTimeoutError` a `errors.py`
3. Tests con mock de `langchain_qdrant.QdrantVectorStore`:
   - Búsqueda exitosa → lista de `RagDocument` ✓
   - Colección inexistente → lista vacía sin excepción ✓
   - Timeout → lista vacía sin excepción ✓
   - Mapeo correcto de `RagCollection.LEGAL` → nombre `"legal"` ✓

**Criterio de done:**
- `pytest tests/unit/test_qdrant_rag_adapter.py` pasa al 100%

---

### TASK-011 — RedisSessionAdapter + tests
**Estimado:** 60 min  
**Dependencias:** TASK-004

**Archivos a crear:**
- `src/adapters/outbound/redis_session_adapter.py`
- `tests/unit/test_redis_session_adapter.py`

**Acciones:**
1. Implementar `RedisSessionAdapter(ISessionStore)`:
   - Constructor recibe `redis_url`, `redis_password`
   - Usar `redis.asyncio.from_url(url, password=password, socket_timeout=2)`
   - `get_profile(session_id) -> UserProfile | None`:
     - `await redis.get(f"session:{session_id}")`
     - Si None → retornar None
     - Deserializar JSON → construir `UserProfile`
   - `save_profile(profile) -> None`:
     - Serializar `UserProfile` a JSON
     - `await redis.setex(f"session:{profile.user_id}", 86400, json_str)`
   - Si `redis.RedisError` → loguear WARN y retornar None / ignorar el error
2. Añadir `SessionStoreError` a `errors.py` (aunque se usa solo para logging, no se propaga)
3. Tests con mock de `redis.asyncio`:
   - Perfil existente → retorna `UserProfile` deserializado ✓
   - Clave inexistente → retorna None ✓
   - `save_profile()` → llama `setex` con TTL 86400 ✓
   - `RedisError` en get → retorna None sin propagar excepción ✓
   - `RedisError` en save → loguea WARN sin propagar excepción ✓

**Criterio de done:**
- `pytest tests/unit/test_redis_session_adapter.py` pasa al 100%

---

### TASK-012 — classify_intent (función clasificadora) + tests
**Estimado:** 60 min  
**Dependencias:** TASK-006, TASK-007

**Archivos a crear:**
- `agents/classify_intent.py`
- `tests/unit/test_classify_intent.py`

**Acciones:**
1. Implementar función factory `make_classify_intent_node(llm_client: ILlmClient)`:
   - Retorna un nodo LangGraph: `async def classify_intent(state: AgentState) -> dict`
   - system_prompt con las 7 categorías, instrucción de responder UNA sola palabra,
     y ejemplos few-shot en español:
     ```
     "¿qué leyes me protegen?" → legal
     "ayúdame a redactar una carta" → redactor
     "hola, quiero participar" (sin perfil) → onboarding
     "¿cuándo es la próxima sesión municipal?" → oportunidades
     "¿hay organizaciones en mi zona?" → red
     "¿cómo planteo mi queja a la municipalidad?" → estratega
     "¿qué es el ODS 16?" → general
     ```
   - Si no existe `user_profile["name"]` → forzar retorno `"onboarding"` sin llamar al LLM
   - Llamar `llm_client.generate(system_prompt, state["user_message"])`
   - Normalizar respuesta a minúsculas y strip
   - Si respuesta no está en los valores válidos de `AgentIntent` → `"general"` como fallback
   - Retornar `{"intent": valor_clasificado}`
2. Tests con mock de `ILlmClient`:
   - Perfil vacío → intent siempre `"onboarding"` sin llamar al LLM ✓
   - LLM responde `"legal"` → state["intent"] = `"legal"` ✓
   - LLM responde texto inesperado → fallback `"general"` ✓
   - LLM responde con espacios extra o mayúsculas → se normaliza ✓

**Criterio de done:**
- `pytest tests/unit/test_classify_intent.py` pasa al 100%
- La función devuelve siempre un intent válido (nunca propaga excepción de clasificación)

---

### TASK-013 — Nodo ONBOARDING + tests
**Estimado:** 60 min  
**Dependencias:** TASK-006

**Archivos a crear:**
- `agents/onboarding_node.py`
- `tests/unit/test_onboarding_node.py`

**Acciones:**
1. Implementar factory `make_onboarding_node(llm_client: ILlmClient)`:
   - Lógica de extracción directa: intentar extraer nombre y/o distrito del mensaje actual
     usando LLM con system_prompt simple antes de preguntar
   - Si no hay nombre → respuesta pidiendo el nombre
   - Si hay nombre pero no distrito → respuesta pidiendo el distrito
   - Si hay nombre y distrito → pedir descripción de problemática,
     actualizar `conversation_stage → "ACTIVE"`
   - Actualizar `state["user_profile"]` con campos recolectados
   - Tono: amigable, informal (tuteo), lenguaje para jóvenes de 15-29 años
2. Tests con mock de `ILlmClient`:
   - Estado sin nombre → respuesta pide nombre, `user_profile` sin cambios en "name" ✓
   - Estado con nombre, sin distrito → respuesta pide distrito ✓
   - Estado con nombre y distrito → conversation_stage = `"ACTIVE"` ✓
   - Mensaje "Hola soy Ana de San Isidro" → extrae nombre="Ana", district="San Isidro" ✓

**Criterio de done:**
- `pytest tests/unit/test_onboarding_node.py` pasa al 100%
- El nodo nunca propaga excepciones (absorbe errores del LLM y da respuesta genérica)

---

### TASK-014 — Nodo LEGAL + tests
**Estimado:** 60 min  
**Dependencias:** TASK-006

**Archivos a crear:**
- `agents/legal_node.py`
- `tests/unit/test_legal_node.py`

**Acciones:**
1. Implementar factory `make_legal_node(llm_client: ILlmClient, rag_client: IRagClient)`:
   - Buscar top-5 en `RagCollection.LEGAL` con `state["user_message"]`
   - Si RAG retorna vacío → continuar solo con LLM (sin contexto)
   - Construir system_prompt:
     ```
     Eres un asistente legal ciudadano para jóvenes peruanos.
     Usa solo la legislación peruana provista en el contexto.
     No opines sobre política. Responde en lenguaje simple.
     Cita el artículo específico cuando sea relevante.
     Si no está en el contexto, dilo honestamente.
     
     Contexto legal:
     {chunks_formateados}
     ```
   - Llamar LLM y guardar en `state["response"]`
   - Guardar chunks en `state["rag_context"]`
2. Tests con mocks de `ILlmClient` e `IRagClient`:
   - RAG retorna chunks → se incluyen en el prompt ✓
   - RAG retorna vacío → LLM igual recibe el mensaje (sin contexto vacío que confunda) ✓
   - Respuesta del LLM se guarda en `state["response"]` ✓

**Criterio de done:**
- `pytest tests/unit/test_legal_node.py` pasa al 100%

---

### TASK-015 — Nodo ESTRATEGA + tests
**Estimado:** 60 min  
**Dependencias:** TASK-006

**Archivos a crear:**
- `agents/estratega_node.py`
- `tests/unit/test_estratega_node.py`

**Acciones:**
1. Implementar factory `make_estratega_node(llm_client, rag_client)`:
   - Buscar top-5 en `RagCollection.PROCEDIMIENTOS`
   - Leer `data/calendar.json` → filtrar eventos por `state["user_profile"]["district"]`
     (si existe) → tomar los 3 más próximos
   - Construir system_prompt instruyendo a generar ruta en pasos numerados (máx 5 pasos)
     con: nombre del usuario (si existe), distrito, problemática, eventos próximos relevantes
   - Guardar respuesta en `state["response"]` y datos de calendario en `state["tool_data"]`
2. Tests:
   - Con perfil completo → prompt incluye nombre y distrito ✓
   - `calendar.json` con eventos → filtrados por distrito ✓
   - Si `data/calendar.json` no existe → continúa sin datos de calendario ✓

**Criterio de done:**
- `pytest tests/unit/test_estratega_node.py` pasa al 100%
- El nodo no falla si `calendar.json` no existe o está vacío

---

### TASK-016 — Nodo OPORTUNIDADES + tests
**Estimado:** 60 min  
**Dependencias:** TASK-006

**Archivos a crear:**
- `agents/oportunidades_node.py`
- `tests/unit/test_oportunidades_node.py`

**Acciones:**
1. Implementar factory `make_oportunidades_node(llm_client, rag_client)`:
   - Leer `data/calendar.json` → parsear fechas → ordenar por fecha ascendente
   - Filtrar solo eventos con fecha >= hoy
   - Si hay distrito en perfil → filtrar por distrito primero, si < 3 resultados ampliar a todos
   - Tomar los 3 primeros eventos
   - Buscar en `RagCollection.PROCEDIMIENTOS` por descripción de cada evento (contexto)
   - system_prompt: "Lista las 3 oportunidades más próximas con: fecha, tipo de evento,
     qué debe hacer el usuario para participar."
   - Guardar en `state["response"]` y JSON filtrado en `state["tool_data"]`
2. Tests:
   - 5 eventos futuros → devuelve solo los 3 más próximos ✓
   - Eventos pasados → excluidos ✓
   - Sin distrito en perfil → devuelve todos sin filtrar ✓

**Criterio de done:**
- `pytest tests/unit/test_oportunidades_node.py` pasa al 100%

---

### TASK-017 — Nodo RED + tests
**Estimado:** 60 min  
**Dependencias:** TASK-006

**Archivos a crear:**
- `agents/red_node.py`
- `tests/unit/test_red_node.py`

**Acciones:**
1. Implementar factory `make_red_node(llm_client, rag_client)`:
   - Leer `data/directorio.json` (lista de organizaciones RENOJ)
   - Si hay distrito en perfil → filtrar por campo `"distrito"` (case-insensitive)
   - Si < 3 resultados → ampliar a nivel Lima
   - Buscar en `RagCollection.CASOS_EXITO` por `state["user_message"]` (top-3)
   - Combinar: organizaciones filtradas + casos de éxito relacionados
   - system_prompt: "Presenta máx 3 organizaciones con: nombre, área, contacto,
     y si hay un caso de éxito similar explícalo brevemente."
   - Si `directorio.json` no existe → notificar al usuario y solo usar RAG casos_exito
2. Tests:
   - Directorio con 5 organizaciones, 2 en el distrito → devuelve las 2 ✓
   - Solo 1 en el distrito → amplía y completa con otras ✓
   - `directorio.json` ausente → respuesta solo con casos RAG, sin crash ✓

**Criterio de done:**
- `pytest tests/unit/test_red_node.py` pasa al 100%

---

### TASK-018 — Nodo REDACTOR + tests
**Estimado:** 60 min  
**Dependencias:** TASK-006

**Archivos a crear:**
- `agents/redactor_node.py`
- `tests/unit/test_redactor_node.py`

**Acciones:**
1. Implementar factory `make_redactor_node(llm_client)`:
   - Detectar tipo de documento del `state["user_message"]`:
     keywords: "carta" → carta; "solicitud"/"información" → solicitud;
     "propuesta"/"PP"/"presupuesto participativo" → propuesta;
     "inscripción"/"mesa" → inscripción; default → carta
   - Leer `data/municipios.json` → buscar funcionario y mesa de partes del distrito del perfil
   - system_prompt varía según tipo de documento:
     ```
     Genera [tipo_documento] formal en español peruano.
     Datos del remitente: {nombre}, vecino/a de {distrito}.
     Destinatario: {funcionario} - {cargo} - {municipio}
     Mesa de partes: {dirección_mesa_partes}
     Fecha: {fecha_hoy}
     Problemática: {issue_del_perfil}
     Formato: encabezado formal, cuerpo, cierre, firma.
     ```
   - Guardar documento completo en `state["response"]`
2. Tests:
   - Mensaje "carta" + perfil completo → documento con encabezado formal ✓
   - `municipios.json` ausente → genera documento sin datos del funcionario ✓
   - Tipo de documento detectado correctamente de keywords ✓

**Criterio de done:**
- `pytest tests/unit/test_redactor_node.py` pasa al 100%

---

### TASK-019 — Nodo GENERAL + guardrails + tests
**Estimado:** 60 min  
**Dependencias:** TASK-006

**Archivos a crear:**
- `agents/general_node.py`
- `tests/unit/test_general_node.py`

**Acciones:**
1. Implementar factory `make_general_node(llm_client, rag_client)`:
   - Buscar en `RagCollection.ODS` y `RagCollection.PROCEDIMIENTOS` (top-3 cada uno)
   - Buscar en `RagCollection.CASOS_EXITO` (top-2)
   - Combinar todos los chunks como contexto
   - system_prompt con guardrail explícito:
     ```
     Eres Participa AI, asistente de participación ciudadana para jóvenes peruanos.
     Solo puedes hablar sobre: leyes peruanas, participación ciudadana, ODS,
     organizaciones juveniles, presupuesto participativo.
     NUNCA emitas opiniones políticas ni sobre candidatos o partidos.
     Si la consulta está fuera de tu ámbito responde:
     "Eso está fuera de lo que puedo ayudarte. ¿Te puedo orientar sobre
     participación ciudadana, leyes o cómo conectarte con organizaciones juveniles?"
     Responde en lenguaje simple, accesible para jóvenes de 15-29 años.
     ```
   - Guardar en `state["response"]`
2. Tests:
   - Consulta sobre participación ciudadana → respuesta normal ✓
   - Consulta "¿qué partido debo votar?" → respuesta de guardrail ✓
   - Consulta sobre violencia → respuesta de guardrail ✓
   - RAG devuelve vacío → solo guardrail + LLM puro ✓

**Criterio de done:**
- `pytest tests/unit/test_general_node.py` pasa al 100%
- Las consultas políticas NUNCA reciben una opinión (test con mock verificando el sistema prompt)

---

### TASK-020 — Orchestrator LangGraph (grafo completo) + tests
**Estimado:** 90 min  
**Dependencias:** TASK-012, TASK-013, TASK-014, TASK-015, TASK-016, TASK-017, TASK-018, TASK-019

**Archivos a crear:**
- `agents/orchestrator.py`
- `tests/unit/test_orchestrator.py`

**Acciones:**
1. Implementar función factory `build_graph(llm_client, rag_client, redis_client)`:
   ```python
   from langgraph.graph import StateGraph, END
   from langgraph.checkpoint.redis import RedisSaver
   
   def build_graph(llm_client, rag_client, redis_client) -> CompiledGraph:
       builder = StateGraph(AgentState)
       
       # Agregar nodos (creados con sus factories)
       builder.add_node("classify_intent", make_classify_intent_node(llm_client))
       builder.add_node("onboarding", make_onboarding_node(llm_client))
       builder.add_node("legal", make_legal_node(llm_client, rag_client))
       builder.add_node("estratega", make_estratega_node(llm_client, rag_client))
       builder.add_node("oportunidades", make_oportunidades_node(llm_client, rag_client))
       builder.add_node("red", make_red_node(llm_client, rag_client))
       builder.add_node("redactor", make_redactor_node(llm_client))
       builder.add_node("general", make_general_node(llm_client, rag_client))
       
       # Entry point
       builder.set_entry_point("classify_intent")
       
       # Routing condicional desde classify_intent
       builder.add_conditional_edges("classify_intent", route_by_intent, {
           "onboarding": "onboarding",
           "legal": "legal",
           "estratega": "estratega",
           "oportunidades": "oportunidades",
           "red": "red",
           "redactor": "redactor",
           "general": "general",
       })
       
       # Todos los nodos terminan en END
       for node in ["onboarding","legal","estratega","oportunidades","red","redactor","general"]:
           builder.add_edge(node, END)
       
       checkpointer = RedisSaver(redis_client)
       return builder.compile(checkpointer=checkpointer)
   ```
2. Implementar `route_by_intent(state: AgentState) -> str`:
   - Lee `state["intent"]` y retorna el nombre del nodo destino
   - Si valor inválido → `"general"`
3. Tests con todos los nodos y adapters mockeados:
   - intent `"legal"` → nodo `legal` ejecutado ✓
   - intent `"onboarding"` → nodo `onboarding` ejecutado ✓
   - intent inválido → nodo `general` ejecutado ✓
   - Estado persiste entre invocaciones (mock de RedisSaver) ✓

**Criterio de done:**
- `pytest tests/unit/test_orchestrator.py` pasa al 100%
- `build_graph(mock_llm, mock_rag, mock_redis)` retorna un grafo compilado sin errores

---

### TASK-021 — ProcessMessageUseCase + tests
**Estimado:** 60 min  
**Dependencias:** TASK-003, TASK-004, TASK-020

**Archivos a crear:**
- `src/application/use_cases/process_message.py`
- `src/application/errors.py`
- `tests/unit/test_process_message_use_case.py`

**Acciones:**
1. Implementar `ProcessMessageUseCase` exactamente según el design §3.1:
   ```python
   async def execute(self, message: Message) -> AgentResponse:
       # 1. STT si es audio
       text = await self._transcribe_if_audio(message)
       
       # 2. Construir estado inicial de LangGraph
       initial_state = {
           "session_id": message.session_id,
           "user_message": text,
           "intent": None,
           "user_profile": await self._load_profile(message.session_id),
           "rag_context": [],
           "tool_data": {},
           "response": "",
           "conversation_history": [],
       }
       
       # 3. Invocar grafo LangGraph
       final_state = await self.orchestrator.ainvoke(
           initial_state,
           config={"configurable": {"thread_id": message.session_id}},
       )
       
       # 4. Guardar perfil actualizado
       await self._save_profile(message.session_id, final_state["user_profile"])
       
       # 5. TTS si la entrada fue audio
       return await self._build_response(message, final_state["response"])
   ```
2. Definir en `src/application/errors.py`:
   - `SttTranscriptionError` — propagado al router como 422
   - `OrchestratorError` — propagado al router como 500
3. Tests con todos los colaboradores mockeados:
   - Mensaje TEXT → STT no llamado, LangGraph llamado, respuesta TEXT ✓
   - Mensaje AUDIO → STT llamado primero, TTS llamado al final, respuesta AUDIO ✓
   - STT falla → `SttTranscriptionError` propagado ✓
   - TTS falla → fallback a texto sin excepción ✓
   - Redis falla → LangGraph ejecuta con perfil vacío ✓

**Criterio de done:**
- `pytest tests/unit/test_process_message_use_case.py` pasa al 100%
- El use case no contiene ningún import de FastAPI, LangChain ni OpenAI directamente

---

### TASK-022 — agent_router.py (FastAPI) + tests de integración
**Estimado:** 60 min  
**Dependencias:** TASK-021

**Archivos a crear:**
- `src/adapters/inbound/agent_router.py`
- `tests/integration/test_agent_router.py`

**Acciones:**
1. Implementar `agent_router.py` con los modelos Pydantic y endpoints del design §4.1:
   - `AgentRequest` con validadores:
     - Si `type == "text"` y `message is None` → `ValueError` (Pydantic)
     - Si `type == "audio"` y `audio_base64 is None` → `ValueError`
     - `type` debe ser `"text"` o `"audio"` (validator o Literal)
   - `AgentResponseDTO`
   - `POST /agent`: construir `Message` del dominio → `use_case.execute()` → mapear a DTO
   - Capturar `SttTranscriptionError` → HTTP 422 con mensaje al usuario
   - Capturar `OrchestratorError` → HTTP 500 con mensaje genérico (sin detalles internos)
   - `GET /health` ya existe en `main.py` — agregar aquí también o mover al router
2. Tests con `httpx.AsyncClient` y `use_case` mockeado:
   - POST texto válido → 200 con `response_type: "text"` ✓
   - POST audio válido → 200 con `response_type: "audio"` ✓
   - POST texto sin campo `message` → 422 ✓
   - POST audio sin `audio_base64` → 422 ✓
   - POST `type: "imagen"` → 422 ✓
   - `SttTranscriptionError` → 422 con mensaje amigable ✓
   - `OrchestratorError` → 500 ✓

**Criterio de done:**
- `pytest tests/integration/test_agent_router.py` pasa al 100%
- Ningún mensaje de error HTTP expone detalles internos de la implementación

---

### TASK-023 — dependencies.py + main.py (wiring completo)
**Estimado:** 45 min  
**Dependencias:** TASK-005, TASK-007, TASK-008, TASK-009, TASK-010, TASK-011, TASK-022

**Archivos a modificar/crear:**
- `dependencies.py` (nuevo)
- `main.py` (reescribir el skeleton de TASK-001)

**Acciones:**
1. Implementar `dependencies.py` con contenedor de DI manual:
   ```python
   _use_case: ProcessMessageUseCase | None = None
   
   async def init_dependencies(config: Config):
       llm = OpenAILlmAdapter(config)
       stt = OpenAISttAdapter(config)
       tts = OpenAITtsAdapter(config)
       rag = QdrantRagAdapter(config)
       redis_client = redis.asyncio.from_url(config.redis_url, ...)
       session_store = RedisSessionAdapter(redis_client)
       graph = build_graph(llm, rag, redis_client)
       global _use_case
       _use_case = ProcessMessageUseCase(stt, tts, session_store, graph)
   
   def get_process_message_use_case() -> ProcessMessageUseCase:
       if _use_case is None:
           raise RuntimeError("Dependencies not initialized")
       return _use_case
   ```
2. Reescribir `main.py`:
   ```python
   @asynccontextmanager
   async def lifespan(app: FastAPI):
       await init_dependencies(config)   # startup
       yield
       # cleanup: cerrar conexiones Redis, etc.
   
   app = FastAPI(title="Participa AI — Agent Service", lifespan=lifespan)
   app.include_router(agent_router)
   # Configurar structlog con OutputFormat JSON
   # CORS con lista blanca (solo el servicio whatsapp)
   ```
3. Verificación manual:
   - `uvicorn main:app --reload` con `.env` completo → arranca sin errores
   - `GET /health` → `{"status": "ok", "service": "ai-agent"}`
   - `POST /agent` con texto mock → responde (aunque no haya datos en Qdrant aún)

**Criterio de done:**
- `uvicorn main:app` arranca correctamente con todas las vars de entorno configuradas
- Sin vars de entorno → falla con mensaje claro antes de arrancar
- El servidor responde a `GET /health` con HTTP 200

---

### TASK-024 — Dockerfile + requirements.txt final + .env.example
**Estimado:** 30 min  
**Dependencias:** TASK-023

**Archivos a crear/modificar:**
- `services/ai-agent/Dockerfile`
- `services/ai-agent/requirements.txt` (verificar versiones y completar)
- `services/ai-agent/.env.example` (completo con todas las variables)

**Acciones:**
1. Crear `Dockerfile` multi-stage exactamente como en el design §12
2. Completar `requirements.txt` con todas las dependencias usadas (sin conflictos de versión):
   - Verificar compatibilidad entre `langgraph`, `langchain`, `langchain-openai`, `langchain-qdrant`
   - Agregar `pydantic-settings` (necesario para `config.py`)
   - Pinear versiones menores para reproducibilidad en Render
3. Completar `.env.example` con todas las variables del design §10, sin valores reales:
   ```bash
   OPENAI_API_KEY=
   OPENAI_MODEL=gpt-4o-mini
   # ... todas las variables del design §10
   DATA_DIR=../../data
   ```
4. Verificación:
   - `docker build -t participa-ai-agent .` (desde `services/ai-agent/`)
   - Imagen final < 500MB
   - `docker run --env-file .env participa-ai-agent` arranca sin errores

**Criterio de done:**
- `docker build` completa sin errores
- `docker run` con `.env` completo → `GET /health` responde 200
- `.env.example` no contiene ningún valor real (solo keys vacías o defaults seguros)
- Imagen no incluye archivos de desarrollo (`tests/`, `*.pyc`, `.env`)

---

## Cobertura mínima requerida (80%)

Los siguientes archivos concentran la lógica crítica y deben tener cobertura cercana al 100%:

| Archivo | Cobertura mínima |
|---|---|
| `src/domain/entities/*.py` | 100% |
| `src/application/use_cases/process_message.py` | 95% |
| `agents/classify_intent.py` | 100% |
| `agents/orchestrator.py` | 90% |
| `src/adapters/inbound/agent_router.py` | 95% |
| `src/adapters/outbound/*.py` (todos) | 85% |
| `agents/*_node.py` (todos) | 85% |

Ejecutar cobertura: `pytest --cov=src --cov=agents --cov-report=term-missing`
