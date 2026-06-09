from __future__ import annotations

import csv
import io
import shutil
import sqlite3
import textwrap
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


DB_PATH = Path(__file__).with_name("backoffice_zeladoria.db")
BACKUP_DIR = Path(__file__).with_name("backups")
TIPOS_OCORRENCIA = (
    "Falta",
    "Hora Extra",
    "Gratificacao",
    "Cobertura",
    "Adiantamento/Vale",
)
TURNOS_ESCALA = ("Diurno", "Noturno", "Plantao", "Cobertura", "Folga")
STATUS_FUNCIONARIO = ("Ativo", "Demitido")
DIAS_SEMANA = {
    "Segunda": 0,
    "Terca": 1,
    "Quarta": 2,
    "Quinta": 3,
    "Sexta": 4,
    "Sabado": 5,
    "Domingo": 6,
}
PROVISAO_TRABALHISTA = 0.0833
st: Any = None


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def execute(query: str, params: tuple[Any, ...] = ()) -> None:
    with get_connection() as conn:
        conn.execute(query, params)
        conn.commit()


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(query, params).fetchall()


def fetch_one(query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute(query, params).fetchone()


def ensure_backup_dir() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def create_backup(label: str = "manual") -> Path:
    ensure_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = "".join(char for char in label.lower() if char.isalnum() or char in ("_", "-")) or "manual"
    backup_path = BACKUP_DIR / f"fortguard_{safe_label}_{timestamp}.db"
    with sqlite3.connect(DB_PATH) as source:
        with sqlite3.connect(backup_path) as destination:
            source.backup(destination)
    return backup_path


def create_daily_backup_if_needed() -> Path | None:
    ensure_backup_dir()
    today_marker = datetime.now().strftime("%Y%m%d")
    existing = list(BACKUP_DIR.glob(f"fortguard_auto_{today_marker}_*.db"))
    if existing or not DB_PATH.exists():
        return None
    return create_backup("auto")


def list_backups() -> list[Path]:
    ensure_backup_dir()
    return sorted(BACKUP_DIR.glob("fortguard_*.db"), key=lambda path: path.stat().st_mtime, reverse=True)


def backup_label(path: Path) -> str:
    modified = datetime.fromtimestamp(path.stat().st_mtime).strftime("%d/%m/%Y %H:%M:%S")
    size_kb = path.stat().st_size / 1024
    return f"{path.name} - {modified} - {size_kb:.1f} KB"


def restore_backup(backup_path: Path) -> Path:
    ensure_backup_dir()
    resolved_backup = backup_path.resolve()
    resolved_backup.relative_to(BACKUP_DIR.resolve())
    if not resolved_backup.exists() or resolved_backup.suffix.lower() != ".db":
        raise ValueError("Backup invalido.")

    emergency_backup = create_backup("antes_restauracao")
    shutil.copy2(resolved_backup, DB_PATH)
    return emergency_backup


def table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}


def add_column_if_missing(
    conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
    definition: str,
) -> None:
    if column_name not in table_columns(conn, table_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def migrate_db(conn: sqlite3.Connection) -> None:
    add_column_if_missing(conn, "condominios", "aliquota_imposto_retido", "REAL NOT NULL DEFAULT 0")
    add_column_if_missing(conn, "funcionarios", "data_vencimento_seguro", "DATE")
    add_column_if_missing(conn, "funcionarios", "status", "TEXT NOT NULL DEFAULT 'Ativo'")
    add_column_if_missing(conn, "funcionarios", "motivo_desligamento", "TEXT")

    entrada_cols = table_columns(conn, "estoque_entradas")
    if "quantidade_pacotes" not in entrada_cols:
        conn.execute("ALTER TABLE estoque_entradas ADD COLUMN quantidade_pacotes REAL")
    if "unidades_por_pacote" not in table_columns(conn, "estoque_entradas"):
        conn.execute("ALTER TABLE estoque_entradas ADD COLUMN unidades_por_pacote REAL")
    entrada_cols = table_columns(conn, "estoque_entradas")
    if "quantidade" in entrada_cols:
        conn.execute(
            """
            UPDATE estoque_entradas
            SET quantidade_pacotes = COALESCE(quantidade_pacotes, quantidade),
                unidades_por_pacote = COALESCE(unidades_por_pacote, 1)
            """
        )
    else:
        conn.execute(
            """
            UPDATE estoque_entradas
            SET quantidade_pacotes = COALESCE(quantidade_pacotes, 1),
                unidades_por_pacote = COALESCE(unidades_por_pacote, 1)
            """
        )

    saida_cols = table_columns(conn, "estoque_saidas")
    if "quantidade_unidades" not in saida_cols:
        conn.execute("ALTER TABLE estoque_saidas ADD COLUMN quantidade_unidades REAL")
    if "quantidade" in table_columns(conn, "estoque_saidas"):
        conn.execute(
            """
            UPDATE estoque_saidas
            SET quantidade_unidades = COALESCE(quantidade_unidades, quantidade)
            """
        )
    else:
        conn.execute(
            """
            UPDATE estoque_saidas
            SET quantidade_unidades = COALESCE(quantidade_unidades, 1)
            """
        )
    conn.commit()


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS condominios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                sindico_contato TEXT,
                valor_contrato_mensal REAL NOT NULL DEFAULT 0,
                data_inicio_contrato DATE NOT NULL,
                aliquota_imposto_retido REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS funcionarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                cargo TEXT NOT NULL,
                salario_base REAL NOT NULL DEFAULT 0,
                condominio_fixo_id INTEGER NULL,
                data_ultimo_aso DATE NOT NULL,
                data_vencimento_seguro DATE,
                status TEXT NOT NULL DEFAULT 'Ativo',
                motivo_desligamento TEXT,
                FOREIGN KEY (condominio_fixo_id) REFERENCES condominios(id)
                    ON UPDATE CASCADE
                    ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS catalogo_itens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_item TEXT NOT NULL UNIQUE,
                unidade_medida TEXT NOT NULL,
                estoque_minimo_alerta REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS estoque_entradas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                quantidade_pacotes REAL NOT NULL CHECK (quantidade_pacotes > 0),
                unidades_por_pacote REAL NOT NULL CHECK (unidades_por_pacote > 0),
                valor_total_pago REAL NOT NULL CHECK (valor_total_pago >= 0),
                data_compra DATE NOT NULL DEFAULT CURRENT_DATE,
                FOREIGN KEY (item_id) REFERENCES catalogo_itens(id)
                    ON UPDATE CASCADE
                    ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS estoque_saidas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                condominio_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                quantidade_unidades REAL NOT NULL CHECK (quantidade_unidades > 0),
                custo_unitario_aplicado REAL NOT NULL CHECK (custo_unitario_aplicado >= 0),
                data_envio DATE NOT NULL DEFAULT CURRENT_DATE,
                FOREIGN KEY (condominio_id) REFERENCES condominios(id)
                    ON UPDATE CASCADE
                    ON DELETE RESTRICT,
                FOREIGN KEY (item_id) REFERENCES catalogo_itens(id)
                    ON UPDATE CASCADE
                    ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS estoque_ajustes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                quantidade_ajuste REAL NOT NULL,
                data_ajuste DATE NOT NULL DEFAULT CURRENT_DATE,
                motivo TEXT,
                FOREIGN KEY (item_id) REFERENCES catalogo_itens(id)
                    ON UPDATE CASCADE
                    ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS ativos_equipamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_equipamento TEXT NOT NULL,
                condominio_atual_id INTEGER NULL,
                data_envio DATE NOT NULL DEFAULT CURRENT_DATE,
                FOREIGN KEY (condominio_atual_id) REFERENCES condominios(id)
                    ON UPDATE CASCADE
                    ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS rh_ocorrencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                funcionario_id INTEGER NOT NULL,
                condominio_afetado_id INTEGER NOT NULL,
                tipo_ocorrencia TEXT NOT NULL CHECK (
                    tipo_ocorrencia IN (
                        'Falta',
                        'Hora Extra',
                        'Gratificacao',
                        'Cobertura',
                        'Adiantamento/Vale'
                    )
                ),
                valor_ajuste REAL NOT NULL DEFAULT 0,
                data_ocorrencia DATE NOT NULL DEFAULT CURRENT_DATE,
                observacao TEXT,
                FOREIGN KEY (funcionario_id) REFERENCES funcionarios(id)
                    ON UPDATE CASCADE
                    ON DELETE RESTRICT,
                FOREIGN KEY (condominio_afetado_id) REFERENCES condominios(id)
                    ON UPDATE CASCADE
                    ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS certidoes_empresa (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_documento TEXT NOT NULL,
                data_vencimento DATE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sinistros_danos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                condominio_id INTEGER NOT NULL,
                funcionario_id INTEGER NULL,
                descricao_dano TEXT NOT NULL,
                custo_reparo REAL NOT NULL DEFAULT 0,
                data_sinistro DATE NOT NULL DEFAULT CURRENT_DATE,
                FOREIGN KEY (condominio_id) REFERENCES condominios(id)
                    ON UPDATE CASCADE
                    ON DELETE RESTRICT,
                FOREIGN KEY (funcionario_id) REFERENCES funcionarios(id)
                    ON UPDATE CASCADE
                    ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS satisfacao_clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                condominio_id INTEGER NOT NULL,
                nota_satisfacao INTEGER NOT NULL CHECK (nota_satisfacao BETWEEN 0 AND 10),
                data_avaliacao DATE NOT NULL DEFAULT CURRENT_DATE,
                observacoes TEXT,
                FOREIGN KEY (condominio_id) REFERENCES condominios(id)
                    ON UPDATE CASCADE
                    ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS escalas_trabalho (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                funcionario_id INTEGER NOT NULL,
                condominio_id INTEGER NULL,
                data_escala DATE NOT NULL,
                turno TEXT NOT NULL CHECK (
                    turno IN ('Diurno', 'Noturno', 'Plantao', 'Cobertura', 'Folga')
                ),
                hora_inicio TEXT NOT NULL,
                hora_fim TEXT NOT NULL,
                posto TEXT,
                observacao TEXT,
                FOREIGN KEY (funcionario_id) REFERENCES funcionarios(id)
                    ON UPDATE CASCADE
                    ON DELETE RESTRICT,
                FOREIGN KEY (condominio_id) REFERENCES condominios(id)
                    ON UPDATE CASCADE
                    ON DELETE SET NULL,
                UNIQUE (funcionario_id, data_escala, turno, hora_inicio)
            );
            """
        )
        migrate_db(conn)
        conn.commit()

    seed_if_empty()
    create_daily_backup_if_needed()


def seed_if_empty() -> None:
    total = fetch_one("SELECT COUNT(*) AS total FROM condominios")
    if total and total["total"] > 0:
        certidoes_total = fetch_one("SELECT COUNT(*) AS total FROM certidoes_empresa")
        if certidoes_total and certidoes_total["total"] == 0:
            with get_connection() as conn:
                conn.executemany(
                    """
                    INSERT INTO certidoes_empresa (nome_documento, data_vencimento)
                    VALUES (?, ?)
                    """,
                    [
                        ("Certidao Negativa Federal", "2026-06-20"),
                        ("Certidao FGTS", "2026-06-15"),
                        ("Certidao Trabalhista", "2026-07-10"),
                    ],
                )
                conn.commit()
        return

    with get_connection() as conn:
        condominios = [
            ("Residencial Jardim Atlantico", "Marcia Lima - (11) 90000-1111", 28500.00, "2025-06-12", 4.65),
            ("Condominio Solar das Palmeiras", "Roberto Alves - (11) 90000-2222", 34200.00, "2025-08-01", 4.65),
            ("Edificio Vila Serena", "Claudia Torres - (11) 90000-3333", 19800.00, "2025-05-20", 3.00),
        ]
        conn.executemany(
            """
            INSERT INTO condominios
                (nome, sindico_contato, valor_contrato_mensal, data_inicio_contrato, aliquota_imposto_retido)
            VALUES (?, ?, ?, ?, ?)
            """,
            condominios,
        )

        funcionarios = [
            ("Joao Pereira", "Zelador", 3800.00, 1, "2025-06-20", "2026-06-30", "Ativo", ""),
            ("Ana Souza", "Auxiliar de Limpeza", 2200.00, 2, "2025-07-15", "2026-07-20", "Ativo", ""),
            ("Carlos Mendes", "Folguista", 2500.00, None, "2026-01-10", "2026-08-15", "Ativo", ""),
        ]
        conn.executemany(
            """
            INSERT INTO funcionarios
                (nome, cargo, salario_base, condominio_fixo_id, data_ultimo_aso, data_vencimento_seguro, status, motivo_desligamento)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            funcionarios,
        )

        itens = [
            ("Desinfetante 5L", "galao", 5),
            ("Saco de Lixo 100L", "pacote", 10),
            ("Papel Toalha", "fardo", 4),
        ]
        conn.executemany(
            """
            INSERT INTO catalogo_itens
                (nome_item, unidade_medida, estoque_minimo_alerta)
            VALUES (?, ?, ?)
            """,
            itens,
        )

        entradas = [
            (1, 4, 5, 360.00, "2026-05-02"),
            (2, 7, 5, 595.00, "2026-05-03"),
            (3, 3, 4, 420.00, "2026-05-05"),
        ]
        conn.executemany(
            """
            INSERT INTO estoque_entradas
                (item_id, quantidade_pacotes, unidades_por_pacote, valor_total_pago, data_compra)
            VALUES (?, ?, ?, ?, ?)
            """,
            entradas,
        )

        saidas = [
            (1, 1, 3, 18.00, "2026-05-10"),
            (2, 2, 5, 17.00, "2026-05-11"),
            (3, 3, 2, 35.00, "2026-05-12"),
        ]
        conn.executemany(
            """
            INSERT INTO estoque_saidas
                (condominio_id, item_id, quantidade_unidades, custo_unitario_aplicado, data_envio)
            VALUES (?, ?, ?, ?, ?)
            """,
            saidas,
        )

        equipamentos = [
            ("Lavadora de Alta Pressao", 1, "2026-05-08"),
            ("Enceradeira Industrial", 2, "2026-05-09"),
        ]
        conn.executemany(
            """
            INSERT INTO ativos_equipamentos
                (nome_equipamento, condominio_atual_id, data_envio)
            VALUES (?, ?, ?)
            """,
            equipamentos,
        )

        ocorrencias = [
            (3, 1, "Cobertura", 180.00, "2026-05-13", "Cobertura de portaria por um dia."),
            (2, 2, "Hora Extra", 95.00, "2026-05-16", "Apoio em limpeza pos-obra."),
            (1, 1, "Adiantamento/Vale", -200.00, "2026-05-18", "Vale descontado no fechamento."),
        ]
        conn.executemany(
            """
            INSERT INTO rh_ocorrencias
                (funcionario_id, condominio_afetado_id, tipo_ocorrencia, valor_ajuste, data_ocorrencia, observacao)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ocorrencias,
        )
        certidoes = [
            ("Certidao Negativa Federal", "2026-06-20"),
            ("Certidao FGTS", "2026-06-15"),
            ("Certidao Trabalhista", "2026-07-10"),
        ]
        conn.executemany(
            """
            INSERT INTO certidoes_empresa (nome_documento, data_vencimento)
            VALUES (?, ?)
            """,
            certidoes,
        )
        sinistros = [
            (1, 1, "Reposicao de vidro trincado durante limpeza de area comum.", 180.00, "2026-05-19"),
        ]
        conn.executemany(
            """
            INSERT INTO sinistros_danos
                (condominio_id, funcionario_id, descricao_dano, custo_reparo, data_sinistro)
            VALUES (?, ?, ?, ?, ?)
            """,
            sinistros,
        )
        satisfacoes = [
            (1, 9, "2026-05-28", "Sindica elogiou regularidade da equipe."),
            (2, 8, "2026-05-28", "Solicitou reforco em limpeza de garagem."),
            (3, 10, "2026-05-28", "Sem apontamentos."),
        ]
        conn.executemany(
            """
            INSERT INTO satisfacao_clientes
                (condominio_id, nota_satisfacao, data_avaliacao, observacoes)
            VALUES (?, ?, ?, ?)
            """,
            satisfacoes,
        )
        conn.commit()


def rows_to_records(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def format_brl(value: float) -> str:
    formatted = f"{value:,.2f}"
    return f"R$ {formatted}".replace(",", "X").replace(".", ",").replace("X", ".")


def parse_db_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def get_condominios() -> list[sqlite3.Row]:
    return fetch_all("SELECT * FROM condominios ORDER BY nome")


def get_funcionarios() -> list[sqlite3.Row]:
    return fetch_all(
        """
        SELECT f.*, c.nome AS condominio_fixo
        FROM funcionarios f
        LEFT JOIN condominios c ON c.id = f.condominio_fixo_id
        ORDER BY f.nome
        """
    )


def get_catalogo_itens() -> list[sqlite3.Row]:
    return fetch_all("SELECT * FROM catalogo_itens ORDER BY nome_item")


def insert_condominio(nome: str, contato: str, valor: float, inicio: date, aliquota_imposto: float) -> None:
    execute(
        """
        INSERT INTO condominios
            (nome, sindico_contato, valor_contrato_mensal, data_inicio_contrato, aliquota_imposto_retido)
        VALUES (?, ?, ?, ?, ?)
        """,
        (nome, contato, valor, inicio.isoformat(), aliquota_imposto),
    )


def update_condominio(
    condominio_id: int,
    nome: str,
    contato: str,
    valor: float,
    inicio: date,
    aliquota_imposto: float,
) -> None:
    execute(
        """
        UPDATE condominios
        SET nome = ?,
            sindico_contato = ?,
            valor_contrato_mensal = ?,
            data_inicio_contrato = ?,
            aliquota_imposto_retido = ?
        WHERE id = ?
        """,
        (nome, contato, valor, inicio.isoformat(), aliquota_imposto, condominio_id),
    )


def insert_funcionario(
    nome: str,
    cargo: str,
    salario: float,
    condominio_id: int | None,
    data_aso: date,
    data_seguro: date | None,
    status: str = "Ativo",
    motivo_desligamento: str = "",
) -> None:
    execute(
        """
        INSERT INTO funcionarios
            (nome, cargo, salario_base, condominio_fixo_id, data_ultimo_aso, data_vencimento_seguro, status, motivo_desligamento)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            nome,
            cargo,
            salario,
            condominio_id,
            data_aso.isoformat(),
            data_seguro.isoformat() if data_seguro else None,
            status,
            motivo_desligamento,
        ),
    )


