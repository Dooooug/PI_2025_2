# app/security_config.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import request, has_request_context, jsonify
import logging
import os

def get_limiter_key():
    """
    Obtém chave única para rate limiting combinando IP e usuário quando disponível
    """
    if not has_request_context():
        return "global"
    
    # Para rotas autenticadas, podemos usar o ID do usuário
    from flask_jwt_extended import get_jwt_identity
    current_user_id = get_jwt_identity()
    
    if current_user_id:
        return f"{get_remote_address()}:{current_user_id}"
    
    return get_remote_address()

def init_security(app):
    """
    Inicializa todas as configurações de segurança da aplicação
    """
    # Configuração do rate limiter
    storage_uri = os.getenv('REDIS_URL', 'memory://')
    
    global limiter
    limiter = Limiter(
        key_func=get_limiter_key,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=storage_uri,
        strategy="fixed-window",
        on_breach=rate_limit_breach_handler
    )
    
    # Configurações de logging de segurança
    setup_security_logging()
    
    # Registrar handlers de erro
    register_error_handlers(app)

def rate_limit_breach_handler(request_limit):
    """
    Handler para quando o rate limit é excedido
    """
    client_ip = get_remote_address()
    logging.warning(
        f"Rate limit exceeded - IP: {client_ip}, "
        f"Endpoint: {request_limit.endpoint}, "
        f"Limit: {request_limit.limit}"
    )

def setup_security_logging():
    """
    Configura logging para segurança
    """
    # Criar diretório de logs se não existir
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configurar um handler separado para logs de segurança
    security_handler = logging.FileHandler('logs/security.log')
    security_handler.setLevel(logging.WARNING)
    security_handler.setFormatter(logging.Formatter(
        '%(asctime)s - SECURITY - %(levelname)s - %(message)s'
    ))
    
    # Adicionar handler ao logger de segurança
    security_logger = logging.getLogger('security')
    security_logger.addHandler(security_handler)
    security_logger.propagate = False

def register_error_handlers(app):
    """
    Registra handlers de erro globalmente
    """
    @app.errorhandler(429)
    def ratelimit_handler(e):
        """Handler personalizado para erros de rate limiting"""
        return jsonify({
            "error": "Limite de requisições excedido",
            "message": "Muitas requisições em um curto período. Tente novamente mais tarde.",
            "retry_after": 60
        }), 429

# Configurações específicas por rota
RATE_LIMITS = {
    'login': "5 per minute",
    'register': "3 per hour", 
    'upload': "10 per hour",
    'delete': "5 per hour",
    'general': "100 per hour",
    'health': "30 per minute"
}

# Inicialização será feita pela função init_security
limiter = None