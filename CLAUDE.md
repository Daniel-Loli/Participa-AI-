# CLAUDE.md — Participa AI

> Contexto permanente del proyecto. Claude Code lo lee automáticamente en cada sesión.
> **Nunca escribas código sin un spec aprobado en `.claude/specs/`.**

---

## Contexto de steering
Lee estos archivos antes de cualquier tarea. Tienen el detalle completo:

- `.claude/steering/product.md` — visión, usuario, problema, funcionalidades, ODS
- `.claude/steering/tech.md` — stack, decisiones de arquitectura, timeouts, testing
- `.claude/steering/structure.md` — estructura de carpetas, naming, reglas de capas, commits

---

## 1. Visión (resumen)

**Participa AI** — agente conversacional WhatsApp que guía a jóvenes peruanos (15-29 años)
desde una preocupación ciudadana hasta una acción de incidencia concreta, legal y verificable.
Soporta texto y notas de voz. Canal único: WhatsApp.

> Detalle completo → `.claude/steering/product.md`

---

## 2. Stack (resumen)

| Servicio | Tecnología |
|---|---|
| Canal | WhatsApp Business API + webhook NestJS |
| Backend negocio | Node.js + NestJS (TypeScript) |
| Backend IA | Python + FastAPI |
| Agentes | LangGraph + LangChain |
| LLM (nano) | OpenAI API — gpt-4.1-nano (classify_intent, onboarding) |
| LLM (mini) | OpenAI API — gpt-4.1-mini (legal, estratega, red, oportunidades, general) |
| LLM (full) | OpenAI API — gpt-4.1 (redactor — documentos formales) |
| Embeddings | OpenAI API — text-embedding-3-small |
| STT (voz → texto) | OpenAI Whisper API — whisper-1 |
| TTS (texto → voz) | OpenAI TTS API — tts-1, voz nova (femenina, cálida) |
| Vector DB / RAG | Qdrant Cloud (free tier) |
| Sesiones / Caché | Redis Cloud (free tier) |
| Observabilidad | LangSmith |
| Documentos fuente | Local en repo (`knowledge-base/`) |
| Despliegue | GCP Cloud Run (dos servicios: whatsapp + ai-agent) |
| Imágenes | GCP Artifact Registry (us-central1) |
| Secrets | GCP Secret Manager |
| CI/CD | GCP Cloud Build (trigger desde GitHub) |

> Decisiones y justificaciones → `.claude/steering/tech.md`

---

## 3. Arquitectura — Flujo E2E

```
① Usuario → WhatsApp: texto o nota de voz
② POST /webhook → Node.js (NestJS): detecta tipo
   └─ audio: descarga OGG → envía base64 al backend IA
③ Node.js → Python (FastAPI /agent): payload + session_id
④ LangGraph Orquestador → nodo correcto según intención
⑤ Nodo RAG → Qdrant (búsqueda vectorial) + LangChain
⑥ Nodo LLM → OpenAI gpt-4o-mini (con historial de conversación)
   └─ audio entrante: Whisper API (STT) antes del LLM
⑦ wa_format.clean() → elimina markdown roto antes de enviar
⑧ Python → Node.js → WhatsApp: respuesta texto o audio
   └─ si respuesta es voz: OpenAI TTS API → audio
⑨ LangGraph → Redis: guarda historial (conversation_history + UserProfile)
```

**Patrón:** Hexagonal. Domain nunca importa frameworks.
Ports en domain, implementaciones en adapters.

> Detalle de capas y reglas → `.claude/steering/structure.md`

---

## 4. Agentes (LangGraph)

| Nodo | Responsabilidad |
|---|---|
| 🎯 Orquestador | Clasifica intención, enruta al nodo correcto, mantiene estado |
| ⚖️ Legal | RAG sobre leyes, traduce normativa a lenguaje simple |
| ⚖️✍️ Legal+Redactor | Nodo compuesto: responde la ley Y solicita confirmación para generar carta (intención compuesta en un solo turno) |
| 🗺️ Estratega | Ruta de incidencia viable según distrito y problemática |
| 📅 Oportunidades | Calendarios municipales, plazos PP, ventanas de acción |
| 🤝 Red | Conecta con RENOJ/SENAJU y casos de éxito similares |
| ✍️ Redactor | Genera cartas, solicitudes y propuestas ciudadanas (previa confirmación del usuario) |

Todos los nodos usan `generate_with_history()` para incluir el historial completo en cada llamada al LLM.

### Comportamientos clave de UX conversacional

