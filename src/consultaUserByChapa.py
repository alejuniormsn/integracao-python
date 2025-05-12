from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
import cx_Oracle
import uuid

from src import get_connection

consultaUserByChapa = APIRouter(prefix="/globus")


@consultaUserByChapa.get("/chapafunc/{chapafunc}")
def function(chapafunc: str):
    try:
        conn = get_connection()

        cursor = conn.cursor()

        query = f"""
              SELECT f.chapafunc CHAPA, f.nomecompletofunc NOME_FUNC, J.nomedepen NOME_MAE, f.fonefunc TELEFONE, sub3.nrdocto CPF, f.emailfunc EMAIL, TO_CHAR(f.dtnasctofunc, 'DD/MM/YYYY') NASCIMENTO
                FROM (SELECT d.nomedepen, D.CODINTFUNC FROM flp_dependentes d WHERE D.codparen ='7')J
                RIGHT JOIN (SELECT P.CODINTFUNC FROM FLP_FUNCIONARIOS P WHERE P.SITUACAOFUNC IN('A','F'))K ON J.CODINTFUNC= K.CODINTFUNC
                INNER JOIN vw_funcionarios f ON K.CODINTFUNC = f.CODINTFUNC
                INNER JOIN (select nrdocto, codintfunc from flp_documentos where tipodocto ='CPF') sub3 ON sub3.codintfunc = f.CODINTFUNC
                WHERE f.chapafunc like :chapafunc and SITUACAOFUNC = 'A'
             """

        cursor.execute(query, {"chapafunc": f"%{chapafunc}"})

        column = [description[0].lower() for description in cursor.description]
        result = cursor.fetchall()

        if not result:
            raise ValueError("Usuário não encontrado para a chapa " f"{chapafunc}")

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
                    column[5]: dt[5],
                    column[6]: dt[6],  # DATE TO_CHAR as string
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