def update_funcionario(
    funcionario_id: int,
    nome: str,
    cargo: str,
    salario: float,
    condominio_id: int | None,
    data_aso: date,
    data_seguro: date | None,
    status: str,
    motivo_desligamento: str,
) -> None:
    execute(
        """
        UPDATE funcionarios
        SET nome = ?,
            cargo = ?,
            salario_base = ?,
            condominio_fixo_id = ?,
            data_ultimo_aso = ?,
            data_vencimento_seguro = ?
            , status = ?
            , motivo_desligamento = ?
        WHERE id = ?
        """,
        (
            nome,
            cargo,
            salario,
            condominio_id,
            data_aso.isoformat(),
            data_seguro.isoformat() if data_seguro else None,
            status,
            motivo_desligamento,
            funcionario_id,
        ),
    )


def insert_certidao(nome_documento: str, data_vencimento: date) -> None:
    execute(
        """
        INSERT INTO certidoes_empresa (nome_documento, data_vencimento)
        VALUES (?, ?)
        """,
        (nome_documento, data_vencimento.isoformat()),
    )


def update_certidao(certidao_id: int, nome_documento: str, data_vencimento: date) -> None:
    execute(
        """
        UPDATE certidoes_empresa
        SET nome_documento = ?, data_vencimento = ?
        WHERE id = ?
        """,
        (nome_documento, data_vencimento.isoformat(), certidao_id),
    )


def get_certidoes() -> list[sqlite3.Row]:
    return fetch_all("SELECT * FROM certidoes_empresa ORDER BY data_vencimento, nome_documento")


def insert_sinistro(
    condominio_id: int,
    funcionario_id: int | None,
    descricao: str,
    custo_reparo: float,
    data_sinistro: date,
) -> None:
    execute(
        """
        INSERT INTO sinistros_danos
            (condominio_id, funcionario_id, descricao_dano, custo_reparo, data_sinistro)
        VALUES (?, ?, ?, ?, ?)
        """,
        (condominio_id, funcionario_id, descricao, custo_reparo, data_sinistro.isoformat()),
    )


def get_historico_sinistros(limit: int = 20) -> list[dict[str, Any]]:
    rows = fetch_all(
        """
        SELECT
            s.data_sinistro AS Data,
            c.nome AS Condominio,
            COALESCE(f.nome, 'Nao informado') AS Funcionario,
            s.descricao_dano AS Descricao,
            s.custo_reparo AS Custo
        FROM sinistros_danos s
        JOIN condominios c ON c.id = s.condominio_id
        LEFT JOIN funcionarios f ON f.id = s.funcionario_id
        ORDER BY s.data_sinistro DESC, s.id DESC
        LIMIT ?
        """,
        (limit,),
    )
    return rows_to_records(rows)


def insert_satisfacao(
    condominio_id: int,
    nota: int,
    data_avaliacao: date,
    observacoes: str,
) -> None:
    execute(
        """
        INSERT INTO satisfacao_clientes
            (condominio_id, nota_satisfacao, data_avaliacao, observacoes)
        VALUES (?, ?, ?, ?)
        """,
        (condominio_id, nota, data_avaliacao.isoformat(), observacoes),
    )


