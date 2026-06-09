from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.schemas.base import ORMModel


class CompanySettingsRead(ORMModel):
    id: int
    nome_empresa: str
    logo_empresa: str | None
    email_supervisor: str
    cor_primaria: str
    smtp_host: str | None
    smtp_porta: int
    smtp_email_remetente: str | None
    smtp_tls: bool
    tempo_minimo_leituras_segundos: int


class PublicCompanySettings(BaseModel):
    nome_empresa: str
    logo_empresa: str | None
    cor_primaria: str


class CompanySettingsUpdate(BaseModel):
    nome_empresa: str = Field(min_length=2, max_length=160)
    email_supervisor: str = Field(min_length=3, max_length=255)
    cor_primaria: str = Field(default="#1f6feb", min_length=4, max_length=20)
    smtp_host: str | None = Field(default=None, max_length=255)
    smtp_porta: int = Field(default=587, ge=1, le=65535)
    smtp_email_remetente: str | None = Field(default=None, max_length=255)
    smtp_senha: str | None = Field(default=None, max_length=255)
    smtp_tls: bool = True
    tempo_minimo_leituras_segundos: int = Field(default=30, ge=0, le=3600)


class QrPointCreate(BaseModel):
    nome_ponto: str = Field(min_length=2, max_length=140)
    codigo_qr: str | None = Field(default=None, min_length=3, max_length=120)
    descricao: str | None = Field(default=None, max_length=1000)
    ordem: int = Field(default=0, ge=0)
    meta_passagens_turno: int = Field(default=4, ge=1, le=50)
    carencia_minutos: int = Field(default=45, ge=0, le=1440)


class QrPointUpdate(BaseModel):
    nome_ponto: str = Field(min_length=2, max_length=140)
    codigo_qr: str = Field(min_length=3, max_length=120)
    descricao: str | None = Field(default=None, max_length=1000)
    ordem: int = Field(default=0, ge=0)
    meta_passagens_turno: int = Field(default=4, ge=1, le=50)
    carencia_minutos: int = Field(default=45, ge=0, le=1440)
    ativo: bool = True


class QrPointRead(ORMModel):
    id: int
    nome_ponto: str
    codigo_qr: str
    descricao: str | None
    ordem: int
    meta_passagens_turno: int
    carencia_minutos: int
    ativo: bool
    criado_em: datetime


class StartShiftResponse(ORMModel):
    id: int
    funcionario_id: int
    data_inicio: datetime
    data_fim: datetime | None
    status: str


class ReadingRead(ORMModel):
    id: int
    turno_id: int
    ponto_qr_id: int
    funcionario_id: int
    data_hora: datetime
    observacao: str | None
    ocorrencia: str | None
    foto: str
    status: str
    ponto: QrPointRead


class PointProgressRead(QrPointRead):
    passagens_realizadas: int
    passagens_pendentes: int
    disponivel: bool
    status_ronda: str
    ultima_leitura: datetime | None
    bloqueado_ate: datetime | None


class ShiftStatusRead(ORMModel):
    turno: StartShiftResponse | None
    funcionario_nome: str | None
    pontos: list[PointProgressRead]
    leituras: list[ReadingRead]
    total_pontos: int
    pontos_realizados: int
    pontos_pendentes: int
    progresso_percentual: int


class FinishShiftRequest(BaseModel):
    observacao_final: str | None = Field(default=None, max_length=1000)


class FinishShiftResponse(ORMModel):
    turno_id: int
    status: str
    pontos_realizados: int
    pontos_pendentes: int
    relatorio_html: str | None
    email_enviado: bool
    email_status: str | None