- **Onboarding inteligente:** `classify_intent` fuerza onboarding hasta tener nombre Y distrito. El nodo extrae ambos datos de un solo mensaje si el usuario los da juntos.
- **Intención compuesta:** Si el usuario pide ley + carta en un mismo mensaje, se activa `legal_redactor` que responde con el contexto legal y solicita confirmación para el documento.
- **Confirmación de documento:** El nodo `redactor` nunca genera el PDF directo. Primero pide confirmación al usuario. El flag `awaiting_doc_confirmation` en el perfil persiste en Redis hasta recibir respuesta afirmativa.
- **Mensajes en partes:** `sendInParts()` (`services/whatsapp/src/application/utils/message-splitter.ts`) divide la respuesta por párrafos (`\n\n`, mínimo 80 chars) y envía cada parte con 400 ms de delay para una UX más ordenada en WhatsApp.

---

## 5. Knowledge Base — 3 cubetas

### Memoria Semántica — RAG (Qdrant Cloud)

| Colección | Documentos fuente |
|---|---|
| `legal` | Ley-n-26300-2025.pdf · Ley_27783.pdf · Ley 28056 ley de marco del presupuesto participativo.pdf · ley27972 Ley Orgánica de Municipalidades.pdf |
| `ods` | ObjetivosAgenda2030.pdf · GlosarioDeterminosODS.pdf |
| `procedimientos` | Manual-de-Usuario-para-Organizaciones-Juveniles.pdf · Glosario de Presupuesto Público.pdf |
| `casos_exito` | Iniciativas exitosas con métricas (a construir) |

### Memoria Episódica (Redis Cloud)

| Clave | Contenido |
|---|---|
| `session:{session_id}` | Historial de conversación (LangGraph checkpoint con conversation_history) |
| `profile:{user_id}` | Nombre, distrito, problemática, etapa, `awaiting_doc_confirmation`, `awaiting_next_action` |
| `last_activity:{session_id}` | Unix timestamp del último mensaje (TTL 24h) — gestionado por NestJS |
| `warning_sent:{session_id}` | Flag de aviso de inactividad enviado (TTL 2 min) — gestionado por NestJS |

### Herramientas — JSONs locales (`data/`)

| Archivo | Contenido |
|---|---|
| `directorio.json` | RENOJ — generado desde BASE-DE-DATOS-ORGANIZACIONES-JUVENILES.xlsx |
| `calendar.json` | Sesiones municipales, audiencias, plazos PP |
| `iniciativas.json` | Proyectos comunitarios activos |
| `municipios.json` | Funcionarios y mesas de partes por distrito |
| `presupuestos.json` | Histórico de Presupuesto Participativo |

---

## 6. Fuentes Gubernamentales — Scraper diario 8AM

**Cron:** GCP Cloud Scheduler `0 13 * * *` (UTC) = 8AM Lima
**Stack:** Python + httpx + BeautifulSoup4
**Pipeline:** scrape → chunk semántico → embed (OpenAI) → Qdrant (deduplicación por hash)

| Fuente | URL | Contenido |
|---|---|---|
| SENAJU principal | `juventud.gob.pe` | Convocatorias, programas, eventos |
| RENOJ | `juventud.gob.pe/organizaciones-juveniles` | Directorio de colectivos |
| Voluntariado | `juventud.gob.pe/voluntariado-juvenil` | Convocatorias activas |
| Observatorio Juventud | `observatorio-juventud.minedu.gob.pe` | Indicadores y datos |
| Municipalidad Lima | `munlima.gob.pe` | Calendario, audiencias, PP Lima |
| Portal Estado | `gob.pe/participacion-ciudadana` | Guías de trámites |
| INFOGOB/JNE | `infogob.pe` | Autoridades locales vigentes |
| MEF | `mef.gob.pe` | Convocatorias PP, montos |

---

## 7. Prioridad de ingestión RAG

| # | Archivo | Colección Qdrant | Prioridad |
|---|---|---|---|
| 1 | Ley-n-26300-2025.pdf | `legal` | 🔴 Core |
| 2 | Ley 28056 ley de marco del presupuesto participativo.pdf | `legal` | 🔴 Core |
| 3 | ley27972 Ley Orgánica de Municipalidades.pdf | `legal` | 🔴 Core |
| 4 | BASE-DE-DATOS-ORGANIZACIONES-JUVENILES.xlsx | `data/directorio.json` | 🔴 Core |
| 5 | Manual-de-Usuario-para-Organizaciones-Juveniles.pdf | `procedimientos` | 🟠 Alto |
| 6 | Ley_27783.pdf | `legal` | 🟠 Alto |
| 7 | Glosario de Presupuesto Público.pdf | `procedimientos` | 🟠 Alto |
| 8 | ObjetivosAgenda2030.pdf | `ods` | 🟡 Medio |
| 9 | GlosarioDeterminosODS.pdf | `ods` | 🟡 Medio |

