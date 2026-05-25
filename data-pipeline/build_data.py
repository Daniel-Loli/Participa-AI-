#!/usr/bin/env python3
"""
Genera los archivos JSON que usan los nodos del agente:
  - directorio.json   (de Excel RENOJ)
  - municipios.json   (funcionarios y mesas de partes Lima)
  - calendar.json     (eventos municipales próximos)
  - iniciativas.json  (casos de éxito e iniciativas ciudadanas)
  - presupuestos.json (histórico PP por distrito)

Uso desde la raíz del proyecto:
    cd services/ai-agent
    python ../../data-pipeline/build_data.py
"""
from __future__ import annotations

import json
from pathlib import Path

import openpyxl

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
# municipios.json — alcaldes y mesas de partes de Lima (principales distritos)
# ---------------------------------------------------------------------------

def build_municipios() -> list[dict]:
    return [
        {
            "distrito": "Lima",
            "funcionario": "Rafael López Aliaga",
            "cargo": "Alcalde",
            "municipio": "Municipalidad Metropolitana de Lima",
            "mesa_partes": "Jr. de la Unión 300, Cercado de Lima",
        },
        {
            "distrito": "Miraflores",
            "funcionario": "Carlos Canales",
            "cargo": "Alcalde",
            "municipio": "Municipalidad de Miraflores",
            "mesa_partes": "Av. Larco 400, Miraflores",
        },
        {
            "distrito": "San Isidro",
            "funcionario": "Manuel Velarde",
            "cargo": "Alcalde",
            "municipio": "Municipalidad de San Isidro",
            "mesa_partes": "Av. Miguel Dasso 250, San Isidro",
        },
        {
            "distrito": "Santiago de Surco",
            "funcionario": "Carlos Bruce",
            "cargo": "Alcalde",
            "municipio": "Municipalidad de Santiago de Surco",
            "mesa_partes": "Av. Ayacucho 824, Surco",
        },
        {
            "distrito": "San Borja",
            "funcionario": "Marco Álvarez",
            "cargo": "Alcalde",
            "municipio": "Municipalidad de San Borja",
            "mesa_partes": "Av. De La Floresta 495, San Borja",
        },
        {
            "distrito": "La Molina",
            "funcionario": "Álvaro Paz de la Barra",
            "cargo": "Alcalde",
            "municipio": "Municipalidad de La Molina",
            "mesa_partes": "Av. La Fontana 1010, La Molina",
        },
        {
            "distrito": "Barranco",
            "funcionario": "Renzo Reggiardo",
            "cargo": "Alcalde",
            "municipio": "Municipalidad de Barranco",
            "mesa_partes": "Jr. Junín 245, Barranco",
        },
        {
            "distrito": "Chorrillos",
            "funcionario": "Augusto Miyashiro",
            "cargo": "Alcalde",
            "municipio": "Municipalidad de Chorrillos",
            "mesa_partes": "Av. Guardia Civil 1025, Chorrillos",
        },
        {
            "distrito": "San Juan de Lurigancho",
            "funcionario": "Jesús Maldonado",
            "cargo": "Alcalde",
            "municipio": "Municipalidad de San Juan de Lurigancho",
            "mesa_partes": "Av. Gran Chimú 400, San Juan de Lurigancho",
        },
        {
            "distrito": "Villa El Salvador",
            "funcionario": "Kevin Quevedo",
            "cargo": "Alcalde",
            "municipio": "Municipalidad de Villa El Salvador",
            "mesa_partes": "Av. Revolución s/n, Villa El Salvador",
        },
        {
            "distrito": "Los Olivos",
            "funcionario": "Felipe Castillo",
            "cargo": "Alcalde",
            "municipio": "Municipalidad de Los Olivos",
            "mesa_partes": "Av. Carlos Izaguirre 176, Los Olivos",
        },
        {
            "distrito": "Callao",
            "funcionario": "John Reynaga",
            "cargo": "Alcalde",
            "municipio": "Municipalidad del Callao",
            "mesa_partes": "Jr. Constitución 104, Callao",
        },
        {
            "distrito": "Ate",
            "funcionario": "Oscar Benavides",
            "cargo": "Alcalde",
            "municipio": "Municipalidad de Ate",
            "mesa_partes": "Av. Nicolás Ayllón 580, Ate",
        },
        {
            "distrito": "San Martín de Porres",
            "funcionario": "Julio Buitrón",
            "cargo": "Alcalde",
            "municipio": "Municipalidad de San Martín de Porres",
            "mesa_partes": "Av. Tomás Valle s/n, SMP",
        },
        {
            "distrito": "Comas",
            "funcionario": "Ulises Villegas",
            "cargo": "Alcalde",
            "municipio": "Municipalidad de Comas",
            "mesa_partes": "Av. Túpac Amaru 100, Comas",
        },
    ]


