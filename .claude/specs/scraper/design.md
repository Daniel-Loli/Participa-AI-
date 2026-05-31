# Design — Módulo: scraper
**Proyecto:** Participa AI  
**Módulo:** `data-pipeline/scraper/`  
**Fecha:** 2026-05-24  
**Estado:** BORRADOR — pendiente aprobación  
**Depende de:** `requirements.md` (aprobado)

---

## 1. Estructura de archivos

```
data-pipeline/
├── scraper/
│   ├── run_scraper.py        ← entrypoint (CLI + orquestador)
│   ├── sources.py            ← configuración declarativa de las 7 fuentes
│   ├── fetcher.py            ← HTTP GET con reintentos y timeout
│   ├── parser.py             ← BeautifulSoup: extrae texto limpio del HTML
│   ├── pipeline.py           ← chunk → embed → upsert (reutiliza lógica de ingest_rag.py)
│   └── requirements.txt      ← dependencias del scraper
├── build_data.py             ← ya existe ✅
└── ingest_rag.py             ← ya existe ✅
```

---

## 2. Configuración de fuentes (`sources.py`)

Cada fuente es un dataclass con todo lo necesario para procesarla. Cada URL
tiene su propio `content_type` para clasificar el contenido en Qdrant:

```python
@dataclass
class SourceUrl:
    url: str
    content_type: str   # "general", "noticia", "voluntariado", "programa", "normativa"

@dataclass
class Source:
    id: str                     # "senaju"
    name: str                   # nombre legible para logs
    urls: list[SourceUrl]       # URLs con su tipo de contenido
    collection: str             # colección Qdrant destino
    css_selectors: list[str]    # selectores BeautifulSoup
```

### URLs configuradas (solo SENAJU)

> Otras fuentes descartadas tras pruebas: munlima (JS-renderizado), infogob (TLS incompatible),
> gob.pe (URLs inválidas), MEF (sin chunks útiles). SENAJU cubre el dominio core del MVP.

| URL | Tipo | Colección |
|---|---|---|
| `juventud.gob.pe` | `general` | `procedimientos` |
| `juventud.gob.pe/noticias/` | `noticia` | `procedimientos` |
| `juventud.gob.pe/voluntariado-juvenil/` | `voluntariado` | `procedimientos` |
| `juventud.gob.pe/participacion-juvenil/` | `programa` | `procedimientos` |
| `juventud.gob.pe/organizaciones-juveniles/` | `normativa` | `procedimientos` |

---

## 3. Flujo de datos

```
run_scraper.py
    │
    ├── args.source → filtra fuentes (o corre todas si no se especifica)
    ├── args.dry-run → imprime chunks clasificados sin subir a Qdrant
    │
    └── por cada Source → por cada SourceUrl:
            │
            fetcher.py
            │   httpx.get(url, timeout=15, verify=False, headers={"User-Agent": ...})
            │   reintento x1 si falla (espera 3s)
            │   → html: str
            │
            parser.py
            │   BeautifulSoup(html, "html.parser")
            │   extraer texto de css_selectors
            │   limpiar whitespace múltiple
            │   → text: str
            │
            pipeline.py
            │   RecursiveCharacterTextSplitter(chunk_size=800, overlap=150)
            │   → chunks: list[str]  (descarta < 60 chars)
            │
            │   OpenAIEmbeddings.embed_documents(batch de 50)
            │   → vectors: list[list[float]]
            │
            │   QdrantClient.upsert(collection, PointStruct(
            │       id=md5(chunk),
            │       vector=vector,
            │       payload={content, source_url, scraped_at, collection}
            │   ))
            │
            → ScrapedResult(source_id, chunks_total, chunks_uploaded, error?)
            
    resumen final → stdout (capturado por Render logs)
```

---

## 4. Módulos en detalle

### 4.1 `run_scraper.py` — Entrypoint

```python
# CLI
python run_scraper.py                  # todas las fuentes
python run_scraper.py --source senaju  # solo una fuente
```

Responsabilidades:
- Cargar variables de entorno (desde `services/ai-agent/.env` o entorno)
- Parsear argumento `--source` (opcional)
- Instanciar clientes OpenAI y Qdrant
- Iterar fuentes, llamar pipeline, capturar errores por fuente
- Imprimir resumen final

