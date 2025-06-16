# app/routes/product_routes.py

from flask import request, jsonify, Blueprint
from flask_jwt_extended import get_jwt_identity
from bson.objectid import ObjectId

# Importa as classes Product e User do módulo models
from app.models import Product, User
# Importa o decorador role_required e a constante ROLES do módulo utils
from app.utils import ROLES, role_required

# Cria um Blueprint para as rotas de produto
product_bp = Blueprint('product', __name__)

# --- Rotas CRUD para Produtos ---

@product_bp.route('/products', methods=['POST'])
@role_required([ROLES['ADMIN'], ROLES['ANALYST']])
def create_product():
    """
    Cria um novo produto. Apenas para administradores e analistas.
    Administradores podem definir o status; analistas criam com status 'pendente'.
    """
    data = request.get_json()
    
    if not data or 'codigo' not in data or 'nome_do_produto' not in data:
        return jsonify({"msg": "Campos 'codigo' e 'nome_do_produto' são obrigatórios"}), 400

    current_user_id_str = get_jwt_identity()
    current_user_data = User.collection().find_one({"_id": ObjectId(current_user_id_str)})
    current_user = User.from_dict(current_user_data) # Converte para objeto User

    status = 'pendente'
    if current_user.role == ROLES['ADMIN']:
        status = data.get('status', 'pendente') # Administradores podem definir o status

    # Cria uma nova instância de Produto com os dados fornecidos
    new_product_instance = Product(
        codigo=data.get('codigo'),
        qtade_maxima_armazenada=data.get('qtade_maxima_armazenada'),
        nome_do_produto=data.get('nome_do_produto'),
        fornecedor=data.get('fornecedor'),
        estado_fisico=data.get('estado_fisico'),
        local_de_armazenamento=data.get('local_de_armazenamento'),
        substancia1=data.get('substancia1'),
        nCas1=data.get('nCas1'),
        concentracao1=data.get('concentracao1'),
        substancia2=data.get('substancia2'),
        nCas2=data.get('nCas2'),
        concentracao2=data.get('concentracao2'),
        substancia3=data.get('substancia3'),
        nCas3=data.get('nCas3'),
        concentracao3=data.get('concentracao3'),
        perigos_fisicos=data.get('perigos_fisicos', []), 
        perigos_saude=data.get('perigos_saude', []),
        perigos_meio_ambiente=data.get('perigos_meio_ambiente', []),
        palavra_de_perigo=data.get('palavra_de_perigo'),
        categoria=data.get('categoria'),
        status=status,
        created_by_user_id=current_user_id_str # Armazena o ID do usuário que criou o produto
    )

    # Insere o novo produto no banco de dados
    result = Product.collection().insert_one(new_product_instance.to_dict())
    new_product_instance._id = result.inserted_id # Atribui o ID gerado pelo MongoDB

    response_data = new_product_instance.to_dict()
    response_data['id'] = str(response_data.pop('_id')) # Renomeia '_id' para 'id' para a resposta
    return jsonify({"msg": "Produto criado com sucesso", "product": response_data}), 201

@product_bp.route('/products', methods=['GET'])
@role_required([ROLES['ADMIN'], ROLES['ANALYST'], ROLES['VIEWER']])
def get_products():
    """
    Retorna uma lista de produtos com base no papel do usuário logado.
    VIEWERs veem apenas produtos 'aprovados'.
    ANALYSTs veem 'aprovados' e os que eles criaram.
    ADMINs veem todos os produtos.
    """
    current_user_id_str = get_jwt_identity()
    current_user_data = User.collection().find_one({"_id": ObjectId(current_user_id_str)})
    current_user = User.from_dict(current_user_data) # Converte para objeto User

    query_filter = {}

    # Define o filtro de consulta com base no papel do usuário
    if current_user.role == ROLES['VIEWER']:
        query_filter = {"status": "aprovado"}
    elif current_user.role == ROLES['ANALYST']:
        query_filter = {
            "$or": [
                {"status": "aprovado"},
                {"created_by_user_id": current_user_id_str}
            ]
        }
    
    products_cursor = Product.collection().find(query_filter)
    
    products_list = []
    for p_data in products_cursor:
        product = Product.from_dict(p_data) # Converte para objeto Product
        
        product_dict = product.to_dict()
        product_dict['id'] = str(product_dict.pop('_id')) # Renomeia '_id' para 'id'
        
        # Busca o nome de usuário do criador do produto
        creator_user_data = User.collection().find_one({"_id": ObjectId(product.created_by_user_id)})
        creator_user = User.from_dict(creator_user_data) if creator_user_data else None
        product_dict['created_by'] = creator_user.username if creator_user else None
        
        products_list.append(product_dict)

    return jsonify(products_list), 200

