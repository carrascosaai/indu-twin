"""Generacion de informes periodicos (Excel y PDF) por poligono.

Reune en una sola estructura (`ReportData`) todo lo que hace falta para
ambos formatos, para no duplicar las consultas: consumo y eficiencia por
nave en el periodo, alertas por severidad, incidencias por estado, y una
seleccion de las alertas mas relevantes. Los renderers (`render_excel`,
`render_pdf`) solo dan formato a esos datos.
"""

import io
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.services.efficiency import efficiency_scores, kwh_per_m2
from app.services.maintenance import maintenance_risk_score, risk_label

PERIOD_LABELS = {"daily": "Diario", "weekly": "Semanal", "monthly": "Mensual"}
PERIOD_DELTAS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
    "monthly": timedelta(days=30),
}

BRAND_BLUE = "1D4ED8"
INK = "0F172A"
SLATE = "64748B"
CRITICAL = "DC2626"
WARNING = "D97706"
OK = "16A34A"


def _hex(value: str) -> colors.Color:
    """openpyxl usa hex sin '#'; reportlab lo exige. Los mismos literales
    (BRAND_BLUE, INK...) sirven para ambos formatos pasando por aqui."""
    return colors.HexColor(f"#{value}")


@dataclass
class BuildingReportRow:
    id: int
    code: str
    name: str
    building_type: str
    area_m2: float
    energy_kwh: float
    efficiency_score: int
    alerts_critical: int
    alerts_warning: int
    maintenance_risk: int
    maintenance_label: str


@dataclass
class AlertRow:
    building_name: str
    severity: str
    message: str
    created_at: datetime
    status: str


@dataclass
class ReportData:
    polygon_name: str
    polygon_address: str | None
    period_key: str
    period_label: str
    period_start: datetime
    period_end: datetime
    generated_at: datetime
    total_energy_kwh: float
    energy_trend_pct: float | None
    avg_temperature: float | None
    critical_alerts: int
    warning_alerts: int
    resolved_alerts: int
    incidents_open: int
    incidents_in_progress: int
    incidents_resolved: int
    buildings: list[BuildingReportRow] = field(default_factory=list)
    top_alerts: list[AlertRow] = field(default_factory=list)


def _sensor_ids(db: Session, building_ids: list[int], sensor_type: models.SensorType) -> list[int]:
    if not building_ids:
        return []
    return db.execute(
        select(models.Sensor.id).where(
            models.Sensor.building_id.in_(building_ids),
            models.Sensor.sensor_type == sensor_type,
        )
    ).scalars().all()


def _energy_sum(db: Session, sensor_ids: list[int], since: datetime, until: datetime) -> float:
    if not sensor_ids:
        return 0.0
    return db.execute(
        select(func.coalesce(func.sum(models.SensorReading.value), 0.0)).where(
            models.SensorReading.sensor_id.in_(sensor_ids),
            models.SensorReading.timestamp >= since,
            models.SensorReading.timestamp < until,
        )
    ).scalar_one()


