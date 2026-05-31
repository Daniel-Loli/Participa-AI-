# tasks.md — Módulo session-timeout

> Basado en: `design.md` ✅
> Estado: pendiente de implementación

---

## Orden de implementación

Las tareas están ordenadas por dependencia. Completar en orden numérico.

---

### TASK-01 — Port ISessionActivity (TypeScript)

**Archivos:**
- CREAR `services/whatsapp/src/domain/ports/session-activity.port.ts`

**Descripción:**
Definir la interfaz `ISessionActivity` con los 5 métodos del design.md.
Agregar `SESSION_ACTIVITY` a `injection-tokens.ts`.

**Criterio done:**
- Archivo creado con la interfaz completa
- Token agregado en `injection-tokens.ts`
- Sin imports de frameworks externos (solo TypeScript puro)

---

### TASK-02 — Adapter RedisSessionActivityAdapter (TypeScript)

**Archivos:**
- CREAR `services/whatsapp/src/adapters/outbound/redis-session-activity.adapter.ts`

**Descripción:**
Implementar `ISessionActivity` con ioredis (el cliente Redis que ya usa el proyecto).

- `updateLastActivity`: `SET last_activity:{id} <unix_ms> EX 86400` + `DEL warning_sent:{id}`
- `getInactiveSessions`: `SCAN` con patrón `last_activity:*`, filtra por `Date.now() - timestamp >= minutos * 60000`
- `markWarningSent`: `SET warning_sent:{id} 1 EX 120`
- `isWarningSent`: `EXISTS warning_sent:{id}`
- `clearActivityKeys`: `DEL last_activity:{id} warning_sent:{id}`

**Criterio done:**
- Todos los métodos implementados
- Test unitario con mock de Redis que verifica los comandos emitidos

---

### TASK-03 — Extender ai-agent-http.adapter.ts con deleteSession()

**Archivos:**
- MODIFICAR `services/whatsapp/src/adapters/outbound/ai-agent-http.adapter.ts`
- MODIFICAR `services/whatsapp/src/domain/ports/ai-agent.port.ts`

**Descripción:**
Agregar `deleteSession(sessionId: string): Promise<void>` al port `IAiAgentClient` e implementarlo.
La llamada es `DELETE {AI_AGENT_SERVICE_URL}/session/{sessionId}`.
Si la respuesta es 404, no lanzar error (sesión ya no existía). Si hay error de red, loguear warn y continuar.

**Criterio done:**
- Método en el port y en el adapter
- Test unitario que verifica llamada HTTP y manejo de 404 sin excepción

---

### TASK-04 — Use case UpdateSessionActivityUseCase (TypeScript)

**Archivos:**
- CREAR `services/whatsapp/src/application/use-cases/update-session-activity.use-case.ts`

**Descripción:**
Use case simple: recibe `sessionId`, llama `sessionActivity.updateLastActivity(sessionId)`.
Inyectar vía `INJECTION_TOKENS.SESSION_ACTIVITY`.

**Criterio done:**
- Use case creado y testeado
- Test unitario verifica que se llama `updateLastActivity` con el session_id correcto

---

### TASK-05 — Use case CheckInactiveSessionsUseCase (TypeScript)

**Archivos:**
- CREAR `services/whatsapp/src/application/use-cases/check-inactive-sessions.use-case.ts`

**Descripción:**
Lógica principal del timeout. Lee env vars `SESSION_WARNING_MINUTES` (default 4) y `SESSION_CLOSE_MINUTES` (default 5).

```
execute():
  sesiones = getInactiveSessions(SESSION_WARNING_MINUTES)
  para cada sesión:
    if inactividad >= SESSION_CLOSE_MINUTES Y isWarningSent:
      sender.sendText(id, GOODBYE_MSG)
      aiAgent.deleteSession(id)
      clearActivityKeys(id)
    else if inactividad >= SESSION_WARNING_MINUTES Y NOT isWarningSent:
      sender.sendText(id, WARNING_MSG)
      markWarningSent(id)
```

Mensajes definidos como constantes en el mismo archivo (ver requirements.md).

**Criterio done:**
- Use case implementado con la lógica de bifurcación
- Tests: verifica envío de aviso a los 4 min, cierre a los 5 min, idempotencia (no re-envía aviso si ya existe)

---

### TASK-06 — Scheduler SessionTimeoutScheduler (TypeScript)

**Archivos:**
- CREAR `services/whatsapp/src/whatsapp/session-timeout.scheduler.ts`
- MODIFICAR `services/whatsapp/src/app.module.ts` — agregar `ScheduleModule.forRoot()`
- MODIFICAR `services/whatsapp/src/whatsapp/whatsapp.module.ts` — registrar scheduler y nuevos providers

