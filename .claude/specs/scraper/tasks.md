# Tasks — Módulo: scraper
**Proyecto:** Participa AI  
**Módulo:** `data-pipeline/scraper/`  
**Fecha:** 2026-05-24  
**Estado:** ✅ COMPLETO — 7/7 tareas implementadas y probadas  
**Depende de:** `design.md` (aprobado)

---

## Resumen de tareas

| ID | Tarea | Estado |
|---|---|---|
| TASK-001 | `requirements.txt` + scaffolding de carpeta | ✅ |
| TASK-002 | `sources.py` — 5 URLs SENAJU con `SourceUrl(url, content_type)` | ✅ |
| TASK-003 | `fetcher.py` — HTTP GET con reintentos, timeout y `verify=False` | ✅ |
| TASK-004 | `parser.py` — extracción de texto limpio con BeautifulSoup | ✅ |
| TASK-005 | `pipeline.py` — chunk → embed → upsert con `content_type` en payload | ✅ |
| TASK-006 | `run_scraper.py` — entrypoint + orquestador + CLI (`--source`, `--dry-run`) | ✅ |
| TASK-007 | Prueba end-to-end: dry-run verificado, 29 chunks identificados correctamente | ✅ |

**Total estimado: ~3.5 horas**

---

## Detalle de tareas

---

### TASK-001 — `requirements.txt` + scaffolding

**Estimado:** 15 min  
**Dependencias:** ninguna

**Archivos a crear:**
- `data-pipeline/scraper/__init__.py`
- `data-pipeline/scraper/requirements.txt`

**Acciones:**
1. Crear `requirements.txt` con las versiones del design §8:
```
httpx==0.27.0
beautifulsoup4==4.12.3
langchain-openai==0.1.8
langchain-text-splitters==0.2.2
qdrant-client==1.9.1
python-dotenv==1.0.1
```
2. Crear `__init__.py` vacío

**Criterio de done:**
- `pip install -r data-pipeline/scraper/requirements.txt` instala sin conflictos

---

### TASK-002 — `sources.py`

**Estimado:** 20 min  
**Dependencias:** TASK-001

**Archivo a crear:** `data-pipeline/scraper/sources.py`

**Acciones:**
1. Definir dataclass `Source` con campos: `id`, `name`, `urls`, `collection`, `css_selectors`
2. Definir lista `ALL_SOURCES` con las 6 fuentes del design §2
3. Exponer función `get_sources(source_id: str | None) -> list[Source]`:
   - Si `source_id` es None → retorna `ALL_SOURCES`
   - Si `source_id` es un ID válido → retorna lista con esa fuente
   - Si `source_id` no existe → lanza `ValueError` con mensaje claro

**Criterio de done:**
- `from scraper.sources import get_sources; get_sources(None)` retorna 6 fuentes
- `get_sources("senaju")` retorna 1 fuente
- `get_sources("invalido")` lanza `ValueError`

---

### TASK-003 — `fetcher.py`

**Estimado:** 30 min  
**Dependencias:** TASK-001

**Archivo a crear:** `data-pipeline/scraper/fetcher.py`

**Acciones:**
1. Definir excepción `FetchError(Exception)`
2. Implementar `fetch(url: str, timeout: int = 15) -> str`:
   - Usar `httpx.get` con `headers={"User-Agent": "ParticipaAI-Scraper/1.0 (contact: participa.ai@hackathon.pe)"}`
   - Si `httpx.TimeoutException` o `httpx.ConnectError` → esperar 3s → reintentar 1 vez
   - Si falla el reintento → lanzar `FetchError(url, motivo)`
   - Si HTTP status >= 400 → lanzar `FetchError(url, f"HTTP {status}")`
   - Esperar 1 segundo antes de retornar (rate limiting cortés)
   - Retornar `response.text`

**Criterio de done:**
- `fetch("https://juventud.gob.pe")` retorna HTML sin error (prueba manual)
- URL inválida → `FetchError` después de 1 reintento

---

### TASK-004 — `parser.py`

**Estimado:** 30 min  
**Dependencias:** TASK-001

**Archivo a crear:** `data-pipeline/scraper/parser.py`