def get_satisfacoes(limit: int = 30) -> list[dict[str, Any]]:
    rows = fetch_all(
        """
        SELECT
            s.data_avaliacao AS Data,
            c.nome AS Condominio,
            s.nota_satisfacao AS Nota,
            COALESCE(s.observacoes, '') AS Observacoes
        FROM satisfacao_clientes s
        JOIN condominios c ON c.id = s.condominio_id
        ORDER BY s.data_avaliacao DESC, s.id DESC
        LIMIT ?
        """,
        (limit,),
    )
    return rows_to_records(rows)


def insert_equipamento(nome: str, condominio_id: int | None, data_envio: date) -> None:
    execute(
        """
        INSERT INTO ativos_equipamentos
            (nome_equipamento, condominio_atual_id, data_envio)
        VALUES (?, ?, ?)
        """,
        (nome, condominio_id, data_envio.isoformat()),
    )


def insert_item(nome: str, unidade: str, estoque_minimo: float) -> None:
    execute(
        """
        INSERT INTO catalogo_itens (nome_item, unidade_medida, estoque_minimo_alerta)
        VALUES (?, ?, ?)
        """,
        (nome, unidade, estoque_minimo),
    )


def update_item(item_id: int, nome: str, unidade: str, estoque_minimo: float) -> None:
    execute(
        """
        UPDATE catalogo_itens
        SET nome_item = ?, unidade_medida = ?, estoque_minimo_alerta = ?
        WHERE id = ?
        """,
        (nome, unidade, estoque_minimo, item_id),
    )


def insert_entrada(
    item_id: int,
    quantidade_pacotes: float,
    unidades_por_pacote: float,
    valor_total: float,
    data_compra: date,
) -> None:
    with get_connection() as conn:
        if "quantidade" in table_columns(conn, "estoque_entradas"):
            conn.execute(
                """
                INSERT INTO estoque_entradas
                    (item_id, quantidade, quantidade_pacotes, unidades_por_pacote, valor_total_pago, data_compra)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    quantidade_pacotes * unidades_por_pacote,
                    quantidade_pacotes,
                    unidades_por_pacote,
                    valor_total,
                    data_compra.isoformat(),
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO estoque_entradas
                    (item_id, quantidade_pacotes, unidades_por_pacote, valor_total_pago, data_compra)
                VALUES (?, ?, ?, ?, ?)
                """,
                (item_id, quantidade_pacotes, unidades_por_pacote, valor_total, data_compra.isoformat()),
            )
        conn.commit()


def insert_estoque_ajuste(item_id: int, quantidade_ajuste: float, data_ajuste: date, motivo: str) -> None:
    execute(
        """
        INSERT INTO estoque_ajustes
            (item_id, quantidade_ajuste, data_ajuste, motivo)
        VALUES (?, ?, ?, ?)
        """,
        (item_id, quantidade_ajuste, data_ajuste.isoformat(), motivo),
    )


def ajustar_saldo_item(item_id: int, saldo_desejado: float, data_ajuste: date, motivo: str) -> float:
    saldo_atual = get_saldo_item(item_id)
    diferenca = saldo_desejado - saldo_atual
    if abs(diferenca) < 0.0001:
        return 0.0
    insert_estoque_ajuste(item_id, diferenca, data_ajuste, motivo)
    return diferenca


def get_ultimo_custo_unitario(item_id: int) -> float | None:
    row = fetch_one(
        """
        SELECT valor_total_pago / (quantidade_pacotes * unidades_por_pacote) AS custo_unitario
        FROM estoque_entradas
        WHERE item_id = ?
        ORDER BY data_compra DESC, id DESC
        LIMIT 1
        """,
        (item_id,),
    )
    if not row:
        return None
    return float(row["custo_unitario"])


def get_saldo_item(item_id: int) -> float:
    row = fetch_one(
        """
        SELECT
            COALESCE((SELECT SUM(quantidade_pacotes * unidades_por_pacote) FROM estoque_entradas WHERE item_id = ?), 0)
            -
            COALESCE((SELECT SUM(quantidade_unidades) FROM estoque_saidas WHERE item_id = ?), 0)
            +
            COALESCE((SELECT SUM(quantidade_ajuste) FROM estoque_ajustes WHERE item_id = ?), 0)
            AS saldo
        """,
        (item_id, item_id, item_id),
    )
    return float(row["saldo"]) if row else 0.0


def insert_saida(condominio_id: int, item_id: int, quantidade_unidades: float, data_envio: date) -> float:
    custo_unitario = get_ultimo_custo_unitario(item_id)
    if custo_unitario is None:
        raise ValueError("Este item ainda nao possui entrada de compra para definir custo.")

    saldo = get_saldo_item(item_id)
    if quantidade_unidades > saldo:
        raise ValueError(f"Saldo insuficiente. Disponivel: {saldo:g}.")

    with get_connection() as conn:
        if "quantidade" in table_columns(conn, "estoque_saidas"):
            conn.execute(
                """
                INSERT INTO estoque_saidas
                    (condominio_id, item_id, quantidade, quantidade_unidades, custo_unitario_aplicado, data_envio)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    condominio_id,
                    item_id,
                    quantidade_unidades,
                    quantidade_unidades,
                    custo_unitario,
                    data_envio.isoformat(),
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO estoque_saidas
                    (condominio_id, item_id, quantidade_unidades, custo_unitario_aplicado, data_envio)
                VALUES (?, ?, ?, ?, ?)
                """,
                (condominio_id, item_id, quantidade_unidades, custo_unitario, data_envio.isoformat()),
            )
        conn.commit()
    return custo_unitario


def insert_rh_ocorrencia(
    funcionario_id: int,
    condominio_id: int,
    tipo: str,
    valor: float,
    data_ocorrencia: date,
    observacao: str,
) -> None:
    execute(
        """
        INSERT INTO rh_ocorrencias
            (funcionario_id, condominio_afetado_id, tipo_ocorrencia, valor_ajuste, data_ocorrencia, observacao)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (funcionario_id, condominio_id, tipo, valor, data_ocorrencia.isoformat(), observacao),
    )


def daterange(data_inicio: date, data_fim: date) -> list[date]:
    dias = []
    atual = data_inicio
    while atual <= data_fim:
        dias.append(atual)
        atual += timedelta(days=1)
    return dias


def insert_escala_trabalho(
    funcionario_id: int,
    condominio_id: int | None,
    data_escala: date,
    turno: str,
    hora_inicio: str,
    hora_fim: str,
    posto: str,
    observacao: str,
) -> None:
    execute(
        """
        INSERT OR REPLACE INTO escalas_trabalho
            (funcionario_id, condominio_id, data_escala, turno, hora_inicio, hora_fim, posto, observacao)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            funcionario_id,
            condominio_id,
            data_escala.isoformat(),
            turno,
            hora_inicio,
            hora_fim,
            posto,
            observacao,
        ),
    )


def gerar_escala_funcionarios_fixos(
    data_inicio: date,
    data_fim: date,
    dias_semana: set[int],
    turno: str,
    hora_inicio: str,
    hora_fim: str,
    posto: str,
    sobrescrever: bool,
) -> int:
    funcionarios_fixos = fetch_all(
        """
        SELECT id, condominio_fixo_id
        FROM funcionarios
        WHERE condominio_fixo_id IS NOT NULL
          AND status = 'Ativo'
        ORDER BY nome
        """
    )
    if not funcionarios_fixos:
        return 0

    criadas = 0
    with get_connection() as conn:
        for dia in daterange(data_inicio, data_fim):
            if dia.weekday() not in dias_semana:
                continue
            for funcionario in funcionarios_fixos:
                if sobrescrever:
                    conn.execute(
                        """
                        DELETE FROM escalas_trabalho
                        WHERE funcionario_id = ? AND data_escala = ?
                        """,
                        (funcionario["id"], dia.isoformat()),
                    )
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO escalas_trabalho
                        (funcionario_id, condominio_id, data_escala, turno, hora_inicio, hora_fim, posto, observacao)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        funcionario["id"],
                        funcionario["condominio_fixo_id"],
                        dia.isoformat(),
                        turno,
                        hora_inicio,
                        hora_fim,
                        posto,
                        "Gerado automaticamente pelo sistema.",
                    ),
                )
                criadas += cursor.rowcount
        conn.commit()
    return criadas


def get_escala_trabalho(
    data_inicio: date,
    data_fim: date,
    condominio_id: int | None = None,
) -> list[dict[str, Any]]:
    params: list[Any] = [data_inicio.isoformat(), data_fim.isoformat()]
    filtro_condominio = ""
    if condominio_id is not None:
        filtro_condominio = "AND e.condominio_id = ?"
        params.append(condominio_id)

    rows = fetch_all(
        f"""
        SELECT
            e.data_escala AS Data,
            CASE strftime('%w', e.data_escala)
                WHEN '0' THEN 'Domingo'
                WHEN '1' THEN 'Segunda'
                WHEN '2' THEN 'Terca'
                WHEN '3' THEN 'Quarta'
                WHEN '4' THEN 'Quinta'
                WHEN '5' THEN 'Sexta'
                WHEN '6' THEN 'Sabado'
            END AS Dia,
            f.nome AS Funcionario,
            f.cargo AS Cargo,
            COALESCE(c.nome, 'Sem condominio') AS Condominio,
            e.turno AS Turno,
            e.hora_inicio AS Entrada,
            e.hora_fim AS Saida,
            COALESCE(e.posto, '') AS Posto,
            COALESCE(e.observacao, '') AS Observacao
        FROM escalas_trabalho e
        JOIN funcionarios f ON f.id = e.funcionario_id
        LEFT JOIN condominios c ON c.id = e.condominio_id
        WHERE e.data_escala BETWEEN ? AND ?
        {filtro_condominio}
        ORDER BY e.data_escala, c.nome, f.nome, e.hora_inicio
        """,
        tuple(params),
    )
    return rows_to_records(rows)


def records_to_csv(records: list[dict[str, Any]]) -> str:
    if not records:
        return ""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(records[0].keys()), delimiter=";")
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue()


def normalize_pdf_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def format_date_br(value: str | date | None) -> str:
    if value is None:
        return ""
    if isinstance(value, date):
        parsed = value
    else:
        parsed = parse_db_date(value)
        if parsed is None:
            return str(value)
    return parsed.strftime("%d/%m/%Y")


