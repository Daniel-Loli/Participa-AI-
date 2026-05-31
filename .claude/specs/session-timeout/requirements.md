# requirements.md — Módulo session-timeout

> Estado: ✅ aprobado
> Servicio principal: `services/whatsapp` (NestJS)
> Servicio secundario: `services/ai-agent` (FastAPI) — nuevo endpoint DELETE /session

---

## Contexto

WhatsApp permite enviar mensajes libres dentro de la ventana de 24h desde el último mensaje del usuario.
El módulo session-timeout aprovecha esta ventana para enviar un aviso de inactividad a los 4 minutos y
cerrar automáticamente la sesión al minuto 5, liberando memoria Redis y mejorando la UX.
No se requieren templates de WhatsApp porque siempre operamos dentro de la ventana de 24h.

---

## Functional Requirements

| ID | Requisito |
|---|---|
| FR-01 | Cada vez que llega un mensaje del usuario, el sistema registra el timestamp de actividad en Redis con clave `last_activity:{session_id}` |
| FR-02 | A los 4 minutos de inactividad (sin nuevo mensaje del usuario), el sistema envía un mensaje de re-engagement preguntando si el usuario tiene más dudas |
| FR-03 | El aviso de re-engagement se envía solo una vez por período de inactividad; se marca con `warning_sent:{session_id}` en Redis |
| FR-04 | Si el usuario responde después del aviso, se resetea el timer y se elimina la marca `warning_sent` |
| FR-05 | A los 5 minutos totales de inactividad (1 min después del aviso), el sistema envía un mensaje de despedida y elimina todos los datos de sesión de Redis |
| FR-06 | La eliminación de sesión incluye: perfil de usuario (`profile:{session_id}`) e historial de conversación (LangGraph checkpoint) |
| FR-07 | El sistema expone un endpoint `DELETE /session/{session_id}` en el agente Python para que NestJS pueda limpiar el lado Python de Redis |

---

## Non-Functional Requirements

| ID | Requisito |
|---|---|
| NFR-01 | El cron job se ejecuta cada 60 segundos usando `@nestjs/schedule` — sin nueva infraestructura |
| NFR-02 | El cron no bloquea el procesamiento de mensajes entrantes (operación asíncrona independiente) |
| NFR-03 | La latencia del cron sobre Redis debe ser < 500 ms por sesión procesada |
| NFR-04 | Si el agente Python no responde al DELETE, NestJS loguea warn pero no propaga el error (sesión se elimina igualmente del lado NestJS) |
| NFR-05 | Nunca se logueará el número de teléfono en texto plano — solo `from_hash` en logs |
| NFR-06 | No requiere templates de WhatsApp aprobados por Meta |
| NFR-07 | Compatible con el free tier de Redis Cloud (sin keyspace notifications — se usa polling) |

---

## Casos de uso

### UC-01 — Registrar actividad al recibir mensaje
**Actor:** Sistema (MessageDispatcher)
**Precondición:** Llega un mensaje de texto o audio del usuario
**Flujo:**
1. MessageDispatcher recibe el mensaje
2. Antes de delegar al use-case, actualiza `last_activity:{session_id}` en Redis con timestamp Unix actual (TTL 24h)
3. Continúa el flujo normal de procesamiento

### UC-02 — Enviar aviso de inactividad (4 min)
**Actor:** Cron scheduler (cada 60s)
**Precondición:** Existen sesiones activas con timestamp de actividad en Redis
**Flujo:**
1. Cron itera las claves `last_activity:*` en Redis
2. Para cada clave, calcula `ahora - last_activity`
3. Si delta >= 4 min Y `warning_sent:{session_id}` no existe:
   - Envía mensaje de re-engagement via WhatsApp
   - Crea `warning_sent:{session_id}` en Redis con TTL de 2 min

### UC-03 — Cerrar sesión por inactividad (5 min)
**Actor:** Cron scheduler (cada 60s)
**Precondición:** Existe `warning_sent:{session_id}` y `last_activity:{session_id}` sigue sin actualizarse
**Flujo:**
1. Si delta >= 5 min Y `warning_sent:{session_id}` existe:
   - Envía mensaje de despedida via WhatsApp
   - Llama `DELETE /session/{session_id}` en el agente Python
   - Elimina `last_activity:{session_id}` y `warning_sent:{session_id}` de Redis

### UC-04 — Resetear timer al responder tras aviso
**Actor:** Sistema (UC-01 se ejecuta después de un mensaje del usuario)
**Flujo:**
1. Llega un mensaje del usuario (incluso después del aviso)
2. UC-01 actualiza `last_activity:{session_id}` con el nuevo timestamp
3. Se elimina `warning_sent:{session_id}` si existía (el usuario volvió a estar activo)

---

## Criterios de aceptación (EARS)

| ID | Criterio |
|---|---|
| CA-01 | WHEN el sistema recibe cualquier mensaje del usuario, SHALL actualizar `last_activity:{session_id}` en Redis |
| CA-02 | WHILE una sesión está activa, WHEN han transcurrido ≥ 4 minutos sin mensaje y no existe `warning_sent`, SHALL enviar el aviso |
| CA-03 | WHEN han transcurrido ≥ 5 minutos sin mensaje y existe `warning_sent`, SHALL enviar despedida y eliminar la sesión |
| CA-04 | WHEN el usuario responde después del aviso, SHALL resetear el timer y eliminar `warning_sent` |
| CA-05 | IF el agente Python responde con error al DELETE, NestJS SHALL loguear el error y continuar sin propagar la excepción |
| CA-06 | El cron SHALL ejecutarse con una granularidad de 60 segundos y SHALL ser idempotente (re-runs sin efecto doble) |
| CA-07 | Los mensajes de aviso y despedida SHALL estar en español, tono cercano, sin markdown roto |

---

## Mensajes definidos

**Aviso de inactividad (4 min):**
> "¿Sigues ahí? 👋 Si tienes más dudas sobre participación ciudadana, con gusto te ayudo. Si no, en un momento cerramos esta sesión."

**Despedida (5 min):**
> "Cerramos esta sesión. Cuando quieras volver a participar, escríbeme y seguimos. ¡Tú puedes hacer la diferencia! 💪"

---

## Fuera del alcance

- Re-engagement después de 24h (requiere templates aprobados por Meta — módulo futuro)
- Estadísticas de tasa de abandono (módulo de analytics — futuro)
- Configuración dinámica de tiempos (hardcodeado en env vars para el MVP)
