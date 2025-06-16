import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv
import logging
import io

# --- Configuração do carregamento de variáveis de ambiente ---
# Encontra o diretório pai do arquivo atual (que é o diretório raiz do projeto)
basedir = os.path.abspath(os.path.dirname(__file__))
# Constrói o caminho completo para o arquivo .env
dotenv_path = os.path.join(basedir, '.env')
print(f"Tentando carregar .env de: {dotenv_path}") # Linha de debug: mostra de onde o .env está sendo carregado
load_dotenv(dotenv_path)
# --- Fim da configuração ---

# Configura o logging para exibir mensagens informativas
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_aws_s3_access():
    """
    Testa o acesso à AWS S3 usando credenciais e configurações do bucket.
    Verifica se as credenciais são válidas, se a região está correta
    e se é possível realizar operações básicas de S3 (listar, upload, delete).
    """
    # 1. Obter variáveis de ambiente
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = os.getenv('AWS_REGION')
    s3_bucket_name = os.getenv('S3_BUCKET_NAME')

    # Debug: Imprime os valores lidos (NÃO faça isso em produção com chaves secretas!)
    print(f"AWS_ACCESS_KEY_ID: {aws_access_key_id}")
    # Usa asteriscos para evitar imprimir a chave secreta completa
    print(f"AWS_SECRET_ACCESS_KEY: {'*' * len(aws_secret_access_key) if aws_secret_access_key else 'None'}")
    print(f"AWS_REGION: {aws_region}")
    print(f"S3_BUCKET_NAME: {s3_bucket_name}")

    # Verifica se todas as variáveis necessárias estão definidas
    if not all([aws_access_key_id, aws_secret_access_key, aws_region, s3_bucket_name]):
        logging.error("Erro: Uma ou mais variáveis de ambiente AWS (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME) não estão definidas.")
        logging.info("Por favor, certifique-se de que seu arquivo .env está configurado corretamente ou que as variáveis estão definidas no ambiente.")
        return False

    logging.info(f"Testando acesso AWS S3 para a região: {aws_region}, bucket: {s3_bucket_name}")

    s3_client = None
    try:
        # 2. Inicializar o cliente S3
        logging.info("Tentando inicializar o cliente S3...")
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region
        )
        logging.info("Cliente S3 inicializado com sucesso.")

        # 3. Testar listagem de buckets (verifica a validade geral das credenciais e conexão)
        logging.info("Tentando listar buckets S3 para verificar as credenciais...")
        s3_client.list_buckets()
        logging.info("Sucesso: Credenciais AWS são válidas e a conexão com o S3 está funcionando.")

        # 4. Tentar fazer upload de um arquivo de teste para o bucket
        test_file_content = "Este é um arquivo de teste para verificar o upload para o S3."
        test_file_name = "s3-test-file.txt"
        s3_object_key = f"test_uploads/{test_file_name}" # Caminho dentro do bucket

        logging.info(f"Tentando fazer upload do arquivo '{test_file_name}' para o bucket '{s3_bucket_name}'...")
        
        # io.BytesIO cria um arquivo em memória a partir de bytes.
        with io.BytesIO(test_file_content.encode('utf-8')) as file_obj:
            s3_client.upload_fileobj(file_obj, s3_bucket_name, s3_object_key)
        
        logging.info(f"Sucesso: Arquivo '{test_file_name}' enviado para s3://{s3_bucket_name}/{s3_object_key}")

        # 5. Tentar deletar o arquivo de teste
        logging.info(f"Tentando deletar o arquivo '{s3_object_key}' do bucket '{s3_bucket_name}'...")
        s3_client.delete_object(Bucket=s3_bucket_name, Key=s3_object_key)
        logging.info(f"Sucesso: Arquivo '{s3_object_key}' deletado do S3.")

        logging.info("Teste de acesso AWS S3 concluído com sucesso!")
        return True

    # --- INÍCIO DA CORREÇÃO DA INDENTAÇÃO ---
    except NoCredentialsError:
        logging.error("Erro: Credenciais AWS não encontradas. Certifique-se de que AWS_ACCESS_KEY_ID e AWS_SECRET_ACCESS_KEY estão definidos corretamente.")
        return False
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logging.error(f"Erro AWS ClientError ({error_code}): {error_message}")
        if error_code == 'InvalidAccessKeyId' or error_code == 'SignatureDoesNotMatch':
            logging.error("Verifique suas chaves de acesso AWS (AWS_ACCESS_KEY_ID e AWS_SECRET_ACCESS_KEY). Elas podem estar incorretas.")
        elif error_code == 'NoSuchBucket':
            logging.error(f"O bucket '{s3_bucket_name}' não existe ou você não tem permissão para acessá-lo. Verifique o nome do bucket e a região.")
        elif error_code == 'AccessDenied':
            logging.error(f"Acesso negado ao bucket '{s3_bucket_name}'. Verifique as permissões IAM para o seu usuário AWS. O usuário precisa de permissões para 's3:ListAllMyBuckets', 's3:PutObject' e 's3:DeleteObject'.")
        elif error_code == 'InvalidRegion':
            logging.error(f"A região AWS '{aws_region}' está incorreta para suas credenciais ou para o bucket. Verifique se a região corresponde à do bucket.")
        else:
            logging.error(f"Erro inesperado do cliente AWS: {e}")
        return False
    except Exception as e:
        logging.error(f"Um erro inesperado ocorreu durante o teste: {e}")
        return False
    # --- FIM DA CORREÇÃO DA INDENTAÇÃO ---

if __name__ == "__main__":
    if test_aws_s3_access():
        print("\nTodos os testes de acesso ao AWS S3 foram bem-sucedidos!")
    else:
        print("\nFalha em um ou mais testes de acesso ao AWS S3. Verifique os logs acima para detalhes.")

