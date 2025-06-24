import os
from pathlib import Path
from typing import List, Optional

from sqlalchemy.engine import Engine
from sqlmodel import Field, SQLModel, Session, create_engine, select


class PluginConfig(SQLModel, table=True):
    """Persistent configuration for loaded plugins."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, sa_column_kwargs={"unique": True})


def _default_db_url() -> str:
    path = Path.home() / ".cache" / "moogla" / "plugins.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path}"


def _resolve_engine(engine: Optional[Engine] = None) -> Engine:
    if engine is not None:
        SQLModel.metadata.create_all(engine)
        return engine
    db_url = os.getenv("MOOGLA_DB_URL")
    engine = create_engine(db_url or _default_db_url())
    SQLModel.metadata.create_all(engine)
    return engine


def get_plugins(engine: Optional[Engine] = None) -> List[str]:
    eng = _resolve_engine(engine)
    with Session(eng) as session:
        rows = session.exec(select(PluginConfig).order_by(PluginConfig.id)).all()
        return [row.name for row in rows]


def add_plugin(name: str, engine: Optional[Engine] = None) -> None:
    eng = _resolve_engine(engine)
    with Session(eng) as session:
        existing = session.exec(select(PluginConfig).where(PluginConfig.name == name)).first()
        if not existing:
            session.add(PluginConfig(name=name))
            session.commit()


def remove_plugin(name: str, engine: Optional[Engine] = None) -> None:
    eng = _resolve_engine(engine)
    with Session(eng) as session:
        entry = session.exec(select(PluginConfig).where(PluginConfig.name == name)).first()
        if entry:
            session.delete(entry)
            session.commit()
