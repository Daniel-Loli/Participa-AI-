# structure.md — Participa AI

## Estructura de carpetas del repositorio

```
participa-ai/
├── CLAUDE.md                          ← contexto permanente para Claude Code
├── .claude/
│   ├── specs/
│   │   ├── requirements.md            ← webhook (aprobado ✓)
│   │   ├── design.md                  ← webhook (aprobado ✓)
│   │   ├── tasks.md                   ← webhook (completo ✓)
│   │   ├── ai-agent/
│   │   │   ├── requirements.md        ← aprobado ✓
│   │   │   ├── design.md              ← aprobado ✓
│   │   │   └── tasks.md               ← completo ✓ (24/24 tareas implementadas)
│   │   ├── session-timeout/           ← spec completo ✓ — pendiente implementación
│   │   │   ├── requirements.md        ← aprobado ✓
│   │   │   ├── design.md              ← aprobado ✓
│   │   │   └── tasks.md               ← 12 tareas definidas
│   │   ├── rag/                       ← pendiente spec formal (implementado en ai-agent)
│   │   ├── memory/                    ← pendiente spec formal (implementado en ai-agent)
│   │   ├── voice/                     ← pendiente spec formal (implementado en ai-agent)
│   │   ├── data-pipeline/             ← pendiente spec formal (implementado)
│   │   └── scraper/                   ← pendiente
│   └── steering/
│       ├── product.md
│       ├── tech.md
│       └── structure.md
│
├── services/
│   ├── whatsapp/                      ← Node.js + NestJS ✅ completo
│   │   ├── src/
│   │   │   ├── domain/
│   │   │   │   ├── entities/
│   │   │   │   ├── ports/
│   │   │   │   └── value-objects/
│   │   │   ├── application/
│   │   │   │   ├── use-cases/
│   │   │   │   ├── utils/             ← message-splitter.ts (sendInParts)
│   │   │   │   └── errors/
│   │   │   ├── adapters/
│   │   │   │   ├── inbound/           ← whatsapp.controller.ts, message.dispatcher.ts, DTOs
│   │   │   │   ├── outbound/          ← whatsapp-api.adapter.ts, ai-agent-http.adapter.ts
│   │   │   │   └── guards/            ← hmac-signature.guard.ts
│   │   │   ├── whatsapp/              ← WhatsAppModule (NestJS DI)
│   │   │   ├── injection-tokens.ts
│   │   │   ├── app.module.ts
│   │   │   └── main.ts
│   │   ├── test/
│   │   │   ├── unit/                  ← 7 specs (guards, adapters, use-cases, dispatcher)
│   │   │   └── integration/           ← whatsapp.controller.spec.ts
│   │   ├── Dockerfile
│   │   ├── .dockerignore
│   │   ├── package.json
│   │   └── .env.example
│   │
│   └── ai-agent/                      ← Python + FastAPI ✅ completo
│       ├── main.py                    ← FastAPI app + lifespan + CORS
│       ├── config.py                  ← pydantic_settings, falla rápido si faltan vars
│       ├── dependencies.py            ← contenedor DI manual (init/cleanup)
│       ├── src/
│       │   ├── domain/
│       │   │   ├── entities/          ← Message, AgentResponse, UserProfile
│       │   │   ├── ports/             ← ILlmClient, IRagClient, ISttClient, ITtsClient, ISessionStore
│       │   │   └── value_objects/     ← MessageType, AgentIntent, RagCollection
│       │   ├── application/
│       │   │   ├── errors.py          ← SttTranscriptionError, OrchestratorError
│       │   │   └── use_cases/
│       │   │       └── process_message.py  ← orquesta STT → LangGraph → TTS → wa_clean()
│       │   └── adapters/
│       │       ├── inbound/
│       │       │   └── agent_router.py     ← POST /agent, GET /health
│       │       └── outbound/
│       │           ├── openai_llm_adapter.py      ← generate() + generate_with_history()
│       │           ├── openai_stt_adapter.py   ← Whisper API
│       │           ├── openai_tts_adapter.py   ← TTS API
│       │           ├── qdrant_rag_adapter.py   ← LangChain + Qdrant
│       │           ├── redis_session_adapter.py
│       │           └── errors.py
│       ├── agents/                    ← nodos LangGraph
│       │   ├── state.py               ← AgentState TypedDict (conversation_history + pdf_base64/pdf_filename)
│       │   ├── classify_intent.py     ← clasificador + fallback a onboarding
│       │   ├── orchestrator.py        ← build_graph() + route_by_intent()
│       │   ├── wa_format.py           ← WA_RULES (prompt) + clean() post-procesador WhatsApp
│       │   ├── pdf_generator.py       ← genera PDF con reportlab (letter_to_base64)
│       │   ├── onboarding_node.py
│       │   ├── legal_node.py          ← RAG en colección 'legal'
│       │   ├── estratega_node.py      ← RAG 'procedimientos' + calendar.json
│       │   ├── oportunidades_node.py  ← calendar.json filtrado por fecha/distrito
│       │   ├── red_node.py            ← directorio.json + RAG 'casos_exito'
│       │   ├── redactor_node.py       ← municipios.json + carta → PDF base64 en estado
│       │   └── general_node.py        ← guardrails + RAG multi-colección
│       ├── data/                      ← JSONs generados por build_data.py
│       │   ├── calendar.json
│       │   ├── directorio.json
│       │   ├── iniciativas.json
│       │   ├── municipios.json
│       │   └── presupuestos.json
│       ├── tests/
│       │   ├── unit/                  ← 16 specs (nodos, adapters, entidades, config)
│       │   └── integration/           ← test_agent_router.py
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── pytest.ini
│       └── .env.example
│
├── data-pipeline/                     ← scripts ETL knowledge base ✅ completo
│   ├── build_data.py                  ← genera los 5 JSONs (Excel RENOJ → directorio.json, etc.)
│   ├── ingest_rag.py                  ← PDFs → chunks → embed OpenAI → Qdrant (idempotente)
│   └── scraper/                       ← ✅ completo (scrapers web diarios)
│       ├── run_scraper.py             ← entrypoint CLI + orquestador
│       ├── sources.py                 ← configuración declarativa de las 6 fuentes
│       ├── fetcher.py                 ← HTTP GET con reintentos y timeout
│       ├── parser.py                  ← BeautifulSoup: extrae texto limpio
│       ├── pipeline.py                ← chunk → embed → upsert Qdrant
│       └── requirements.txt
│
├── knowledge-base/                    ← documentos fuente (en repo, no en cloud)
│   ├── legal/
│   │   ├── Ley-n-26300 - 2025.pdf     ✅
│   │   ├── Ley_27783.pdf              ✅
│   │   └── Ley N.° 28056 - 2003.pdf   ✅
│   ├── ods/
│   │   ├── ObjetivosAgenda2030.pdf    ✅
│   │   └── GlosarioDeterminosODS.pdf  ✅
│   ├── procedimientos/
│   │   ├── Manual-de-Usuario-para-Organizaciones-Juveniles.pdf  ✅
│   │   └── Glosario de Presupuesto Público.pdf                  ✅
│   ├── data/
│   │   └── BASE-DE-DATOS-ORGANIZACIONES-JUVENILES-E-INSTITUCIONES-PRIVADAS.xlsx  ✅
│   └── casos_exito/                   ← ⬜ a construir
│
├── cloudbuild.yaml                    ← CI/CD GCP Cloud Build (build + deploy ambos servicios)
├── docker-compose.yml                 ← ⬜ pendiente (desarrollo local con Redis)
└── .env.example                       ← ⬜ pendiente (variables globales del proyecto)
```

