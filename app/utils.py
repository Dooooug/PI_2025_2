# app/utils.py

from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
import functools

# Importa a classe User do módulo models (certifique-se que app/models.py está correto)
from app.models import User

# Define os papéis (roles) disponíveis na aplicação
ROLES = {
    'ADMIN': 'administrador',
    'ANALYST': 'analista',
    'VIEWER': 'visualizador'
}

def role_required(required_roles):
    """
    Decorador para verificar se o usuário autenticado tem um dos papéis necessários.
    """
    def decorator(fn):
        @functools.wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            current_user_id = get_jwt_identity()
            
            # Busca os dados do usuário no MongoDB usando a classe User
            user_data = User.collection().find_one({"_id": ObjectId(current_user_id)})
            if not user_data:
                return jsonify({"msg": "Usuário não encontrado"}), 404
            
            # Converte o dicionário do MongoDB para um objeto User
            user = User.from_dict(user_data)

            # Verifica se o papel do usuário está entre os papéis requeridos
            if user.role not in required_roles:
                return jsonify({"msg": "Acesso negado: Nível de permissão insuficiente"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

