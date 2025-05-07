# Use a imagem base oficial do Python
FROM python:3.9

# Defina o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copie os arquivos de requisitos para o diretório de trabalho
COPY requirements.txt .

# Instale as dependências necessárias
RUN pip install --no-cache-dir -r requirements.txt

# Copie todo o conteúdo do diretório atual para o diretório de trabalho no contêiner
COPY . .

# Exponha a porta na qual a aplicação irá rodar
EXPOSE 5000

COPY ./quimidocs /app/quimidocs

# Defina o comando para executar a aplicação
CMD ["flask", "run", "--host=0.0.0.0"]