**Acciones:**
1. Implementar `parse_html(html: str, css_selectors: list[str]) -> str`:
   - Crear `BeautifulSoup(html, "html.parser")`
   - Eliminar tags: `script`, `style`, `nav`, `footer`, `header`, `noscript`, `iframe`
   - Para cada selector en `css_selectors` → `soup.select(selector)` → extraer `.get_text(separator=" ")`
   - Unir todo el texto extraído
   - Colapsar múltiples espacios/newlines en un solo `\n`
   - Strip final
   - Retornar texto limpio

**Criterio de done:**
- HTML de prueba con `<nav>menú</nav><main><p>Convocatoria abierta</p></main>` →
  el nav no aparece en el resultado, "Convocatoria abierta" sí aparece

---

### TASK-005 — `pipeline.py`

**Estimado:** 40 min  
**Dependencias:** TASK-002

**Archivo a crear:** `data-pipeline/scraper/pipeline.py`

**Acciones:**
1. Copiar funciones `content_id()` y lógica de chunking de `ingest_rag.py` (mismos parámetros: 800/150)
2. Implementar `process_source_text(text, source_url, collection, embeddings, qdrant_client) -> int`:
   - Dividir texto en chunks (`RecursiveCharacterTextSplitter`)
   - Descartar chunks con menos de 60 caracteres
   - Procesar en batches de 50
   - Por cada batch:
     - `embeddings.embed_documents(texts)` — timeout implícito de langchain
     - Construir `PointStruct` con payload: `{content, source, scraped_at (ISO UTC), collection, type: "scraped"}`
     - `qdrant_client.upsert(collection_name, points)`
     - Esperar 0.4s entre batches
   - Si la colección no existe → crearla (1536 dims, coseno) antes del primer upsert
   - Retornar total de puntos subidos
3. Si error en un batch → loguear WARNING y continuar con el siguiente batch

**Criterio de done:**
- Llamada con texto de prueba y cliente Qdrant real → puntos aparecen en Qdrant
- Re-ejecución con el mismo texto → no duplica (mismo ID determinístico)

---

### TASK-006 — `run_scraper.py`

**Estimado:** 40 min  
**Dependencias:** TASK-002, TASK-003, TASK-004, TASK-005

**Archivo a crear:** `data-pipeline/scraper/run_scraper.py`

**Acciones:**
1. Cargar vars de entorno: intentar `services/ai-agent/.env` primero, luego entorno del sistema
2. Validar que existen `OPENAI_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY` — si no → `sys.exit(1)` con mensaje
3. Parsear argumento CLI `--source <id>` con `argparse`
4. Instanciar `OpenAIEmbeddings` y `QdrantClient`
5. Obtener fuentes con `get_sources(args.source)`
6. Para cada fuente:
   - Para cada URL en `source.urls`:
     - Llamar `fetch(url)` → si `FetchError` → log ERROR, continuar
     - Llamar `parse_html(html, source.css_selectors)`
     - Llamar `process_source_text(text, url, source.collection, embeddings, qdrant)`
   - Guardar resultado en lista
7. Imprimir resumen final:
```
========================================
  Scraper Participa AI — Resumen
========================================
  Fuentes procesadas : 6/6
  Chunks generados   : 342
  Puntos subidos     : 318
  Tiempo total       : 4m 12s
  Errores            : 0
========================================
```

**Criterio de done:**
- `python data-pipeline/scraper/run_scraper.py` procesa todas las fuentes e imprime resumen
- `python data-pipeline/scraper/run_scraper.py --source senaju` procesa solo SENAJU
- Sin vars de entorno → mensaje claro y exit code 1

---

### TASK-007 — Prueba manual end-to-end

**Estimado:** 30 min  
**Dependencias:** TASK-006

**Acciones:**
1. Desde la raíz del proyecto, con `.env` configurado:
   ```
   cd services/ai-agent
   python ../../data-pipeline/scraper/run_scraper.py --source senaju
   ```
2. Verificar en Qdrant Cloud dashboard que aparecen puntos nuevos en `procedimientos`
   con `type: "scraped"` en el payload
3. Verificar que re-ejecutar no duplica puntos (mismo count en Qdrant)
4. Verificar que `--source invalido` da error claro

**Criterio de done:**
- Puntos con `type: "scraped"` visibles en Qdrant Cloud
- Re-ejecución idempotente confirmada
- El agente puede recuperar esos chunks (búsqueda manual en Qdrant confirma relevancia)