> El Excel del RENOJ va a `data/directorio.json` (dato estructurado), NO al índice vectorial.

---

## 8. Reglas críticas de desarrollo

1. **Nunca escribas código sin un spec aprobado** en `.claude/specs/`
2. **Arquitectura hexagonal innegociable** — domain nunca importa frameworks externos
3. **Cada función pública tiene su test** — cobertura mínima 80%
4. **Secrets siempre en variables de entorno** — nunca hardcodeados, nunca en commits
5. **Comentarios en español** — nombres de variables/funciones en inglés
6. **Nunca loguear PII** — solo `from_hash` (SHA256), `message_type`, `timestamp`, `status`
7. **POST /webhook responde 200 inmediatamente** antes de procesar (evitar reintentos de Meta)
8. **Todo texto de respuesta pasa por `wa_format.clean()`** antes de enviarse a WhatsApp

> Convenciones completas de naming, capas y commits → `.claude/steering/structure.md`

---

## 9. Variables de entorno

```bash
# Session timeout (services/whatsapp)
SESSION_WARNING_MINUTES=4    # minutos de inactividad antes del aviso
SESSION_CLOSE_MINUTES=5      # minutos de inactividad antes del cierre

# OpenAI
OPENAI_API_KEY=
OPENAI_MODEL_NANO=gpt-4.1-nano
OPENAI_MODEL_MINI=gpt-4.1-mini
OPENAI_MODEL_FULL=gpt-4.1
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_WHISPER_MODEL=whisper-1
OPENAI_TTS_MODEL=tts-1
OPENAI_TTS_VOICE=nova

# Qdrant Cloud
QDRANT_URL=
QDRANT_API_KEY=
QDRANT_COLLECTION_LEGAL=legal
QDRANT_COLLECTION_ODS=ods
QDRANT_COLLECTION_PROCEDIMIENTOS=procedimientos
QDRANT_COLLECTION_CASOS=casos_exito

# LangSmith (observabilidad)
LANGCHAIN_API_KEY=
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=participa-ai

# Redis Cloud (sesiones)
REDIS_URL=
REDIS_PASSWORD=

# WhatsApp Business API
WHATSAPP_VERIFY_TOKEN=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_APP_SECRET=

# Interno
AI_AGENT_SERVICE_URL=https://participa-ai-agent-87805706219.us-central1.run.app
NODE_ENV=production
```

---

## 10. Workflow SDD — Prompts de activación

**Fase 1 — Requirements:**
```
Genera .claude/specs/[modulo]/requirements.md para el módulo [nombre].
Incluye: functional requirements, non-functional requirements,
casos de uso y criterios de aceptación en formato EARS. No escribas código.
```

**Fase 2 — Design:**
```
Basándote en .claude/specs/[modulo]/requirements.md, genera
.claude/specs/[modulo]/design.md con: estructura de archivos,
ports del dominio hexagonal y contratos de API. No escribas código.
```

**Fase 3 — Tasks:**
```
Basándote en .claude/specs/[modulo]/design.md, genera
.claude/specs/[modulo]/tasks.md como lista atómica ordenada
por dependencia. Cada tarea: id, archivos, criterio done. Máx 2h por tarea.
```

**Fase 4 — Implementación:**
```
Implementa TASK-[id] de .claude/specs/[modulo]/tasks.md.
Corre los tests. Reporta resultado antes de continuar.
```

---

## 11. Módulos — Estado y orden

| # | Módulo | Servicio | Estado | Depende de |
|---|---|---|---|---|
| 1 | `webhook` | `services/whatsapp` | ✅ completo | — |
| 2 | `ai-agent` | `services/ai-agent` | ✅ completo | 1 |
| 3 | `rag` | `services/ai-agent` | ✅ completo (QdrantRagAdapter + nodos RAG) | 2 |
| 4 | `memory` | `services/ai-agent` | ✅ completo (RedisSessionAdapter + generate_with_history + LangGraph checkpointing) | 2 |
| 5 | `voice` | `services/ai-agent` | ✅ completo (OpenAI Whisper STT + TTS) | 2 |
| 6 | `data-pipeline` | `data-pipeline/` | ✅ completo (build_data.py + ingest_rag.py) | 3 |
| 7 | `scraper` | `data-pipeline/` | ✅ completo (6 fuentes, cron 8AM Lima vía GCP Cloud Scheduler) | 6 |
| 8 | `ux-conversacional` | `services/whatsapp` + `services/ai-agent` | ✅ completo (wa_format.py + message-splitter.ts: respuestas en partes, tono juvenil, flujo guiado, flags de conversación persistidos) | 2 |
| 9 | `session-timeout` | `services/whatsapp` + `services/ai-agent` | 🔲 spec aprobado — pendiente implementación | 1, 4 |
