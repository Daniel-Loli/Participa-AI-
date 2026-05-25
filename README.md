# Participa AI

Agente conversacional WhatsApp que guía a jóvenes peruanos (15-29 años) desde una preocupación ciudadana hasta una acción de incidencia concreta, legal y verificable.

**Hackathon Becas BCP 2025**

---

## Stack

| Capa | Tecnología |
|---|---|
| Canal | WhatsApp Business API |
| Backend | Node.js + NestJS (TypeScript) |
| IA | Python + FastAPI + LangGraph |
| LLM | OpenAI gpt-4o-mini |
| Vector DB | Qdrant Cloud |
| Sesiones | Redis Cloud |
| Despliegue | GCP Cloud Run |

## Servicios

- `services/whatsapp` — webhook NestJS, puerto 3000
- `services/ai-agent` — agentes LangGraph, puerto 8000
- `data-pipeline` — ingestión RAG y scraper diario

## Despliegue

CI/CD automático via GCP Cloud Build desde GitHub. Ver `cloudbuild.yaml`.
