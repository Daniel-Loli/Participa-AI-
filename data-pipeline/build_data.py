#!/usr/bin/env python3
"""
Genera los archivos JSON que usan los nodos del agente:
  - directorio.json   (de Excel RENOJ — única fuente local con respaldo oficial)
  - municipios.json   (nombre oficial y web de municipalidades de Lima Metropolitana)
  - calendar.json     (eventos municipales — VACÍO hasta tener scraper de fuentes oficiales)

REGLA: aquí no se inventa nada. Los datos de funcionarios, mesas de partes, eventos,
iniciativas y presupuestos se eliminaron porque no provenían de ninguna fuente oficial
(eran seed de demo del MVP). Cuando exista el scraper de munlima/INFOGOB/MEF, esos
datos se generarán desde sus fuentes reales.

Uso desde la raíz del proyecto:
    cd services/ai-agent
    python ../../data-pipeline/build_data.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import openpyxl

# Forzar UTF-8 en stdout para Windows (cp1252 no soporta "✓")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
# Los nodos buscan data/ relativo a services/ai-agent/
DATA_DIR = ROOT / "services" / "ai-agent" / "data"
EXCEL_PATH = ROOT / "knowledge-base" / "data" / "BASE-DE-DATOS-ORGANIZACIONES-JUVENILES-E-INSTITUCIONES-PRIVADAS.xlsx"


def clean(value) -> str:
    return str(value).strip() if value is not None else ""


# ---------------------------------------------------------------------------
# directorio.json — organizaciones RENOJ desde el Excel
# ---------------------------------------------------------------------------

def build_directorio() -> list[dict]:
    wb = openpyxl.load_workbook(EXCEL_PATH)
    ws = wb.active  # hoja "ORGANIZACIONES JUVENILES"

    orgs = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        nombre = clean(row[1])
        if not nombre:
            continue
        orgs.append({
            "nombre": nombre,
            "region": clean(row[2]),
            "provincia": clean(row[3]),
            "distrito": clean(row[3]),   # mejor aproximación disponible en el Excel
            "representante": clean(row[4]),
            "contacto": clean(row[5]),
            "tipo": clean(row[6]),
            "area": clean(row[7]),
            "area2": clean(row[8]),
        })
    return orgs


# ---------------------------------------------------------------------------
# municipios.json — solo datos verificables: nombre oficial y dominio web
# (sin nombres de alcaldes ni direcciones de mesa de partes: cambian y no
#  tenemos fuente oficial automatizada todavía — INFOGOB/JNE pendiente)
# ---------------------------------------------------------------------------

# URLs verificadas con HTTP 200 el 2026-06-12 (web propia o página en el portal gob.pe)
_DISTRITOS_LIMA = [
    ("Lima", "Municipalidad Metropolitana de Lima", "https://www.munlima.gob.pe"),
    ("Miraflores", "Municipalidad de Miraflores", "https://www.miraflores.gob.pe"),
    ("San Isidro", "Municipalidad de San Isidro", "https://msi.gob.pe"),
    ("Santiago de Surco", "Municipalidad de Santiago de Surco", "https://www.munisurco.gob.pe"),
    ("San Borja", "Municipalidad de San Borja", "https://www.gob.pe/munisanborja"),
    ("La Molina", "Municipalidad de La Molina", "https://www.gob.pe/munilamolina"),
    ("Barranco", "Municipalidad de Barranco", "https://www.munibarranco.gob.pe"),
    ("Chorrillos", "Municipalidad de Chorrillos", "https://www.munichorrillos.gob.pe"),
    ("San Juan de Lurigancho", "Municipalidad de San Juan de Lurigancho", "https://www.gob.pe/munisanjuandelurigancho"),
    ("Villa El Salvador", "Municipalidad de Villa El Salvador", "https://www.gob.pe/munivillaelsalvador"),
    ("Los Olivos", "Municipalidad de Los Olivos", "https://www.gob.pe/munilosolivos"),
    ("Callao", "Municipalidad Provincial del Callao", "https://www.gob.pe/municallao"),
    ("Ate", "Municipalidad de Ate", "https://www.gob.pe/muniate"),
    ("San Martín de Porres", "Municipalidad de San Martín de Porres", "https://www.gob.pe/munisanmartindeporres"),
    ("Comas", "Municipalidad de Comas", "https://www.gob.pe/municomas"),
]


def build_municipios() -> list[dict]:
    return [
        {"distrito": distrito, "municipio": municipio, "web": web}
        for distrito, municipio, web in _DISTRITOS_LIMA
    ]


# ---------------------------------------------------------------------------
# calendar.json — vacío hasta tener scraper de calendarios municipales
# (los eventos anteriores eran datos de demo sin fuente oficial)
# ---------------------------------------------------------------------------

def build_calendar() -> list[dict]:
    return []


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)

    print("Construyendo directorio.json desde Excel RENOJ...")
    orgs = build_directorio()
    (DATA_DIR / "directorio.json").write_text(
        json.dumps(orgs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  ✓ data/directorio.json   — {len(orgs)} organizaciones")

    print("Construyendo municipios.json...")
    municipios = build_municipios()
    (DATA_DIR / "municipios.json").write_text(
        json.dumps(municipios, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  ✓ data/municipios.json   — {len(municipios)} distritos")

    print("Construyendo calendar.json...")
    events = build_calendar()
    (DATA_DIR / "calendar.json").write_text(
        json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  ✓ data/calendar.json     — {len(events)} eventos")

    print(f"\n  ✓ Todos los archivos generados en: {DATA_DIR}\n")


if __name__ == "__main__":
    main()
