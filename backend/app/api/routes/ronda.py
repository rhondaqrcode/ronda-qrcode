from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import BytesIO
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.app.api.deps import get_current_user, require_admin, require_supervisor
from backend.app.db.session import get_db
from backend.app.models import (
    CompanySettings,
    Employee,
    QrPoint,
    QrReading,
    ReadingStatus,
    Shift,
    ShiftStatus,
    User,
)
from backend.app.schemas.ronda import (
    CompanySettingsRead,
    CompanySettingsUpdate,
    FinishShiftRequest,
    FinishShiftResponse,
    PublicCompanySettings,
    QrPointCreate,
    QrPointRead,
    QrPointUpdate,
    ReadingRead,
    ShiftStatusRead,
    StartShiftResponse,
)
from backend.app.services.ronda_report import generate_shift_report_html, send_shift_report_email
from backend.app.services.storage import cleanup_old_storage_files, save_compressed_upload_file

router = APIRouter()


@router.get("/public-config", response_model=PublicCompanySettings)
def public_config(db: Session = Depends(get_db)) -> PublicCompanySettings:
    config = _get_config(db)
    return PublicCompanySettings(
        nome_empresa=config.nome_empresa,
        logo_empresa=config.logo_empresa,
        cor_primaria=config.cor_primaria,
    )


@router.get("/config", response_model=CompanySettingsRead)
def read_config(
    db: Session = Depends(get_db),
    _: User = Depends(require_supervisor),
) -> CompanySettings:
    return _get_config(db)


@router.put("/config", response_model=CompanySettingsRead)
def update_config(
    payload: CompanySettingsUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> CompanySettings:
    config = _get_config(db)
    for key, value in payload.model_dump().items():
        if key == "smtp_senha" and not value:
            continue
        setattr(config, key, value)
    db.commit()
    db.refresh(config)
    return config


@router.post("/config/logo", response_model=CompanySettingsRead)
def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> CompanySettings:
    _ensure_image(file)
    filename = _save_upload(file, "logos")
    config = _get_config(db)
    config.logo_empresa = f"/uploads/{filename}"
    db.commit()
    db.refresh(config)
    return config


@router.post("/pontos", response_model=QrPointRead, status_code=status.HTTP_201_CREATED)
def create_qr_point(
    payload: QrPointCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_supervisor),
) -> QrPoint:
    codigo = _normalize_code(payload.codigo_qr or f"PONTO_{uuid4().hex[:10]}")
    existing = db.scalar(select(QrPoint).where(func.lower(QrPoint.codigo_qr) == codigo.lower()))
    if existing:
        raise HTTPException(status_code=409, detail="Ja existe ponto com este codigo QR.")
    ponto = QrPoint(
        nome_ponto=payload.nome_ponto,
        codigo_qr=codigo,
        descricao=payload.descricao,
        ordem=payload.ordem,
        meta_passagens_turno=payload.meta_passagens_turno,
        carencia_minutos=payload.carencia_minutos,
        ativo=True,
    )
    db.add(ponto)
    db.commit()
    db.refresh(ponto)
    return ponto


@router.get("/pontos", response_model=list[QrPointRead])
def list_qr_points(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[QrPoint]:
    statement = select(QrPoint).order_by(QrPoint.ordem, QrPoint.nome_ponto)
    if not include_inactive:
        statement = statement.where(QrPoint.ativo.is_(True))
    return list(db.scalars(statement).all())


@router.put("/pontos/{point_id}", response_model=QrPointRead)
def update_qr_point(
    point_id: int,
    payload: QrPointUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_supervisor),
) -> QrPoint:
    ponto = _get_point(db, point_id)
    codigo = _normalize_code(payload.codigo_qr)
    existing = db.scalar(
        select(QrPoint).where(func.lower(QrPoint.codigo_qr) == codigo.lower(), QrPoint.id != point_id)
    )
    if existing:
        raise HTTPException(status_code=409, detail="Ja existe ponto com este codigo QR.")
    ponto.nome_ponto = payload.nome_ponto
    ponto.codigo_qr = codigo
    ponto.descricao = payload.descricao
    ponto.ordem = payload.ordem
    ponto.meta_passagens_turno = payload.meta_passagens_turno
    ponto.carencia_minutos = payload.carencia_minutos
    ponto.ativo = payload.ativo
    db.commit()
    db.refresh(ponto)
    return ponto


@router.patch("/pontos/{point_id}/status", response_model=QrPointRead)
def set_qr_point_status(
    point_id: int,
    ativo: bool,
    db: Session = Depends(get_db),
    _: User = Depends(require_supervisor),
) -> QrPoint:
    ponto = _get_point(db, point_id)
    ponto.ativo = ativo
    db.commit()
    db.refresh(ponto)
    return ponto


@router.delete("/pontos/{point_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_qr_point(
    point_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_supervisor),
) -> None:
    ponto = _get_point(db, point_id)
    has_readings = db.scalar(
        select(func.count()).select_from(QrReading).where(QrReading.ponto_qr_id == point_id)
    )
    if has_readings:
        ponto.ativo = False
    else:
        db.delete(ponto)
    db.commit()


