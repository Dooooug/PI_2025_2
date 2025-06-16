# Use imagem Python oficial
FROM python:3.10-slim

# Define diretório de trabalho
WORKDIR /app

# Copia apenas o requirements.txt primeiro para instalar dependências
COPY requirements.txt .

# Instala dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o projeto
COPY . .

# Expõe a porta 5000
EXPOSE 5000

# Define variável para Flask localizar o app
ENV FLASK_APP=run.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

# Usa Flask CLI para rodar a aplicação
CMD ["flask", "run"]
