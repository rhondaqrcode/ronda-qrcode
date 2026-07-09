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
                    raio_padrao_metros=20,
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
                        latitude=-23.550520,
                        longitude=-46.633308,
                        raio_permitido_metros=20,
                    ),
                    QrPoint(
                        nome_ponto="Garagem",
                        codigo_qr="PONTO_GARAGEM_02",
                        descricao="Verificar circulacao, iluminacao e limpeza.",
                        ordem=2,
                        meta_passagens_turno=4,
                        carencia_minutos=45,
                        latitude=-23.550620,
                        longitude=-46.633408,
                        raio_permitido_metros=20,
                    ),
                    QrPoint(
                        nome_ponto="Corredor Operacional",
                        codigo_qr="PONTO_CORREDOR_03",
                        descricao="Registrar condicao geral do corredor.",
                        ordem=3,
                        meta_passagens_turno=4,
                        carencia_minutos=45,
                        latitude=-23.550720,
                        longitude=-46.633508,
                        raio_permitido_metros=20,
                    ),
                ]
            )
        db.commit()


def _ensure_ronda_columns() -> None:
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    if "pontos_qr" not in table_names:
        return
    statements = []
    columns = {column["name"] for column in inspector.get_columns("pontos_qr")}
    if "meta_passagens_turno" not in columns:
        statements.append("ALTER TABLE pontos_qr ADD COLUMN meta_passagens_turno INTEGER NOT NULL DEFAULT 4")
    if "carencia_minutos" not in columns:
        statements.append("ALTER TABLE pontos_qr ADD COLUMN carencia_minutos INTEGER NOT NULL DEFAULT 45")
    if "latitude" not in columns:
        statements.append("ALTER TABLE pontos_qr ADD COLUMN latitude FLOAT")
    if "longitude" not in columns:
        statements.append("ALTER TABLE pontos_qr ADD COLUMN longitude FLOAT")
    if "raio_permitido_metros" not in columns:
        statements.append("ALTER TABLE pontos_qr ADD COLUMN raio_permitido_metros INTEGER")

    if "configuracoes" in table_names:
        config_columns = {column["name"] for column in inspector.get_columns("configuracoes")}
        if "raio_padrao_metros" not in config_columns:
            statements.append("ALTER TABLE configuracoes ADD COLUMN raio_padrao_metros INTEGER NOT NULL DEFAULT 20")

    if "leituras_qr" in table_names:
        reading_columns = {column["name"] for column in inspector.get_columns("leituras_qr")}
        if "gps_latitude" not in reading_columns:
            statements.append("ALTER TABLE leituras_qr ADD COLUMN gps_latitude FLOAT NOT NULL DEFAULT 0")
        if "gps_longitude" not in reading_columns:
            statements.append("ALTER TABLE leituras_qr ADD COLUMN gps_longitude FLOAT NOT NULL DEFAULT 0")
        if "gps_precisao_metros" not in reading_columns:
            statements.append("ALTER TABLE leituras_qr ADD COLUMN gps_precisao_metros FLOAT NOT NULL DEFAULT 0")
        if "gps_distancia_metros" not in reading_columns:
            statements.append("ALTER TABLE leituras_qr ADD COLUMN gps_distancia_metros FLOAT NOT NULL DEFAULT 0")
        if "gps_status" not in reading_columns:
            statements.append(
                "ALTER TABLE leituras_qr ADD COLUMN gps_status VARCHAR(40) NOT NULL DEFAULT 'GPS VALIDADO'"
            )
    if not statements:
        return
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