@router.get("/pontos/{point_id}/qr.svg")
def qr_code_svg(
    point_id: int,
    db: Session = Depends(get_db),
) -> Response:
    ponto = _get_point(db, point_id)
    try:
        import qrcode
        import qrcode.image.svg
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail="Dependencia qrcode nao instalada. Execute pip install -r requirements.txt.",
        ) from exc

    image = qrcode.make(
        ponto.codigo_qr,
        image_factory=qrcode.image.svg.SvgPathImage,
        border=4,
    )
    buffer = BytesIO()
    image.save(buffer)
    return Response(content=buffer.getvalue(), media_type="image/svg+xml")


@router.post("/turnos/iniciar", response_model=StartShiftResponse, status_code=status.HTTP_201_CREATED)
def start_shift(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Shift:
    employee = _current_employee(user, db)
    active = _active_shift(db, employee.id)
    if active:
        return active
    turno = Shift(funcionario_id=employee.id, status=ShiftStatus.active)
    db.add(turno)
    db.commit()
    db.refresh(turno)
    return turno


@router.get("/turnos/ativo", response_model=ShiftStatusRead)
def current_shift_status(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ShiftStatusRead:
    employee = _current_employee(user, db)
    return _build_shift_status(db, employee, _active_shift(db, employee.id))


@router.post("/leituras", response_model=ReadingRead, status_code=status.HTTP_201_CREATED)
def create_reading(
    codigo_qr: str = Form(...),
    observacao: str | None = Form(default=None),
    ocorrencia: str | None = Form(default=None),
    foto: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> QrReading:
    cleanup_old_storage_files()
    _ensure_image(foto)
    employee = _current_employee(user, db)
    turno = _active_shift(db, employee.id)
    if not turno:
        raise HTTPException(status_code=422, detail="Inicie um turno antes de registrar leituras.")

    ponto = db.scalar(
        select(QrPoint).where(
            func.lower(QrPoint.codigo_qr) == _normalize_code(codigo_qr).lower(),
            QrPoint.ativo.is_(True),
        )
    )
    if not ponto:
        raise HTTPException(status_code=404, detail="QR Code nao encontrado ou ponto inativo.")

    readings_count = db.scalar(
        select(func.count()).select_from(QrReading).where(
            QrReading.turno_id == turno.id,
            QrReading.ponto_qr_id == ponto.id,
        )
    ) or 0
    if readings_count >= ponto.meta_passagens_turno:
        raise HTTPException(status_code=409, detail="Meta de passagens deste ponto ja foi atingida.")

    last_point_reading = db.scalar(
        select(QrReading)
        .where(QrReading.turno_id == turno.id, QrReading.ponto_qr_id == ponto.id)
        .order_by(QrReading.data_hora.desc())
        .limit(1)
    )
    if last_point_reading and ponto.carencia_minutos:
        blocked_until = _as_aware(last_point_reading.data_hora) + timedelta(minutes=ponto.carencia_minutos)
        now = datetime.now(timezone.utc)
        if now < blocked_until:
            remaining_seconds = int((blocked_until - now).total_seconds())
            remaining_minutes = max((remaining_seconds + 59) // 60, 1)
            release_time = blocked_until.astimezone().strftime("%H:%M")
            raise HTTPException(
                status_code=429,
                detail=(
                    "Ponto verificado recentemente dentro do tempo de carencia. "
                    f"Proxima leitura liberada as {release_time}. Aguarde cerca de {remaining_minutes} min."
                ),
            )

    filename = _save_upload(foto, "ronda")
    leitura = QrReading(
        turno_id=turno.id,
        ponto_qr_id=ponto.id,
        funcionario_id=employee.id,
        observacao=observacao,
        ocorrencia=ocorrencia,
        foto=f"/uploads/{filename}",
        status=ReadingStatus.completed,
    )
    db.add(leitura)
    db.commit()
    return _get_reading(db, leitura.id)


@router.post("/turnos/finalizar", response_model=FinishShiftResponse)
def finish_shift(
    payload: FinishShiftRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FinishShiftResponse:
    employee = _current_employee(user, db)
    turno = _active_shift(db, employee.id)
    if not turno:
        raise HTTPException(status_code=404, detail="Nao existe turno ativo para finalizar.")

    turno.data_fim = datetime.now(timezone.utc)
    turno.status = ShiftStatus.finished
    turno.observacao_final = payload.observacao_final
    db.commit()
    db.refresh(turno)

    config = _get_config(db)
    report_url = generate_shift_report_html(db, turno, config)
    email_sent, email_status = send_shift_report_email(db, turno, config, report_url)
    turno.relatorio_html = report_url
    turno.email_enviado = email_sent
    turno.email_status = email_status
    db.commit()

    pontos_ativos = list(db.scalars(select(QrPoint).where(QrPoint.ativo.is_(True))).all())
    realizados = (
        db.scalar(select(func.count()).select_from(QrReading).where(QrReading.turno_id == turno.id)) or 0
    )
    meta_total = sum(ponto.meta_passagens_turno for ponto in pontos_ativos)
    return FinishShiftResponse(
        turno_id=turno.id,
        status=turno.status.value,
        pontos_realizados=realizados,
        pontos_pendentes=max(meta_total - realizados, 0),
        relatorio_html=report_url,
        email_enviado=email_sent,
        email_status=email_status,
    )


@router.post("/logout", response_model=FinishShiftResponse | None)
def logout_and_close_shift(
    payload: FinishShiftRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FinishShiftResponse | None:
    employee = _current_employee(user, db)
    if not _active_shift(db, employee.id):
        return None
    return finish_shift(payload, db, user)


def _get_config(db: Session) -> CompanySettings:
    config = db.scalar(select(CompanySettings).limit(1))
    if config:
        return config
    config = CompanySettings()
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def _get_point(db: Session, point_id: int) -> QrPoint:
    ponto = db.get(QrPoint, point_id)
    if not ponto:
        raise HTTPException(status_code=404, detail="Ponto QR nao encontrado.")
    return ponto


def _get_reading(db: Session, reading_id: int) -> QrReading:
    leitura = db.scalar(
        select(QrReading).where(QrReading.id == reading_id).options(selectinload(QrReading.ponto))
    )
    if not leitura:
        raise HTTPException(status_code=404, detail="Leitura nao encontrada.")
    return leitura


def _current_employee(user: User, db: Session) -> Employee:
    if user.employee_id is None:
        raise HTTPException(status_code=422, detail="Usuario nao possui funcionario vinculado.")
    employee = db.get(Employee, user.employee_id)
    if not employee or not employee.is_active:
        raise HTTPException(status_code=403, detail="Funcionario inativo ou nao encontrado.")
    return employee


def _active_shift(db: Session, employee_id: int) -> Shift | None:
    return db.scalar(
        select(Shift)
        .where(Shift.funcionario_id == employee_id, Shift.status == ShiftStatus.active)
        .options(selectinload(Shift.leituras).selectinload(QrReading.ponto))
        .order_by(Shift.data_inicio.desc())
        .limit(1)
    )


def _build_shift_status(db: Session, employee: Employee, turno: Shift | None) -> ShiftStatusRead:
    pontos = list(
        db.scalars(select(QrPoint).where(QrPoint.ativo.is_(True)).order_by(QrPoint.ordem, QrPoint.nome_ponto))
    )
    leituras = list(turno.leituras) if turno else []
    pontos_com_status = [_build_point_progress(ponto, leituras, bool(turno)) for ponto in pontos]
    realizados = len(leituras)
    total = sum(ponto.meta_passagens_turno for ponto in pontos)
    return ShiftStatusRead(
        turno=turno,
        funcionario_nome=employee.name,
        pontos=pontos_com_status,
        leituras=leituras,
        total_pontos=total,
        pontos_realizados=realizados,
        pontos_pendentes=max(total - realizados, 0),
        progresso_percentual=round((realizados / total) * 100) if total else 0,
    )


def _build_point_progress(ponto: QrPoint, leituras: list[QrReading], has_active_shift: bool) -> dict:
    point_readings = [leitura for leitura in leituras if leitura.ponto_qr_id == ponto.id]
    last_reading = max(point_readings, key=lambda item: item.data_hora, default=None)
    completed = len(point_readings)
    pending = max(ponto.meta_passagens_turno - completed, 0)
    now = datetime.now(timezone.utc)
    blocked_until = None

    if not has_active_shift:
        status_ronda = "aguardando_turno"
        available = False
    elif completed >= ponto.meta_passagens_turno:
        status_ronda = "meta_atingida"
        available = False
    elif last_reading and ponto.carencia_minutos:
        blocked_until = _as_aware(last_reading.data_hora) + timedelta(minutes=ponto.carencia_minutos)
        available = now >= blocked_until
        status_ronda = "disponivel" if available else "bloqueado_carencia"
    else:
        status_ronda = "disponivel"
        available = True

    return {
        "id": ponto.id,
        "nome_ponto": ponto.nome_ponto,
        "codigo_qr": ponto.codigo_qr,
        "descricao": ponto.descricao,
        "ordem": ponto.ordem,
        "meta_passagens_turno": ponto.meta_passagens_turno,
        "carencia_minutos": ponto.carencia_minutos,
        "ativo": ponto.ativo,
        "criado_em": ponto.criado_em,
        "passagens_realizadas": completed,
        "passagens_pendentes": pending,
        "disponivel": available,
        "status_ronda": status_ronda,
        "ultima_leitura": last_reading.data_hora if last_reading else None,
        "bloqueado_ate": blocked_until,
    }


def _ensure_image(file: UploadFile) -> None:
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=422, detail="Envie um arquivo de imagem valido.")


def _save_upload(file: UploadFile, folder: str) -> str:
    return save_compressed_upload_file(file, folder)


def _normalize_code(value: str) -> str:
    return value.strip().upper().replace(" ", "_")


def _as_aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
