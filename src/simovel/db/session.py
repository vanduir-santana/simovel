"""
Módulo de sessão indepedente.

Com esse módulo é possível, por exemplo, usar o SQLAlchemy
desacoplado do Flask. Parte do processo para facilitar e simplificar
futuras migrações (exemplo Flask pra FastAPI).
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from simovel.config.geral import Parametros


engine = create_engine(
    Parametros.DATABASE_URI,
    echo=False,
    future=True
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    expire_on_commit=False,
)

@event.listens_for(engine, "connect")
def enable_fk(dbapi_connection, connection_record):
    print('Habilitando foreign_keys para SQLite via Sessão Local...')
    dbapi_connection.execute("PRAGMA foreign_keys=ON")