# ---------------------------------------------------------------------------
# calendar.json — eventos municipales Lima 2026
# ---------------------------------------------------------------------------

def build_calendar() -> list[dict]:
    return [
        {
            "fecha": "2026-06-05",
            "tipo": "Audiencia Pública",
            "titulo": "Audiencia de Presupuesto Participativo 2027",
            "distrito": "Lima",
            "descripcion": "Priorización de proyectos PP 2027 para el Cercado de Lima.",
            "requisitos": "Registro previo en la Municipalidad Metropolitana",
            "enlace": "https://www.munlima.gob.pe",
        },
        {
            "fecha": "2026-06-12",
            "tipo": "Sesión de Concejo",
            "titulo": "Sesión Ordinaria del Concejo Metropolitano de Lima",
            "distrito": "Lima",
            "descripcion": "Sesión pública del concejo. Ciudadanos pueden solicitar el uso de la palabra.",
            "requisitos": "Solicitud escrita con 48 horas de anticipación",
            "enlace": "https://www.munlima.gob.pe",
        },
        {
            "fecha": "2026-06-20",
            "tipo": "Presupuesto Participativo",
            "titulo": "Taller de Formulación de Ideas PP 2027 - Miraflores",
            "distrito": "Miraflores",
            "descripcion": "Taller para formular y presentar propuestas al PP 2027.",
            "requisitos": "Ser vecino empadronado de Miraflores",
            "enlace": "https://www.miraflores.gob.pe",
        },
        {
            "fecha": "2026-07-03",
            "tipo": "Audiencia Pública",
            "titulo": "Audiencia de Rendición de Cuentas - SJL",
            "distrito": "San Juan de Lurigancho",
            "descripcion": "El alcalde rinde cuentas sobre la ejecución presupuestal semestral.",
            "requisitos": "Ninguno, entrada libre",
            "enlace": "https://www.munisjl.gob.pe",
        },
        {
            "fecha": "2026-07-15",
            "tipo": "Presupuesto Participativo",
            "titulo": "Inscripción de Agentes Participantes PP 2027 - Lima",
            "distrito": "Lima",
            "descripcion": "Plazo de inscripción como agente participante para el PP 2027.",
            "requisitos": "DNI y acreditar residencia o trabajo en el distrito",
            "enlace": "https://www.munlima.gob.pe/pp",
        },
        {
            "fecha": "2026-07-20",
            "tipo": "Taller Ciudadano",
            "titulo": "Taller: Cómo presentar una propuesta al PP",
            "distrito": "Villa El Salvador",
            "descripcion": "Capacitación gratuita sobre el proceso de Presupuesto Participativo.",
            "requisitos": "Ninguno, inscripción en la municipalidad",
            "enlace": "https://www.mves.gob.pe",
        },
        {
            "fecha": "2026-07-28",
            "tipo": "Sesión de Concejo",
            "titulo": "Sesión Solemne por Fiestas Patrias - Los Olivos",
            "distrito": "Los Olivos",
            "descripcion": "Sesión especial con participación ciudadana y reconocimientos.",
            "requisitos": "Ninguno",
            "enlace": "https://www.munilosolivos.gob.pe",
        },
        {
            "fecha": "2026-08-01",
            "tipo": "Presupuesto Participativo",
            "titulo": "Priorización de Proyectos PP 2027 - Los Olivos",
            "distrito": "Los Olivos",
            "descripcion": "Votación y priorización de proyectos por los agentes participantes.",
            "requisitos": "Estar registrado como agente participante",
            "enlace": "https://www.munilosolivos.gob.pe",
        },
        {
            "fecha": "2026-08-15",
            "tipo": "Sesión de Concejo",
            "titulo": "Sesión de Aprobación PP Metropolitano 2027",
            "distrito": "Lima",
            "descripcion": "Sesión especial del Concejo Metropolitano para aprobación formal del PP.",
            "requisitos": "Ninguno, sesión pública",
            "enlace": "https://www.munlima.gob.pe",
        },
        {
            "fecha": "2026-09-10",
            "tipo": "Audiencia Pública",
            "titulo": "Audiencia de Consulta Vecinal - San Borja",
            "distrito": "San Borja",
            "descripcion": "Consulta a vecinos sobre proyectos de mejora urbana.",
            "requisitos": "Ser residente de San Borja",
            "enlace": "https://www.munisanborja.gob.pe",
        },
    ]


# ---------------------------------------------------------------------------
# iniciativas.json — casos de éxito e iniciativas ciudadanas exitosas
# ---------------------------------------------------------------------------

