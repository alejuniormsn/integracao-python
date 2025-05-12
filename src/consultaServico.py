from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from datetime import datetime
import cx_Oracle

from src import get_connection
from src.utils import serialize_datetime

consultaServico = APIRouter(prefix="/globus")

@consultaServico.get("/consulta-servico/{chapa}/{turno}")
def function(chapa: str, turno: int):
    try:
        conn = get_connection()

        cursor = conn.cursor()

        params = {
            "chapa": f"%{chapa}",
            "turno": turno,
        }

        query = f"""
            SELECT 
                S.HORASAIDAGARAGEM AS hora_partida,
                S.HORARECOLHIDA AS hora_retorno,
                V.PREFIXOVEIC AS veiculo,
                L.CODIGOLINHA AS linha,
                S.ODOMETROINIC AS odometro_inicial,
                S.ODOMETROFIN AS odometro_final,
                S.ROLETAINIC AS catraca_inicial,
                S.ROLETAFIN AS catraca_final,
                S.USUARIOCHEGADA AS usuario,
                S.DTUSUCHEGADA AS data_baixa,
                S.CODIGO_DA_GUIA AS codigo_guia
            FROM PLT_SAIDARECOLHIDA S
            INNER JOIN FRT_CADVEICULOS V ON S.CODIGOVEIC = V.CODIGOVEIC
            INNER JOIN BGM_CADLINHAS L ON S.CODINTLINHA = L.CODINTLINHA
            WHERE S.HORASAIDAGARAGEM = (
            SELECT MAX(P1.HORASAIDAGARAGEM)
            FROM PLT_SAIDARECOLHIDA P1
            INNER JOIN FLP_FUNCIONARIOS F1 ON P1.CODINTMOT = F1.CODINTFUNC
            WHERE F1.CHAPAFUNC LIKE :chapa AND F1.SITUACAOFUNC = 'A'
            )
            AND S.COD_INTTURNO = :turno
            AND S.CODOCORRPLTSAIDA != 6
            AND EXISTS (
            SELECT 1
            FROM FLP_FUNCIONARIOS F
            WHERE (F.CODINTFUNC = S.CODINTMOT OR F.CODINTFUNC = S.CODINTCOB)
            AND F.CHAPAFUNC LIKE :chapa
            AND F.SITUACAOFUNC = 'A'
            )
            ORDER BY S.HORASAIDAGARAGEM
        """

        cursor.execute(query, params)

        column = [description[0].lower() for description in cursor.description]
        result = cursor.fetchall()

        if not result:
            raise ValueError(
                f"Nenhum registro encontrado para esta chapa {chapa} neste turno. Fale com o PLANTÃO."
            )

        dt = result[0]
        data = {
            column[0]: serialize_datetime(dt[0]),
            column[1]: serialize_datetime(dt[1]),
            column[2]: dt[2],
            column[3]: dt[3],
            column[4]: dt[4],
            column[5]: dt[5],
            column[6]: dt[6],
            column[7]: dt[7],
            column[8]: dt[8],
            column[9]: serialize_datetime(dt[9]),
            column[10]: dt[10],
        }

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