def get_balancete_movimentos(data_inicio: date, data_fim: date) -> dict[str, Any]:
    dre = get_dashboard_data(data_inicio, data_fim)
    entradas = rows_to_records(
        fetch_all(
            """
            SELECT
                e.data_compra AS Data,
                i.nome_item AS Item,
                e.quantidade_pacotes AS Pacotes,
                e.unidades_por_pacote AS Unidades_Por_Pacote,
                e.quantidade_pacotes * e.unidades_por_pacote AS Total_Unidades,
                i.unidade_medida AS Unidade,
                e.valor_total_pago AS Valor_Total,
                e.valor_total_pago / (e.quantidade_pacotes * e.unidades_por_pacote) AS Custo_Unitario
            FROM estoque_entradas e
            JOIN catalogo_itens i ON i.id = e.item_id
            WHERE e.data_compra BETWEEN ? AND ?
            ORDER BY e.data_compra, i.nome_item
            """,
            (data_inicio.isoformat(), data_fim.isoformat()),
        )
    )
    saidas = rows_to_records(
        fetch_all(
            """
            SELECT
                s.data_envio AS Data,
                c.nome AS Condominio,
                i.nome_item AS Item,
                s.quantidade_unidades AS Quantidade_Unidades,
                i.unidade_medida AS Unidade,
                s.custo_unitario_aplicado AS Custo_Unitario,
                s.quantidade_unidades * s.custo_unitario_aplicado AS Valor_Total
            FROM estoque_saidas s
            JOIN condominios c ON c.id = s.condominio_id
            JOIN catalogo_itens i ON i.id = s.item_id
            WHERE s.data_envio BETWEEN ? AND ?
            ORDER BY s.data_envio, c.nome, i.nome_item
            """,
            (data_inicio.isoformat(), data_fim.isoformat()),
        )
    )
    ajustes_estoque = rows_to_records(
        fetch_all(
            """
            SELECT
                a.data_ajuste AS Data,
                i.nome_item AS Item,
                a.quantidade_ajuste AS Ajuste,
                i.unidade_medida AS Unidade,
                COALESCE(a.motivo, '') AS Motivo
            FROM estoque_ajustes a
            JOIN catalogo_itens i ON i.id = a.item_id
            WHERE a.data_ajuste BETWEEN ? AND ?
            ORDER BY a.data_ajuste, i.nome_item
            """,
            (data_inicio.isoformat(), data_fim.isoformat()),
        )
    )
    rh = rows_to_records(
        fetch_all(
            """
            SELECT
                o.data_ocorrencia AS Data,
                f.nome AS Funcionario,
                c.nome AS Condominio,
                o.tipo_ocorrencia AS Tipo,
                o.valor_ajuste AS Valor,
                COALESCE(o.observacao, '') AS Observacao
            FROM rh_ocorrencias o
            JOIN funcionarios f ON f.id = o.funcionario_id
            JOIN condominios c ON c.id = o.condominio_afetado_id
            WHERE o.data_ocorrencia BETWEEN ? AND ?
            ORDER BY o.data_ocorrencia, c.nome, f.nome
            """,
            (data_inicio.isoformat(), data_fim.isoformat()),
        )
    )
    sinistros = rows_to_records(
        fetch_all(
            """
            SELECT
                s.data_sinistro AS Data,
                c.nome AS Condominio,
                COALESCE(f.nome, 'Nao informado') AS Funcionario,
                s.descricao_dano AS Descricao,
                s.custo_reparo AS Custo
            FROM sinistros_danos s
            JOIN condominios c ON c.id = s.condominio_id
            LEFT JOIN funcionarios f ON f.id = s.funcionario_id
            WHERE s.data_sinistro BETWEEN ? AND ?
            ORDER BY s.data_sinistro, c.nome
            """,
            (data_inicio.isoformat(), data_fim.isoformat()),
        )
    )
    equipamentos = rows_to_records(
        fetch_all(
            """
            SELECT
                e.data_envio AS Data,
                e.nome_equipamento AS Equipamento,
                COALESCE(c.nome, 'Sem condominio') AS Condominio
            FROM ativos_equipamentos e
            LEFT JOIN condominios c ON c.id = e.condominio_atual_id
            WHERE e.data_envio BETWEEN ? AND ?
            ORDER BY e.data_envio, e.nome_equipamento
            """,
            (data_inicio.isoformat(), data_fim.isoformat()),
        )
    )
    certidoes = rows_to_records(
        fetch_all(
            """
            SELECT
                nome_documento AS Documento,
                data_vencimento AS Data_Vencimento
            FROM certidoes_empresa
            ORDER BY data_vencimento, nome_documento
            """
        )
    )
    satisfacoes = rows_to_records(
        fetch_all(
            """
            SELECT
                s.data_avaliacao AS Data,
                c.nome AS Condominio,
                s.nota_satisfacao AS Nota,
                COALESCE(s.observacoes, '') AS Observacoes
            FROM satisfacao_clientes s
            JOIN condominios c ON c.id = s.condominio_id
            WHERE s.data_avaliacao BETWEEN ? AND ?
            ORDER BY s.data_avaliacao, c.nome
            """,
            (data_inicio.isoformat(), data_fim.isoformat()),
        )
    )
    escala = get_escala_trabalho(data_inicio, data_fim)
    saldo_estoque = get_saldo_estoque()
    totais = {
        "receita": sum(float(row["Faturamento Liquido"]) for row in dre),
        "custo_material": sum(float(row["Custo Material"]) for row in dre),
        "custo_rh_fixo": sum(float(row["Custo RH Fixo"]) for row in dre),
        "provisao": sum(float(row["Provisao Trabalhista"]) for row in dre),
        "ajustes_rh": sum(float(row["Ajustes RH"]) for row in dre),
        "lucro": sum(float(row["Lucro Liquido"]) for row in dre),
        "sinistros": sum(float(row["Custos Sinistros"]) for row in dre),
        "compras": sum(float(row["Valor_Total"]) for row in entradas),
        "saidas_material": sum(float(row["Valor_Total"]) for row in saidas),
        "movimentos_rh": sum(float(row["Valor"]) for row in rh),
    }
    return {
        "dre": dre,
        "entradas": entradas,
        "saidas": saidas,
        "ajustes_estoque": ajustes_estoque,
        "rh": rh,
        "sinistros": sinistros,
        "equipamentos": equipamentos,
        "certidoes": certidoes,
        "satisfacoes": satisfacoes,
        "escala": escala,
        "saldo_estoque": saldo_estoque,
        "totais": totais,
    }


def add_pdf_section(lines: list[str], titulo: str, rows: list[dict[str, Any]], empty_text: str) -> None:
    lines.append("")
    lines.append(titulo)
    lines.append("-" * min(len(titulo), 90))
    if not rows:
        lines.append(empty_text)
        return
    for row in rows:
        parts = []
        for key, value in row.items():
            label = key.replace("_", " ")
            if "Data" in key:
                formatted = format_date_br(value)
            elif isinstance(value, float):
                formatted = format_brl(value)
            else:
                formatted = str(value)
            parts.append(f"{label}: {formatted}")
        wrapped = textwrap.wrap(" | ".join(parts), width=115) or [""]
        lines.extend(wrapped)


def render_pdf_pages(lines: list[str], max_lines_per_page: int = 52) -> list[str]:
    pages = []
    current: list[str] = []
    for line in lines:
        if line == "__PAGE_BREAK__":
            pages.append("\n".join(current))
            current = []
            continue
        current.append(line)
        if len(current) >= max_lines_per_page:
            pages.append("\n".join(current))
            current = []
    if current:
        pages.append("\n".join(current))
    return pages


def build_simple_pdf(title: str, lines: list[str]) -> bytes:
    pages = render_pdf_pages(lines)
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",  # pages object filled after page objects are known
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    page_object_numbers = []
    for page_text in pages:
        content_lines = ["BT", "/F1 9 Tf", "40 800 Td", "12 TL"]
        content_lines.append(f"({normalize_pdf_text(title)}) Tj")
        content_lines.append("T*")
        content_lines.append("T*")
        for line in page_text.splitlines():
            content_lines.append(f"({normalize_pdf_text(line)}) Tj")
            content_lines.append("T*")
        content_lines.append("ET")
        stream = "\n".join(content_lines).encode("latin-1", errors="ignore")
        content_object_number = len(objects) + 2
        page_object = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_object_number} 0 R >>"
        ).encode("latin-1")
        page_object_numbers.append(len(objects) + 1)
        objects.append(page_object)
        objects.append(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream")

    kids = " ".join(f"{number} 0 R" for number in page_object_numbers)
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_object_numbers)} >>".encode("latin-1")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def gerar_balancete_pdf(data_inicio: date, data_fim: date) -> bytes:
    movimentos = get_balancete_movimentos(data_inicio, data_fim)
    totais = movimentos["totais"]
    titulo = f"FortGuard - Balancete Mensal {data_inicio.strftime('%m/%Y')}"
    lines = [
        "BALANCETE MENSAL COMPLETO",
        f"Periodo: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}",
        f"Gerado em: {date.today().strftime('%d/%m/%Y')}",
        "",
        "RESUMO FINANCEIRO",
        f"Faturamento liquido dos contratos: {format_brl(totais['receita'])}",
        f"Custo material aplicado: {format_brl(totais['custo_material'])}",
        f"Custo RH fixo: {format_brl(totais['custo_rh_fixo'])}",
        f"Provisao trabalhista: {format_brl(totais['provisao'])}",
        f"Ajustes RH: {format_brl(totais['ajustes_rh'])}",
        f"Custos com sinistros: {format_brl(totais['sinistros'])}",
        f"Lucro liquido: {format_brl(totais['lucro'])}",
        "",
        "RESUMO DE MOVIMENTOS",
        f"Compras de materiais no mes: {format_brl(totais['compras'])}",
        f"Materiais enviados aos condominios: {format_brl(totais['saidas_material'])}",
        f"Movimentos de RH lancados: {format_brl(totais['movimentos_rh'])}",
        f"Entradas de estoque: {len(movimentos['entradas'])}",
        f"Saidas de estoque: {len(movimentos['saidas'])}",
        f"Ajustes de estoque: {len(movimentos['ajustes_estoque'])}",
        f"Ocorrencias de RH: {len(movimentos['rh'])}",
        f"Sinistros e danos: {len(movimentos['sinistros'])}",
        f"Avaliacoes de satisfacao: {len(movimentos['satisfacoes'])}",
        f"Lancamentos de escala: {len(movimentos['escala'])}",
    ]
    add_pdf_section(lines, "DRE POR CONDOMINIO", movimentos["dre"], "Nenhum condominio cadastrado.")
    add_pdf_section(lines, "COMPRAS / ENTRADAS DE MATERIAIS", movimentos["entradas"], "Sem compras no periodo.")
    add_pdf_section(lines, "SAIDAS DE MATERIAIS PARA CONDOMINIOS", movimentos["saidas"], "Sem saidas no periodo.")
    add_pdf_section(lines, "AJUSTES DE ESTOQUE", movimentos["ajustes_estoque"], "Sem ajustes de estoque no periodo.")
    add_pdf_section(lines, "MOVIMENTOS E AJUSTES DE RH", movimentos["rh"], "Sem ocorrencias de RH no periodo.")
    add_pdf_section(lines, "SINISTROS E DANOS MATERIAIS", movimentos["sinistros"], "Sem sinistros no periodo.")
    add_pdf_section(lines, "EQUIPAMENTOS ENVIADOS NO PERIODO", movimentos["equipamentos"], "Sem envio de equipamentos no periodo.")
    add_pdf_section(lines, "CERTIDOES DA EMPRESA", movimentos["certidoes"], "Sem certidoes cadastradas.")
    add_pdf_section(lines, "SATISFACAO DOS SINDICOS", movimentos["satisfacoes"], "Sem avaliacoes no periodo.")
    add_pdf_section(lines, "ESCALA DE TRABALHO DO PERIODO", movimentos["escala"], "Sem escala lancada no periodo.")
    add_pdf_section(lines, "SALDO ATUAL DO ESTOQUE CENTRAL", movimentos["saldo_estoque"], "Sem itens no estoque.")
    return build_simple_pdf(titulo, lines)


