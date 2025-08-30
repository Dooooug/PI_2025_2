# app/security_middleware.py
import time
import hashlib
from flask import request, jsonify
import logging
from datetime import datetime, timedelta
import re

class SecurityMiddleware:
    """Middleware de segurança para proteção adicional"""
    
    def __init__(self, app):
        self.app = app
        self.failed_attempts = {}
        self.blocked_ips = {}
        self.suspicious_activities = {}
        
        # Configurações
        self.MAX_FAILED_ATTEMPTS = 10  # Máximo de tentativas falhas por IP
        self.BLOCK_TIME = 900  # 15 minutos em segundos
        self.SUSPICIOUS_THRESHOLD = 5  # Limite para atividades suspeitas
        
    def __call__(self, environ, start_response):
        """Middleware principal que intercepta todas as requisições"""
        client_ip = self.get_client_ip(environ)
        
        # Verificar se IP está bloqueado
        if self.is_ip_blocked(client_ip):
            return self.blocked_response(start_response)
        
        # Verificar atividades suspeitas
        if self.check_suspicious_activity(environ, client_ip):
            return self.suspicious_response(start_response)
        
        # Processar a requisição normalmente
        return self.app(environ, start_response)
    
    def get_client_ip(self, environ):
        """Obtém o IP real do cliente considerando proxies"""
        # Tentar obter IP de headers comuns de proxy
        for header in ['HTTP_X_FORWARDED_FOR', 'HTTP_X_REAL_IP', 'REMOTE_ADDR']:
            ip = environ.get(header)
            if ip:
                # Em caso de múltiplos IPs (X-Forwarded-For), pegar o primeiro
                if ',' in ip:
                    ip = ip.split(',')[0].strip()
                return ip
        return 'unknown'
    
    def is_ip_blocked(self, client_ip):
        """Verifica se o IP está bloqueado temporariamente"""
        if client_ip in self.blocked_ips:
            block_until = self.blocked_ips[client_ip]
            if time.time() < block_until:
                return True
            else:
                # Remover bloqueio expirado
                del self.blocked_ips[client_ip]
        return False
    
    def check_suspicious_activity(self, environ, client_ip):
        """Verifica atividades suspeitas na requisição"""
        path = environ.get('PATH_INFO', '')
        method = environ.get('REQUEST_METHOD', '')
        user_agent = environ.get('HTTP_USER_AGENT', '')
        
        # 1. Verificar User-Agent suspeito ou ausente
        if not user_agent or len(user_agent) < 10:
            self.record_suspicious_activity(client_ip, "Missing User-Agent")
            return True
        
        # 2. Verificar padrões de SQL injection em parâmetros
        if self.detect_sql_injection(environ):
            self.record_suspicious_activity(client_ip, "SQL Injection attempt")
            return True
        
        # 3. Verificar caminhos sensíveis acessados frequentemente
        if self.is_sensitive_path(path) and self.is_high_frequency(client_ip):
            self.record_suspicious_activity(client_ip, "High frequency on sensitive path")
            return True
        
        return False
    
    def detect_sql_injection(self, environ):
        """Detecta tentativas básicas de SQL injection"""
        # Verificar query string
        query_string = environ.get('QUERY_STRING', '')
        injection_patterns = [
            r'union.*select',
            r'select.*from',
            r'insert.*into',
            r'delete.*from',
            r'drop.*table',
            r'--',
            r'/\*',
            r'waitfor.*delay',
            r'xp_cmdshell'
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, query_string, re.IGNORECASE):
                return True
        
        # Verificar corpo da requisição para POST/PUT
        if environ['REQUEST_METHOD'] in ['POST', 'PUT']:
            try:
                # Tentar ler o conteúdo do corpo (apenas para verificação)
                content_length = int(environ.get('CONTENT_LENGTH', 0))
                if content_length > 0:
                    request_body = environ['wsgi.input'].read(content_length)
                    environ['wsgi.input'] = type('', (object,), {'read': lambda: request_body})()
                    
                    for pattern in injection_patterns:
                        if re.search(pattern, request_body.decode('utf-8', 'ignore'), re.IGNORECASE):
                            return True
            except:
                pass
        
        return False
    
    def is_sensitive_path(self, path):
        """Identifica caminhos sensíveis que precisam de proteção extra"""
        sensitive_paths = [
            '/login',
            '/register',
            '/upload',
            '/users/',
            '/products/'
        ]
        
        return any(path.startswith(p) for p in sensitive_paths)
    
    def is_high_frequency(self, client_ip):
        """Verifica se há muitas requisições em curto período"""
        current_time = time.time()
        
        # Manter registro das últimas requisições
        if client_ip not in self.suspicious_activities:
            self.suspicious_activities[client_ip] = []
        
        # Adicionar timestamp atual
        self.suspicious_activities[client_ip].append(current_time)
        
        # Manter apenas registros dos últimos 60 segundos
        self.suspicious_activities[client_ip] = [
            t for t in self.suspicious_activities[client_ip] 
            if current_time - t < 60
        ]
        
        # Se mais de 30 requisições em 60 segundos, considerar suspeito
        return len(self.suspicious_activities[client_ip]) > 30
    
    def record_suspicious_activity(self, client_ip, reason):
        """Registra atividade suspeita e incrementa contador"""
        logging.warning(f"Suspicious activity detected - IP: {client_ip}, Reason: {reason}")
        
        if client_ip not in self.failed_attempts:
            self.failed_attempts[client_ip] = 0
        
        self.failed_attempts[client_ip] += 1
        
        # Se exceder o limite, bloquear IP
        if self.failed_attempts[client_ip] >= self.MAX_FAILED_ATTEMPTS:
            self.blocked_ips[client_ip] = time.time() + self.BLOCK_TIME
            logging.warning(f"IP blocked: {client_ip} for {self.BLOCK_TIME} seconds")
    
    def blocked_response(self, start_response):
        """Resposta para IPs bloqueados"""
        start_response('429 Too Many Requests', [
            ('Content-Type', 'application/json'),
            ('Retry-After', str(self.BLOCK_TIME))
        ])
        return [json.dumps({
            "error": "Acesso temporariamente bloqueado",
            "message": "Muitas tentativas suspeitas detectadas. Tente novamente em 15 minutos.",
            "retry_after": self.BLOCK_TIME
        }).encode()]
    
    def suspicious_response(self, start_response):
        """Resposta para atividades suspeitas"""
        start_response('400 Bad Request', [
            ('Content-Type', 'application/json')
        ])
        return [json.dumps({
            "error": "Atividade suspeita detectada",
            "message": "Sua requisição foi identificada como suspeita."
        }).encode()]

# Função auxiliar para inicializar o middleware
def init_security_middleware(app):
    """Inicializa e configura o middleware de segurança"""
    app.wsgi_app = SecurityMiddleware(app.wsgi_app)
    logging.info("Security middleware initialized")
    return app