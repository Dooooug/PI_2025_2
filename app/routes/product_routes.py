from flask_cors import CORS  # Importação do Flask-CORS
from flask import request, jsonify
from .. import db
from ..models import Product
from flask import current_app as app

app.secret_key = 204314

# Adicionar o CORS ao app
CORS(app)  # Habilita o CORS para todas as rotas

@app.route('/products', methods=['POST'])
def add_product():
    data = request.get_json()
    
    # Verificação dos campos obrigatórios
    if not data or 'codigo' not in data or 'nome_do_produto' not in data:
        return jsonify({"error": "Campos obrigatórios faltando"}), 400

    new_product = Product(
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
        perigos_fisicos=','.join(data.get('perigos_fisicos', [])),
        perigos_saude=','.join(data.get('perigos_saude', [])),
        perigos_meio_ambiente=','.join(data.get('perigos_meio_ambiente', [])),
        palavra_de_perigo=data.get('palavra_de_perigo'),
        categoria=data.get('categoria')
    )

    db.session.add(new_product)
    db.session.commit()

    return jsonify({"message": "Produto adicionado com sucesso!", "product": {
        "id": new_product.id,
        "codigo": new_product.codigo,
        "qtade_maxima_armazenada": new_product.qtade_maxima_armazenada,
        "nome_do_produto": new_product.nome_do_produto,
        "fornecedor": new_product.fornecedor,
        "estado_fisico": new_product.estado_fisico,
        "local_de_armazenamento": new_product.local_de_armazenamento,
        "substancia1": new_product.substancia1,
        "nCas1": new_product.nCas1,
        "concentracao1": new_product.concentracao1,
        "substancia2": new_product.substancia2,
        "nCas2": new_product.nCas2,
        "concentracao2": new_product.concentracao2,
        "substancia3": new_product.substancia3,
        "nCas3": new_product.nCas3,
        "concentracao3": new_product.concentracao3,
        "perigos_fisicos": new_product.perigos_fisicos.split(','),
        "perigos_saude": new_product.perigos_saude.split(','),
        "perigos_meio_ambiente": new_product.perigos_meio_ambiente.split(','),
        "palavra_de_perigo": new_product.palavra_de_perigo,
        "categoria": new_product.categoria
    }}), 201

@app.route('/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    products_list = [{
        "id": p.id,
        "codigo": p.codigo,
        "qtade_maxima_armazenada": p.qtade_maxima_armazenada,
        "nome_do_produto": p.nome_do_produto,
        "fornecedor": p.fornecedor,
        "estado_fisico": p.estado_fisico,
        "local_de_armazenamento": p.local_de_armazenamento,
        "substancia1": p.substancia1,
        "nCas1": p.nCas1,
        "concentracao1": p.concentracao1,
        "substancia2": p.substancia2,
        "nCas2": p.nCas2,
        "concentracao2": p.concentracao2,
        "substancia3": p.substancia3,
        "nCas3": p.nCas3,
        "concentracao3": p.concentracao3,
        "perigos_fisicos": p.perigos_fisicos.split(','),
        "perigos_saude": p.perigos_saude.split(','),
        "perigos_meio_ambiente": p.perigos_meio_ambiente.split(','),
        "palavra_de_perigo": p.palavra_de_perigo,
        "categoria": p.categoria
    } for p in products]

    return jsonify(products_list), 200
    
if __name__ == '__main__':
    app.run(debug=True)
    