def gerar_colinha_nota_fiscal_pdf(condominio_id: int, data_inicio: date, data_fim: date) -> bytes:
    condominio = fetch_one("SELECT * FROM condominios WHERE id = ?", (condominio_id,))
    if not condominio:
        raise ValueError("Condominio nao encontrado.")

    valor_bruto = float(condominio["valor_contrato_mensal"])
    aliquota = float(condominio["aliquota_imposto_retido"])
    imposto_retido = valor_bruto * (aliquota / 100)
    valor_liquido = valor_bruto - imposto_retido
    competencia = data_inicio.strftime("%m/%Y")
    descricao = (
        "Servicos de zeladoria, conservacao e limpeza referentes ao mes "
        f"{competencia}, conforme contrato mensal."
    )

    titulo = f"FortGuard - Colinha Nota Fiscal {competencia}"
    lines = [
        "COLINHA PARA EMISSAO DE NOTA FISCAL",
        "Este documento nao e nota fiscal oficial.",
        "Use apenas como apoio para preencher o portal da prefeitura ou emissor fiscal autorizado.",
        "",
        "COMPETENCIA",
        f"Periodo: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}",
        f"Mes de referencia: {competencia}",
        "",
        "TOMADOR / CONDOMINIO",
        f"Nome: {condominio['nome']}",
        f"Contato do sindico: {condominio['sindico_contato'] or ''}",
        "",
        "VALORES PARA CONFERENCIA",
        f"Valor bruto do contrato: {format_brl(valor_bruto)}",
        f"Aliquota de imposto retido: {aliquota:.2f}%",
        f"Valor do imposto retido: {format_brl(imposto_retido)}",
        f"Valor liquido previsto: {format_brl(valor_liquido)}",
        "",
        "DESCRICAO SUGERIDA DO SERVICO",
        descricao,
        "",
        "OBSERVACOES",
        "1. Confira CNPJ, inscricao municipal, codigo de servico e dados fiscais antes de emitir.",
        "2. Se a prefeitura calcular impostos diferentes, siga o valor do emissor oficial.",
        "3. Guarde a nota fiscal oficial emitida fora deste sistema.",
    ]
    return build_simple_pdf(titulo, lines)


def get_month_range(reference: date) -> tuple[date, date]:
    first_day = reference.replace(day=1)
    if first_day.month == 12:
        next_month = first_day.replace(year=first_day.year + 1, month=1)
    else:
        next_month = first_day.replace(month=first_day.month + 1)
    return first_day, next_month - timedelta(days=1)


def get_dashboard_data(data_inicio: date, data_fim: date) -> list[dict[str, Any]]:
    rows = fetch_all(
        """
        SELECT
            c.id,
            c.nome AS condominio,
            c.valor_contrato_mensal,
            c.aliquota_imposto_retido,
            c.data_inicio_contrato,
            COALESCE(mat.custo_material, 0) AS custo_material,
            COALESCE(rhf.custo_rh_fixo, 0) AS custo_rh_fixo,
            COALESCE(ajr.ajustes_rh, 0) AS ajustes_rh,
            COALESCE(sin.custos_sinistros, 0) AS custos_sinistros,
            sat.nota_satisfacao AS nota_satisfacao
        FROM condominios c
        LEFT JOIN (
            SELECT condominio_id, SUM(quantidade_unidades * custo_unitario_aplicado) AS custo_material
            FROM estoque_saidas
            WHERE data_envio BETWEEN ? AND ?
            GROUP BY condominio_id
        ) mat ON mat.condominio_id = c.id
        LEFT JOIN (
            SELECT condominio_fixo_id, SUM(salario_base) AS custo_rh_fixo
            FROM funcionarios
            WHERE condominio_fixo_id IS NOT NULL
              AND status = 'Ativo'
            GROUP BY condominio_fixo_id
        ) rhf ON rhf.condominio_fixo_id = c.id
        LEFT JOIN (
            SELECT condominio_afetado_id, SUM(valor_ajuste) AS ajustes_rh
            FROM rh_ocorrencias
            WHERE data_ocorrencia BETWEEN ? AND ?
            GROUP BY condominio_afetado_id
        ) ajr ON ajr.condominio_afetado_id = c.id
        LEFT JOIN (
            SELECT condominio_id, SUM(custo_reparo) AS custos_sinistros
            FROM sinistros_danos
            WHERE data_sinistro BETWEEN ? AND ?
            GROUP BY condominio_id
        ) sin ON sin.condominio_id = c.id
        LEFT JOIN (
            SELECT sc.condominio_id, sc.nota_satisfacao
            FROM satisfacao_clientes sc
            JOIN (
                SELECT condominio_id, MAX(data_avaliacao || '-' || printf('%010d', id)) AS chave
                FROM satisfacao_clientes
                GROUP BY condominio_id
            ) ult
              ON ult.condominio_id = sc.condominio_id
             AND ult.chave = sc.data_avaliacao || '-' || printf('%010d', sc.id)
        ) sat ON sat.condominio_id = c.id
        ORDER BY c.nome
        """,
        (
            data_inicio.isoformat(),
            data_fim.isoformat(),
            data_inicio.isoformat(),
            data_fim.isoformat(),
            data_inicio.isoformat(),
            data_fim.isoformat(),
        ),
    )

    records = []
    for row in rows:
        custo_material = float(row["custo_material"])
        custo_rh_fixo = float(row["custo_rh_fixo"])
        provisao = custo_rh_fixo * PROVISAO_TRABALHISTA
        ajustes_rh = float(row["ajustes_rh"])
        custos_sinistros = float(row["custos_sinistros"])
        contrato = float(row["valor_contrato_mensal"])
        imposto_retido = contrato * (float(row["aliquota_imposto_retido"]) / 100)
        faturamento_liquido = contrato - imposto_retido
        despesas = custo_material + custo_rh_fixo + provisao + ajustes_rh + custos_sinistros
        lucro = faturamento_liquido - despesas
        margem = (lucro / faturamento_liquido * 100) if faturamento_liquido else 0
        records.append(
            {
                "Condominio": row["condominio"],
                "Valor Contrato": contrato,
                "Imposto Retido": imposto_retido,
                "Faturamento Liquido": faturamento_liquido,
                "Custo Material": custo_material,
                "Custo RH Fixo": custo_rh_fixo,
                "Provisao Trabalhista": provisao,
                "Ajustes RH": ajustes_rh,
                "Custos Sinistros": custos_sinistros,
                "Lucro Liquido": lucro,
                "Margem %": margem,
                "Nota Satisfacao": row["nota_satisfacao"] if row["nota_satisfacao"] is not None else "",
            }
        )
    return records


def get_alertas_contratos() -> list[str]:
    hoje = date.today()
    alertas = []
    for row in get_condominios():
        inicio = parse_db_date(row["data_inicio_contrato"])
        if not inicio:
            continue
        try:
            aniversario = inicio.replace(year=hoje.year)
        except ValueError:
            aniversario = date(hoje.year, 2, 28)
        if aniversario < hoje:
            try:
                aniversario = inicio.replace(year=hoje.year + 1)
            except ValueError:
                aniversario = date(hoje.year + 1, 2, 28)
        dias_para_aniversario = (aniversario - hoje).days
        if 0 <= dias_para_aniversario <= 30:
            alertas.append(
                f"Contrato de {row['nome']} completa ciclo anual em {dias_para_aniversario} dias. Inicio: {inicio.strftime('%d/%m/%Y')}."
            )
    return alertas


def get_alertas_aso() -> list[str]:
    hoje = date.today()
    alertas = []
    for row in get_funcionarios():
        aso = parse_db_date(row["data_ultimo_aso"])
        if not aso:
            continue
        dias = (hoje - aso).days
        if dias >= 335:
            alertas.append(f"{row['nome']} esta com ASO ha {dias} dias. Ultimo ASO: {aso.strftime('%d/%m/%Y')}.")
        seguro = parse_db_date(row["data_vencimento_seguro"]) if "data_vencimento_seguro" in row.keys() else None
        if seguro:
            dias_seguro = (seguro - hoje).days
            if dias_seguro < 0:
                alertas.append(f"Seguro de {row['nome']} esta vencido desde {seguro.strftime('%d/%m/%Y')}.")
            elif dias_seguro <= 30:
                alertas.append(f"Seguro de {row['nome']} vence em {dias_seguro} dias: {seguro.strftime('%d/%m/%Y')}.")
    return alertas


def get_alertas_certidoes() -> list[str]:
    hoje = date.today()
    alertas = []
    for row in get_certidoes():
        vencimento = parse_db_date(row["data_vencimento"])
        if not vencimento:
            continue
        dias = (vencimento - hoje).days
        if dias < 0:
            alertas.append(f"Certidao vencida: {row['nome_documento']} venceu em {vencimento.strftime('%d/%m/%Y')}.")
        elif dias < 15:
            alertas.append(f"Certidao vencendo: {row['nome_documento']} vence em {dias} dias.")
    return alertas


def get_saldo_estoque() -> list[dict[str, Any]]:
    rows = fetch_all(
        """
        SELECT
            i.id,
            i.nome_item AS Item,
            i.unidade_medida AS Unidade,
            i.estoque_minimo_alerta AS Minimo,
            COALESCE(e.total_entradas, 0) AS Entradas_Unidades,
            COALESCE(s.total_saidas, 0) AS Saidas,
            COALESCE(a.total_ajustes, 0) AS Ajustes,
            COALESCE(e.total_entradas, 0) - COALESCE(s.total_saidas, 0) + COALESCE(a.total_ajustes, 0) AS Saldo
        FROM catalogo_itens i
        LEFT JOIN (
            SELECT item_id, SUM(quantidade_pacotes * unidades_por_pacote) AS total_entradas
            FROM estoque_entradas
            GROUP BY item_id
        ) e ON e.item_id = i.id
        LEFT JOIN (
            SELECT item_id, SUM(quantidade_unidades) AS total_saidas
            FROM estoque_saidas
            GROUP BY item_id
        ) s ON s.item_id = i.id
        LEFT JOIN (
            SELECT item_id, SUM(quantidade_ajuste) AS total_ajustes
            FROM estoque_ajustes
            GROUP BY item_id
        ) a ON a.item_id = i.id
        ORDER BY i.nome_item
        """
    )
    records = rows_to_records(rows)
    for row in records:
        row["Status"] = "Abaixo do minimo" if row["Saldo"] < row["Minimo"] else "OK"
    return records


