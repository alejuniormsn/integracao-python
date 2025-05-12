from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from datetime import datetime
import cx_Oracle
import uuid

from src import get_connection
from src.utils import serialize_datetime

saidaRecolhida = APIRouter(prefix="/globus")

@saidaRecolhida.get("/saida-recolhida/{DTSAIDA}/{PREFIXOVEIC}")
def function(DTSAIDA: str, PREFIXOVEIC: str):
    try:
        conn = get_connection()

        cursor = conn.cursor()

        query = f"""
            SELECT DTSAIDA, C.PREFIXOVEIC, F.NOMEFUNC, F.CHAPAFUNC, F.DESCFUNCAO, L.NROFICIALLINHA, s.horasaidagaragem ,S.HORARECOLHIDA FROM PLT_SAIDARECOLHIDA S
            INNER JOIN FRT_CADVEICULOS C ON S.CODIGOVEIC=C.CODIGOVEIC
            INNER JOIN vw_funcionarios F ON F.CODINTFUNC=S.CODINTMOT OR F.CODINTFUNC=S.CODINTCOB
            INNER JOIN BGM_CADLINHAS L ON L.CODINTLINHA = S.CODINTLINHA
            WHERE DTSAIDA=TO_DATE(:DTSAIDA, 'YYYY/MM/DD') AND C.PREFIXOVEIC LIKE :PREFIXOVEIC ORDER BY s.horasaidagaragem
        """

        cursor.execute(
            query, {"DTSAIDA": f"{DTSAIDA}", "PREFIXOVEIC": f"%{PREFIXOVEIC}"}
        )

        column = [description[0].lower() for description in cursor.description]
        result = cursor.fetchall()

        if not result:
            raise ValueError(f"Veículo {PREFIXOVEIC} não encontrado")

        data = list()
        for dt in result:
            data.append(
                {
                    "id": uuid.uuid4().hex,
                    column[0]: serialize_datetime(dt[0]),
                    column[1]: dt[1],
                    column[2]: dt[2],
                    column[3]: dt[3],
                    column[4]: dt[4],
                    column[5]: dt[5],
                    column[6]: serialize_datetime(dt[6]),
                    column[7]: serialize_datetime(dt[7]),
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
        cursor.close()
        conn.close()