def build_report_data(db: Session, polygon: models.Polygon, period: str) -> ReportData:
    if period not in PERIOD_DELTAS:
        raise ValueError(f"Periodo desconocido: {period}")

    now = datetime.now(UTC)
    delta = PERIOD_DELTAS[period]
    since, until = now - delta, now
    previous_since = since - delta

    buildings = db.execute(
        select(models.Building).where(models.Building.polygon_id == polygon.id)
    ).scalars().all()
    building_ids = [b.id for b in buildings]

    energy_ids_by_building = {
        b.id: _sensor_ids(db, [b.id], models.SensorType.energy) for b in buildings
    }
    energy_by_building = {
        b.id: _energy_sum(db, energy_ids_by_building[b.id], since, until) for b in buildings
    }
    total_energy = sum(energy_by_building.values())

    all_energy_ids = _sensor_ids(db, building_ids, models.SensorType.energy)
    previous_total_energy = _energy_sum(db, all_energy_ids, previous_since, since)
    # Solo fiable si hay historico que cubra el periodo anterior entero: si
    # el dato mas antiguo es mas reciente que `previous_since`, esa ventana
    # esta incompleta y el porcentaje saldria disparado sin significar nada.
    earliest_reading = (
        db.execute(
            select(func.min(models.SensorReading.timestamp)).where(
                models.SensorReading.sensor_id.in_(all_energy_ids)
            )
        ).scalar_one()
        if all_energy_ids
        else None
    )
    # SQLite no guarda tz, así que vuelve como naive: se asume UTC, que es
    # lo unico que escribe la app (ver utcnow() en models.py).
    if earliest_reading is not None and earliest_reading.tzinfo is None:
        earliest_reading = earliest_reading.replace(tzinfo=UTC)
    has_full_previous_period = earliest_reading is not None and earliest_reading <= previous_since
    energy_trend_pct = (
        round((total_energy - previous_total_energy) / previous_total_energy * 100, 1)
        if has_full_previous_period and previous_total_energy > 0
        else None
    )

    temp_ids = _sensor_ids(db, building_ids, models.SensorType.temperature)
    avg_temperature = None
    if temp_ids:
        avg_temperature = db.execute(
            select(func.avg(models.SensorReading.value)).where(
                models.SensorReading.sensor_id.in_(temp_ids),
                models.SensorReading.timestamp >= since,
                models.SensorReading.timestamp < until,
            )
        ).scalar_one()
        avg_temperature = round(avg_temperature, 1) if avg_temperature is not None else None

    efficiency_values = {b.id: kwh_per_m2(energy_by_building[b.id], b.area_m2) for b in buildings}
    scores = efficiency_scores(efficiency_values)

    period_alerts = (
        db.execute(
            select(models.Alert).where(
                models.Alert.building_id.in_(building_ids),
                models.Alert.created_at >= since,
                models.Alert.created_at < until,
            )
        ).scalars().all()
        if building_ids
        else []
    )
    alerts_by_building: dict[int, list[models.Alert]] = {b.id: [] for b in buildings}
    for a in period_alerts:
        alerts_by_building.setdefault(a.building_id, []).append(a)

    critical_alerts = sum(1 for a in period_alerts if a.severity == models.AlertSeverity.critical)
    warning_alerts = sum(1 for a in period_alerts if a.severity == models.AlertSeverity.warning)
    resolved_alerts = sum(1 for a in period_alerts if a.status == models.AlertStatus.resolved)

    period_incidents = (
        db.execute(
            select(models.Incident).where(
                models.Incident.building_id.in_(building_ids),
                models.Incident.created_at >= since,
                models.Incident.created_at < until,
            )
        ).scalars().all()
        if building_ids
        else []
    )
    incidents_open = sum(1 for i in period_incidents if i.status == models.IncidentStatus.open)
    incidents_in_progress = sum(
        1 for i in period_incidents if i.status == models.IncidentStatus.in_progress
    )
    incidents_resolved = sum(
        1 for i in period_incidents if i.status == models.IncidentStatus.resolved
    )

    building_rows: list[BuildingReportRow] = []
    for b in buildings:
        b_alerts = alerts_by_building.get(b.id, [])
        b_critical = sum(1 for a in b_alerts if a.severity == models.AlertSeverity.critical)
        b_warning = sum(1 for a in b_alerts if a.severity == models.AlertSeverity.warning)
        risk = maintenance_risk_score(len(b_alerts), None, b.status.value)
        building_rows.append(
            BuildingReportRow(
                id=b.id,
                code=b.code,
                name=b.name,
                building_type=b.building_type,
                area_m2=b.area_m2,
                energy_kwh=round(energy_by_building[b.id], 2),
                efficiency_score=scores[b.id],
                alerts_critical=b_critical,
                alerts_warning=b_warning,
                maintenance_risk=risk,
                maintenance_label=risk_label(risk),
            )
        )
    building_rows.sort(key=lambda r: r.energy_kwh, reverse=True)

    building_names = {b.id: b.name for b in buildings}
    top_alerts = [
        AlertRow(
            building_name=building_names.get(a.building_id, "?"),
            severity=a.severity.value,
            message=a.message,
            created_at=a.created_at,
            status=a.status.value,
        )
        for a in sorted(period_alerts, key=lambda a: a.created_at, reverse=True)[:20]
    ]

    return ReportData(
        polygon_name=polygon.name,
        polygon_address=polygon.address,
        period_key=period,
        period_label=PERIOD_LABELS[period],
        period_start=since,
        period_end=until,
        generated_at=now,
        total_energy_kwh=round(total_energy, 2),
        energy_trend_pct=energy_trend_pct,
        avg_temperature=avg_temperature,
        critical_alerts=critical_alerts,
        warning_alerts=warning_alerts,
        resolved_alerts=resolved_alerts,
        incidents_open=incidents_open,
        incidents_in_progress=incidents_in_progress,
        incidents_resolved=incidents_resolved,
        buildings=building_rows,
        top_alerts=top_alerts,
    )


