import csv
import io
import uuid
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from fencing_api.security import utcnow


def _rate_text(rate: dict | None) -> str:
    if not rate or rate.get("value") is None:
        return "not available (no samples)"
    return f"{rate['value'] * 100:.1f}% ({rate['numerator']}/{rate['denominator']})"


def build_performance_pdf(*, title: str, athlete_name: str, stats: dict, model_note: str) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 20 * mm
    pdf.setFont("Times-Roman", 16)
    pdf.drawString(20 * mm, y, title)
    y -= 8 * mm
    pdf.setFont("Times-Roman", 10)
    pdf.drawString(20 * mm, y, f"Athlete: {athlete_name}")
    y -= 5 * mm
    pdf.drawString(20 * mm, y, f"Generated: {utcnow().isoformat()}")
    y -= 5 * mm
    pdf.drawString(20 * mm, y, "Source: validated human annotations and touch events")
    y -= 5 * mm
    pdf.drawString(20 * mm, y, f"Model: {model_note}")
    y -= 5 * mm
    pdf.drawString(20 * mm, y, f"Formula version: {stats.get('formula_version', '1')}")
    y -= 8 * mm
    if stats.get("data_status") != "ok":
        pdf.drawString(20 * mm, y, "No validated records. This report does not contain performance rates.")
        pdf.save()
        return buffer.getvalue()
    block = stats.get("combined") or {}
    lines = [
        f"Data status: {stats.get('data_status')}",
        f"Weapons in the sample: {', '.join(stats.get('weapons_present') or []) or 'unspecified'}",
        f"Mixed weapons: {'yes — rates below are combined and should be read per weapon' if stats.get('mixed_weapons') else 'no'}",
        f"Touches scored: {block.get('touches_scored')}",
        f"Touches conceded: {block.get('touches_conceded')}",
        f"Offensive attempts: {block.get('offensive_attempts')}",
        f"Offensive success rate: {_rate_text(block.get('offensive_success_rate'))}",
        f"Defensive actions: {block.get('defensive_actions')}",
        f"Riposte success rate: {_rate_text(block.get('riposte_success_rate'))}",
        f"Counter-attack effectiveness: {_rate_text(block.get('counter_attack_effectiveness'))}",
        f"Undated bouts excluded from the timeline: {block.get('undated_bout_count')}",
    ]
    pdf.setFont("Times-Roman", 11)
    for line in lines:
        if y < 20 * mm:
            pdf.showPage()
            y = height - 20 * mm
            pdf.setFont("Times-Roman", 11)
        pdf.drawString(20 * mm, y, line[:110])
        y -= 6 * mm
    pdf.save()
    return buffer.getvalue()


def annotations_csv(rows: list[dict]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=["id", "video_id", "action_type_code", "status", "outcome", "start_ms", "end_ms", "target_area", "actor_athlete_id"],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in writer.fieldnames})
    return buffer.getvalue().encode("utf-8")


def safe_filename(value: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value)
    return cleaned.strip("-") or "report"


def xml_text(value: str) -> str:
    return escape(value)
