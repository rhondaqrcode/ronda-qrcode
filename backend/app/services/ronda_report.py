from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import html
import logging
import os
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import settings
from backend.app.models import CompanySettings, QrPoint, QrReading, Shift

logger = logging.getLogger(__name__)
RESEND_API_URL = "https://api.resend.com/emails"
DEFAULT_RESEND_FROM_EMAIL = "Ronda QR <onboarding@resend.dev>"


def generate_shift_report_html(db: Session, turno: Shift, config: CompanySettings) -> str:
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    turno = _load_turno(db, turno.id)
    pontos = list(
        db.scalars(select(QrPoint).where(QrPoint.ativo.is_(True)).order_by(QrPoint.ordem, QrPoint.nome_ponto))
    )
    leituras_por_ponto: dict[int, list[QrReading]] = {}
    for leitura in turno.leituras:
        leituras_por_ponto.setdefault(leitura.ponto_qr_id, []).append(leitura)
    realizados = len(turno.leituras)
    meta_total = sum(ponto.meta_passagens_turno for ponto in pontos)
    pendentes = max(meta_total - realizados, 0)
    fim = turno.data_fim or datetime.now(timezone.utc)
    duracao = fim - turno.data_inicio

    status_final = "Ronda concluida com sucesso" if pendentes == 0 else "Ronda concluida com pendencias"
    if turno.status.value != "finished":
        status_final = "Turno encerrado parcialmente"

    rows = []
    for ponto in pontos:
        leituras = leituras_por_ponto.get(ponto.id, [])
        ultima_leitura = max(leituras, key=lambda item: item.data_hora, default=None)
        fotos = ", ".join(
            f'<a href="{html.escape(leitura.foto)}">Foto {index}</a>'
            for index, leitura in enumerate(leituras, start=1)
        )
        gps_info = _gps_info_html(ultima_leitura)
        rows.append(
            f"""
            <tr>
              <td>{html.escape(ponto.nome_ponto)}</td>
              <td><strong>{len(leituras)}/{ponto.meta_passagens_turno}</strong></td>
              <td>{'Meta atingida' if len(leituras) >= ponto.meta_passagens_turno else 'Pendente'}</td>
              <td>{_fmt(ultima_leitura.data_hora) if ultima_leitura else '-'}</td>
              <td>{html.escape(ultima_leitura.observacao or '-') if ultima_leitura else '-'}</td>
              <td>{html.escape(ultima_leitura.ocorrencia or '-') if ultima_leitura else '-'}</td>
              <td>{gps_info}</td>
              <td>{fotos or '-'}</td>
            </tr>
            """
        )

    logo = (
        f'<img src="{html.escape(config.logo_empresa)}" alt="Logo" class="logo" />'
        if config.logo_empresa
        else '<div class="logo-fallback">Logo</div>'
    )
    content = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <title>Relatorio de Turno</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #172033; margin: 0; background: #f4f6f8; }}
    .wrap {{ max-width: 980px; margin: 0 auto; background: #fff; padding: 28px; }}
    .header {{ display: flex; align-items: center; gap: 16px; border-bottom: 3px solid {config.cor_primaria}; padding-bottom: 16px; }}
    .logo {{ max-width: 120px; max-height: 72px; object-fit: contain; }}
    .logo-fallback {{ width: 96px; height: 56px; display: grid; place-items: center; background: #eef2f6; color: #6b7280; }}
    h1 {{ margin: 0; font-size: 22px; }}
    .summary {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 22px 0; }}
    .box {{ background: #f8fafc; border: 1px solid #e5e7eb; padding: 14px; border-radius: 8px; }}
    .box span {{ display: block; color: #667085; font-size: 12px; }}
    .box strong {{ font-size: 24px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
    th, td {{ border: 1px solid #e5e7eb; padding: 10px; text-align: left; font-size: 13px; vertical-align: top; }}
    th {{ background: #f1f5f9; }}
    .status {{ color: {config.cor_primaria}; font-weight: 700; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="header">
      {logo}
      <div>
        <h1>{html.escape(config.nome_empresa)}</h1>
        <div>Relatorio de Turno - {html.escape(turno.funcionario.name)}</div>
      </div>
    </div>
    <p class="status">{status_final}</p>
    <p>
      <strong>Funcionario:</strong> {html.escape(turno.funcionario.name)}<br />
      <strong>Inicio:</strong> {_fmt(turno.data_inicio)}<br />
      <strong>Fim:</strong> {_fmt(fim)}<br />
      <strong>Duracao:</strong> {str(duracao).split('.')[0]}<br />
      <strong>Observacao final:</strong> {html.escape(turno.observacao_final or '-')}
    </p>
    <div class="summary">
      <div class="box"><span>Meta de passagens</span><strong>{meta_total}</strong></div>
      <div class="box"><span>Realizados</span><strong>{realizados}</strong></div>
      <div class="box"><span>Pendentes</span><strong>{pendentes}</strong></div>
    </div>
    <table>
      <thead>
        <tr>
          <th>Ponto</th>
          <th>Passagens</th>
          <th>Status</th>
          <th>Ultimo horario</th>
          <th>Observacao</th>
          <th>Ocorrencia</th>
          <th>Localizacao</th>
          <th>Foto</th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </div>
</body>
</html>"""

    filename = f"turno-{turno.id}-{uuid4().hex[:8]}.html"
    path = settings.reports_dir / filename
    path.write_text(content, encoding="utf-8")
    return f"/reports-files/{filename}"


def send_shift_report_email(
    db: Session,
    turno: Shift,
    config: CompanySettings,
    report_url: str,
) -> tuple[bool, str]:
    resend_api_key = os.environ.get("RESEND_API_KEY")
    resend_from_email = os.environ.get("RESEND_FROM_EMAIL", DEFAULT_RESEND_FROM_EMAIL)
    recipient = config.email_supervisor
    if not resend_api_key:
        logger.info(
            "Resend skipped for shift report: RESEND_API_KEY is not configured. "
            "turno_id=%s recipient=%s sender=%s",
            turno.id,
            recipient,
            resend_from_email,
        )
        return False, "Resend nao configurado; relatorio gerado e envio aguardando configuracao."

    turno = _load_turno(db, turno.id)
    subject = f"Relatorio de Ronda - Turno #{turno.id}"
    report_path = _url_to_path(report_url)
    html_body = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    if html_body:
        html_body = html_body.replace(
            "</body>",
            (
                "<p><strong>Link/arquivo do relatorio:</strong> "
                f"{html.escape(report_url)}</p></body>"
            ),
        )
    else:
        html_body = (
            "<html><body>"
            "<h1>Relatorio de Ronda</h1>"
            f"<p>Relatorio de turno gerado. Link/arquivo: {html.escape(report_url)}</p>"
            "</body></html>"
        )
    logger.info(
        "Preparing Resend shift report email. turno_id=%s funcionario_id=%s leituras=%s "
        "sender=%s recipient=%s report_url=%s report_path=%s report_exists=%s html_body_bytes=%s",
        turno.id,
        turno.funcionario_id,
        len(turno.leituras),
        resend_from_email,
        recipient,
        report_url,
        report_path,
        report_path.exists(),
        len(html_body.encode("utf-8")),
    )

    payload = {
        "from": resend_from_email,
        "to": [recipient],
        "subject": subject,
        "html": html_body,
    }
    headers = {
        "Authorization": f"Bearer {resend_api_key}",
        "Content-Type": "application/json",
    }

    try:
        logger.info(
            "Posting shift report email to Resend API. turno_id=%s url=%s sender=%s recipient=%s",
            turno.id,
            RESEND_API_URL,
            resend_from_email,
            recipient,
        )
        response = httpx.post(RESEND_API_URL, headers=headers, json=payload, timeout=20)
        logger.info(
            "Resend API response for shift report. turno_id=%s status_code=%s response_body=%s",
            turno.id,
            response.status_code,
            response.text[:1000],
        )
    except httpx.HTTPError as exc:
        logger.exception(
            "Resend HTTP failure while sending shift report. turno_id=%s sender=%s recipient=%s report_url=%s",
            turno.id,
            resend_from_email,
            recipient,
            report_url,
        )
        return False, f"Falha no envio via Resend: {exc}"
    except Exception:
        logger.exception(
            "Unexpected Resend failure while sending shift report. turno_id=%s sender=%s recipient=%s report_url=%s",
            turno.id,
            resend_from_email,
            recipient,
            report_url,
        )
        raise

    if response.status_code >= 400:
        return False, f"Falha no envio via Resend: HTTP {response.status_code} - {response.text[:500]}"

    logger.info(
        "Resend shift report email sent successfully. turno_id=%s recipient=%s report_url=%s",
        turno.id,
        recipient,
        report_url,
    )
    return True, "Relatorio enviado automaticamente ao supervisor."


def _load_turno(db: Session, turno_id: int) -> Shift:
    return db.scalar(
        select(Shift)
        .where(Shift.id == turno_id)
        .options(
            selectinload(Shift.funcionario),
            selectinload(Shift.leituras).selectinload(QrReading.ponto),
        )
    )


def _url_to_path(url: str) -> Path:
    relative = url.removeprefix("/uploads/").removeprefix("/reports-files/")
    if url.startswith("/uploads/"):
        return settings.uploads_dir / relative
    return settings.reports_dir / relative


def _fmt(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.strftime("%d/%m/%Y %H:%M")


def _gps_info_html(leitura: QrReading | None) -> str:
    if leitura is None:
        return "-"
    status_label = leitura.gps_status or "GPS VALIDADO"
    initialized = "Sim" if leitura.gps_inicializou_posto else "Nao"
    return (
        f"<strong>{html.escape(status_label)}</strong><br />"
        f"Latitude: {_fmt_coord(leitura.gps_latitude)}<br />"
        f"Longitude: {_fmt_coord(leitura.gps_longitude)}<br />"
        f"Precisao GPS: {_fmt_meters(leitura.gps_precisao_metros)}<br />"
        f"Distancia do posto: {_fmt_meters(leitura.gps_distancia_metros)}<br />"
        f"Posto inicializado automaticamente: {initialized}"
    )


def _fmt_coord(value: float | None) -> str:
    return "-" if value is None else f"{value:.6f}"


def _fmt_meters(value: float | None) -> str:
    if value is None:
        return "-"
    formatted = f"{value:.1f}".replace(".", ",")
    if formatted.endswith(",0"):
        formatted = formatted[:-2]
    return f"{formatted} metros"