def build_iniciativas() -> list[dict]:
    return [
        {
            "id": "ini-001",
            "titulo": "Parque Inclusivo San Juan de Lurigancho",
            "distrito": "San Juan de Lurigancho",
            "region": "Lima",
            "año": 2024,
            "tipo": "Presupuesto Participativo",
            "estado": "Ejecutado",
            "monto_sol": 450000,
            "descripcion": "Construcción de área de juegos inclusiva para niños y jóvenes con discapacidad en el parque zonal Huiracocha.",
            "impacto": "3,200 familias beneficiadas. Primer parque inclusivo de Lima Este.",
            "promotores": "Colectivo Jóvenes con Voz SJL",
            "contacto": "jovenes.sjl@gmail.com",
            "ods": ["ODS 10", "ODS 11"],
        },
        {
            "id": "ini-002",
            "titulo": "Red de Bibliotecas Comunitarias Villa El Salvador",
            "distrito": "Villa El Salvador",
            "region": "Lima",
            "año": 2023,
            "tipo": "Iniciativa Ciudadana",
            "estado": "En operación",
            "monto_sol": 180000,
            "descripcion": "Apertura de 5 puntos de lectura y wifi gratuito en los conos de Villa El Salvador, gestionados por jóvenes voluntarios.",
            "impacto": "1,800 jóvenes acceden mensualmente. 60% reducción en brecha digital del distrito.",
            "promotores": "Asociación Jóvenes Constructores VES",
            "contacto": "jovenesVES@hotmail.com",
            "ods": ["ODS 4", "ODS 10"],
        },
        {
            "id": "ini-003",
            "titulo": "Vigilancia Ciudadana del Presupuesto Municipal - Comas",
            "distrito": "Comas",
            "region": "Lima",
            "año": 2024,
            "tipo": "Vigilancia Ciudadana",
            "estado": "Activo",
            "monto_sol": 0,
            "descripcion": "Grupo de 30 jóvenes que monitorean la ejecución del presupuesto municipal de Comas.",
            "impacto": "Detectaron 2 irregularidades. Lograron reasignación de S/. 120,000 hacia programas juveniles.",
            "promotores": "Observatorio Ciudadano Comas Joven",
            "contacto": "observatorio.comas@gmail.com",
            "ods": ["ODS 16", "ODS 17"],
        },
        {
            "id": "ini-004",
            "titulo": "Propuesta de Ordenanza de Espacio Joven - Los Olivos",
            "distrito": "Los Olivos",
            "region": "Lima",
            "año": 2023,
            "tipo": "Propuesta Normativa",
            "estado": "Aprobado",
            "monto_sol": 0,
            "descripcion": "Jóvenes redactaron y presentaron una propuesta de ordenanza para centros de emprendimiento juvenil. Aprobada en sesión de concejo.",
            "impacto": "Ordenanza N.° 567-2023-MDLO aprobada. 2 centros aperturados en 2024.",
            "promotores": "Red Juvenil Los Olivos",
            "contacto": "redjuvenil.losolivos@gmail.com",
            "ods": ["ODS 8", "ODS 16"],
        },
        {
            "id": "ini-005",
            "titulo": "Plan de Gestión de Residuos con Jóvenes - Miraflores",
            "distrito": "Miraflores",
            "region": "Lima",
            "año": 2024,
            "tipo": "Presupuesto Participativo",
            "estado": "En ejecución",
            "monto_sol": 320000,
            "descripcion": "Propuesta ganadora del PP 2025 para puntos de acopio de reciclaje administrados por jóvenes.",
            "impacto": "40 jóvenes empleados. 15 toneladas/mes de residuos reciclados.",
            "promotores": "Colectivo Verde Miraflores",
            "contacto": "verdemiraflores@gmail.com",
            "ods": ["ODS 12", "ODS 13"],
        },
        {
            "id": "ini-006",
            "titulo": "Solicitud de Información Pública sobre Obras - Barranco",
            "distrito": "Barranco",
            "region": "Lima",
            "año": 2024,
            "tipo": "Solicitud de Información",
            "estado": "Resuelto",
            "monto_sol": 0,
            "descripcion": "Vecinos jóvenes solicitaron información sobre obras paralizadas usando la Ley 27806. Obtuvieron respuesta en 7 días.",
            "impacto": "Se reanudaron obras paralizadas 8 meses.",
            "promotores": "Jóvenes de Barranco por el Cambio",
            "contacto": "barranco.cambio@gmail.com",
            "ods": ["ODS 16"],
        },
        {
            "id": "ini-007",
            "titulo": "Mesa de Concertación Juvenil - San Martín de Porres",
            "distrito": "San Martín de Porres",
            "region": "Lima",
            "año": 2023,
            "tipo": "Participación Institucional",
            "estado": "Activo",
            "monto_sol": 0,
            "descripcion": "Primera Mesa de Concertación Juvenil en SMP con 25 delegados de colegios, universidades y colectivos.",
            "impacto": "3 propuestas presentadas al concejo. 1 aprobada: semáforos peatonales en 5 intersecciones.",
            "promotores": "MUNI Joven SMP",
            "contacto": "munijoven.smp@gmail.com",
            "ods": ["ODS 16", "ODS 17"],
        },
    ]


