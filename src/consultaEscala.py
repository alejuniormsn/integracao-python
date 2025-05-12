from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from datetime import datetime
import cx_Oracle
import uuid

from src import get_connection
from src.utils import serialize_datetime

consultaEscala = APIRouter(prefix="/globus")

@consultaEscala.get("/consulta-escala/{chapafunc}")
def function(chapafunc: str):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Primeira consulta (escala de 03 dias)
        query1 = f"""
            SELECT TRUNC(S.DAT_ESCALA) AS DATA, V.PREFIXOVEIC AS VEICULO, S.DESCLOCMOT AS LOCAL,
                S.NOMELINHA AS LINHA, S.HOR_INICIO_SERVICO AS INICIO, S.HOR_FIM_SERVICO AS FIM
            FROM VW_SERVICOS_FUNCIONARIOS S
            LEFT JOIN FRT_CADVEICULOS V ON S.COD_VEIC = V.CODIGOVEIC
            LEFT JOIN FLP_FUNCIONARIOS F ON S.COD_MOTORISTA = F.CODINTFUNC OR S.COD_COBRADOR = F.CODINTFUNC
            WHERE F.CHAPAFUNC LIKE :chapafunc
            AND S.DAT_ESCALA BETWEEN SYSDATE - 1
            AND SYSDATE + 3
            ORDER BY S.HOR_INICIO_SERVICO
        """
        cursor.execute(query1, {"chapafunc": f"%{chapafunc}"})
        columns1 = [description[0].lower() for description in cursor.description]
        result1 = cursor.fetchall()

        data1 = []
        for dt in result1:
            data1.append(
                {
                    "id": uuid.uuid4().hex,
                    columns1[0]: serialize_datetime(dt[0]),
                    columns1[1]: dt[1],
                    columns1[2]: dt[2],
                    columns1[3]: dt[3],
                    columns1[4]: serialize_datetime(dt[4]),
                    columns1[5]: serialize_datetime(dt[5]),
                }
            )

        if not data1:
            raise ValueError("Escala não encontrada para a chapa "f"{chapafunc}")

        # Segunda consulta (saldo da arrecadação)
        query2 = f"""
            SELECT S.CHAPAFUNC, S.CREDITO - S.DEBITO AS SALDO
            FROM (SELECT f.chapafunc, SUM(CASE WHEN l.flg_tipolanc = 'D' THEN l.vlr_documento ELSE 0 END) AS debito,
            SUM(CASE WHEN l.flg_tipolanc = 'C' THEN l.vlr_documento ELSE 0 END) AS credito
            FROM t_arr_lanc_func l
            LEFT JOIN flp_funcionarios f ON l.cod_funcionario = f.codintfunc
            GROUP BY f.chapafunc) S WHERE S.CREDITO - S.DEBITO <> 0
            AND S.CHAPAFUNC LIKE :chapafunc
        """
        cursor.execute(query2, {"chapafunc": f"%{chapafunc}"})
        columns2 = [description[0].lower() for description in cursor.description]
        result2 = cursor.fetchall()

        data2 = []
        for dt in result2:
            data2.append(
                {
                    columns2[0]: dt[0],
                    columns2[1]: dt[1],
                }
            )

        # Terceira consulta (folga provisionada)
        query3 = f"""
            SELECT F.CHAPAFUNC, TO_CHAR(V.DATA, 'DD/MM/YYYY') as FOLGA
            FROM VW_FOLGAS V LEFT JOIN FLP_FUNCIONARIOS F ON V.COD_FUNC = F.CODINTFUNC
            WHERE F.CHAPAFUNC LIKE :chapafunc
            AND V.DATA BETWEEN SYSDATE
            AND SYSDATE + 30 ORDER BY V.DATA
        """
        cursor.execute(query3, {"chapafunc": f"%{chapafunc}"})
        columns3 = [description[0].lower() for description in cursor.description]
        result3 = cursor.fetchall()

        data3 = []
        for dt in result3:
            data3.append(
                {
                    "id": uuid.uuid4().hex,
                    columns3[0]: dt[0],
                    columns3[1]: serialize_datetime(dt[1]),
                }
            )

        # Quarta consulta (dados do user)
        query4 = f"""
                    SELECT CHAPAFUNC, DESCFUNCAO, NOMEFUNC FROM VW_FUNCIONARIOS WHERE CHAPAFUNC LIKE :chapafunc
                  """
        cursor.execute(query4, {"chapafunc": f"%{chapafunc}"})
        columns4 = [description[0].lower() for description in cursor.description]
        result4 = cursor.fetchall()

        data4 = []
        for dt in result4:
            data4.append(
                {
                    columns4[0]: dt[0],
                    columns4[1]: dt[1],
                    columns4[2]: dt[2],
                }
            )

        # Combina os resultados
        combined_data = {
            "escala": data1,
            "rel24d": data2,
            "folgas": data3,
            "usuario": data4,
        }

        return JSONResponse(content=combined_data, status_code=status.HTTP_200_OK)

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
