from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime
import cx_Oracle

from src import get_connection

controleServico = APIRouter(prefix="/globus")


class ControleServico(BaseModel):
    chapa: str
    turno: int  # 1 ou 2
    hora_retorno: str
    catraca_final: int
    odometro_final: int
    usuario: str
    data_baixa: str


def validate_datetime_format(value: str, field_name: str) -> None:
    expected_format = "%d/%m/%Y %H:%M:%S"
    try:
        datetime.strptime(value, expected_format)
    except ValueError:
        raise ValueError(
            f"O campo '{field_name}' com valor '{value}' deve estar no formato 'DD/MM/YYYY HH24:MI:SS' (ex: '14/03/2025 15:00:00')"
        )


@controleServico.post("/controle-servico")
def create_controle_servico(controle: ControleServico):
    try:
        # Validação manual dos campos antes de qualquer operação
        validate_datetime_format(controle.hora_partida, "hora_partida")
        validate_datetime_format(controle.hora_retorno, "hora_retorno")
        validate_datetime_format(controle.data_baixa, "data_baixa")

        conn = get_connection()
        cursor = conn.cursor()

        params = {
            "chapa": f"%{controle.chapa}",
            "turno": controle.turno,
        }

        query_verifica_cobrador = """
            SELECT CASE WHEN S.CODINTCOB IS NOT NULL THEN 1 ELSE 0 END AS TEM_COBRADOR
            FROM PLT_SAIDARECOLHIDA S
            INNER JOIN FLP_FUNCIONARIOS F ON F.CODINTFUNC = S.CODINTMOT OR F.CODINTFUNC = S.CODINTCOB 
            WHERE F.CHAPAFUNC LIKE :chapa AND F.SITUACAOFUNC = 'A' AND S.COD_INTTURNO = :turno
                AND S.HORASAIDAGARAGEM = (
                    SELECT MAX(HORASAIDAGARAGEM)
                    FROM PLT_SAIDARECOLHIDA P1
                    INNER JOIN FLP_FUNCIONARIOS F1 ON P1.CODINTMOT = F1.CODINTFUNC
                    WHERE F1.CHAPAFUNC LIKE :chapa
                )
        """

        cursor.execute(query_verifica_cobrador, params)

        result = cursor.fetchall()

        if not result:
            raise ValueError(
                f"Nenhum registro encontrado para esta chapa {controle.chapa} neste turno"
            )

        tem_cobrador = result[0][0] == 1

        # Parâmetros para o UPDATE
        params2 = {
            "hora_retorno": controle.hora_retorno,
            "odometro_final": controle.odometro_final,
            "catraca_final": controle.catraca_final,
            "chapa": f"%{controle.chapa}",
            "turno": controle.turno,
            "usuario": controle.usuario,
            "data_baixa": controle.data_baixa,
        }

        # 3. Query Dinâmica
        query_base = """
            UPDATE PLT_SAIDARECOLHIDA S
            SET S.HORAFINMOT = TO_DATE(:hora_retorno, 'DD/MM/YYYY HH24:MI:SS'),
                S.ODOMETROFIN = :odometro_final,
                S.ROLETAFIN = :catraca_final,
                S.USUARIOCHEGADA = :usuario,
                S.DTUSUCHEGADA = TO_DATE(:data_baixa, 'DD/MM/YYYY HH24:MI:SS'),
        """

        if tem_cobrador:
            query_base += (
                ", S.HORAFINCOB = TO_DATE(:hora_retorno, 'DD/MM/YYYY HH24:MI:SS')"
            )

        query_base += """
            WHERE S.HORASAIDAGARAGEM = (
                SELECT MAX(P1.HORASAIDAGARAGEM)
                FROM PLT_SAIDARECOLHIDA P1
                INNER JOIN FLP_FUNCIONARIOS F1 ON P1.CODINTMOT = F1.CODINTFUNC
                WHERE F1.CHAPAFUNC LIKE :chapa AND F1.SITUACAOFUNC = 'A'
            )
            AND S.COD_INTTURNO = :turno
            AND EXISTS (
                SELECT 1
                FROM FLP_FUNCIONARIOS F
                WHERE (F.CODINTFUNC = S.CODINTMOT OR F.CODINTFUNC = S.CODINTCOB)
                AND F.CHAPAFUNC LIKE :chapa AND F.SITUACAOFUNC = 'A'
            )
        """

        cursor.execute(query_base, params2)
        conn.commit()

        if cursor.rowcount == 0:
            raise ValueError("Nenhum registro foi atualizado")

        response = {"message": "Controle de serviço atualizado com sucesso"}
        return JSONResponse(content=response, status_code=status.HTTP_200_OK)

    except ValueError as e:
        status_code = (
            status.HTTP_400_BAD_REQUEST
            if "formato" in str(e)
            else status.HTTP_404_NOT_FOUND
        )
        return JSONResponse(
            content={"status": status_code, "message": str(e)},
            status_code=status_code,
        )
    except cx_Oracle.DatabaseError as e:
        return JSONResponse(
            content={"status": 500, "message": f"Erro no banco de dados: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as e:
        return JSONResponse(
            content={"status": 400, "message": f"Erro na requisição: {str(e)}"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    finally:
        if "cursor" in locals():
            cursor.close()
        if "conn" in locals():
            conn.close()