## Convenciones de nomenclatura

### TypeScript (Node.js)
| Elemento | Convención | Ejemplo |
|---|---|---|
| Archivos | kebab-case | `handle-text-message.use-case.ts` |
| Clases | PascalCase | `HandleTextMessageUseCase` |
| Interfaces | PascalCase con I | `IMessageSender` |
| Enums | PascalCase | `MessageType` |
| Variables/funciones | camelCase | `parseMessageType()` |
| Constantes | SCREAMING_SNAKE | `UNSUPPORTED_MESSAGE_TEXT` |
| Tests | mismo nombre + `.spec.ts` | `handle-text-message.use-case.spec.ts` |

### Python (ai-agent)
| Elemento | Convención | Ejemplo |
|---|---|---|
| Archivos | snake_case | `handle_text_message.py` |
| Clases | PascalCase | `HandleTextMessageUseCase` |
| Interfaces (ABC) | PascalCase con I | `IAgentOrchestrator` |
| Funciones/variables | snake_case | `parse_message_type()` |
| Constantes | SCREAMING_SNAKE | `UNSUPPORTED_MESSAGE_TEXT` |
| Tests | `test_` + nombre | `test_handle_text_message.py` |

## Reglas de arquitectura hexagonal

### Lo que SÍ puede hacer el Domain
- Definir entidades, value objects y enums
- Definir interfaces (ports) que el mundo exterior debe implementar
- Contener lógica de negocio pura (sin I/O)
- Importar solo librerías de la librería estándar del lenguaje

