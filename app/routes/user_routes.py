from flask_cors import CORS  # Importação do Flask-CORS
from flask import request, jsonify
from .. import db
from ..models import User, Product
from flask import current_app as app
from flask import session
from werkzeug.security import generate_password_hash

app.secret_key = 204314

# Adicionar o CORS ao app
CORS(app)  # Habilita o CORS para todas as rotas

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    app.logger.info(f"Dados recebidos: {data}")
    email = data.get('email')
    senha = data.get('senha')

    # Busca o usuário no banco de dados pelo email
    user = User.query.filter_by(email=email).first()

    # Verifica se o usuário existe e se a senha está correta
    if not user or not user.check_password(senha):  # check_password é uma função que valida a senha
        return jsonify({'message': 'Credenciais inválidas'}), 401

    # Retorna o ID do usuário junto com a mensagem de sucesso
    return jsonify({'message': 'Login bem-sucedido', 'id': user.id}), 200


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Validação e registro de novo usuário
    nome = data.get('nome')
    email = data.get('email')
    senha = data.get('senha')

    # Adicionar verificações de validação aqui...
    if not nome or len(nome) > 150:
        return jsonify({'message': 'O nome deve ter no máximo 500 caracteres'}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Usuário já existe'}), 409

    new_user = User(nome=nome, email=email)
    new_user.set_password(senha)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'Usuário registrado com sucesso'}), 201

@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    try:
        # Busca o usuário pelo ID
        user = User.query.get(user_id)

        # Verifica se o usuário existe
        if not user:
            return jsonify({'error': 'Usuário não encontrado.'}), 404

        # Retorna os dados do usuário
        return jsonify({'Id': user.id, 'Nome': user.nome, 'Email': user.email}), 200

    except Exception as e:
        print(f"Erro no servidor: {e}")
        return jsonify({'error': 'Erro interno no servidor'}), 500
    
@app.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    try:
        if user_id <= 0:
            return jsonify({'error': 'ID do usuário inválido'}), 400

        data = request.get_json()
        print(f"Dados recebidos para atualização do usuário {user_id}: {data}")

        if not data:
            return jsonify({'error': 'Dados de entrada são obrigatórios'}), 400
        if 'email' not in data:
            return jsonify({'error': 'O campo email é obrigatório'}), 400
        if 'senha' not in data:
            return jsonify({'error': 'O campo senha é obrigatório'}), 400

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': f'Usuário com ID {user_id} não encontrado'}), 404

        print(f"Usuário encontrado: ID={user.id}, Email={user.email}")

        user.email = data['email']
        user.senha = generate_password_hash(data['senha'])  # Hash da senha

        try:
            db.session.commit()
            print(f"Alterações salvas com sucesso para o usuário ID={user.id}")

            return jsonify({
                'message': 'Usuário atualizado com sucesso',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'nome': user.nome if hasattr(user, 'nome') else 'Nome não definido',
                }
            }), 200  # Código de status 200 OK
        except Exception as commit_error:
            print(f"Erro ao salvar alterações no banco: {commit_error}")
            db.session.rollback()
            return jsonify({'error': 'Erro ao salvar no banco de dados'}), 500

    except Exception as e:
        print(f"Erro no servidor: {e}")
        return jsonify({'error': 'Erro interno no servidor. Tente novamente.'}), 500


@app.route('/current_user', methods=['GET'])
def get_current_user():
    try:
        # Exemplo: obtendo user_id da sessão
        user_id = session.get('user_id')  # Certifique-se de que `session` esteja configurada

        # Validação: Certifica-se de que o usuário está autenticado
        if not user_id:
            return jsonify({'error': 'Usuário não autenticado'}), 401

        # Busca o usuário no banco de dados pelo ID
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': f'Usuário com ID {user_id} não encontrado'}), 404

        # Retorna as informações do usuário autenticado
        return jsonify({
            'id': user.id,
            'email': user.email,
            'nome': user.nome if hasattr(user, 'nome') else 'Nome não definido'
        }), 200
    except Exception as e:
        print(f"Erro ao buscar usuário: {e}")
        return jsonify({'error': 'Erro interno no servidor'}), 500
    
    
if __name__ == '__main__':
    app.run(debug=True)
    





