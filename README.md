# Projeto de Integração ao Oracle (Globus) usando Python com FastAPI

# - Banco de Dados Oracle

    URL de conexão: "globus/glb2012@192.168.0.5:1521/oracle"

- Necessário instalação do Oracle Instant Client e configuração de variável de ambiente na S.O.
  https://www.oracle.com/database/technologies/instant-client/linux-x86-64-downloads.html
  Variável de ambiente: export LD_LIBRARY_PATH=/opt/oracle/instantclient_11_2:$LD_LIBRARY_PATH

# - Aplicação servida pelo PM2:

    https://pm2.keymetrics.io/docs/usage/quick-start/

- Comando via terminal Linux do server de backend:

  Ambiente de produção (Na pasta da aplicação):
  poetry shell
  Server start: pm2 start main.py -i 1 --name ApiGlobus
  Server stop: pm2 stop all
  Server status: pm2 list
  Server restart: pm2 restart all

  Ambiente de desenvolvimento (Na pasta da aplicação):
  poetry shell
  uvicorn main:app --reload
