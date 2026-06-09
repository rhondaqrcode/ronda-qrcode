from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models import Checklist, ChecklistStatus, Employee, GeneratedReport, ReportType


def generate_productivity_pdf(db: Session, title: str) -> GeneratedReport:
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}.pdf"
    path = settings.reports_dir / filename

    rows = db.execute(
        select(Employee.name, func.count(Checklist.id))
        .join(Checklist, Checklist.employee_id == Employee.id, isouter=True)
        .where((Checklist.status == ChecklistStatus.completed) | (Checklist.id.is_(None)))
        .group_by(Employee.id)
        .order_by(func.count(Checklist.id).desc())
    ).all()

    _write_productivity_pdf(path, title, rows)

    report = GeneratedReport(
        title=title,
        report_type=ReportType.productivity,
        file_path=str(path),
        file_url=f"/reports-files/{filename}",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def _write_productivity_pdf(path: Path, title: str, rows: list[tuple[str, int]]) -> None:
    lines = [
        title,
        f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        "Funcionario - Servicos concluidos",
        *[f"{name} - {total}" for name, total in rows],
    ]
    _write_simple_pdf(path, lines)


def _write_simple_pdf(path: Path, lines: list[str]) -> None:
    # Gerador minimo de PDF texto para o MVP; pode ser trocado por ReportLab depois.
    text_commands = ["BT", "/F1 12 Tf", "50 790 Td"]
    for index, line in enumerate(lines[:38]):
        if index:
            text_commands.append("0 -18 Td")
        text_commands.append(f"({_pdf_escape(line)}) Tj")
    text_commands.append("ET")
    stream = "\n".join(text_commands).encode("latin-1", errors="replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]

    content = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(content))
        content.extend(f"{number} 0 obj\n".encode())
        content.extend(obj)
        content.extend(b"\nendobj\n")

    xref_at = len(content)
    content.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    content.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        content.extend(f"{offset:010d} 00000 n \n".encode())
    content.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    )
    path.write_bytes(content)


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
