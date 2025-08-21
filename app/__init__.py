from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from pymongo import MongoClient
import os

# Importa as classes Product e User
from app.models import Product, User

# Variável global para a instância do banco de dados MongoDB
# Esta variável será acessada pelos métodos .collection() das suas classes de modelo
db = None

def create_app():
    app = Flask(__name__)

    # Configurações do Flask com valores padrão para evitar erros
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    app.config['MONGO_URI'] = os.environ.get('MONGO_URI')
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')
    app.config['MONGO_DB_NAME'] = os.environ.get('MONGO_DB_NAME', 'quimicadocs_db') # Nome do seu banco de dados MongoDB

    # Inicializa JWT
    jwt = JWTManager(app)

    # Conexão com o MongoDB
    try:
        mongo_client = MongoClient(app.config['MONGO_URI'])
        global db # Declara que você vai modificar a variável global 'db'
        db = mongo_client[app.config['MONGO_DB_NAME']] # Atribui o banco de dados específico
        print("Conexão MongoDB estabelecida com sucesso.")
    except Exception as e:
        print(f"Erro ao conectar ao MongoDB: {e}")
        exit(1) # Saída segura se a conexão falhar

    # REMOVIDAS: As linhas abaixo não são mais necessárias
    # User.set_collection(app.mongo_db['users'])
    # Product.set_collection(app.mongo_db['products'])
    # O método .collection() nas classes User e Product já importa 'db' e retorna a coleção.

    # Configuração do CORS para permitir requisições do frontend
    CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

    # Importa e registra os Blueprints
    from app.routes.user_routes import user_bp
    from app.routes.product_routes import product_bp
    from app.routes.pdf_routes import pdf_bp

    app.register_blueprint(user_bp) 
    app.register_blueprint(product_bp)# (OPCIONAL) Adicionar um prefixo /api, comum para APIs - (pdf_bp, url_prefix='/api')
    app.register_blueprint(pdf_bp)

    # Rota inicial
    @app.route('/')
    def home():
        return "Aplicação Flask funcionando"

    return app