### 4.2 `fetcher.py`

```python
async def fetch(url: str, timeout: int = 15) -> str:
    # httpx.AsyncClient con User-Agent
    # reintento 1x si ConnectError o TimeoutException (espera 3s)
    # lanza FetchError si falla en ambos intentos
```

### 4.3 `parser.py`

```python
def parse_html(html: str, css_selectors: list[str]) -> str:
    # BeautifulSoup: extraer texto de los selectores en orden
    # strip de tags script, style, nav, footer, header
    # colapsar whitespace múltiple en un solo \n
    # retorna texto plano limpio
```

### 4.4 `pipeline.py`

Reutiliza la lógica de `ingest_rag.py` extraída a funciones:

```python
def content_id(text: str) -> int           # MD5 → int (mismo algoritmo)
def split_text(text: str) -> list[str]     # chunk 800/150
async def embed_and_upload(
    chunks: list[str],
    source_url: str,
    collection: str,
    embeddings: OpenAIEmbeddings,
    qdrant: QdrantClient,
) -> int                                   # retorna cantidad de puntos subidos
```

---

## 5. Manejo de errores

| Error | Comportamiento |
|---|---|
| `FetchError` (timeout, 404, red) | Log ERROR, continuar con siguiente fuente |
| `openai.APIError` en embedding | Log ERROR en ese batch, continuar con siguientes chunks |
| `qdrant.exceptions.UnexpectedResponse` | Log ERROR, continuar |
| Variable de entorno faltante | `sys.exit(1)` inmediato con mensaje claro |
| Colección Qdrant no existe | Crearla automáticamente (igual que `ingest_rag.py`) |

---

## 6. Payload en Qdrant

Cada punto subido por el scraper tiene este payload:

```json
{
  "content": "texto del chunk",
  "source": "https://juventud.gob.pe/voluntariado-juvenil/",
  "scraped_at": "2026-05-24T08:03:21Z",
  "collection": "procedimientos",
  "type": "scraped",
  "content_type": "voluntariado"
}
```

- `type: "scraped"` distingue estos chunks de los PDFs (`type: "pdf"`)
- `content_type` clasifica el contenido por su naturaleza: `general`, `noticia`, `voluntariado`, `programa`, `normativa`
- Ambos campos permiten filtrar búsquedas RAG por origen o tipo si se necesita en el futuro

---

## 7. Render Cron Job — configuración en `render.yaml`

```yaml
services:
  # ... servicios existentes

  - type: cron
    name: participa-scraper
    runtime: python
    schedule: "0 13 * * *"          # 8AM Lima (UTC-5)
    buildCommand: pip install -r data-pipeline/scraper/requirements.txt
    startCommand: cd data-pipeline && python scraper/run_scraper.py
    envVars:
      - fromGroup: participa-ai-env  # mismo grupo de vars que el ai-agent
```

---

## 8. Dependencias (`scraper/requirements.txt`)

```
httpx==0.27.0
beautifulsoup4==4.12.3
langchain-openai==0.1.8
langchain-text-splitters==0.2.2
qdrant-client==1.9.1
python-dotenv==1.0.1
```

Mismas versiones que ya usa `services/ai-agent/requirements.txt` para evitar conflictos.

---

## 9. Decisiones de diseño

### ¿Por qué `httpx` y no `requests`?
`httpx` soporta `async`, lo que permite en el futuro paralelizar el fetch de múltiples fuentes. Por ahora se usa en modo síncrono por simplicidad.

### ¿Por qué no un framework de scraping (Scrapy, Playwright)?
Las 7 fuentes son páginas gubernamentales con HTML renderizado en servidor (no JS-heavy). `httpx` + `BeautifulSoup` es suficiente y no agrega dependencias pesadas.

### ¿Por qué no guardar en `directorio.json` los resultados de INFOGOB?
INFOGOB tiene datos estructurados de autoridades. Por ahora va a Qdrant como texto, lo que permite búsqueda semántica. Si en el futuro se necesita lookup exacto por distrito, se puede agregar un extractor estructurado separado.

### ¿Por qué un solo `run_scraper.py` y no un scraper por fuente?
Para el Render Cron Job, un único proceso que orquesta todo es más simple de operar y monitorear. El `--source` flag permite ejecutar uno solo si se necesita debugging.
