from typing import Union
from sqlalchemy.orm import Session
from sqlalchemy.orm.scoping import scoped_session


SessionType = Union[Session, scoped_session]


# implementar da forma abaixo no futuro (fica mais desacoplado)
# a ideia é a camada de dados ficar completamente desacoplada do DB

# from typing import Protocol, runtime_checkable
#
# @runtime_checkable
# class SessionType(Protocol):
#     def query(self, *args, **kwargs): ...
#     def add(self, obj): ...
#     def commit(self): ...
#     def rollback(self): ...