### Lo que NUNCA puede hacer el Domain
- Importar NestJS, FastAPI, Axios, httpx, LangChain o cualquier framework
- Hacer llamadas HTTP, leer archivos o escribir en base de datos
- Importar desde `adapters/` o `application/`

### Lo que puede hacer Application
- Importar entidades y ports del Domain
- Orquestar llamadas entre ports
- NO importar implementaciones concretas de adapters

### Lo que puede hacer Adapters
- Implementar los ports del Domain
- Importar frameworks externos (NestJS, Axios, LangChain, Qdrant SDK, Redis)
- NO contener lógica de negocio (eso va en Application)

## Reglas de commits
```
feat(webhook): implementar HmacSignatureGuard
feat(ai-agent): agregar nodo Legal con RAG sobre Qdrant
fix(voice): corregir decodificación de audio OGG
test(webhook): agregar tests de idempotencia
docs(claude): actualizar stack a OpenAI + Qdrant
chore(docker): optimizar imagen multi-stage
```

Formato: `tipo(módulo): descripción en español, imperativo, minúsculas`

## Reglas de logging
- NUNCA loguear el contenido de mensajes de usuarios (PII)
- NUNCA loguear números de teléfono en texto plano
- Loguear siempre: `from_hash` (SHA256 del número), `message_type`, `timestamp`, `status`
- Niveles: `ERROR` para fallos inesperados, `WARN` para timeouts y reintentos, `INFO` para flujos normales
- En Python: usar `structlog` con salida JSON para compatibilidad con Render logs

## Reglas de variables de entorno
- Todos los secrets en variables de entorno
- Cada servicio tiene su propio `.env.example` con las variables que necesita
- `.env` nunca se commitea (está en `.gitignore`)
- Si falta una variable crítica al arrancar → el servicio debe fallar rápido con mensaje claro

## Orden de implementación de módulos
1. `webhook` ✅ completo
2. `ai-agent` ✅ completo (FastAPI + LangGraph + todos los nodos + wiring completo)
3. `rag` ✅ completo (QdrantRagAdapter + integrado en los 6 nodos que lo usan)
4. `memory` ✅ completo (RedisSessionAdapter + LangGraph checkpointer + generate_with_history())
5. `voice` ✅ completo (OpenAISttAdapter Whisper + OpenAITtsAdapter TTS)
6. `data-pipeline` ✅ completo (build_data.py genera JSONs; ingest_rag.py sube PDFs a Qdrant)
7. `scraper` ✅ completo (6 fuentes, cron 8AM Lima vía GCP Cloud Scheduler)
8. `ux-conversacional` ✅ completo (wa_format.py + message-splitter.ts: respuestas en partes, tono juvenil, flags de conversación persistidos en Redis)
9. `pdf-export` ✅ completo (pdf_generator.py: reportlab; redactor_node envía carta como PDF adjunto)
10. `session-timeout` 🔲 spec aprobado — pendiente implementación (ver `.claude/specs/session-timeout/`)
