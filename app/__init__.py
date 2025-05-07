from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_cors import CORS

db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:204314@localhost:5432/user_db'
    app.config['JWT_SECRET_KEY'] = 'sua_chave_secreta'

    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)
    CORS(app)  # Habilitar CORS para o frontend

    with app.app_context():
        from app.routes import user_routes,product_routes  # Importa as rotas
        
        db.create_all()  # Cria as tabelas

    return app
