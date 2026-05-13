# Validação do Sistema

## Health público

```bash
curl http://127.0.0.1:8000/health
```

## Login

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@matchflow.local","password":"admin123"}'
```

## Status protegido

Use o token retornado no login:

```bash
curl http://127.0.0.1:8000/api/system/status \
  -H "Authorization: Bearer TOKEN_AQUI"
```

O status retorna disponibilidade do dataset, tamanho, timestamp, cache, relatório de qualidade, Ollama, versão e uptime.
