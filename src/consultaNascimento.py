from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from datetime import datetime
import cx_Oracle
import uuid

from src import get_connection
from src.utils import serialize_datetime

consultaNascimento = APIRouter(prefix="/globus")

@consultaNascimento.get("/consulta-nascimento/{chapafunc}")
def function(chapafunc: str):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        query = f"""
                  SELECT chapafunc CHAPA, nomecompletofunc NOME, TO_CHAR(dtnasctofunc, 'DD/MM/YYYY') NASCIMENTO FROM FLP_FUNCIONARIOS
                    WHERE chapafunc like :chapafunc AND SITUACAOFUNC = 'A'
                """
        cursor.execute(query, {"chapafunc": f"%{chapafunc}"})
        columns1 = [description[0].lower() for description in cursor.description]
        result = cursor.fetchall()

        if not result:
            raise ValueError("Não encontrado para a chapa: " f"{chapafunc}")

        data = []
        for dt in result:
            data.append(
                {
                    "id": uuid.uuid4().hex,
                    columns1[0]: dt[0],
                    columns1[1]: dt[1],
                    columns1[2]: serialize_datetime(dt[2]),
                }
            )
        return JSONResponse(content=data, status_code=status.HTTP_200_OK)

    except cx_Oracle.DatabaseError as e:
        return JSONResponse(
            content={"status": 500, "message": f"Erro no banco de dados: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except ValueError as e:
        return JSONResponse(
            content={"status": 404, "message": str(e)},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return JSONResponse(
            content={"status": 400, "message": f"Erro na requisição: {str(e)}"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
