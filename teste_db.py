# app.py ou config.py (onde você configura o MongoDB)
import os
from pymongo import MongoClient
import logging

# Configuração de log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def connect_to_mongodb():
    try:
        # Certifique-se de que essas variáveis de ambiente estão definidas
        MONGO_HOST = os.getenv('MONGO_HOST')
        MONGO_PORT = os.getenv('MONGO_PORT', '27017') # Valor padrão para porta
        MONGO_USER = os.getenv('MONGO_USER')
        MONGO_PASSWORD = os.getenv('MONGO_PASSWORD')
        MONGO_DB_NAME = os.getenv('MONGO_DB_NAME')

        # Verificação para depuração: imprime os valores das variáveis
        logger.info(f"MONGO_HOST: {MONGO_HOST}")
        logger.info(f"MONGO_PORT: {MONGO_PORT}")
        logger.info(f"MONGO_USER: {'*' * len(MONGO_USER) if MONGO_USER else None}") # Não logar a senha real
        logger.info(f"MONGO_DB_NAME: {MONGO_DB_NAME}")

        # Verifique se alguma variável essencial é None
        if not all([MONGO_HOST, MONGO_USER, MONGO_PASSWORD, MONGO_DB_NAME]):
            logger.error("Uma ou mais variáveis de ambiente do MongoDB não foram definidas. Verifique MONGO_HOST, MONGO_USER, MONGO_PASSWORD, MONGO_DB_NAME.")
            raise ValueError("Configurações do MongoDB incompletas.")

        # Construa a URI de conexão
        if MONGO_USER and MONGO_PASSWORD:
            mongo_uri = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB_NAME}"
        else:
            # Caso não use autenticação (menos comum em produção)
            mongo_uri = f"mongodb://{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB_NAME}"

        client = MongoClient(mongo_uri)
        db = client[MONGO_DB_NAME]
        logger.info("Conexão ao MongoDB estabelecida com sucesso!")
        return db
    except ValueError as ve:
        logger.error(f"Erro de configuração ao conectar ao MongoDB: {ve}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao conectar ao MongoDB: {e}")
        return None

# No seu arquivo principal da aplicação Flask (ex: app.py)
# db_connection = connect_to_mongodb()
# if db_connection:
#     # Use db_connection para interagir com o MongoDB
#     pass
# else:
#     # Lidar com o caso de falha na conexão (ex: sair da aplicação ou mostrar erro)
#     pass