from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from PIL import Image
import cx_Oracle
import base64
import io

from src import get_connection

consultaUser = APIRouter(prefix="/globus")


def redimensionar_imagem(imagem_bytes: bytes, largura: int, altura: int) -> str:
    imagem = Image.open(io.BytesIO(imagem_bytes))
    imagem_redimensionada = imagem.resize((largura, altura))
    buffer = io.BytesIO()
    imagem_redimensionada.save(buffer, format="JPEG")
    nova_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{nova_base64}"

@consultaUser.get("/consulta-user/{chapafunc_filter}")
async def function(chapafunc_filter: str, largura: int = 250, altura: int = 300):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = """
                SELECT 
                    f.chapafunc,
                    f.nomecompletofunc,
                    J.nomedepen,
                    f.fonefunc,
                    sub3.nrdocto,
                    f.emailfunc,
                    TO_CHAR(f.dtnasctofunc, 'DD/MM/YYYY'),
                    FI.IMAGEM
                FROM 
                    (SELECT d.nomedepen, D.CODINTFUNC 
                    FROM flp_dependentes d 
                    WHERE D.codparen = '7') J
                RIGHT JOIN 
                    (SELECT P.CODINTFUNC 
                    FROM FLP_FUNCIONARIOS P 
                    WHERE P.SITUACAOFUNC IN ('A', 'F')) K 
                ON J.CODINTFUNC = K.CODINTFUNC
                INNER JOIN 
                    vw_funcionarios f 
                ON K.CODINTFUNC = f.CODINTFUNC
                INNER JOIN 
                    (SELECT nrdocto, codintfunc 
                    FROM flp_documentos 
                    WHERE tipodocto = 'CPF') sub3 
                ON sub3.codintfunc = f.CODINTFUNC
                LEFT JOIN 
                    FLP_FUNCIONARIOS_IMAGENS FI 
                ON FI.CODINTFUNC = f.CODINTFUNC
                WHERE 
                    f.chapafunc LIKE :chapafunc_filter AND SITUACAOFUNC = 'A'
        """
        cursor.execute(query, {"chapafunc_filter": f"%{chapafunc_filter}"})
        result = cursor.fetchall()

        if not result:
            raise ValueError("Usuário não encontrado para a chapa " f"{chapafunc_filter}")

        data = []
        for row in result:
            chapafunc = row[0]
            nome_func = row[1]
            nome_mae = row[2]
            telefone = row[3]
            cpf = row[4]
            email = row[5]
            nascimento = row[6]
            long_raw_data = row[7]  # FI.IMAGEM

            # Processa a imagem se disponível
            if not long_raw_data:
                raise ValueError("Imagem do funcionário não encontrada. Verifique com o RH.")
            
            resized_base64 = redimensionar_imagem(long_raw_data, largura, altura)

            data.append(
                {
                    "chapafunc": chapafunc,
                    "nome_func": nome_func,
                    "nome_mae": nome_mae,
                    "telefone": telefone,
                    "cpf": cpf,
                    "email": email,
                    "nascimento": nascimento,
                    "base64": resized_base64,
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
