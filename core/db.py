from sqlmodel import SQLModel, Session, create_engine

from core.config import get_settings

_url = get_settings().database_url

if _url.startswith("sqlite"):
    engine = create_engine(_url, echo=False, connect_args={"check_same_thread": False})
else:
    engine = create_engine(_url, echo=False)


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session