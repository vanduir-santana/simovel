from typing import Generator

from sqlalchemy.orm.session import Session

from simovel.db.session import SessionLocal


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