def _fmt_dt(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y %H:%M")


def _fmt_date(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y")


# ---------------------------------------------------------------- Excel ----

def render_excel(report: ReportData) -> bytes:
    wb = Workbook()

    header_fill = PatternFill("solid", fgColor=BRAND_BLUE)
    header_font = Font(color="FFFFFF", bold=True, size=11)
    title_font = Font(bold=True, size=16, color=INK)
    subtitle_font = Font(size=10, color=SLATE)
    label_font = Font(bold=True, size=10, color=SLATE)
    value_font = Font(bold=True, size=14, color=INK)
    thin = Side(style="thin", color="E2E8F0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    def style_header_row(ws, row: int, ncols: int):
        for c in range(1, ncols + 1):
            cell = ws.cell(row=row, column=c)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = border

    def autosize(ws, widths: list[int]):
        for i, w in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(i)].width = w

    # --- Resumen ---
    ws = wb.active
    ws.title = "Resumen"
    ws.merge_cells("A1:D1")
    ws["A1"] = f"Informe {report.period_label.lower()} — {report.polygon_name}"
    ws["A1"].font = title_font
    ws.merge_cells("A2:D2")
    ws["A2"] = (
        f"{_fmt_date(report.period_start)} — {_fmt_date(report.period_end)}"
        f"  ·  generado el {_fmt_dt(report.generated_at)}"
    )
    ws["A2"].font = subtitle_font
    if report.polygon_address:
        ws.merge_cells("A3:D3")
        ws["A3"] = report.polygon_address
        ws["A3"].font = subtitle_font

    kpis = [
        ("Consumo total", f"{report.total_energy_kwh:,.1f} kWh".replace(",", ".")),
        (
            "Tendencia vs. periodo anterior",
            f"{report.energy_trend_pct:+.1f}%" if report.energy_trend_pct is not None else "—",
        ),
        (
            "Temperatura media",
            f"{report.avg_temperature:.1f} °C" if report.avg_temperature is not None else "—",
        ),
        ("Naves", str(len(report.buildings))),
        ("Alertas críticas", str(report.critical_alerts)),
        ("Alertas de aviso", str(report.warning_alerts)),
        ("Incidencias abiertas", str(report.incidents_open)),
        ("Incidencias resueltas", str(report.incidents_resolved)),
    ]
    row = 5
    for i, (label, value) in enumerate(kpis):
        r = row + (i // 2)
        c = 1 + (i % 2) * 2
        ws.cell(row=r, column=c, value=label).font = label_font
        ws.cell(row=r, column=c + 1, value=value).font = value_font
    autosize(ws, [24, 16, 24, 16])

    # --- Naves ---
    ws2 = wb.create_sheet("Naves")
    headers = [
        "Código",
        "Nave",
        "Tipo",
        "Superficie (m²)",
        "Consumo (kWh)",
        "Eficiencia (0-100)",
        "Alertas críticas",
        "Alertas aviso",
        "Riesgo mantenimiento",
    ]
    for c, h in enumerate(headers, start=1):
        ws2.cell(row=1, column=c, value=h)
    style_header_row(ws2, 1, len(headers))
    for r, b in enumerate(report.buildings, start=2):
        values = [
            b.code,
            b.name,
            b.building_type,
            b.area_m2,
            b.energy_kwh,
            b.efficiency_score,
            b.alerts_critical,
            b.alerts_warning,
            f"{b.maintenance_label} ({b.maintenance_risk})",
        ]
        for c, v in enumerate(values, start=1):
            cell = ws2.cell(row=r, column=c, value=v)
            cell.border = border
            if b.alerts_critical > 0 and c == 7:
                cell.font = Font(color=CRITICAL, bold=True)
    autosize(ws2, [8, 28, 14, 14, 14, 16, 14, 12, 20])

    # --- Alertas ---
    ws3 = wb.create_sheet("Alertas")
    headers3 = ["Fecha", "Nave", "Severidad", "Mensaje", "Estado"]
    for c, h in enumerate(headers3, start=1):
        ws3.cell(row=1, column=c, value=h)
    style_header_row(ws3, 1, len(headers3))
    for r, a in enumerate(report.top_alerts, start=2):
        values = [
            _fmt_dt(a.created_at),
            a.building_name,
            "Crítica" if a.severity == "critical" else "Aviso",
            a.message,
            "Resuelta" if a.status == "resolved" else "Activa",
        ]
        for c, v in enumerate(values, start=1):
            cell = ws3.cell(row=r, column=c, value=v)
            cell.border = border
            if c == 3:
                cell.font = Font(color=CRITICAL if a.severity == "critical" else WARNING, bold=True)
    autosize(ws3, [18, 28, 12, 60, 12])

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


# ------------------------------------------------------------------ PDF ----

def render_pdf(report: ReportData) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        title=f"Informe {report.period_label} — {report.polygon_name}",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleINDU", parent=styles["Title"], fontSize=20, textColor=_hex(INK),
        spaceAfter=2,
    )
    subtitle_style = ParagraphStyle(
        "SubtitleINDU", parent=styles["Normal"], fontSize=10, textColor=_hex(SLATE),
    )
    section_style = ParagraphStyle(
        "SectionINDU", parent=styles["Heading2"], fontSize=13, textColor=_hex(INK),
        spaceBefore=14, spaceAfter=6,
    )
    body_style = ParagraphStyle("BodyINDU", parent=styles["Normal"], fontSize=9, leading=13)

    elements = []

    elements.append(Paragraph("INDU-TWIN", ParagraphStyle(
        "Brand", parent=styles["Normal"], fontSize=9, textColor=_hex(BRAND_BLUE),
        fontName="Helvetica-Bold",
    )))
    elements.append(Paragraph(f"Informe {report.period_label.lower()}", title_style))
    elements.append(Paragraph(
        f"{report.polygon_name}"
        + (f" · {report.polygon_address}" if report.polygon_address else ""),
        subtitle_style,
    ))
    elements.append(Paragraph(
        f"Periodo: {_fmt_date(report.period_start)} – {_fmt_date(report.period_end)}"
        f"  ·  Generado el {_fmt_dt(report.generated_at)}",
        subtitle_style,
    ))
    elements.append(Spacer(1, 6))
    elements.append(HRFlowable(width="100%", thickness=1.2, color=_hex(BRAND_BLUE)))
    elements.append(Spacer(1, 12))

    # --- KPI cards (as a table so they lay out in a tidy grid) ---
    def kpi_cell(label: str, value: str, accent: str = INK) -> Table:
        t = Table(
            [[Paragraph(label, ParagraphStyle(
                "kpiLabel", fontSize=8, textColor=_hex(SLATE), fontName="Helvetica",
            ))], [Paragraph(value, ParagraphStyle(
                "kpiValue", fontSize=15, textColor=_hex(accent),
                fontName="Helvetica-Bold", spaceBefore=2,
            ))]],
            colWidths=[42 * mm],
        )
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), _hex("F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.6, _hex("E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ]))
        return t

    trend_txt = f"{report.energy_trend_pct:+.1f}%" if report.energy_trend_pct is not None else "—"
    trend_color = CRITICAL if (report.energy_trend_pct or 0) > 15 else INK
    temp_txt = f"{report.avg_temperature:.1f} °C" if report.avg_temperature is not None else "—"

    kpi_row1 = [
        kpi_cell("CONSUMO TOTAL", f"{report.total_energy_kwh:,.0f} kWh".replace(",", ".")),
        kpi_cell("VS. PERIODO ANTERIOR", trend_txt, trend_color),
        kpi_cell("TEMPERATURA MEDIA", temp_txt),
        kpi_cell("NAVES", str(len(report.buildings))),
    ]
    critical_color = CRITICAL if report.critical_alerts else INK
    warning_color = WARNING if report.warning_alerts else INK
    open_incidents = report.incidents_open + report.incidents_in_progress
    kpi_row2 = [
        kpi_cell("ALERTAS CRÍTICAS", str(report.critical_alerts), critical_color),
        kpi_cell("ALERTAS DE AVISO", str(report.warning_alerts), warning_color),
        kpi_cell("INCIDENCIAS ABIERTAS", str(open_incidents)),
        kpi_cell("INCIDENCIAS RESUELTAS", str(report.incidents_resolved), OK),
    ]
    kpi_table = Table([kpi_row1, kpi_row2], colWidths=[44 * mm] * 4, hAlign="LEFT")
    kpi_table.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(kpi_table)

    # --- Ranking de naves ---
    elements.append(Paragraph("Consumo y eficiencia por nave", section_style))
    if report.buildings:
        rows = [["Nave", "Tipo", "Consumo", "Eficiencia", "Alertas", "Riesgo mant."]]
        for b in report.buildings:
            alerts_txt = f"{b.alerts_critical} crít. / {b.alerts_warning} aviso"
            rows.append([
                Paragraph(f"{b.code} · {b.name}", body_style),
                b.building_type,
                f"{b.energy_kwh:,.1f} kWh".replace(",", "."),
                str(b.efficiency_score),
                alerts_txt,
                f"{b.maintenance_label} ({b.maintenance_risk})",
            ])
        col_widths = [52 * mm, 22 * mm, 24 * mm, 20 * mm, 26 * mm, 30 * mm]
        t = Table(rows, colWidths=col_widths, repeatRows=1)
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), _hex(BRAND_BLUE)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _hex("F8FAFC")]),
            ("GRID", (0, 0), (-1, -1), 0.4, _hex("E2E8F0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
        for i, b in enumerate(report.buildings, start=1):
            if b.alerts_critical > 0:
                style.append(("TEXTCOLOR", (4, i), (4, i), _hex(CRITICAL)))
        t.setStyle(TableStyle(style))
        elements.append(t)
    else:
        elements.append(Paragraph("Este polígono todavía no tiene naves.", body_style))

    # --- Alertas destacadas ---
    elements.append(Paragraph("Alertas del periodo", section_style))
    if report.top_alerts:
        severity_style = {
            "critical": ParagraphStyle(
                "sevCrit", parent=body_style, textColor=_hex(CRITICAL), fontName="Helvetica-Bold",
            ),
            "warning": ParagraphStyle(
                "sevWarn", parent=body_style, textColor=_hex(WARNING), fontName="Helvetica-Bold",
            ),
        }
        rows = [["Fecha", "Nave", "Severidad", "Mensaje"]]
        for a in report.top_alerts:
            rows.append([
                a.created_at.strftime("%d/%m %H:%M"),
                Paragraph(a.building_name, body_style),
                Paragraph(
                    "Crítica" if a.severity == "critical" else "Aviso",
                    severity_style[a.severity],
                ),
                Paragraph(a.message, body_style),
            ])
        t = Table(rows, colWidths=[20 * mm, 38 * mm, 18 * mm, 98 * mm], repeatRows=1)
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), _hex(INK)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.4, _hex("E2E8F0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        t.setStyle(TableStyle(style))
        elements.append(t)
    else:
        elements.append(Paragraph("Sin alertas en este periodo.", body_style))

    def _footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(_hex(SLATE))
        canvas.drawString(16 * mm, 10 * mm, "INDU-TWIN · Digital Twin SaaS")
        canvas.drawRightString(
            A4[0] - 16 * mm, 10 * mm, f"Página {canvas.getPageNumber()}"
        )
        canvas.restoreState()

    doc.build(elements, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
