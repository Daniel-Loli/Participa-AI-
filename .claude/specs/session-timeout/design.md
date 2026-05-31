# design.md — Módulo session-timeout

> Basado en: `requirements.md` ✅
> Estado: ✅ aprobado

---

## Estructura de archivos

```
services/whatsapp/src/
├── domain/
│   └── ports/
│       └── session-activity.port.ts         (NUEVO)
├── application/
│   ├── use-cases/
│   │   ├── update-session-activity.use-case.ts   (NUEVO)
│   │   └── check-inactive-sessions.use-case.ts   (NUEVO)
│   └── utils/
│       └── message-splitter.ts              (ya existe ✅)
├── adapters/
│   ├── inbound/
│   │   └── message.dispatcher.ts            (MODIFICAR — llama UpdateSessionActivity antes de despachar)
│   └── outbound/
│       ├── redis-session-activity.adapter.ts (NUEVO)
│       └── ai-agent-http.adapter.ts          (MODIFICAR — agregar deleteSession())
└── whatsapp/
    ├── session-timeout.scheduler.ts          (NUEVO — @Cron cada 60s)
    └── whatsapp.module.ts                    (MODIFICAR — registrar nuevos providers)

services/ai-agent/
├── src/
│   ├── domain/ports/
│   │   └── i_session_store.py               (MODIFICAR — agregar delete_session())
│   ├── application/use_cases/
│   │   └── delete_session.py                (NUEVO)
│   └── adapters/
│       ├── inbound/
│       │   └── agent_router.py              (MODIFICAR — agregar DELETE /session/{session_id})
│       └── outbound/
│           └── redis_session_adapter.py     (MODIFICAR — implementar delete_session())
```

---

## Ports del dominio hexagonal

### `ISessionActivity` (TypeScript)

```typescript
// services/whatsapp/src/domain/ports/session-activity.port.ts
export interface ISessionActivity {
  // Actualiza el timestamp de última actividad. TTL: 24h.
  updateLastActivity(sessionId: string): Promise<void>;

  // Devuelve los IDs de sesiones con inactividad >= minutos indicados.
  getInactiveSessions(minInactiveMinutes: number): Promise<string[]>;

  // Marca que ya se envió el aviso. TTL: 2 min (cubre el 1 min extra hasta cierre).
  markWarningSent(sessionId: string): Promise<void>;

  // True si el aviso ya fue enviado para esta sesión.
  isWarningSent(sessionId: string): Promise<boolean>;

  // Limpia ambas claves de actividad para la sesión.
  clearActivityKeys(sessionId: string): Promise<void>;
}
```

### `ISessionStore` — extensión Python

```python
# Nuevo método en i_session_store.py
@abstractmethod
async def delete_session(self, session_id: str) -> None:
    """Elimina profile:{session_id} y checkpoint LangGraph de Redis."""
```

---

## Claves Redis

| Clave | Tipo | Valor | TTL |
|---|---|---|---|
| `last_activity:{session_id}` | String | Unix timestamp (int) | 24h |
| `warning_sent:{session_id}` | String | `"1"` | 2 min |
| `profile:{session_id}` | Hash/JSON | UserProfile serializado | 24h (Python gestiona) |
| LangGraph checkpoint | JSON | Estado del grafo | gestionado por AsyncRedisSaver |

> **Nota:** `last_activity` lo gestiona NestJS. `profile` y checkpoint los elimina Python vía DELETE /session.
> NestJS y Python comparten el mismo Redis Cloud — las claves son visibles desde ambos servicios.

---

## Contratos de API

### NestJS → Python: eliminar sesión

```
DELETE /session/{session_id}
Authorization: (mismo header interno que usa POST /agent)
Response 200: { "deleted": true }
Response 404: { "deleted": false }  // sesión ya no existía — no es error
```

### Flujo completo del cron

```
SessionTimeoutScheduler.checkInactiveSessions() [cada 60s]
  │
  ├─ checkInactiveSessions.execute()
  │     │
  │     ├─ getInactiveSessions(4 min) → [session_id_A, session_id_B, ...]
  │     │
  │     └─ para cada sesión con >= 4 min de inactividad:
  │           │
  │           ├─ isWarningSent? → No → sendText(aviso) + markWarningSent()
  │           │
  │           └─ isWarningSent? → Sí + >= 5 min → sendText(despedida)
  │                                               + aiAgent.deleteSession()
  │                                               + clearActivityKeys()
```

### Flujo de actualización de actividad

```
MessageDispatcher.dispatch(message)
  │
  ├─ updateSessionActivity.execute(sessionId)   [antes de procesar]
  │     └─ sessionActivity.updateLastActivity(sessionId)
  │           └─ REDIS SET last_activity:{id} <timestamp> EX 86400
  │           └─ REDIS DEL warning_sent:{id}   [resetea aviso si existía]
  │
  └─ handleTextMessage.execute() / handleAudioMessage.execute()
```

---

## Variables de entorno nuevas

```bash
# En services/whatsapp/.env.example
SESSION_WARNING_MINUTES=4    # minutos de inactividad antes del aviso
SESSION_CLOSE_MINUTES=5      # minutos de inactividad antes del cierre
REDIS_URL=                   # ya existe
```

---

## Módulo NestJS — wiring

```typescript
// whatsapp.module.ts — providers a agregar
{
  provide: INJECTION_TOKENS.SESSION_ACTIVITY,
  useClass: RedisSessionActivityAdapter,
},
UpdateSessionActivityUseCase,
CheckInactiveSessionsUseCase,
SessionTimeoutScheduler,
```

Dependencias NestJS nuevas:
- `@nestjs/schedule` — `npm install @nestjs/schedule`
- `ScheduleModule.forRoot()` en `AppModule`

---

## Decisiones de diseño

| Decisión | Alternativa descartada | Razón |
|---|---|---|
| Polling con cron cada 60s | Redis keyspace notifications | Free tier de Redis Cloud no garantiza keyspace events |
| DELETE /session en Python | NestJS elimina claves Python directamente | Evita acoplamiento entre servicios sobre formato interno de claves Redis |
| `warning_sent` con TTL 2 min | Flag en UserProfile | Más simple; el TTL maneja la expiración automáticamente sin estado extra |
| NestJS gestiona `last_activity` | Python gestiona el timer | NestJS recibe el mensaje primero y ya tiene el session_id disponible |
| Tiempos en env vars | Hardcodeados | Permite ajustar sin redeploy |