def get_equipamentos() -> list[dict[str, Any]]:
    rows = fetch_all(
        """
        SELECT
            e.id,
            e.nome_equipamento AS Equipamento,
            COALESCE(c.nome, 'Sem alocacao') AS Condominio,
            e.data_envio AS Data
        FROM ativos_equipamentos e
        LEFT JOIN condominios c ON c.id = e.condominio_atual_id
        ORDER BY e.nome_equipamento
        """
    )
    return rows_to_records(rows)


def get_historico_ocorrencias(limit: int = 20) -> list[dict[str, Any]]:
    rows = fetch_all(
        """
        SELECT
            o.id AS ID,
            o.data_ocorrencia AS Data,
            f.nome AS Funcionario,
            c.nome AS Condominio,
            o.tipo_ocorrencia AS Tipo,
            o.valor_ajuste AS Valor,
            o.observacao AS Observacao
        FROM rh_ocorrencias o
        JOIN funcionarios f ON f.id = o.funcionario_id
        JOIN condominios c ON c.id = o.condominio_afetado_id
        ORDER BY o.data_ocorrencia DESC, o.id DESC
        LIMIT ?
        """,
        (limit,),
    )
    return rows_to_records(rows)


def delete_rh_ocorrencia(ocorrencia_id: int) -> None:
    execute("DELETE FROM rh_ocorrencias WHERE id = ?", (ocorrencia_id,))


def select_options(rows: list[sqlite3.Row], label_field: str = "nome") -> dict[str, int]:
    return {f"{row[label_field]} (ID {row['id']})": row["id"] for row in rows}


def optional_condominio_options(condominios: list[sqlite3.Row]) -> dict[str, int | None]:
    options: dict[str, int | None] = {"Sem condominio fixo": None}
    options.update(select_options(condominios))
    return options


def money_column_config() -> dict[str, st.column_config.NumberColumn]:
    return {
        "Valor Contrato": st.column_config.NumberColumn("Valor Contrato", format="R$ %.2f"),
        "Imposto Retido": st.column_config.NumberColumn("Imposto Retido", format="R$ %.2f"),
        "Faturamento Liquido": st.column_config.NumberColumn("Faturamento Liquido", format="R$ %.2f"),
        "Custo Material": st.column_config.NumberColumn("Custo Material", format="R$ %.2f"),
        "Custo RH Fixo": st.column_config.NumberColumn("Custo RH Fixo", format="R$ %.2f"),
        "Provisao Trabalhista": st.column_config.NumberColumn("Provisao Trabalhista", format="R$ %.2f"),
        "Ajustes RH": st.column_config.NumberColumn("Ajustes RH", format="R$ %.2f"),
        "Custos Sinistros": st.column_config.NumberColumn("Custos Sinistros", format="R$ %.2f"),
        "Lucro Liquido": st.column_config.NumberColumn("Lucro Liquido", format="R$ %.2f"),
        "Margem %": st.column_config.NumberColumn("Margem %", format="%.2f%%"),
        "Nota Satisfacao": st.column_config.NumberColumn("Nota Satisfacao", format="%d"),
    }


