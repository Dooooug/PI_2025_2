from pymongo.collection import Collection
from bson.objectid import ObjectId

class User:
    _collection: Collection = None

    def __init__(self, username, email, password_hash, role, _id=None): # Adicionado 'email'
        self._id = _id
        self.username = username
        self.email = email # Novo atributo
        self.password_hash = password_hash
        self.role = role

    @classmethod
    def set_collection(cls, collection_instance: Collection):
        """
        Define a instância da coleção MongoDB para a classe User.
        Esta função é chamada uma vez durante a inicialização da aplicação.
        """
        cls._collection = collection_instance

    @classmethod
    def collection(cls) -> Collection:
        """
        Retorna a instância da coleção MongoDB para a classe User.
        Levanta um erro se a coleção não tiver sido definida.
        """
        if cls._collection is None:
            raise RuntimeError("MongoDB collection for User is not set. Call User.set_collection() during app initialization.")
        return cls._collection

    def to_dict(self):
        """
        Converte o objeto User em um dicionário para inserção/atualização no MongoDB.
        Inclui '_id' apenas se não for None.
        """
        data = {
            "username": self.username,
            "email": self.email, # Incluído no dicionário
            "password_hash": self.password_hash,
            "role": self.role
        }
        # Adiciona _id ao dicionário APENAS se ele não for None
        # Isso permite que o MongoDB gere um ObjectId para novas inserções
        if self._id is not None:
            data["_id"] = self._id
        return data

    @staticmethod
    def from_dict(data):
        """Cria um objeto User a partir de um dicionário (geralmente do MongoDB)."""
        return User(
            _id=data.get('_id'),
            username=data.get('username'),
            email=data.get('email'), # Incluído na criação do objeto a partir do dicionário
            password_hash=data.get('password_hash'),
            role=data.get('role')
        )

class Product:
    _collection: Collection = None

    def __init__(self, codigo, qtade_maxima_armazenada, nome_do_produto, fornecedor, estado_fisico,
                 local_de_armazenamento, substancia1, nCas1, concentracao1, substancia2, nCas2,
                 concentracao2, substancia3, nCas3, concentracao3, perigos_fisicos, perigos_saude,
                 perigos_meio_ambiente, palavra_de_perigo, categoria, status, created_by_user_id,
                 pdf_url=None, pdf_s3_key=None, _id=None): # NOVOS CAMPOS AQUI
        self._id = _id
        self.codigo = codigo
        self.qtade_maxima_armazenada = qtade_maxima_armazenada
        self.nome_do_produto = nome_do_produto
        self.fornecedor = fornecedor
        self.estado_fisico = estado_fisico
        self.local_de_armazenamento = local_de_armazenamento
        self.substancia1 = substancia1
        self.nCas1 = nCas1
        self.concentracao1 = concentracao1
        self.substancia2 = substancia2
        self.nCas2 = nCas2
        self.concentracao2 = concentracao2
        self.substancia3 = substancia3
        self.nCas3 = nCas3
        self.concentracao3 = concentracao3
        self.perigos_fisicos = perigos_fisicos
        self.perigos_saude = perigos_saude
        self.perigos_meio_ambiente = perigos_meio_ambiente
        self.palavra_de_perigo = palavra_de_perigo
        self.categoria = categoria
        self.status = status
        self.created_by_user_id = created_by_user_id
        self.pdf_url = pdf_url # NOVO CAMPO
        self.pdf_s3_key = pdf_s3_key # NOVO CAMPO

    @classmethod
    def set_collection(cls, collection_instance: Collection):
        """
        Define a instância da coleção MongoDB para a classe Product.
        Esta função é chamada uma vez durante a inicialização da aplicação.
        """
        cls._collection = collection_instance

    @classmethod
    def collection(cls) -> Collection:
        """
        Retorna a instância da coleção MongoDB para a classe Product.
        Levanta um erro se a coleção não tiver sido definida.
        """
        if cls._collection is None:
            raise RuntimeError("MongoDB collection for Product is not set. Call Product.set_collection() during app initialization.")
        return cls._collection

    def to_dict(self):
        """
        Converte o objeto Product em um dicionário para inserção/atualização no MongoDB.
        Inclui '_id' apenas se não for None.
        """
        data = {
            "codigo": self.codigo,
            "qtade_maxima_armazenada": self.qtade_maxima_armazenada,
            "nome_do_produto": self.nome_do_produto,
            "fornecedor": self.fornecedor,
            "estado_fisico": self.estado_fisico,
            "local_de_armazenamento": self.local_de_armazenamento,
            "substancia1": self.substancia1,
            "nCas1": self.nCas1,
            "concentracao1": self.concentracao1,
            "substancia2": self.substancia2,
            "nCas2": self.nCas2,
            "concentracao2": self.concentracao2,
            "substancia3": self.substancia3,
            "nCas3": self.nCas3,
            "concentracao3": self.concentracao3,
            "perigos_fisicos": self.perigos_fisicos,
            "perigos_saude": self.perigos_saude,
            "perigos_meio_ambiente": self.perigos_meio_ambiente,
            "palavra_de_perigo": self.palavra_de_perigo,
            "categoria": self.categoria,
            "status": self.status,
            "created_by_user_id": self.created_by_user_id,
            "pdf_url": self.pdf_url, # NOVO CAMPO NO to_dict
            "pdf_s3_key": self.pdf_s3_key # NOVO CAMPO NO to_dict
        }
        # Adiciona _id ao dicionário APENAS se ele não for None
        # Isso permite que o MongoDB gere um ObjectId para novas inserções
        if self._id is not None:
            data["_id"] = self._id
        return data

    @staticmethod
    def from_dict(data):
        """Cria um objeto Product a partir de um dicionário (geralmente do MongoDB)."""
        return Product(
            _id=data.get('_id'),
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
            status=data.get('status'),
            created_by_user_id=data.get('created_by_user_id'),
            pdf_url=data.get('pdf_url'), # NOVO CAMPO NO from_dict
            pdf_s3_key=data.get('pdf_s3_key') # NOVO CAMPO NO from_dict
        )
