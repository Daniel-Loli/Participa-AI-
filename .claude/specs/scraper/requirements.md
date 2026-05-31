# Requirements — Módulo: scraper
**Proyecto:** Participa AI  
**Módulo:** `data-pipeline/scraper/`  
**Fecha:** 2026-05-24  
**Estado:** BORRADOR — pendiente aprobación  

---

## 1. Functional Requirements

### FR-01 — Ejecución diaria automática
El sistema DEBE ejecutarse automáticamente todos los días a las 8:00 AM (hora Lima, UTC-5)
como un Render Cron Job con expresión `0 13 * * *` (UTC).

### FR-02 — Fuentes a escrapear
El sistema DEBE extraer contenido de las siguientes 5 URLs de SENAJU, clasificadas por tipo de contenido:

| URL | Tipo de contenido | Colección Qdrant destino |
|---|---|---|
| `https://juventud.gob.pe` | `general` | `procedimientos` |
| `https://juventud.gob.pe/noticias/` | `noticia` | `procedimientos` |
| `https://juventud.gob.pe/voluntariado-juvenil/` | `voluntariado` | `procedimientos` |
| `https://juventud.gob.pe/participacion-juvenil/` | `programa` | `procedimientos` |
| `https://juventud.gob.pe/organizaciones-juveniles/` | `normativa` | `procedimientos` |

> Otras fuentes (munlima, gob.pe, infogob, MEF, observatorio) descartadas por incompatibilidades SSL,
> URLs inválidas o contenido JS-renderizado no accesible sin browser. SENAJU cubre el dominio core del MVP.

### FR-03 — Extracción de contenido
El sistema DEBE extraer solo texto relevante de cada página:
- Títulos, subtítulos y párrafos de contenido
- Fechas, plazos, requisitos y convocatorias
- EXCLUIR: menús de navegación, headers, footers, scripts, estilos CSS

### FR-04 — Chunking semántico
El sistema DEBE dividir el texto extraído en chunks de máximo 800 caracteres
con overlap de 150 caracteres, usando los mismos separadores que `ingest_rag.py`
(`\n\n`, `\n`, `. `, ` `).

### FR-05 — Deduplicación por hash
El sistema DEBE generar un ID determinístico por chunk usando MD5 del contenido
(mismo algoritmo que `ingest_rag.py`). Si el chunk ya existe en Qdrant con ese ID,
el upsert lo sobreescribe sin crear duplicado.

### FR-06 — Embeddings y carga a Qdrant
El sistema DEBE:
1. Embeber cada chunk con `text-embedding-3-small` (OpenAI)
2. Hacer upsert en la colección Qdrant correspondiente
3. Incluir en el payload: `content`, `source` (URL), `scraped_at` (ISO timestamp), `collection`
4. Crear la colección si no existe (vectores de 1536 dims, distancia coseno)

### FR-07 — Clasificación de contenido por tipo
Cada chunk subido a Qdrant DEBE incluir en su payload el campo `content_type`
con el valor correspondiente a la URL de origen (`general`, `noticia`, `voluntariado`,
`programa`, `normativa`). Esto permite en el futuro filtrar búsquedas RAG por tipo.

### FR-08 — Tolerancia a fallos por URL
Si una URL falla (timeout, 404, error de red), el sistema DEBE:
- Loguear el error con nivel ERROR indicando la URL y el motivo
- Continuar con las demás URLs (no abortar el proceso completo)
- Retornar un resumen final con cuántas URLs tuvieron éxito y cuántas fallaron

### FR-09 — Reporte de ejecución
Al finalizar, el sistema DEBE imprimir un resumen con:
- Fuentes procesadas: N/7
- Total de chunks generados
- Total de puntos subidos a Qdrant
- Tiempo total de ejecución
- Errores ocurridos (si los hay)

### FR-09 — Configuración por variables de entorno
El sistema DEBE leer las mismas variables de entorno que usa el ai-agent:
`OPENAI_API_KEY`, `OPENAI_EMBEDDING_MODEL`, `QDRANT_URL`, `QDRANT_API_KEY`.
Cargadas desde `services/ai-agent/.env` si existe, o desde el entorno de Render.

### FR-10 — Filtrado de contenido mínimo
El sistema DEBE descartar chunks con menos de 60 caracteres (ruido de extracción).

---

## 2. Non-Functional Requirements

### NFR-01 — Timeouts
- Petición HTTP por página: máximo 15 segundos
- Embedding batch (50 chunks): máximo 30 segundos
- Upsert Qdrant: máximo 10 segundos

### NFR-02 — Rate limiting cortés
El sistema DEBE esperar 1 segundo entre peticiones a la misma fuente
y 0.4 segundos entre batches de embedding (misma cadencia que `ingest_rag.py`).

### NFR-03 — User-Agent
El sistema DEBE identificarse con un User-Agent descriptivo:
`ParticipaAI-Scraper/1.0 (contact: participa.ai@hackathon.pe)`

### NFR-04 — Duración máxima
La ejecución completa de todas las fuentes DEBE terminar en menos de 10 minutos
(límite del Render Cron Job free tier).

### NFR-05 — Sin estado persistente entre ejecuciones
El scraper es stateless: no guarda qué URLs ya visitó entre días. La deduplicación
se maneja exclusivamente a través de los IDs determinísticos en Qdrant.

### NFR-06 — Sin PII
El scraper NUNCA almacena información de usuarios ni extrae datos personales.
Solo indexa contenido público gubernamental.

---

## 3. Casos de uso

### CU-01 — Ejecución diaria exitosa
**Actor:** Render Cron Job  
**Precondición:** Variables de entorno configuradas, Qdrant y OpenAI accesibles  
**Flujo:**
1. Cron dispara el script a las 8AM hora Lima
2. El script itera las 7 fuentes en secuencia
3. Por cada fuente: GET → parse → chunk → embed → upsert
4. Al final imprime el resumen
**Postcondición:** Qdrant tiene contenido actualizado del día

### CU-02 — Fuente no disponible
**Actor:** Render Cron Job  
**Precondición:** Una de las fuentes devuelve error 503  
**Flujo:**
1. El scraper intenta GET a la fuente
2. Recibe timeout o error HTTP
3. Loguea ERROR con fuente y detalle
4. Continúa con la siguiente fuente
**Postcondición:** Las demás 6 fuentes se procesan correctamente

### CU-03 — Re-ejecución manual
**Actor:** Desarrollador  
**Precondición:** Quiere re-indexar una fuente específica  
**Flujo:**
1. Ejecuta `python scraper/run_scraper.py --source senaju`
2. Solo procesa esa fuente  
**Postcondición:** Solo los chunks de esa fuente son actualizados en Qdrant

---

## 4. Criterios de aceptación (EARS)

| ID | Criterio |
|---|---|
| CA-01 | WHEN el cron se dispara THEN todas las fuentes disponibles son procesadas en < 10 minutos |
| CA-02 | WHEN una fuente devuelve error HTTP THEN las demás fuentes continúan procesándose |
| CA-03 | WHEN un chunk ya existe en Qdrant (mismo hash) THEN se actualiza sin crear duplicado |
| CA-04 | WHEN el scraping termina THEN el log muestra cuántas fuentes tuvieron éxito |
| CA-05 | WHEN falta una variable de entorno crítica THEN el script falla inmediatamente con mensaje claro |
| CA-06 | WHEN un chunk tiene menos de 60 caracteres THEN es descartado sin subirse a Qdrant |
| CA-07 | IF se pasa `--source <id>` THEN solo esa fuente es procesada |