**Descripción:**
`@Injectable()` con `@Cron(CronExpression.EVERY_MINUTE)` que llama `checkInactiveSessions.execute()`.
Captura cualquier excepción del use case para que nunca mate el proceso.

Instalar dependencia: `npm install @nestjs/schedule` en `services/whatsapp/`.

**Criterio done:**
- Scheduler registrado y corriendo
- `npm run build` sin errores TypeScript
- En logs se ve el cron ejecutarse (modo dev)

---

### TASK-07 — Integrar UpdateSessionActivity en MessageDispatcher

**Archivos:**
- MODIFICAR `services/whatsapp/src/adapters/inbound/message.dispatcher.ts`

**Descripción:**
Inyectar `UpdateSessionActivityUseCase` en el dispatcher.
Al inicio del método `dispatch()`, llamar `await updateSessionActivity.execute(message.sessionId)` antes de despachar al use case de texto o audio.

**Criterio done:**
- Test de integración del dispatcher verifica que `updateLastActivity` se llama con el session_id correcto
- El flujo normal de mensajes no se ve afectado

---

### TASK-08 — Port ISessionStore: delete_session (Python)

**Archivos:**
- MODIFICAR `services/ai-agent/src/domain/ports/i_session_store.py`

**Descripción:**
Agregar método abstracto `delete_session(session_id: str) -> None`.

**Criterio done:**
- Método abstracto agregado al ABC
- Sin imports de frameworks externos en el domain

---

### TASK-09 — RedisSessionAdapter: implementar delete_session (Python)

**Archivos:**
- MODIFICAR `services/ai-agent/src/adapters/outbound/redis_session_adapter.py`

**Descripción:**
Implementar `delete_session`:
1. `DEL profile:{session_id}` — elimina el perfil de usuario
2. Eliminar claves del LangGraph checkpoint: el `AsyncRedisSaver` usa el patrón `checkpoint/{session_id}` — hacer `SCAN` con patrón `*{session_id}*` y eliminar todas las coincidencias

**Criterio done:**
- Método implementado
- Test unitario verifica que se eliminan las claves correctas con mock de Redis

---

### TASK-10 — Use case DeleteSessionUseCase (Python)

**Archivos:**
- CREAR `services/ai-agent/src/application/use_cases/delete_session.py`

**Descripción:**
Use case simple: recibe `session_id`, llama `session_store.delete_session(session_id)`.

**Criterio done:**
- Use case creado y testeado

---

### TASK-11 — Endpoint DELETE /session/{session_id} (Python FastAPI)

**Archivos:**
- MODIFICAR `services/ai-agent/src/adapters/inbound/agent_router.py`
- MODIFICAR `services/ai-agent/dependencies.py` — exponer `DeleteSessionUseCase`

**Descripción:**
```python
@router.delete("/session/{session_id}", status_code=200)
async def delete_session(session_id: str, use_case: DeleteSessionUseCase = Depends(...)):
    await use_case.execute(session_id)
    return {"deleted": True}
```
Si la sesión no existe, devolver `{"deleted": False}` con status 200 (no 404).

**Criterio done:**
- Endpoint accesible en `DELETE /session/{session_id}`
- Test de integración verifica respuesta 200 con `{"deleted": True}`

---

### TASK-12 — Variables de entorno y .env.example

**Archivos:**
- MODIFICAR `services/whatsapp/.env.example`
- MODIFICAR `services/whatsapp/src/app.module.ts` o config — leer `SESSION_WARNING_MINUTES` y `SESSION_CLOSE_MINUTES`

**Descripción:**
Agregar las dos variables con valores por defecto documentados en `.env.example`.
Validar que existan al arrancar (o usar defaults explícitos en código).

**Criterio done:**
- `.env.example` actualizado
- El servicio arranca sin las vars usando defaults 4 y 5

---

## Resumen de dependencias entre tasks

```
TASK-01 (port) → TASK-02 (adapter) → TASK-04, TASK-05 (use cases) → TASK-06 (scheduler)
                                                                   → TASK-07 (dispatcher)
TASK-03 (deleteSession adapter) → TASK-05
TASK-08 (port Python) → TASK-09 (adapter Python) → TASK-10 (use case Python) → TASK-11 (endpoint)
TASK-11 → TASK-03 (NestJS llama al endpoint)
TASK-12 → cualquier tarea que lea env vars
```

Orden sugerido de implementación: 01 → 08 → 02 → 09 → 03 → 10 → 04 → 11 → 05 → 06 → 07 → 12
