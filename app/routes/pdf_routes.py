import os
import logging
import re
from flask import Blueprint, request, jsonify
from flask_cors import CORS
import boto3
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime
import uuid
from flask_jwt_extended import get_jwt_identity
from bson.objectid import ObjectId
from bson.errors import InvalidId

# Importa as classes User e Product
from app.models import User, Product
# Importa o decorador role_required e a constante ROLES
from app.utils import ROLES, role_required

# ✅ NOVO: Importações para rate limiting
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()

# ============================================================
# CONFIGURAÇÃO DE SEGURANÇA
# ============================================================

class SensitiveDataFilter(logging.Filter):
    """Filtro para remover informações sensíveis dos logs"""
    def filter(self, record):
        if hasattr(record, 'msg'):
            sensitive_patterns = [
                r'(aws_access_key_id|aws_secret_access_key|password|token|secret)=[^&\s]*',
                r'(\bAKIA[0-9A-Z]{16}\b)',
                r'(\b[0-9a-fA-F]{40}\b)',
                r'(mongo_uri|mongodb\+srv://)[^@\s]*@[^\s]*'
            ]
            
            for pattern in sensitive_patterns:
                record.msg = re.sub(pattern, r'\1=***', str(record.msg))
        return True

# Configurar logging com filtro de segurança
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s",
    filters=[SensitiveDataFilter()]
)

# ============================================================
# FUNÇÕES DE VALIDAÇÃO
# ============================================================

def is_valid_objectid(id_str):
    """Valida se uma string é um ObjectId válido"""
    try:
        ObjectId(id_str)
        return True
    except (InvalidId, TypeError):
        return False

def get_aws_client(service_name):
    """Obtém cliente AWS de forma segura"""
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = os.getenv('AWS_REGION')
    
    if not all([aws_access_key_id, aws_secret_access_key, aws_region]):
        logging.error("Configuração AWS incompleta")
        return None
        
    try:
        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region
        )
        return session.client(service_name)
    except Exception as e:
        logging.error(f"Erro ao criar cliente AWS: {type(e).__name__}")
        return None

# ============================================================
# CONFIGURAÇÃO DO BLUEPRINT E CLIENTES
# ============================================================

pdf_bp = Blueprint('pdf_routes', __name__)
CORS(pdf_bp)

# ✅ NOVO: Configuração do Rate Limiter para PDF
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
    strategy="fixed-window"
)

# ✅ NOVO: Aplicar rate limiting geral ao blueprint de PDF
limiter.limit("50 per hour")(pdf_bp)

# --- Configurar AWS S3 de forma segura ---
s3_bucket_name = os.getenv('S3_BUCKET_NAME')
s3_client = get_aws_client('s3')

if s3_client:
    logging.info("Cliente AWS S3 inicializado com sucesso.")
else:
    logging.error("Falha ao inicializar cliente AWS S3")

# --- Configurar MongoDB para metadados de PDF ---
mongo_uri = os.getenv('MONGO_URI')
mongo_db_name = os.getenv('MONGO_DB_NAME')
mongo_pdf_collection_name = os.getenv('MONGO_COLLECTION_NAME')

mongo_client = None
pdf_metadata_collection = None

try:
    if mongo_uri and mongo_db_name and mongo_pdf_collection_name:
        mongo_client = MongoClient(mongo_uri)
        pdf_metadata_collection = mongo_client[mongo_db_name][mongo_pdf_collection_name]
        logging.info(f"Conexão MongoDB estabelecida para metadados de PDF")
    else:
        logging.error("Variáveis de ambiente MongoDB não configuradas")
except Exception as e:
    logging.error(f"Erro ao conectar ao MongoDB: {type(e).__name__}")

