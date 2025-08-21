# Dockerfile (backend)
FROM python:3.11-slim

# Diretório de trabalho dentro do container
WORKDIR /app

# Copia o arquivo de dependências
COPY requirements.txt .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o restante da aplicação para dentro do container
COPY . .

# Define as variáveis de ambiente para o Flask
ENV FLASK_APP=run.py
ENV FLASK_ENV=development
ENV PYTHONUNBUFFERED=1

# Expõe a porta 5000
EXPOSE 5000

# Comando padrão para iniciar o Flask
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000", "--reload"]
