from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from rest_api.deps.db import get_session
from simovel.db.models import CidadeModel


app = FastAPI(
    title="Simóvel API",
    version="1.0.0"
)


@app.get("/health")
def healthcheck():
    return { "status": "ok"}


@app.get("/uf/{uf}/cidades")
def obter_cidades_por_uf(
    uf: str,
    session: Session = Depends(get_session),
):
    """
    Obtem todas as cidades de uma determinada UF.
    """
    cidades: list[CidadeModel] = CidadeModel.obter_cidades_por_uf(
        session,
        uf
    )

    return CidadeModel.cidades_to_list(cidades)
