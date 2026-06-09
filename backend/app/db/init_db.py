from sqlalchemy import inspect, select, text

from backend.app.core.config import settings
from backend.app.core.security import get_password_hash
from backend.app.db.session import Base, SessionLocal, engine
from backend.app.models import CompanySettings, Employee, Location, QrPoint, User, UserRole


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_ronda_columns()

    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == settings.default_admin_email))
        if not admin:
            employee = Employee(
                name="Administrador",
                phone="",
                position="Supervisor geral",
                is_active=True,
            )
            admin = User(
                email=settings.default_admin_email,
                name="Administrador",
                hashed_password=get_password_hash(settings.default_admin_password),
                role=UserRole.admin,
                is_active=True,
                employee=employee,
            )
            db.add(admin)

        has_location = db.scalar(select(Location).limit(1))
        if not has_location:
            db.add(
                Location(
                    name="Cliente Exemplo",
                    address="Endereco operacional",
                    city="Sao Paulo",
                    is_active=True,
                )
            )
        has_settings = db.scalar(select(CompanySettings).limit(1))
        if not has_settings:
            db.add(
                CompanySettings(
                    nome_empresa="Empresa Exemplo",
                    email_supervisor="supervisor@empresa.local",
                    cor_primaria="#1f6feb",
                    tempo_minimo_leituras_segundos=30,
                )
            )
        has_qr_points = db.scalar(select(QrPoint).limit(1))
        if not has_qr_points:
            db.add_all(
                [
                    QrPoint(
                        nome_ponto="Portao Principal",
                        codigo_qr="PONTO_PORTAO_01",
                        descricao="Conferir acesso principal e registrar foto.",
                        ordem=1,
                        meta_passagens_turno=4,
                        carencia_minutos=45,
                    ),
                    QrPoint(
                        nome_ponto="Garagem",
                        codigo_qr="PONTO_GARAGEM_02",
                        descricao="Verificar circulacao, iluminacao e limpeza.",
                        ordem=2,
                        meta_passagens_turno=4,
                        carencia_minutos=45,
                    ),
                    QrPoint(
                        nome_ponto="Corredor Operacional",
                        codigo_qr="PONTO_CORREDOR_03",
                        descricao="Registrar condicao geral do corredor.",
                        ordem=3,
                        meta_passagens_turno=4,
                        carencia_minutos=45,
                    ),
                ]
            )
        db.commit()


def _ensure_ronda_columns() -> None:
    inspector = inspect(engine)
    if "pontos_qr" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("pontos_qr")}
    statements = []
    if "meta_passagens_turno" not in columns:
        statements.append("ALTER TABLE pontos_qr ADD COLUMN meta_passagens_turno INTEGER NOT NULL DEFAULT 4")
    if "carencia_minutos" not in columns:
        statements.append("ALTER TABLE pontos_qr ADD COLUMN carencia_minutos INTEGER NOT NULL DEFAULT 45")
    if not statements:
        return
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