def render_dashboard() -> None:
    st.subheader("Dashboard Financeiro e Alertas")
    referencia = st.date_input("Mes de referencia", value=date.today())
    data_inicio, data_fim = get_month_range(referencia)
    st.caption(f"Fechamento de {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}.")
    records = get_dashboard_data(data_inicio, data_fim)

    if not records:
        st.info("Nenhum condominio cadastrado.")
        return

    total_receita = sum(float(row["Faturamento Liquido"]) for row in records)
    total_lucro = sum(float(row["Lucro Liquido"]) for row in records)
    margem_media = (total_lucro / total_receita * 100) if total_receita else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Faturamento liquido", format_brl(total_receita))
    col2.metric("Lucro liquido", format_brl(total_lucro))
    col3.metric("Margem consolidada", f"{margem_media:.2f}%")

    st.dataframe(
        records,
        hide_index=True,
        use_container_width=True,
        column_config=money_column_config(),
    )

    pdf_bytes = gerar_balancete_pdf(data_inicio, data_fim)
    st.download_button(
        "DOWNLOAD DO BALANCETE COMPLETO EM PDF",
        data=pdf_bytes,
        file_name=f"balancete_fortguard_{data_inicio.strftime('%Y_%m')}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

    st.subheader("Colinha da Nota Fiscal")
    condominios = get_condominios()
    if condominios:
        nf_options = select_options(condominios)
        nf_label = st.selectbox("Condominio para gerar colinha", list(nf_options.keys()))
        nf_pdf = gerar_colinha_nota_fiscal_pdf(nf_options[nf_label], data_inicio, data_fim)
        st.download_button(
            "BAIXAR COLINHA DA NOTA FISCAL EM PDF",
            data=nf_pdf,
            file_name=f"colinha_nf_fortguard_{data_inicio.strftime('%Y_%m')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    st.subheader("Alertas Visuais Urgentes")
    alertas = get_alertas_contratos() + get_alertas_aso() + get_alertas_certidoes()
    if not alertas:
        st.success("Nenhum alerta critico no momento.")
    for alerta in alertas:
        st.warning(alerta)


def render_cadastro() -> None:
    condominios = get_condominios()
    funcionarios = get_funcionarios()

    st.subheader("Condominios e Contratos")
    col_new, col_edit = st.columns(2)

    with col_new:
        with st.form("novo_condominio", clear_on_submit=True):
            st.markdown("**Novo condominio**")
            nome = st.text_input("Nome do condominio")
            contato = st.text_input("Contato do sindico")
            valor = st.number_input("Valor mensal do contrato", min_value=0.0, step=100.0)
            aliquota = st.number_input("Aliquota de imposto retido (%)", min_value=0.0, max_value=100.0, step=0.1)
            inicio = st.date_input("Inicio do contrato", value=date.today())
            submitted = st.form_submit_button("Cadastrar condominio", use_container_width=True)
            if submitted:
                if not nome.strip():
                    st.error("Informe o nome do condominio.")
                else:
                    insert_condominio(nome.strip(), contato.strip(), valor, inicio, aliquota)
                    st.success("Condominio cadastrado.")
                    st.rerun()

    with col_edit:
        if condominios:
            options = select_options(condominios)
            selected_label = st.selectbox("Editar condominio", list(options.keys()))
            selected = fetch_one("SELECT * FROM condominios WHERE id = ?", (options[selected_label],))
            if selected:
                with st.form("editar_condominio"):
                    nome = st.text_input("Nome", value=selected["nome"])
                    contato = st.text_input("Contato", value=selected["sindico_contato"] or "")
                    valor = st.number_input(
                        "Valor mensal",
                        min_value=0.0,
                        value=float(selected["valor_contrato_mensal"]),
                        step=100.0,
                    )
                    aliquota = st.number_input(
                        "Aliquota de imposto retido (%)",
                        min_value=0.0,
                        max_value=100.0,
                        value=float(selected["aliquota_imposto_retido"]),
                        step=0.1,
                    )
                    inicio = st.date_input("Data de inicio", value=parse_db_date(selected["data_inicio_contrato"]))
                    submitted = st.form_submit_button("Salvar alteracoes", use_container_width=True)
                    if submitted:
                        update_condominio(selected["id"], nome.strip(), contato.strip(), valor, inicio, aliquota)
                        st.success("Contrato atualizado.")
                        st.rerun()

    st.divider()
    st.subheader("Funcionarios")
    col_new, col_edit = st.columns(2)
    cond_options = optional_condominio_options(condominios)

    with col_new:
        with st.form("novo_funcionario", clear_on_submit=True):
            st.markdown("**Novo funcionario**")
            nome = st.text_input("Nome do funcionario")
            cargo = st.text_input("Cargo")
            salario = st.number_input("Salario base", min_value=0.0, step=100.0)
            cond_label = st.selectbox("Condominio fixo", list(cond_options.keys()))
            aso = st.date_input("Data do ultimo ASO", value=date.today())
            seguro = st.date_input("Vencimento do seguro", value=date.today() + timedelta(days=365))
            status = st.selectbox("Status", STATUS_FUNCIONARIO)
            motivo = st.text_area("Motivo do desligamento", disabled=status == "Ativo")
            submitted = st.form_submit_button("Cadastrar funcionario", use_container_width=True)
            if submitted:
                if not nome.strip() or not cargo.strip():
                    st.error("Informe nome e cargo.")
                else:
                    insert_funcionario(
                        nome.strip(),
                        cargo.strip(),
                        salario,
                        cond_options[cond_label],
                        aso,
                        seguro,
                        status,
                        motivo.strip() if status == "Demitido" else "",
                    )
                    st.success("Funcionario cadastrado.")
                    st.rerun()

    with col_edit:
        if funcionarios:
            func_options = select_options(funcionarios)
            selected_label = st.selectbox("Editar funcionario", list(func_options.keys()))
            selected = fetch_one("SELECT * FROM funcionarios WHERE id = ?", (func_options[selected_label],))
            if selected:
                current_cond = selected["condominio_fixo_id"]
                current_label = next((label for label, cid in cond_options.items() if cid == current_cond), "Sem condominio fixo")
                with st.form("editar_funcionario"):
                    nome = st.text_input("Nome", value=selected["nome"])
                    cargo = st.text_input("Cargo", value=selected["cargo"])
                    salario = st.number_input(
                        "Salario base",
                        min_value=0.0,
                        value=float(selected["salario_base"]),
                        step=100.0,
                    )
                    cond_label = st.selectbox(
                        "Condominio fixo",
                        list(cond_options.keys()),
                        index=list(cond_options.keys()).index(current_label),
                    )
                    aso = st.date_input("Ultimo ASO", value=parse_db_date(selected["data_ultimo_aso"]))
                    seguro_atual = parse_db_date(selected["data_vencimento_seguro"]) or date.today()
                    seguro = st.date_input("Vencimento do seguro", value=seguro_atual)
                    status_atual = selected["status"] if selected["status"] in STATUS_FUNCIONARIO else "Ativo"
                    status = st.selectbox(
                        "Status",
                        STATUS_FUNCIONARIO,
                        index=STATUS_FUNCIONARIO.index(status_atual),
                    )
                    motivo = st.text_area(
                        "Motivo do desligamento",
                        value=selected["motivo_desligamento"] or "",
                        disabled=status == "Ativo",
                    )
                    submitted = st.form_submit_button("Salvar funcionario", use_container_width=True)
                    if submitted:
                        update_funcionario(
                            selected["id"],
                            nome.strip(),
                            cargo.strip(),
                            salario,
                            cond_options[cond_label],
                            aso,
                            seguro,
                            status,
                            motivo.strip() if status == "Demitido" else "",
                        )
                        st.success("Funcionario atualizado.")
                        st.rerun()

    st.divider()
    st.subheader("Equipamentos da Empresa")
    with st.form("novo_equipamento", clear_on_submit=True):
        col1, col2, col3 = st.columns([2, 2, 1])
        nome = col1.text_input("Equipamento")
        cond_label = col2.selectbox("Condominio alocado", list(cond_options.keys()))
        data_envio = col3.date_input("Data de envio", value=date.today())
        submitted = st.form_submit_button("Cadastrar equipamento", use_container_width=True)
        if submitted:
            if not nome.strip():
                st.error("Informe o nome do equipamento.")
            else:
                insert_equipamento(nome.strip(), cond_options[cond_label], data_envio)
                st.success("Equipamento cadastrado.")
                st.rerun()

    equipamentos = get_equipamentos()
    if equipamentos:
        st.dataframe(equipamentos, hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("Certidoes da Empresa")
    certidoes = get_certidoes()
    col_new, col_edit = st.columns(2)
    with col_new:
        with st.form("nova_certidao", clear_on_submit=True):
            st.markdown("**Nova certidao**")
            nome_doc = st.text_input("Nome do documento")
            vencimento = st.date_input("Data de vencimento", value=date.today() + timedelta(days=30))
            submitted = st.form_submit_button("Cadastrar certidao", use_container_width=True)
            if submitted:
                if not nome_doc.strip():
                    st.error("Informe o nome da certidao.")
                else:
                    insert_certidao(nome_doc.strip(), vencimento)
                    st.success("Certidao cadastrada.")
                    st.rerun()

    with col_edit:
        if certidoes:
            cert_options = select_options(certidoes, "nome_documento")
            selected_label = st.selectbox("Editar certidao", list(cert_options.keys()))
            selected = fetch_one("SELECT * FROM certidoes_empresa WHERE id = ?", (cert_options[selected_label],))
            if selected:
                with st.form("editar_certidao"):
                    nome_doc = st.text_input("Documento", value=selected["nome_documento"])
                    vencimento = st.date_input("Vencimento", value=parse_db_date(selected["data_vencimento"]))
                    submitted = st.form_submit_button("Salvar certidao", use_container_width=True)
                    if submitted:
                        if not nome_doc.strip():
                            st.error("Informe o nome da certidao.")
                        else:
                            update_certidao(selected["id"], nome_doc.strip(), vencimento)
                            st.success("Certidao atualizada.")
                            st.rerun()

    if certidoes:
        cert_records = rows_to_records(certidoes)
        st.dataframe(cert_records, hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("Notas de Satisfacao do Sindico")
    cond_options_satisfacao = select_options(condominios) if condominios else {}
    if not cond_options_satisfacao:
        st.info("Cadastre condominios antes de lancar notas de satisfacao.")
    else:
        with st.form("nova_satisfacao", clear_on_submit=True):
            col1, col2, col3 = st.columns([2, 1, 1])
            cond_label = col1.selectbox("Condominio avaliado", list(cond_options_satisfacao.keys()))
            nota = col2.number_input("Nota", min_value=0, max_value=10, value=10, step=1)
            data_avaliacao = col3.date_input("Data da avaliacao", value=date.today())
            observacoes = st.text_area("Observacoes do sindico")
            submitted = st.form_submit_button("Registrar satisfacao", use_container_width=True)
            if submitted:
                insert_satisfacao(
                    cond_options_satisfacao[cond_label],
                    int(nota),
                    data_avaliacao,
                    observacoes.strip(),
                )
                st.success("Nota de satisfacao registrada.")
                st.rerun()

        satisfacoes = get_satisfacoes()
        if satisfacoes:
            st.dataframe(satisfacoes, hide_index=True, use_container_width=True)


def render_estoque() -> None:
    condominios = get_condominios()
    itens = get_catalogo_itens()

    st.subheader("Catalogo de Itens")
    with st.form("novo_item", clear_on_submit=True):
        col1, col2, col3 = st.columns([2, 1, 1])
        nome = col1.text_input("Nome do item")
        unidade = col2.text_input("Unidade de medida", value="unidade")
        minimo = col3.number_input("Estoque minimo", min_value=0.0, step=1.0)
        submitted = st.form_submit_button("Cadastrar item", use_container_width=True)
        if submitted:
            if not nome.strip() or not unidade.strip():
                st.error("Informe o item e a unidade.")
            else:
                try:
                    insert_item(nome.strip(), unidade.strip(), minimo)
                    st.success("Item cadastrado.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Ja existe um item com esse nome.")

    if itens:
        st.subheader("Editar item cadastrado e corrigir quantidade")
        item_options_edit = select_options(itens, "nome_item")
        item_label_edit = st.selectbox("Item para editar", list(item_options_edit.keys()))
        item_id_edit = item_options_edit[item_label_edit]
        selected_item = fetch_one("SELECT * FROM catalogo_itens WHERE id = ?", (item_id_edit,))
        saldo_atual = get_saldo_item(item_id_edit)

        if selected_item:
            with st.form("editar_item_estoque"):
                col1, col2, col3 = st.columns([2, 1, 1])
                nome_edit = col1.text_input("Nome do item", value=selected_item["nome_item"], key="nome_item_edit")
                unidade_edit = col2.text_input("Unidade", value=selected_item["unidade_medida"], key="unidade_item_edit")
                minimo_edit = col3.number_input(
                    "Estoque minimo",
                    min_value=0.0,
                    value=float(selected_item["estoque_minimo_alerta"]),
                    step=1.0,
                    key="minimo_item_edit",
                )

                col4, col5 = st.columns([1, 2])
                saldo_correto = col4.number_input(
                    "Saldo correto",
                    min_value=0.0,
                    value=float(saldo_atual),
                    step=1.0,
                    key="saldo_correto_edit",
                )
                data_ajuste = col5.date_input("Data da correcao", value=date.today(), key="data_ajuste_item")
                motivo = st.text_area(
                    "Motivo da correcao",
                    value="Correcao manual de inventario.",
                    key="motivo_ajuste_item",
                )
                submitted = st.form_submit_button("Salvar edicao e quantidade", use_container_width=True)
                if submitted:
                    if not nome_edit.strip() or not unidade_edit.strip():
                        st.error("Informe nome e unidade.")
                    else:
                        try:
                            update_item(item_id_edit, nome_edit.strip(), unidade_edit.strip(), minimo_edit)
                            diferenca = ajustar_saldo_item(
                                item_id_edit,
                                saldo_correto,
                                data_ajuste,
                                motivo.strip() or "Correcao manual de inventario.",
                            )
                            st.success(f"Item atualizado. Ajuste aplicado: {diferenca:g}.")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Ja existe outro item com esse nome.")

    st.divider()
    col_entrada, col_saida = st.columns(2)
    item_options = select_options(itens, "nome_item") if itens else {}
    cond_options = select_options(condominios) if condominios else {}

    with col_entrada:
        st.subheader("Entrada de Materiais")
        if not item_options:
            st.info("Cadastre itens antes de registrar compras.")
        else:
            with st.form("entrada_materiais", clear_on_submit=True):
                item_label = st.selectbox("Item comprado", list(item_options.keys()))
                quantidade_pacotes = st.number_input("Quantidade de pacotes", min_value=0.01, step=1.0)
                unidades_por_pacote = st.number_input("Unidades por pacote", min_value=0.01, step=1.0)
                valor_total = st.number_input("Valor total pago", min_value=0.0, step=10.0)
                data_compra = st.date_input("Data da compra", value=date.today())
                submitted = st.form_submit_button("Registrar entrada", use_container_width=True)
                if submitted:
                    insert_entrada(
                        item_options[item_label],
                        quantidade_pacotes,
                        unidades_por_pacote,
                        valor_total,
                        data_compra,
                    )
                    total_unidades = quantidade_pacotes * unidades_por_pacote
                    st.success(f"Entrada registrada com {total_unidades:g} unidades individuais.")
                    st.rerun()

    with col_saida:
        st.subheader("Saida para Condominio")
        if not item_options or not cond_options:
            st.info("Cadastre condominios e itens antes de registrar saidas.")
        else:
            with st.form("saida_materiais", clear_on_submit=True):
                cond_label = st.selectbox("Condominio destino", list(cond_options.keys()))
                item_label = st.selectbox("Item enviado", list(item_options.keys()))
                quantidade = st.number_input("Unidades enviadas", min_value=0.01, step=1.0)
                data_envio = st.date_input("Data do envio", value=date.today())
                submitted = st.form_submit_button("Registrar saida", use_container_width=True)
                if submitted:
                    try:
                        custo = insert_saida(cond_options[cond_label], item_options[item_label], quantidade, data_envio)
                        st.success(f"Saida registrada com custo unitario aplicado de {format_brl(custo)}.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))

    st.divider()
    st.subheader("Saldo Atual do Estoque Central")
    saldo = get_saldo_estoque()
    if not saldo:
        st.info("Nenhum item cadastrado.")
        return

    baixo = [row for row in saldo if row["Saldo"] < row["Minimo"]]
    for row in baixo:
        st.warning(f"{row['Item']} abaixo do minimo. Saldo: {row['Saldo']:g} {row['Unidade']}. Minimo: {row['Minimo']:g}.")

    saldo_visivel = [{key: value for key, value in row.items() if key != "id"} for row in saldo]
    st.dataframe(
        saldo_visivel,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Minimo": st.column_config.NumberColumn("Minimo", format="%.2f"),
            "Entradas_Unidades": st.column_config.NumberColumn("Entradas_Unidades", format="%.2f"),
            "Saidas": st.column_config.NumberColumn("Saidas", format="%.2f"),
            "Ajustes": st.column_config.NumberColumn("Ajustes", format="%.2f"),
            "Saldo": st.column_config.NumberColumn("Saldo", format="%.2f"),
        },
    )


def render_escala() -> None:
    funcionarios = get_funcionarios()
    condominios = get_condominios()

    st.subheader("Escala de Trabalho")
    if not funcionarios:
        st.info("Cadastre funcionarios antes de montar a escala.")
        return

    cond_options = optional_condominio_options(condominios)
    func_options = select_options(funcionarios)

    col_gerar, col_manual = st.columns(2)

    with col_gerar:
        st.markdown("**Gerar escala dos funcionarios fixos**")
        with st.form("gerar_escala_fixa"):
            hoje = date.today()
            inicio_padrao, fim_padrao = get_month_range(hoje)
            data_inicio = st.date_input("Inicio do periodo", value=inicio_padrao, key="escala_inicio_auto")
            data_fim = st.date_input("Fim do periodo", value=fim_padrao, key="escala_fim_auto")
            dias_labels = st.multiselect(
                "Dias de trabalho",
                list(DIAS_SEMANA.keys()),
                default=["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado"],
            )
            turno = st.selectbox("Turno", TURNOS_ESCALA, key="turno_auto")
            col1, col2 = st.columns(2)
            hora_inicio = col1.text_input("Entrada", value="08:00", key="entrada_auto")
            hora_fim = col2.text_input("Saida", value="17:00", key="saida_auto")
            posto = st.text_input("Posto", value="Posto fixo")
            sobrescrever = st.checkbox("Substituir escalas ja existentes dos mesmos dias")
            submitted = st.form_submit_button("Gerar escala", use_container_width=True)
            if submitted:
                if data_fim < data_inicio:
                    st.error("A data final nao pode ser anterior a data inicial.")
                elif not dias_labels:
                    st.error("Selecione pelo menos um dia da semana.")
                else:
                    total = gerar_escala_funcionarios_fixos(
                        data_inicio,
                        data_fim,
                        {DIAS_SEMANA[dia] for dia in dias_labels},
                        turno,
                        hora_inicio.strip(),
                        hora_fim.strip(),
                        posto.strip(),
                        sobrescrever,
                    )
                    st.success(f"Escala gerada com {total} lancamentos.")
                    st.rerun()

    with col_manual:
        st.markdown("**Lancamento manual ou cobertura**")
        with st.form("escala_manual", clear_on_submit=True):
            funcionario_label = st.selectbox("Funcionario", list(func_options.keys()))
            condominio_label = st.selectbox("Condominio", list(cond_options.keys()))
            data_escala = st.date_input("Data", value=date.today(), key="data_escala_manual")
            turno = st.selectbox("Turno", TURNOS_ESCALA, key="turno_manual")
            col1, col2 = st.columns(2)
            hora_inicio = col1.text_input("Entrada", value="08:00", key="entrada_manual")
            hora_fim = col2.text_input("Saida", value="17:00", key="saida_manual")
            posto = st.text_input("Posto / funcao no dia", value="")
            observacao = st.text_area("Observacao")
            submitted = st.form_submit_button("Salvar lancamento", use_container_width=True)
            if submitted:
                condominio_id = cond_options[condominio_label]
                if turno != "Folga" and condominio_id is None:
                    st.error("Para trabalho/cobertura, selecione um condominio.")
                elif not hora_inicio.strip() or not hora_fim.strip():
                    st.error("Informe entrada e saida.")
                else:
                    insert_escala_trabalho(
                        func_options[funcionario_label],
                        condominio_id,
                        data_escala,
                        turno,
                        hora_inicio.strip(),
                        hora_fim.strip(),
                        posto.strip(),
                        observacao.strip(),
                    )
                    st.success("Lancamento salvo na escala.")
                    st.rerun()

    st.divider()
    st.subheader("Consultar Escala")
    filtro_col1, filtro_col2, filtro_col3 = st.columns([1, 1, 2])
    inicio = filtro_col1.date_input("De", value=date.today(), key="escala_inicio_consulta")
    fim = filtro_col2.date_input("Ate", value=date.today() + timedelta(days=14), key="escala_fim_consulta")
    filtro_options: dict[str, int | None] = {"Todos os condominios": None}
    filtro_options.update(select_options(condominios))
    filtro_label = filtro_col3.selectbox("Filtrar por condominio", list(filtro_options.keys()))

    if fim < inicio:
        st.error("A data final nao pode ser anterior a data inicial.")
        return

    escala = get_escala_trabalho(inicio, fim, filtro_options[filtro_label])
    if not escala:
        st.info("Nenhuma escala encontrada para o periodo.")
        return

    st.dataframe(escala, hide_index=True, use_container_width=True)
    st.download_button(
        "Baixar escala em CSV",
        data=records_to_csv(escala),
        file_name=f"escala_fortguard_{inicio.isoformat()}_{fim.isoformat()}.csv",
        mime="text/csv",
        use_container_width=True,
    )


def render_rh() -> None:
    funcionarios = get_funcionarios()
    condominios = get_condominios()

    st.subheader("Diario de Bordo do RH e Sinistros")
    if not funcionarios or not condominios:
        st.info("Cadastre funcionarios e condominios antes de lancar ocorrencias.")
        return

    func_options = select_options(funcionarios)
    cond_options = select_options(condominios)

    with st.form("nova_ocorrencia", clear_on_submit=True):
        col1, col2 = st.columns(2)
        funcionario_label = col1.selectbox("Funcionario", list(func_options.keys()))
        condominio_label = col2.selectbox("Condominio afetado", list(cond_options.keys()))
        col3, col4 = st.columns(2)
        tipo = col3.selectbox("Tipo de ocorrencia", TIPOS_OCORRENCIA)
        valor = col4.number_input(
            "Valor do ajuste",
            value=0.0,
            step=10.0,
            help="Use positivo para extras/creditos e negativo para faltas/vales.",
        )
        data_ocorrencia = st.date_input("Data da ocorrencia", value=date.today())
        observacao = st.text_area("Observacao")
        submitted = st.form_submit_button("Lancar ocorrencia", use_container_width=True)
        if submitted:
            insert_rh_ocorrencia(
                func_options[funcionario_label],
                cond_options[condominio_label],
                tipo,
                valor,
                data_ocorrencia,
                observacao.strip(),
            )
            st.success("Ocorrencia lancada.")
            st.rerun()

    st.subheader("Historico Recente")
    historico = get_historico_ocorrencias()
    if not historico:
        st.info("Nenhuma ocorrencia lancada.")
    else:
        st.dataframe(
            historico,
            hide_index=True,
            use_container_width=True,
            column_config={"Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")},
        )
        delete_options = {
            f"ID {row['ID']} - {row['Data']} - {row['Funcionario']} - {row['Tipo']} - {format_brl(float(row['Valor']))}": row["ID"]
            for row in historico
        }
        with st.form("excluir_ocorrencia_rh"):
            st.markdown("**Excluir lancamento de RH**")
            selected_delete = st.selectbox("Lancamento para excluir", list(delete_options.keys()))
            confirmar = st.checkbox("Confirmo que quero excluir este lancamento")
            submitted_delete = st.form_submit_button("Excluir lancamento selecionado", use_container_width=True)
            if submitted_delete:
                if not confirmar:
                    st.error("Marque a confirmacao antes de excluir.")
                else:
                    delete_rh_ocorrencia(delete_options[selected_delete])
                    st.success("Lancamento excluido.")
                    st.rerun()

    st.divider()
    st.subheader("Sinistros e Danos Materiais")
    funcionario_options_sinistro: dict[str, int | None] = {"Nao informado": None}
    funcionario_options_sinistro.update(func_options)
    with st.form("novo_sinistro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        condominio_label = col1.selectbox("Condominio do sinistro", list(cond_options.keys()))
        funcionario_label = col2.selectbox("Funcionario envolvido", list(funcionario_options_sinistro.keys()))
        descricao = st.text_area("Descricao do dano")
        col3, col4 = st.columns(2)
        custo = col3.number_input("Custo do reparo", min_value=0.0, step=50.0)
        data_sinistro = col4.date_input("Data do sinistro", value=date.today())
        submitted = st.form_submit_button("Registrar sinistro", use_container_width=True)
        if submitted:
            if not descricao.strip():
                st.error("Informe a descricao do dano.")
            else:
                insert_sinistro(
                    cond_options[condominio_label],
                    funcionario_options_sinistro[funcionario_label],
                    descricao.strip(),
                    custo,
                    data_sinistro,
                )
                st.success("Sinistro registrado.")
                st.rerun()

    historico_sinistros = get_historico_sinistros()
    if historico_sinistros:
        st.dataframe(
            historico_sinistros,
            hide_index=True,
            use_container_width=True,
            column_config={"Custo": st.column_config.NumberColumn("Custo", format="R$ %.2f")},
        )


def render_backup() -> None:
    st.subheader("Backup dos Dados")
    st.info("Os backups guardam uma copia completa do banco de dados local do FortGuard.")

    backups = list_backups()
    col1, col2, col3 = st.columns(3)
    col1.metric("Backups salvos", str(len(backups)))
    if DB_PATH.exists():
        col2.metric("Banco atual", f"{DB_PATH.stat().st_size / 1024:.1f} KB")
    if backups:
        ultimo = datetime.fromtimestamp(backups[0].stat().st_mtime).strftime("%d/%m/%Y %H:%M")
        col3.metric("Ultimo backup", ultimo)
    else:
        col3.metric("Ultimo backup", "Nenhum")

    if st.button("Criar backup agora", use_container_width=True):
        backup_path = create_backup("manual")
        st.success(f"Backup criado: {backup_path.name}")
        st.rerun()

    backups = list_backups()
    if not backups:
        st.warning("Ainda nao existe backup salvo. Clique em Criar backup agora.")
        return

    st.subheader("Baixar backup")
    download_options = {backup_label(path): path for path in backups}
    selected_download = st.selectbox("Backup para baixar", list(download_options.keys()), key="backup_download")
    selected_download_path = download_options[selected_download]
    st.download_button(
        "Baixar arquivo de backup",
        data=selected_download_path.read_bytes(),
        file_name=selected_download_path.name,
        mime="application/octet-stream",
        use_container_width=True,
    )

    st.divider()
    st.subheader("Restaurar backup")
    st.warning("Restaurar troca os dados atuais pelos dados do backup selecionado.")
    restore_options = {backup_label(path): path for path in backups}
    selected_restore = st.selectbox("Backup para restaurar", list(restore_options.keys()), key="backup_restore")
    with st.form("restaurar_backup"):
        confirmar = st.checkbox("Confirmo que quero substituir os dados atuais por este backup")
        submitted = st.form_submit_button("Restaurar backup selecionado", use_container_width=True)
        if submitted:
            if not confirmar:
                st.error("Marque a confirmacao antes de restaurar.")
            else:
                try:
                    emergency_backup = restore_backup(restore_options[selected_restore])
                    st.success(
                        "Backup restaurado. "
                        f"Antes da restauracao, salvei uma copia de seguranca: {emergency_backup.name}"
                    )
                    st.rerun()
                except (OSError, ValueError, sqlite3.Error) as exc:
                    st.error(f"Nao foi possivel restaurar o backup: {exc}")


def main() -> None:
    global st
    import streamlit as streamlit

    st = streamlit
    st.set_page_config(
        page_title="FortGuard",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    init_db()

    st.title("FortGuard")
    st.caption("Sistema interno FortGuard")

    tab_dashboard, tab_cadastro, tab_escala, tab_estoque, tab_rh, tab_backup = st.tabs(
        [
            "Dashboard Financeiro e Alertas",
            "Cadastro, Contratos e Certidoes",
            "Escala de Trabalho",
            "Estoque Item por Item",
            "Diario de Bordo do RH e Sinistros",
            "Backup",
        ]
    )

    with tab_dashboard:
        render_dashboard()
    with tab_cadastro:
        render_cadastro()
    with tab_escala:
        render_escala()
    with tab_estoque:
        render_estoque()
    with tab_rh:
        render_rh()
    with tab_backup:
        render_backup()


if __name__ == "__main__":
    main()
