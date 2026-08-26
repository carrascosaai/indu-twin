from datetime import UTC, datetime
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import models
from app.deps import forbid_tenant, get_current_user, get_db
from app.services.reports import PERIOD_DELTAS, build_report_data, render_excel, render_pdf

router = APIRouter(
    prefix="/api/polygons",
    tags=["reports"],
    dependencies=[Depends(get_current_user), Depends(forbid_tenant)],
)

_MEDIA_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}


@router.get("/{polygon_id}/reports/{period}")
def download_report(
    polygon_id: int, period: str, format: str = "pdf", db: Session = Depends(get_db)
):
    if period not in PERIOD_DELTAS:
        raise HTTPException(400, "Periodo invalido: usa daily, weekly o monthly")
    if format not in _MEDIA_TYPES:
        raise HTTPException(400, "Formato invalido: usa pdf o xlsx")

    polygon = db.get(models.Polygon, polygon_id)
    if not polygon:
        raise HTTPException(404, "Poligono no encontrado")

    report = build_report_data(db, polygon, period)
    content = render_pdf(report) if format == "pdf" else render_excel(report)

    slug = polygon.name.lower().replace(" ", "_")
    date_tag = datetime.now(UTC).strftime("%Y%m%d")
    filename = f"informe_{slug}_{period}_{date_tag}.{format}"

    return StreamingResponse(
        BytesIO(content),
        media_type=_MEDIA_TYPES[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