@product_bp.route('/products/<product_id>', methods=['GET'])
@role_required([ROLES['ADMIN'], ROLES['ANALYST'], ROLES['VIEWER']])
def get_product(product_id):
    """
    Retorna os detalhes de um produto específico pelo ID.
    O acesso é restrito com base no papel do usuário e no status do produto.
    """
    try:
        product_data = Product.collection().find_one({"_id": ObjectId(product_id)})
    except Exception:
        return jsonify({"msg": "ID de produto inválido"}), 400

    if not product_data:
        return jsonify({"msg": "Produto não encontrado"}), 404

    product = Product.from_dict(product_data) # Converte para objeto Product

    current_user_id_str = get_jwt_identity()
    current_user_data = User.collection().find_one({"_id": ObjectId(current_user_id_str)})
    current_user = User.from_dict(current_user_data) # Converte para objeto User

    # Lógica de autorização baseada no papel do usuário
    if current_user.role == ROLES['VIEWER'] and product.status != 'aprovado':
        return jsonify({"msg": "Acesso negado: Este produto não está aprovado para visualização"}), 403
    elif current_user.role == ROLES['ANALYST'] and product.status != 'aprovado' and product.created_by_user_id != current_user_id_str:
        return jsonify({"msg": "Acesso negado: Este produto não está aprovado ou não foi criado por você"}), 403

    response_data = product.to_dict()
    response_data['id'] = str(response_data.pop('_id'))
    
    # Busca o nome de usuário do criador do produto
    creator_user_data = User.collection().find_one({"_id": ObjectId(product.created_by_user_id)})
    creator_user = User.from_dict(creator_user_data) if creator_user_data else None
    response_data['created_by'] = creator_user.username if creator_user else None
    return jsonify(response_data), 200

@product_bp.route('/products/<product_id>', methods=['PUT'])
@role_required([ROLES['ADMIN'], ROLES['ANALYST']])
def update_product(product_id):
    """
    Atualiza um produto existente pelo ID. Apenas para administradores e analistas.
    Analistas podem editar apenas seus próprios produtos pendentes.
    Administradores podem editar qualquer campo, incluindo o status.
    """
    try:
        product_data_from_db = Product.collection().find_one({"_id": ObjectId(product_id)})
    except Exception:
        return jsonify({"msg": "ID de produto inválido"}), 400

    if not product_data_from_db:
        return jsonify({"msg": "Produto não encontrado"}), 404
    
    product_to_update = Product.from_dict(product_data_from_db) # Converte para objeto Product

    current_user_id_str = get_jwt_identity()
    current_user_data = User.collection().find_one({"_id": ObjectId(current_user_id_str)})
    current_user = User.from_dict(current_user_data) # Converte para objeto User

    data = request.get_json()
    update_fields = {}

    # Lógica de autorização e campos permitidos para atualização para analistas
    if current_user.role == ROLES['ANALYST']:
        if product_to_update.created_by_user_id != current_user_id_str:
            return jsonify({"msg": "Acesso negado: Você só pode editar seus próprios produtos"}), 403
        if product_to_update.status == 'aprovado':
            return jsonify({"msg": "Acesso negado: Produtos aprovados não podem ser editados por Analistas"}), 403
        
        if 'status' in data: # Analistas não podem alterar o status
            return jsonify({"msg": "Analistas não podem alterar o status do produto"}), 403

    # Copia os campos do payload para update_fields, excluindo _id, status e created_by_user_id
    # A atualização do status é tratada separadamente para administradores
    for key, value in data.items():
        if key in product_to_update.to_dict() and key not in ['_id', 'status', 'created_by_user_id']:
            update_fields[key] = value

    # Administradores podem atualizar o status
    if current_user.role == ROLES['ADMIN'] and 'status' in data:
        new_status = data['status']
        if new_status in ['pendente', 'aprovado', 'rejeitado']:
            update_fields['status'] = new_status
        else:
            return jsonify({"msg": "Status inválido"}), 400
    
    if update_fields:
        Product.collection().update_one({"_id": ObjectId(product_id)}, {"$set": update_fields})
        updated_product_data = Product.collection().find_one({"_id": ObjectId(product_id)})
        updated_product_instance = Product.from_dict(updated_product_data)
        
        response_data = updated_product_instance.to_dict()
        response_data['id'] = str(response_data.pop('_id'))
        
        # Busca o nome de usuário do criador para incluir na resposta
        creator_user_data = User.collection().find_one({"_id": ObjectId(updated_product_instance.created_by_user_id)})
        creator_user = User.from_dict(creator_user_data) if creator_user_data else None
        response_data['created_by'] = creator_user.username if creator_user else None
        return jsonify({"msg": "Produto atualizado com sucesso", "product": response_data}), 200
    else:
        return jsonify({"msg": "Nenhum dado para atualizar"}), 400