# ============================================================
# VALIDAÇÃO DE UPLOAD DE ARQUIVOS
# ============================================================

ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def allowed_file(filename):
    """Verifica se a extensão do arquivo é permitida"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_file_size(file):
    """Valida o tamanho do arquivo"""
    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    file.seek(0)
    return file_length <= MAX_FILE_SIZE

# ============================================================
# ROTAS
# ============================================================

@pdf_bp.route('/upload', methods=['POST'])
@role_required([ROLES['ADMIN']])
@limiter.limit("10 per hour")  # ✅ NOVO: Limite de 10 uploads por hora por usuário
def upload_file():
    """
    Endpoint para fazer upload de arquivos para o AWS S3 e armazenar seus metadados no MongoDB.
    Somente administradores podem realizar este upload.
    """
    logging.info("Recebendo requisição de upload de arquivo...")

    if s3_client is None or s3_bucket_name is None:
        logging.error("AWS S3 não está configurado corretamente")
        return jsonify({"error": "Configuração do AWS S3 ausente ou inválida"}), 500

    if pdf_metadata_collection is None:
        logging.error("MongoDB não está configurado corretamente")
        return jsonify({"error": "Configuração do MongoDB ausente ou inválida"}), 500

    if 'file' not in request.files:
        logging.error("Nenhum arquivo foi enviado na requisição")
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    file = request.files['file']
    if file.filename == '':
        logging.warning("Usuário enviou um arquivo sem nome")
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400

    # Validações de segurança
    if not allowed_file(file.filename):
        logging.warning(f"Tentativa de upload de tipo de arquivo não permitido: {file.filename}")
        return jsonify({"error": "Tipo de arquivo não permitido"}), 400

    if not validate_file_size(file):
        logging.warning("Tentativa de upload de arquivo muito grande")
        return jsonify({"error": "Arquivo muito grande"}), 400

    try:
        original_file_name = file.filename
        file_extension = os.path.splitext(original_file_name)[1]
        unique_s3_file_name = f"{uuid.uuid4()}{file_extension}"
        file_key = f"uploads/{unique_s3_file_name}"

        logging.info(f"Iniciando upload do arquivo: {original_file_name}")
        
        s3_client.upload_fileobj(file, s3_bucket_name, file_key)
        
        file_url = f"https://{s3_bucket_name}.s3.{os.getenv('AWS_REGION')}.amazonaws.com/{file_key}"

        if not file_url:
            logging.error("Falha ao obter URL do arquivo do S3")
            return jsonify({"error": "Erro ao obter URL do arquivo"}), 500

        logging.info(f"Upload realizado com sucesso para S3")

        # --- Armazenamento de metadados no MongoDB ---
        current_user_id = get_jwt_identity()
        if not is_valid_objectid(current_user_id):
            logging.warning("ID de usuário inválido no JWT")
            return jsonify({"error": "Erro de autenticação"}), 401

        pdf_document_metadata = {
            "original_filename": original_file_name,
            "s3_file_key": file_key,
            "url": file_url,
            "uploaded_at": datetime.utcnow(),
            "uploaded_by_user_id": ObjectId(current_user_id)
        }
        
        insert_result = pdf_metadata_collection.insert_one(pdf_document_metadata)
        inserted_id = str(insert_result.inserted_id)

        logging.info(f"Metadados armazenados no MongoDB com ID: {inserted_id}")

        return jsonify({
            "message": "Arquivo enviado com sucesso",
            "url": file_url,
            "s3_file_key": file_key,
            "id": inserted_id,
            "original_filename": original_file_name
        }), 200

    except boto3.exceptions.S3UploadFailedError as e:
        logging.error(f"Erro ao enviar arquivo para o S3: {type(e).__name__}")
        return jsonify({"error": "Erro ao enviar arquivo"}), 500
    except Exception as e:
        logging.error(f"Erro inesperado durante o upload: {type(e).__name__}")
        return jsonify({"error": "Erro interno do servidor"}), 500

@pdf_bp.route('/pdfs', methods=['GET'])
@role_required([ROLES['ADMIN'], ROLES['ANALYST'], ROLES['VIEWER']])
@limiter.limit("30 per minute")  # ✅ NOVO: Limite de 30 consultas por minuto
def get_pdfs():
    """
    Endpoint para listar produtos que possuem um PDF associado, filtrando por role.
    Retorna apenas campos específicos para visualizadores.
    """
    logging.info("Recebendo requisição para listar PDFs")

    if Product.collection() is None:
        logging.error("Coleção de produtos MongoDB não configurada")
        return jsonify({"error": "Configuração da coleção de produtos ausente"}), 500

    current_user_id_str = get_jwt_identity()
    
    if not is_valid_objectid(current_user_id_str):
        logging.warning("ID de usuário inválido no JWT")
        return jsonify({"error": "Erro de autenticação"}), 401

    try:
        current_user_data = User.collection().find_one(
            {"_id": ObjectId(current_user_id_str)},
            {"username": 1, "role": 1, "active": 1}
        )
        
        if not current_user_data:
            logging.warning("Usuário não encontrado no banco de dados")
            return jsonify({"error": "Usuário não encontrado"}), 404
            
        if not current_user_data.get('active', True):
            logging.warning("Tentativa de acesso por usuário inativo")
            return jsonify({"error": "Usuário desativado"}), 403

        current_user = User.from_dict(current_user_data)

        query_filter = {"pdf_url": {"$exists": True, "$ne": None}}
        projection = {}

        # Lógica de filtragem e projeção baseada no papel do usuário
        if current_user.role == ROLES['VIEWER']:
            query_filter["status"] = "aprovado"
            projection = {
                "_id": 1,
                "nome_do_produto": 1,
                "qtade_maxima_armazenada": 1,
                "pdf_url": 1
            }
        elif current_user.role == ROLES['ANALYST']:
            query_filter["$or"] = [
                {"status": "aprovado"},
                {"created_by_user_id": current_user_id_str}
            ]
        elif current_user.role == ROLES['ADMIN']:
            # Administrador vê todos os produtos com PDF
            pass
        else:
            logging.warning(f"Papel de usuário inválido: {current_user.role}")
            return jsonify({"error": "Papel de usuário inválido"}), 403

        products_with_pdfs = []
        products_cursor = Product.collection().find(query_filter, projection)
        
        for p_data in products_cursor:
            p_data['_id'] = str(p_data['_id'])
            if 'pdf_url' in p_data:
                p_data['url_download'] = p_data.pop('pdf_url')
            products_with_pdfs.append(p_data)
        
        logging.info(f"Retornando {len(products_with_pdfs)} documentos PDF/produtos")
        return jsonify(products_with_pdfs), 200
        
    except Exception as e:
        logging.error(f"Erro ao buscar PDFs: {type(e).__name__}")
        return jsonify({"error": "Erro interno do servidor"}), 500

@pdf_bp.route('/pdfs/<pdf_id>', methods=['DELETE'])
@role_required([ROLES['ADMIN']])
@limiter.limit("5 per hour")  # ✅ NOVO: Limite de 5 exclusões por hora
def delete_pdf(pdf_id):
    """
    Endpoint para deletar um PDF e seus metadados
    """
    # Validação de segurança do ID
    if not is_valid_objectid(pdf_id):
        return jsonify({"error": "ID inválido"}), 400

    try:
        # Busca metadados do PDF
        pdf_data = pdf_metadata_collection.find_one({"_id": ObjectId(pdf_id)})
        if not pdf_data:
            return jsonify({"error": "PDF não encontrado"}), 404

        # Remove do S3
        if s3_client and 's3_file_key' in pdf_data:
            try:
                s3_client.delete_object(Bucket=s3_bucket_name, Key=pdf_data['s3_file_key'])
                logging.info(f"Arquivo removido do S3: {pdf_data['s3_file_key']}")
            except Exception as e:
                logging.error(f"Erro ao deletar do S3: {type(e).__name__}")

        # Remove metadados do MongoDB
        result = pdf_metadata_collection.delete_one({"_id": ObjectId(pdf_id)})
        
        if result.deleted_count == 0:
            return jsonify({"error": "PDF não encontrado"}), 404

        logging.info(f"PDF deletado com sucesso: {pdf_id}")
        return jsonify({"message": "PDF deletado com sucesso"}), 200

    except Exception as e:
        logging.error(f"Erro ao deletar PDF: {type(e).__name__}")
        return jsonify({"error": "Erro interno do servidor"}), 500

# ✅ NOVO: Rota de health check sem autenticação
@pdf_bp.route('/health', methods=['GET'])
@limiter.limit("10 per minute")  # Limite generoso para health checks
def health_check():
    """
    Endpoint para verificar a saúde do serviço de PDF
    """
    try:
        # Verifica conexão com MongoDB
        if pdf_metadata_collection:
            pdf_metadata_collection.find_one()
        
        # Verifica conexão com S3
        if s3_client and s3_bucket_name:
            s3_client.head_bucket(Bucket=s3_bucket_name)
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "mongodb": "connected" if pdf_metadata_collection else "disconnected",
                "aws_s3": "connected" if s3_client else "disconnected"
            }
        }), 200
        
    except Exception as e:
        logging.error(f"Health check failed: {type(e).__name__}")
        return jsonify({
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": "Service unavailable"
        }), 503