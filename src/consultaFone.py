from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
import cx_Oracle
import uuid

from src import get_connection

consultaFone = APIRouter(prefix="/globus")


@consultaFone.get("/fonefunc/{fonefunc}")
def function(fonefunc: str):
    try:
        conn = get_connection()

        cursor = conn.cursor()

        query = f"""
              SELECT 
                  f.chapafunc AS CHAPA,
                  f.nomecompletofunc AS NOME_FUNC,
                  f.descfuncaocompleta AS FUNCAO,
                  f.descdepto AS DEPTO,
                  f.fonefunc AS CONTATO,
                  TO_CHAR(CAST(f.dtadmfunc AS TIMESTAMP), 'YYYY-MM-DD"T"HH24:MI:SS.FF3"Z"') AS ADMISSAO
              FROM VW_FUNCIONARIOS f
              WHERE f.fonefunc like :fonefunc
              AND SITUACAOFUNC = 'A'
            """

        cursor.execute(query, {"fonefunc": f"%{fonefunc}"})

        column = [description[0].lower() for description in cursor.description]
        result = cursor.fetchall()

        if not result:
            raise ValueError("Telefone não encontrado para o número: " f"{fonefunc}")

        data = list()
        for dt in result:
            data.append(
                {
                    "id": uuid.uuid4().hex,
                    column[0]: dt[0],
                    column[1]: dt[1],
                    column[2]: dt[2],
                    column[3]: dt[3],
                    column[4]: dt[4],
                    column[5]: dt[5],  # DATE TO_CHAR as string
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
