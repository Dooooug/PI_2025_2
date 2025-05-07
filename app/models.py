from . import db, bcrypt
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(500), nullable=False)
    email = db.Column(db.String(500), unique=True, nullable=False)
    senha_hash = db.Column(db.String(500), nullable=False)

    def set_password(self, password):
        self.senha_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.senha_hash, password)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), nullable=False)
    qtade_maxima_armazenada = db.Column(db.String(50), nullable=True)
    nome_do_produto = db.Column(db.String(200), nullable=False)
    fornecedor = db.Column(db.String(200), nullable=True)
    estado_fisico = db.Column(db.String(50), nullable=True)
    local_de_armazenamento = db.Column(db.String(100), nullable=True)
    substancia1 = db.Column(db.String(200), nullable=True)
    nCas1 = db.Column(db.String(50), nullable=True)
    concentracao1 = db.Column(db.String(50), nullable=True)
    substancia2 = db.Column(db.String(200), nullable=True)
    nCas2 = db.Column(db.String(50), nullable=True)
    concentracao2 = db.Column(db.String(50), nullable=True)
    substancia3 = db.Column(db.String(200), nullable=True)
    nCas3 = db.Column(db.String(50), nullable=True)
    concentracao3 = db.Column(db.String(50), nullable=True)
    perigos_fisicos = db.Column(db.Text, nullable=True)
    perigos_saude = db.Column(db.Text, nullable=True)
    perigos_meio_ambiente = db.Column(db.Text, nullable=True)
    palavra_de_perigo = db.Column(db.String(50), nullable=True)
    categoria = db.Column(db.String(50), nullable=True)
