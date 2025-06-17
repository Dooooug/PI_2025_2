import os
import logging
from flask import Blueprint, request, jsonify
from flask_cors import CORS
import boto3
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime
import uuid
from flask_jwt_extended import get_jwt_identity # Necessário para obter a identidade do usuário logado
from bson.objectid import ObjectId # Necessário para buscar usuário e produto por ID

# Importa as classes User e Product
from app.models import User, Product
# Importa o decorador role_required e a constante ROLES
from app.utils import ROLES, role_required

load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

pdf_bp = Blueprint('pdf_routes', __name__)
CORS(pdf_bp)

# --- Configurar AWS S3 ---
aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
aws_region = os.getenv('AWS_REGION')
s3_bucket_name = os.getenv('S3_BUCKET_NAME')

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

# --- Configurar MongoDB para metadados de PDF (ainda usado por /upload) ---
mongo_uri = os.getenv('MONGO_URI')
mongo_db_name = os.getenv('MONGO_DB_NAME')
mongo_pdf_collection_name = os.getenv('MONGO_COLLECTION_NAME')

mongo_client = None
pdf_metadata_collection = None # Renomeado para maior clareza
try:
    mongo_client = MongoClient(mongo_uri)
    pdf_metadata_collection = mongo_client[mongo_db_name][mongo_pdf_collection_name]
    logging.info(f"Conexão MongoDB estabelecida para metadados de PDF no DB '{mongo_db_name}' e coleção '{mongo_pdf_collection_name}'.")
except Exception as e:
    logging.error(f"Erro ao conectar ao MongoDB para metadados de PDF: {e}")

@pdf_bp.route('/upload', methods=['POST'])
@role_required([ROLES['ADMIN']]) # Apenas administradores podem fazer upload
def upload_file():
    """
    Endpoint para fazer upload de arquivos para o AWS S3 e armazenar seus metadados no MongoDB.
    Somente administradores podem realizar este upload.
    """
    logging.info("Recebendo requisição de upload de arquivo...")

    if s3_client is None or s3_bucket_name is None:
        logging.error("AWS S3 não está configurado corretamente. Verifique as variáveis de ambiente.")
        return jsonify({"error": "Configuração do AWS S3 ausente ou inválida"}), 500

    if pdf_metadata_collection is None:
        logging.error("MongoDB (coleção de metadados de PDF) não está configurado corretamente. Verifique as variáveis de ambiente e a conexão.")
        return jsonify({"error": "Configuração do MongoDB para metadados de PDF ausente ou inválida"}), 500

    if 'file' not in request.files:
        logging.error("Nenhum arquivo foi enviado na requisição.")
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    file = request.files['file']
    if file.filename == '':
        logging.warning("Usuário enviou um arquivo sem nome.")
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400

    try:
        original_file_name = file.filename
        file_extension = os.path.splitext(original_file_name)[1]
        unique_s3_file_name = f"{uuid.uuid4()}{file_extension}"
        file_key = f"uploads/{unique_s3_file_name}"

        logging.info(f"Iniciando upload do arquivo original: {original_file_name} (S3 key: {file_key}) para o bucket {s3_bucket_name}")
        
        s3_client.upload_fileobj(file, s3_bucket_name, file_key)
        
        file_url = f"https://{s3_bucket_name}.s3.{aws_region}.amazonaws.com/{file_key}"

        if not file_url:
            logging.error("Falha ao obter URL do arquivo do S3.")
            return jsonify({"error": "Erro ao obter URL do arquivo"}), 500

        logging.info(f"Upload realizado com sucesso para S3! URL: {file_url}")

        # --- Armazenamento de metadados no MongoDB (coleção de metadados de PDF) ---
        # Este registro é apenas para rastrear o upload do arquivo em si.
        # A associação com um produto e seu status deve ser feita na rota de produtos.
        logging.info(f"Inserindo metadados do upload no MongoDB para o arquivo: {original_file_name}")

        pdf_document_metadata = {
            "original_filename": original_file_name,
            "s3_file_key": file_key,
            "url": file_url,
            "uploaded_at": datetime.utcnow(),
            "uploaded_by_user_id": get_jwt_identity() # Registra quem fez o upload
        }
        
        insert_result = pdf_metadata_collection.insert_one(pdf_document_metadata)
        inserted_id = str(insert_result.inserted_id)

        logging.info(f"Arquivo '{original_file_name}' e metadados armazenados no MongoDB com ID: {inserted_id}.")

        # A URL retornada pode ser usada para atualizar um documento de produto existente
        # ou para criar um novo produto que a utilize.
        return jsonify({
            "message": "Arquivo enviado com sucesso. Você pode usar esta URL para associá-lo a um produto.",
            "url": file_url,
            "s3_file_key": file_key, # Retorna a chave S3 também, útil para delete
            "id": inserted_id,
            "original_filename": original_file_name
        }), 200

    except boto3.exceptions.S3UploadFailedError as e:
        logging.exception(f"Erro ao enviar arquivo para o S3: {e}")
        return jsonify({"error": f"Erro ao enviar arquivo para S3: {str(e)}"}), 500
    except Exception as e:
        logging.exception("Erro inesperado durante o upload ou armazenamento no MongoDB.")
        return jsonify({"error": f"Erro inesperado: {str(e)}"}), 500

