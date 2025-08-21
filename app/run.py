# run.py

import os
import sys

# Adiciona o diretório raiz do projeto ao sys.path
# Isso garante que Python pode encontrar o pacote 'app'
# independentemente de onde 'run.py' é executado.
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)

