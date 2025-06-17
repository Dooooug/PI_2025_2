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
    Requer 'username', 'email' e 'senha'. 'role' é opcional (padrão: VIEWER).
    """
    data = request.get_json()
    username = data.get('username')
    email = data.get('email') # NOVO: Captura o email
    senha = data.get('senha') # CORRIGIDO: usa 'senha' conforme o frontend
    # Define o papel (role) padrão como VIEWER se não for fornecido
    role = data.get('role', ROLES['VIEWER'])

    if not username or not email or not senha: # NOVO: Valida o email também
        return jsonify({"msg": "Nome de usuário, email e senha são obrigatórios"}), 400

    # Verifica se o nome de usuário já existe
    if User.collection().find_one({"username": username}):
        return jsonify({"msg": "Nome de usuário já existe"}), 409
    
    # NOVO: Verifica se o email já existe
    if User.collection().find_one({"email": email}):
        return jsonify({"msg": "Email já está em uso"}), 409

    # Valida se o papel fornecido é um dos papéis permitidos
    if role not in ROLES.values():
        return jsonify({"msg": "Role inválido"}), 400

    # Gera o hash da senha antes de armazenar
    hashed_password = generate_password_hash(senha) # Usa 'senha' para o hash

    # Cria uma nova instância de User e insere no banco de dados
    new_user = User(username=username, email=email, password_hash=hashed_password, role=role) # NOVO: Passa o email
    result = User.collection().insert_one(new_user.to_dict())
    new_user._id = result.inserted_id # Atribui o ID gerado pelo MongoDB ao objeto

    return jsonify({
        "msg": "Usuário registrado com sucesso",
        "user": {"id": str(new_user._id), "username": new_user.username, "email": new_user.email, "role": new_user.role} # NOVO: Inclui email na resposta
    }), 201

# Rota de login
@user_bp.route('/login', methods=['POST'])
def login():
    """
    Autentica um usuário e retorna um token de acesso JWT.
    Requer 'email' e 'senha'.
    """
    data = request.get_json()
    email = data.get('email') # CORRIGIDO: Usa 'email' para login
    senha = data.get('senha') # CORRIGIDO: Usa 'senha' conforme o frontend

    if not email or not senha:
        return jsonify({"msg": "Email e senha são obrigatórios"}), 400

    # Busca o usuário no banco de dados pelo email
    user_data = User.collection().find_one({"email": email}) # CORRIGIDO: Busca por email

    # Verifica se o usuário existe e se a senha está correta
    if not user_data or not check_password_hash(user_data['password_hash'], senha): # Usa 'senha' para checar hash
        return jsonify({"msg": "Email ou senha inválidos"}), 401
    
    # Converte o dicionário do MongoDB para um objeto User
    user = User.from_dict(user_data)

    # Cria um token de acesso JWT com a identidade do usuário (ID do MongoDB)
    access_token = create_access_token(identity=str(user._id))
    return jsonify(access_token=access_token, user={'id': str(user._id), 'username': user.username, 'email': user.email, 'role': user.role}), 200 # Inclui email na resposta

# --- Rotas CRUD para Usuários (Administrador) ---

@user_bp.route('/users', methods=['GET'])
@role_required([ROLES['ADMIN']])
def get_users():
    """
    Retorna uma lista de todos os usuários. Apenas para administradores.
    Inclui o email dos usuários.
    """
    users_cursor = User.collection().find({})
    users_list = []
    for user_data in users_cursor:
        user = User.from_dict(user_data)
        users_list.append({"id": str(user._id), "username": user.username, "email": user.email, "role": user.role}) # NOVO: Inclui email
    return jsonify(users_list), 200

@user_bp.route('/users/<user_id>', methods=['GET'])
@role_required([ROLES['ADMIN']])
def get_user(user_id):
    """
    Retorna os detalhes de um usuário específico pelo ID. Apenas para administradores.
    Inclui o email do usuário.
    """
    try:
        user_data = User.collection().find_one({"_id": ObjectId(user_id)})
    except Exception:
        return jsonify({"msg": "ID de usuário inválido"}), 400

    if not user_data:
        return jsonify({"msg": "Usuário não encontrado"}), 404
    
    user = User.from_dict(user_data)
    return jsonify({"id": str(user._id), "username": user.username, "email": user.email, "role": user.role}), 200 # NOVO: Inclui email

@user_bp.route('/users/<user_id>', methods=['PUT'])
@role_required([ROLES['ADMIN']])
def update_user(user_id):
    """
    Atualiza um usuário existente pelo ID. Apenas para administradores.
    Permite atualizar 'username', 'email', 'senha' e 'role'.
    """
    try:
        user_data_from_db = User.collection().find_one({"_id": ObjectId(user_id)})
    except Exception:
        return jsonify({"msg": "ID de usuário inválido"}), 400

    if not user_data_from_db:
        return jsonify({"msg": "Usuário não encontrado"}), 404

    data = request.get_json()
    update_data = {}

    if 'username' in data:
        update_data['username'] = data['username']
    
    if 'email' in data: # NOVO: Permite atualizar o email
        # Opcional: Adicionar validação para email duplicado ao atualizar, excluindo o próprio usuário
        existing_user_with_email = User.collection().find_one({"email": data['email'], "_id": {"$ne": ObjectId(user_id)}})
        if existing_user_with_email:
            return jsonify({"msg": "Email já está em uso por outro usuário"}), 409
        update_data['email'] = data['email']
    
    if 'role' in data:
        if data['role'] not in ROLES.values():
            return jsonify({"msg": "Role inválido"}), 400
        update_data['role'] = data['role']
    
    if 'senha' in data: # CORRIGIDO: Usa 'senha' para atualização de senha
        update_data['password_hash'] = generate_password_hash(data['senha'])

    if update_data:
        User.collection().update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
        updated_user_data = User.collection().find_one({"_id": ObjectId(user_id)})
        updated_user = User.from_dict(updated_user_data)
        return jsonify({
            "msg": "Usuário atualizado com sucesso",
            "user": {"id": str(updated_user._id), "username": updated_user.username, "email": updated_user.email, "role": updated_user.role} # NOVO: Inclui email
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
        result = User.collection().delete_one({"_id": ObjectId(user_id)})
    except Exception:
        return jsonify({"msg": "ID de usuário inválido"}), 400
        
    if result.deleted_count == 0:
        return jsonify({"msg": "Usuário não encontrado"}), 404
    return jsonify({"msg": "Usuário deletado com sucesso"}), 200
