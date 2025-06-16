import os
import logging
from flask import Blueprint, request, jsonify
from flask_cors import CORS
import boto3 # Importar a biblioteca boto3 para AWS S3
from dotenv import load_dotenv
from pymongo import MongoClient # Importar a biblioteca PyMongo para MongoDB
from datetime import datetime # Para timestamps no MongoDB
import uuid # Para gerar nomes de arquivo únicos para o S3

load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

pdf_bp = Blueprint('pdf_routes', __name__)
CORS(pdf_bp)

# --- Configurar AWS S3 ---
# Obtenha as credenciais da AWS e a região das variáveis de ambiente
aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
aws_region = os.getenv('AWS_REGION')
s3_bucket_name = os.getenv('S3_BUCKET_NAME')

# Inicialize o cliente S3
s3_client = None
try:
    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region
    )
    logging.info("Cliente AWS S3 inicializado com sucesso.")
except Exception as e:
    logging.error(f"Erro ao inicializar o cliente AWS S3: {e}")
    # O cliente S3 permanece None se houver um erro, e a rota de upload o verificará.

# --- Configurar MongoDB ---
mongo_uri = os.getenv('MONGO_URI')
mongo_db_name = os.getenv('MONGO_DB_NAME') # Nome padrão do banco de dados
mongo_collection_name = os.getenv('MONGO_COLLECTION_NAME') # Nome padrão da coleção

mongo_client = None
pdf_collection = None
try:
    mongo_client = MongoClient(mongo_uri)
    pdf_collection = mongo_client[mongo_db_name][mongo_collection_name]
    logging.info(f"Conexão MongoDB estabelecida com sucesso ao DB '{mongo_db_name}' e coleção '{mongo_collection_name}'.")
except Exception as e:
    logging.error(f"Erro ao conectar ao MongoDB: {e}")
    # As variáveis permanecem None se houver um erro, e as rotas as verificarão.

@pdf_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    Endpoint para fazer upload de arquivos para o AWS S3 e armazenar seus metadados no MongoDB.
    """
    logging.info("Recebendo requisição de upload de arquivo...")

    # Verificar se o cliente S3 foi inicializado corretamente
    if s3_client is None or s3_bucket_name is None:
        logging.error("AWS S3 não está configurado corretamente. Verifique as variáveis de ambiente.")
        return jsonify({"error": "Configuração do AWS S3 ausente ou inválida"}), 500

    # Verificar se a coleção MongoDB foi inicializada corretamente
    if pdf_collection is None:
        logging.error("MongoDB não está configurado corretamente. Verifique as variáveis de ambiente e a conexão.")
        return jsonify({"error": "Configuração do MongoDB ausente ou inválida"}), 500

    # Verificação da presença do arquivo na requisição
    if 'file' not in request.files:
        logging.error("Nenhum arquivo foi enviado na requisição.")
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    file = request.files['file']
    if file.filename == '':
        logging.warning("Usuário enviou um arquivo sem nome.")
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400

    try:
        original_file_name = file.filename
        # Gerar um nome de arquivo único para o S3 para evitar colisões
        # Preserva a extensão original do arquivo
        file_extension = os.path.splitext(original_file_name)[1]
        unique_s3_file_name = f"{uuid.uuid4()}{file_extension}"
        file_key = f"uploads/{unique_s3_file_name}" # Ex: uploads/unique-uuid.pdf

        logging.info(f"Iniciando upload do arquivo original: {original_file_name} (S3 key: {file_key}) para o bucket {s3_bucket_name}")
        
        # O método upload_fileobj é eficiente para streams de arquivo
        s3_client.upload_fileobj(file, s3_bucket_name, file_key)
        
        # Constrói a URL pública do arquivo no S3
        file_url = f"https://{s3_bucket_name}.s3.{aws_region}.amazonaws.com/{file_key}"

        if not file_url:
            logging.error("Falha ao obter URL do arquivo do S3.")
            return jsonify({"error": "Erro ao obter URL do arquivo"}), 500

        logging.info(f"Upload realizado com sucesso para S3! URL: {file_url}")

        # --- Armazenamento de metadados no MongoDB ---
        logging.info(f"Inserindo metadados no MongoDB para o arquivo: {original_file_name}")

        pdf_document = {
            "original_filename": original_file_name,
            "s3_file_key": file_key, # Chave única no S3
            "url": file_url,
            "uploaded_at": datetime.utcnow() # Data e hora do upload
        }
        
        insert_result = pdf_collection.insert_one(pdf_document)
        # O _id é um ObjectId, converta para string para retornar no JSON
        inserted_id = str(insert_result.inserted_id)

        logging.info(f"Arquivo '{original_file_name}' e metadados armazenados no MongoDB com ID: {inserted_id}.")

        return jsonify({
            "message": "Arquivo enviado com sucesso",
            "url": file_url,
            "id": inserted_id, # ID do documento no MongoDB
            "original_filename": original_file_name
        }), 200

    except boto3.exceptions.S3UploadFailedError as e:
        logging.exception(f"Erro ao enviar arquivo para o S3: {e}")
        return jsonify({"error": f"Erro ao enviar arquivo para S3: {str(e)}"}), 500
    except Exception as e: # Captura outras exceções (MongoDB, etc.)
        logging.exception("Erro inesperado durante o upload ou armazenamento no MongoDB.")
        return jsonify({"error": f"Erro inesperado: {str(e)}"}), 500

# --- Novo Endpoint para listar PDFs (para Postman) ---
@pdf_bp.route('/pdfs', methods=['GET'])
def get_pdfs():
    """
    Endpoint para listar todos os metadados de arquivos PDF armazenados no MongoDB.
    """
    logging.info("Recebendo requisição para listar PDFs...")

    # Verificar se a coleção MongoDB foi inicializada corretamente
    if pdf_collection is None:
        logging.error("MongoDB não está configurado corretamente. Verifique as variáveis de ambiente e a conexão.")
        return jsonify({"error": "Configuração do MongoDB ausente ou inválida"}), 500

    try:
        pdfs = []
        # Itera sobre todos os documentos na coleção de PDFs
        for doc in pdf_collection.find({}):
            # Converte ObjectId para string para que possa ser serializado em JSON
            doc['_id'] = str(doc['_id'])
            # Se 'uploaded_at' for um objeto datetime, converta para string ISO 8601
            if 'uploaded_at' in doc and isinstance(doc['uploaded_at'], datetime):
                doc['uploaded_at'] = doc['uploaded_at'].isoformat()
            pdfs.append(doc)
        
        logging.info(f"Retornando {len(pdfs)} documentos PDF.")
        return jsonify(pdfs), 200
    except Exception as e:
        logging.exception("Erro ao buscar PDFs no MongoDB.")
        return jsonify({"error": f"Erro ao listar PDFs: {str(e)}"}), 500