# --- Endpoint para listar PDFs (agora busca de Produtos e filtra por role) ---
@pdf_bp.route('/pdfs', methods=['GET'])
@role_required([ROLES['ADMIN'], ROLES['ANALYST'], ROLES['VIEWER']]) # Todos podem acessar, mas com filtro
def get_pdfs():
    """
    Endpoint para listar produtos que possuem um PDF associado, filtrando por role.
    Retorna apenas campos específicos para visualizadores.
    """
    logging.info("Recebendo requisição para listar PDFs (baseado em produtos)...")

    # Verifica se a coleção de Produtos está acessível (definida em app/__init__.py)
    if Product.collection() is None:
        logging.error("Coleção de produtos MongoDB não está configurada corretamente.")
        return jsonify({"error": "Configuração da coleção de produtos ausente ou inválida"}), 500

    current_user_id_str = get_jwt_identity()
    current_user_data = User.collection().find_one({"_id": ObjectId(current_user_id_str)})
    current_user = User.from_dict(current_user_data) # Converte para objeto User

    query_filter = {"pdf_url": {"$exists": True, "$ne": None}} # Apenas produtos com PDF
    projection = {} # Para projeção de campos

    # Lógica de filtragem e projeção baseada no papel do usuário
    if current_user.role == ROLES['VIEWER']:
        query_filter["status"] = "aprovado"
        # Visualizador vê apenas nome do produto, qtade_maxima_armazenada, e url do PDF
        projection = {
            "_id": 1, # ID do produto
            "nome_do_produto": 1,
            "qtade_maxima_armazenada": 1,
            "pdf_url": 1 # Assumindo que a URL do PDF está neste campo no modelo Product
        }
    elif current_user.role == ROLES['ANALYST']:
        query_filter["$or"] = [
            {"status": "aprovado"},
            {"created_by_user_id": current_user_id_str}
        ]
        # Analista vê todos os campos (ou pode-se definir uma projeção específica)
        projection = {} # Retorna todos os campos
    elif current_user.role == ROLES['ADMIN']:
        # Administrador vê todos os produtos com PDF
        projection = {} # Retorna todos os campos
    else:
        # Caso de um papel não reconhecido, negar acesso
        return jsonify({"msg": "Acesso negado: Papel de usuário inválido"}), 403

    try:
        products_with_pdfs = []
        # Realiza a consulta na coleção de Produtos
        products_cursor = Product.collection().find(query_filter, projection)
        
        for p_data in products_cursor:
            # Converte ObjectId para string para JSON
            p_data['_id'] = str(p_data['_id'])
            # Renomeia pdf_url para 'url_download' para ser mais descritivo no frontend
            if 'pdf_url' in p_data:
                p_data['url_download'] = p_data.pop('pdf_url')
            products_with_pdfs.append(p_data)
        
        logging.info(f"Retornando {len(products_with_pdfs)} documentos PDF/produtos.")
        return jsonify(products_with_pdfs), 200
    except Exception as e:
        logging.exception("Erro ao buscar PDFs/produtos no MongoDB.")
        return jsonify({"error": f"Erro ao listar PDFs: {str(e)}"}), 500

# O bloco if __name__ == "__main__": original (relacionado ao PostgreSQL)
# foi removido, pois a conexão MongoDB é estabelecida globalmente quando o Blueprint
# é carregado, e este arquivo será importado por sua aplicação Flask principal.

