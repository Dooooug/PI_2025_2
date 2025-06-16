# app/routes/user_routes.py

from flask import request, jsonify, Blueprint
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId

# Importa a classe User do módulo models
from app.models import User
# Importa o decorador role_required e a constante ROLES do módulo utils
from app.utils import ROLES, role_required

# Cria um Blueprint para as rotas de usuário
user_bp = Blueprint('user', __name__)

# Rota de registro de usuário
@user_bp.route('/register', methods=['POST'])
def register():
    """
    Registra um novo usuário na aplicação.
    Requer 'username' e 'password'. 'role' é opcional (padrão: VIEWER).
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    # Define o papel (role) padrão como VIEWER se não for fornecido
    role = data.get('role', ROLES['VIEWER'])

    if not username or not password:
        return jsonify({"msg": "Nome de usuário e senha são obrigatórios"}), 400

    # Verifica se o nome de usuário já existe
    if User.collection().find_one({"username": username}):
        return jsonify({"msg": "Nome de usuário já existe"}), 409

    # Valida se o papel fornecido é um dos papéis permitidos
    if role not in ROLES.values():
        return jsonify({"msg": "Role inválido"}), 400

    # Gera o hash da senha antes de armazenar
    hashed_password = generate_password_hash(password)

    # Cria uma nova instância de User e insere no banco de dados
    new_user = User(username=username, password_hash=hashed_password, role=role)
    result = User.collection().insert_one(new_user.to_dict())
    new_user._id = result.inserted_id # Atribui o ID gerado pelo MongoDB ao objeto

    return jsonify({
        "msg": "Usuário registrado com sucesso",
        "user": {"id": str(new_user._id), "username": new_user.username, "role": new_user.role}
    }), 201

# Rota de login
@user_bp.route('/login', methods=['POST'])
def login():
    """
    Autentica um usuário e retorna um token de acesso JWT.
    Requer 'username' e 'password'.
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # Busca o usuário no banco de dados pelo nome de usuário
    user_data = User.collection().find_one({"username": username})

    # Verifica se o usuário existe e se a senha está correta
    if not user_data or not check_password_hash(user_data['password_hash'], password):
        return jsonify({"msg": "Nome de usuário ou senha inválidos"}), 401
    
    # Converte o dicionário do MongoDB para um objeto User
    user = User.from_dict(user_data)

    # Cria um token de acesso JWT com a identidade do usuário (ID do MongoDB)
    access_token = create_access_token(identity=str(user._id))
    return jsonify(access_token=access_token, user={'id': str(user._id), 'username': user.username, 'role': user.role}), 200

# --- Rotas CRUD para Usuários (Administrador) ---

@user_bp.route('/users', methods=['GET'])
@role_required([ROLES['ADMIN']])
def get_users():
    """
    Retorna uma lista de todos os usuários. Apenas para administradores.
    """
    users_cursor = User.collection().find({})
    users_list = []
    # Itera sobre os usuários, converte para objeto User e adiciona à lista
    for user_data in users_cursor:
        user = User.from_dict(user_data)
        users_list.append({"id": str(user._id), "username": user.username, "role": user.role})
    return jsonify(users_list), 200

@user_bp.route('/users/<user_id>', methods=['GET'])
@role_required([ROLES['ADMIN']])
def get_user(user_id):
    """
    Retorna os detalhes de um usuário específico pelo ID. Apenas para administradores.
    """
    try:
        # Tenta converter o ID fornecido para ObjectId
        user_data = User.collection().find_one({"_id": ObjectId(user_id)})
    except Exception:
        return jsonify({"msg": "ID de usuário inválido"}), 400

    if not user_data:
        return jsonify({"msg": "Usuário não encontrado"}), 404
    
    # Converte o dicionário do MongoDB para um objeto User
    user = User.from_dict(user_data)
    return jsonify({"id": str(user._id), "username": user.username, "role": user.role}), 200

@user_bp.route('/users/<user_id>', methods=['PUT'])
@role_required([ROLES['ADMIN']])
def update_user(user_id):
    """
    Atualiza um usuário existente pelo ID. Apenas para administradores.
    Permite atualizar 'username', 'password' e 'role'.
    """
    try:
        # Busca o usuário existente para verificar sua existência
        user_data_from_db = User.collection().find_one({"_id": ObjectId(user_id)})
    except Exception:
        return jsonify({"msg": "ID de usuário inválido"}), 400

    if not user_data_from_db:
        return jsonify({"msg": "Usuário não encontrado"}), 404

    data = request.get_json()
    update_data = {}

    # Adiciona campos à atualização se estiverem presentes no payload
    if 'username' in data:
        update_data['username'] = data['username']
    if 'role' in data:
        # Valida o novo papel
        if data['role'] not in ROLES.values():
            return jsonify({"msg": "Role inválido"}), 400
        update_data['role'] = data['role']
    
    if 'password' in data:
        update_data['password_hash'] = generate_password_hash(data['password'])

    if update_data:
        # Realiza a atualização no banco de dados
        User.collection().update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
        # Busca o usuário atualizado para retornar os dados mais recentes
        updated_user_data = User.collection().find_one({"_id": ObjectId(user_id)})
        updated_user = User.from_dict(updated_user_data)
        return jsonify({
            "msg": "Usuário atualizado com sucesso",
            "user": {"id": str(updated_user._id), "username": updated_user.username, "role": updated_user.role}
        }), 200
    else:
        return jsonify({"msg": "Nenhum dado para atualizar"}), 400

@user_bp.route('/users/<user_id>', methods=['DELETE'])
@role_required([ROLES['ADMIN']])
def delete_user(user_id):
    """
    Deleta um usuário pelo ID. Apenas para administradores.
    """
    try:
        # Tenta deletar o usuário
        result = User.collection().delete_one({"_id": ObjectId(user_id)})
    except Exception:
        return jsonify({"msg": "ID de usuário inválido"}), 400
        
    if result.deleted_count == 0:
        return jsonify({"msg": "Usuário não encontrado"}), 404
    return jsonify({"msg": "Usuário deletado com sucesso"}), 200

