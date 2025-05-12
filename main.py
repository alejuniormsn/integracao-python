from fastapi import FastAPI
import uvicorn
from src.saidaRecolhida import saidaRecolhida
from src.consultaUserByChapa import consultaUserByChapa
from src.consultaEscala import consultaEscala
from src.consultaNascimento import consultaNascimento
from src.consultaUser import consultaUser
from src.consultaFone import consultaFone
from src.controleServico import controleServico
from src.consultaServico import consultaServico

app = FastAPI()


@app.get("/globus/check")
def function():
    return "{ status: HTTP_200_OK }"


app.include_router(consultaUserByChapa)
app.include_router(consultaFone)
app.include_router(saidaRecolhida)
app.include_router(consultaEscala)
app.include_router(consultaNascimento)
app.include_router(consultaUser)
app.include_router(controleServico)
app.include_router(consultaServico)

if __name__ == "__main__":
    uvicorn.run(app=app, host="192.168.0.21", port=8000)
