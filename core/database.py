"""
Persistência SQLite via SQLAlchemy — histórico de leituras e infrações.

O arquivo tacografos.db é criado automaticamente na raiz do projeto.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, create_engine, inspect, text
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)

# Banco local na raiz do projeto (ex.: E:\CRONOTACOGRAFOS\tacografos.db)
RAIZ_PROJETO = Path(__file__).resolve().parent.parent
CAMINHO_DB = RAIZ_PROJETO / "tacografos.db"
DATABASE_URL = f"sqlite:///{CAMINHO_DB.as_posix()}"

# check_same_thread=False permite usar a conexão com FastAPI (threads do Uvicorn)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base declarativa dos models SQLAlchemy."""


class LeituraViagem(Base):
    """Registro de uma leitura processada (uma viagem / um disco)."""

    __tablename__ = "leituras_viagem"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    placa_veiculo: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    data_processamento: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
    )
    distancia_total_km: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # "zigue_zague" (contagem dos traços, 5 km cada) ou "velocidade" (integração da curva)
    distancia_metodo: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    velocidade_maxima: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    velocidade_media: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Imagem desdobrada desta viagem (em temp/), usada no laudo e no detalhe
    caminho_imagem: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    # Qualidade da leitura: nota de alinhamento dos anéis (>= 2 confiável) e avisos (JSON)
    nota_aneis: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avisos_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relação 1:N — uma viagem possui várias infrações
    infracoes: Mapped[list["Infracao"]] = relationship(
        "Infracao",
        back_populates="viagem",
        cascade="all, delete-orphan",
    )


class Infracao(Base):
    """Infração/alerta detectado e associado a uma LeituraViagem."""

    __tablename__ = "infracoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    viagem_id: Mapped[int] = mapped_column(
        ForeignKey("leituras_viagem.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo_infracao: Mapped[str] = mapped_column(String(64), nullable=False)
    hora_inicio: Mapped[str] = mapped_column(String(8), nullable=False)
    hora_fim: Mapped[str] = mapped_column(String(8), nullable=False)
    # Excesso: velocidade máxima do evento | Parada: 0.0
    velocidade_registrada: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    viagem: Mapped["LeituraViagem"] = relationship(
        "LeituraViagem",
        back_populates="infracoes",
    )


def get_db() -> Generator[Session, None, None]:
    """
    Dependency do FastAPI: abre uma sessão por requisição e fecha ao final.

    Uso:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def criar_tabelas() -> None:
    """Cria as tabelas no SQLite e acrescenta colunas novas em bancos antigos."""
    Base.metadata.create_all(bind=engine)
    _migrar_colunas_novas()


def _migrar_colunas_novas() -> None:
    """
    create_all() não altera tabelas que já existem; aqui adicionamos (vazias)
    as colunas criadas depois, para quem já tem um tacografos.db com histórico.
    """
    existentes = {c["name"] for c in inspect(engine).get_columns(LeituraViagem.__tablename__)}
    with engine.begin() as conexao:
        for coluna in LeituraViagem.__table__.columns:
            if coluna.name not in existentes:
                tipo = coluna.type.compile(dialect=engine.dialect)
                conexao.execute(
                    text(f"ALTER TABLE {LeituraViagem.__tablename__} ADD COLUMN {coluna.name} {tipo}")
                )
