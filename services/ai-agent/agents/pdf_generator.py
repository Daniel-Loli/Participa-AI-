from __future__ import annotations

import base64
import io
import re
from datetime import date

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

_BLUE = HexColor("#1a3a6e")
_GOLD = HexColor("#F5C842")
_GRAY = HexColor("#888888")


def _strip_wa_markdown(text: str) -> str:
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    return text.strip()


def generate_letter_pdf(letter_text: str, doc_type: str, name: str, district: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=3 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
    )

    base_styles = getSampleStyleSheet()

    header_style = ParagraphStyle(
        "PAHeader",
        parent=base_styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=_BLUE,
        alignment=TA_CENTER,
        spaceAfter=2,
    )
    subheader_style = ParagraphStyle(
        "PASubHeader",
        parent=base_styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        textColor=_GRAY,
        alignment=TA_CENTER,
        spaceAfter=14,
    )
    body_style = ParagraphStyle(
        "PABody",
        parent=base_styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=16,
        alignment=TA_JUSTIFY,
        spaceAfter=10,
    )
    footer_style = ParagraphStyle(
        "PAFooter",
        parent=base_styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        textColor=_GRAY,
        alignment=TA_CENTER,
    )

    story = []

    # Encabezado institucional
    story.append(Paragraph("PARTICIPA AI", header_style))
    story.append(Paragraph("Plataforma de Participación Ciudadana Juvenil", subheader_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=_GOLD, spaceAfter=20))

    # Cuerpo de la carta (limpiado de markdown WhatsApp)
    clean_text = _strip_wa_markdown(letter_text)
    paragraphs = [p.strip() for p in clean_text.split("\n\n") if p.strip()]

    for para in paragraphs:
        # Preservar saltos de línea simples como <br/>
        html_para = para.replace("\n", "<br/>")
        story.append(Paragraph(html_para, body_style))

    # Pie de página
    story.append(Spacer(1, 1.2 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_GRAY, spaceAfter=6))
    story.append(
        Paragraph(
            f"Documento generado con Participa AI — {date.today().strftime('%d/%m/%Y')}",
            footer_style,
        )
    )

    doc.build(story)
    return buffer.getvalue()


def letter_to_base64(letter_text: str, doc_type: str, name: str, district: str) -> str:
    pdf_bytes = generate_letter_pdf(letter_text, doc_type, name, district)
    return base64.b64encode(pdf_bytes).decode()