@product_bp.route('/products/<product_id>', methods=['DELETE'])
@role_required([ROLES['ADMIN']])
def delete_product(product_id):
    """
    Deleta um produto pelo ID. Apenas para administradores.
    """
    try:
        result = Product.collection().delete_one({"_id": ObjectId(product_id)})
    except Exception:
        return jsonify({"msg": "ID de produto inválido"}), 400

    if result.deleted_count == 0:
        return jsonify({"msg": "Produto não encontrado"}), 404
    return jsonify({"msg": "Produto deletado com sucesso"}), 200

@product_bp.route('/products/search', methods=['GET'])
@role_required([ROLES['ADMIN'], ROLES['ANALYST'], ROLES['VIEWER']])
def search_products():
    """
    Pesquisa produtos com base em um critério (nome, código, ID, substância, categoria, fornecedor).
    O acesso aos resultados é restrito com base no papel do usuário.
    """
    query_param = request.args.get('q', '').strip()
    search_by = request.args.get('by', 'nome_do_produto')

    current_user_id_str = get_jwt_identity()
    current_user_data = User.collection().find_one({"_id": ObjectId(current_user_id_str)})
    current_user = User.from_dict(current_user_data) # Converte para objeto User

    query_filter = {}

    # Define o filtro inicial baseado no papel do usuário
    if current_user.role == ROLES['VIEWER']:
        query_filter["status"] = "aprovado"
    elif current_user.role == ROLES['ANALYST']:
        query_filter["$or"] = [
            {"status": "aprovado"},
            {"created_by_user_id": current_user_id_str}
        ]

    if query_param:
        # Adiciona o filtro de pesquisa ao query_filter
        if search_by == 'nome_do_produto':
            query_filter['nome_do_produto'] = {'$regex': query_param, '$options': 'i'}
        elif search_by == 'codigo':
            query_filter['codigo'] = {'$regex': query_param, '$options': 'i'}
        elif search_by == 'id':
            try:
                query_filter['_id'] = ObjectId(query_param)
            except Exception:
                return jsonify({"msg": "ID inválido"}), 400
        elif search_by in ['substancia1', 'substancia2', 'substancia3']:
            # Se a pesquisa é por uma substância específica
            query_filter[search_by] = {'$regex': query_param, '$options': 'i'}
        elif search_by == 'categoria':
            query_filter['categoria'] = {'$regex': query_param, '$options': 'i'}
        elif search_by == 'fornecedor':
            query_filter['fornecedor'] = {'$regex': query_param, '$options': 'i'}
        else:
            return jsonify({"msg": "Campo de pesquisa inválido. Use 'nome_do_produto', 'codigo', 'id', 'substancia1', 'substancia2', 'substancia3', 'categoria' ou 'fornecedor'"}), 400
    
    products_cursor = Product.collection().find(query_filter)
    
    products_list = []
    for p_data in products_cursor:
        product = Product.from_dict(p_data)
        product_dict = product.to_dict()
        product_dict['id'] = str(product_dict.pop('_id'))
        
        # Busca o nome de usuário do criador para incluir na resposta
        creator_user_data = User.collection().find_one({"_id": ObjectId(product.created_by_user_id)})
        creator_user = User.from_dict(creator_user_data) if creator_user_data else None
        product_dict['created_by'] = creator_user.username if creator_user else None
        products_list.append(product_dict)

    return jsonify(products_list), 200

