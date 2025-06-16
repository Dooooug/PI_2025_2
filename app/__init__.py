# app/__init__.py

from flask import Flask
from flask_jwt_extended import JWTManager
from pymongo import MongoClient
import os

# Importa as classes Product e User
from app.models import Product, User

def create_app():
    app = Flask(__name__)

    # Configurações do Flask
    ###app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    app.config['MONGO_URI'] = os.environ.get('MONGO_URI')
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')

    # Inicializa JWT
    jwt = JWTManager(app)

    # Conexão com o MongoDB
    mongo_client = MongoClient(app.config['MONGO_URI'])
    app.mongo_db = mongo_client.get_default_database() # Ou especifique o nome do banco de dados

    # Define a coleção para as classes de modelo
    # Isso associa as classes User e Product às suas coleções no MongoDB
    User.set_collection(app.mongo_db['users'])
    Product.set_collection(app.mongo_db['products'])

    # --- Importa e registra os Blueprints ---
    from app.routes.user_routes import user_bp
    from app.routes.product_routes import product_bp
    from app.routes.pdf_routes import pdf_bp

    app.register_blueprint(user_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(pdf_bp)

    # Rota de home da aplicação (pode ser mantida aqui ou movida para um Blueprint genérico)
    @app.route('/')
    def home():
        return "Aplicação Flask funcionando"

    

    return app

