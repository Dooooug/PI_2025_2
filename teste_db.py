import psycopg2
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

try:
    connection = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', 5432),
        user=os.getenv('DB_USER', 'user'),
        password=os.getenv('DB_PASSWORD', '204314'),
        dbname=os.getenv('DB_NAME', 'user_db')
    )
    print("Conexão com o banco de dados bem-sucedida!")
except psycopg2.OperationalError as e:
    print("Erro operacional! Verifique as credenciais ou o servidor do banco.")
    print(f"Detalhes: {e}")
except Exception as e:
    print("Erro inesperado ao conectar ao banco.")
    print(f"Detalhes: {e}")
finally:
    try:
        if connection:
            connection.close()
            print("Conexão fechada com sucesso.")
    except NameError:
        print("A conexão não foi criada devido ao erro.")