# ---------------------------------------------------------------------------
# presupuestos.json — histórico de Presupuesto Participativo por distrito
# ---------------------------------------------------------------------------

def build_presupuestos() -> list[dict]:
    return [
        {
            "año": 2024,
            "distrito": "Lima",
            "monto_total_sol": 45000000,
            "monto_aprobado_sol": 38500000,
            "proyectos_aprobados": 12,
            "fecha_convocatoria": "2024-03-01",
            "fecha_priorizacion": "2024-05-15",
            "fecha_aprobacion": "2024-06-30",
            "proyectos_destacados": [
                "Mejoramiento vial Av. Abancay",
                "Centro de emprendimiento juvenil Cercado",
                "Parque inclusivo El Agustino",
            ],
            "enlace": "https://www.munlima.gob.pe/presupuesto-participativo",
        },
        {
            "año": 2024,
            "distrito": "San Juan de Lurigancho",
            "monto_total_sol": 12000000,
            "monto_aprobado_sol": 9800000,
            "proyectos_aprobados": 8,
            "fecha_convocatoria": "2024-02-15",
            "fecha_priorizacion": "2024-04-20",
            "fecha_aprobacion": "2024-06-01",
            "proyectos_destacados": [
                "Parque inclusivo Huiracocha",
                "Posta médica Huáscar",
                "Losas deportivas zona 5",
            ],
            "enlace": "https://www.munisjl.gob.pe/pp",
        },
        {
            "año": 2024,
            "distrito": "Villa El Salvador",
            "monto_total_sol": 8500000,
            "monto_aprobado_sol": 7200000,
            "proyectos_aprobados": 6,
            "fecha_convocatoria": "2024-03-10",
            "fecha_priorizacion": "2024-05-05",
            "fecha_aprobacion": "2024-06-15",
            "proyectos_destacados": [
                "Red de bibliotecas comunitarias",
                "Mejoramiento pistas sector 3",
                "Centro cultural juvenil",
            ],
            "enlace": "https://www.mves.gob.pe/pp",
        },
        {
            "año": 2024,
            "distrito": "Los Olivos",
            "monto_total_sol": 9200000,
            "monto_aprobado_sol": 7800000,
            "proyectos_aprobados": 7,
            "fecha_convocatoria": "2024-02-20",
            "fecha_priorizacion": "2024-04-25",
            "fecha_aprobacion": "2024-06-10",
            "proyectos_destacados": [
                "Centro de emprendimiento juvenil",
                "Pistas y veredas Pro",
                "Parque lineal Universitaria",
            ],
            "enlace": "https://www.munilosolivos.gob.pe/pp",
        },
        {
            "año": 2025,
            "distrito": "Lima",
            "monto_total_sol": 48000000,
            "monto_aprobado_sol": None,
            "proyectos_aprobados": None,
            "fecha_convocatoria": "2025-03-01",
            "fecha_priorizacion": "2025-05-20",
            "fecha_aprobacion": None,
            "estado": "En proceso de priorización",
            "proyectos_destacados": [],
            "enlace": "https://www.munlima.gob.pe/presupuesto-participativo",
        },
        {
            "año": 2025,
            "distrito": "San Juan de Lurigancho",
            "monto_total_sol": 13500000,
            "monto_aprobado_sol": None,
            "proyectos_aprobados": None,
            "fecha_convocatoria": "2025-02-15",
            "fecha_priorizacion": "2025-04-25",
            "fecha_aprobacion": None,
            "estado": "Convocatoria abierta — inscripción de agentes participantes hasta el 30/03/2025",
            "proyectos_destacados": [],
            "enlace": "https://www.munisjl.gob.pe/pp",
        },
    ]


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

    print("Construyendo iniciativas.json...")
    iniciativas = build_iniciativas()
    (DATA_DIR / "iniciativas.json").write_text(
        json.dumps(iniciativas, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  ✓ data/iniciativas.json  — {len(iniciativas)} iniciativas")

    print("Construyendo presupuestos.json...")
    presupuestos = build_presupuestos()
    (DATA_DIR / "presupuestos.json").write_text(
        json.dumps(presupuestos, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  ✓ data/presupuestos.json — {len(presupuestos)} registros PP")

    print(f"\n  ✓ Todos los archivos generados en: {DATA_DIR}\n")


if __name__ == "__main__":
    main()
