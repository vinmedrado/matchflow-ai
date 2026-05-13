# Middleware de Autenticação Local

O middleware global protege todas as rotas privadas.

## Rotas públicas

- `/health`
- `/api/auth/login`
- `/docs`
- `/redoc`
- `/openapi.json`

## Rotas privadas

Todas as demais rotas exigem:

```http
Authorization: Bearer <token>
```

Tokens expirados retornam HTTP 401 padronizado.
