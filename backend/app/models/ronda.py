import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.session import Base


class ShiftStatus(str, enum.Enum):
    active = "active"
    finished = "finished"


class ReadingStatus(str, enum.Enum):
    completed = "completed"


class CompanySettings(Base):
    __tablename__ = "configuracoes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nome_empresa: Mapped[str] = mapped_column(String(160), default="Empresa Exemplo", nullable=False)
    logo_empresa: Mapped[str | None] = mapped_column(String(500), nullable=True)
    email_supervisor: Mapped[str] = mapped_column(
        String(255), default="supervisor@empresa.local", nullable=False
    )
    cor_primaria: Mapped[str] = mapped_column(String(20), default="#1f6feb", nullable=False)
    smtp_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_porta: Mapped[int] = mapped_column(Integer, default=587, nullable=False)
    smtp_email_remetente: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_senha: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_tls: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tempo_minimo_leituras_segundos: Mapped[int] = mapped_column(Integer, default=30, nullable=False)


class QrPoint(Base):
    __tablename__ = "pontos_qr"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nome_ponto: Mapped[str] = mapped_column(String(140), nullable=False)
    codigo_qr: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    ordem: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    meta_passagens_turno: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    carencia_minutos: Mapped[int] = mapped_column(Integer, default=45, nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    leituras = relationship("QrReading", back_populates="ponto")


class Shift(Base):
    __tablename__ = "turnos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    funcionario_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    data_inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    data_fim: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[ShiftStatus] = mapped_column(
        Enum(ShiftStatus), default=ShiftStatus.active, nullable=False
    )
    observacao_final: Mapped[str | None] = mapped_column(Text, nullable=True)
    relatorio_html: Mapped[str | None] = mapped_column(String(500), nullable=True)
    email_enviado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_status: Mapped[str | None] = mapped_column(String(500), nullable=True)

    funcionario = relationship("Employee")
    leituras = relationship("QrReading", back_populates="turno")


class QrReading(Base):
    __tablename__ = "leituras_qr"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    turno_id: Mapped[int] = mapped_column(ForeignKey("turnos.id"), nullable=False)
    ponto_qr_id: Mapped[int] = mapped_column(ForeignKey("pontos_qr.id"), nullable=False)
    funcionario_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    data_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocorrencia: Mapped[str | None] = mapped_column(Text, nullable=True)
    foto: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[ReadingStatus] = mapped_column(
        Enum(ReadingStatus), default=ReadingStatus.completed, nullable=False
    )

    turno = relationship("Shift", back_populates="leituras")
    ponto = relationship("QrPoint", back_populates="leituras")
    funcionario = relationship("Employee")
