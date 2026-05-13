# Demo Mode

O modo demo permite abrir o MatchFlow sem depender de scraping real ou APIs pagas.

## Rodar local

```bash
cp .env.example .env
# mantenha DEMO_MODE=true
uvicorn backend.main:app --host 127.0.0.1 --port 8000
cd frontend && npm install && npm run dev
```

Usuário demo local:

- e-mail: `admin@matchflow.local`
- senha: `admin123`

## Roteiro de apresentação

1. Dashboard: visão executiva.
2. Data Operations: status do Data Engine e outputs.
3. AI Copilot Premium: explicabilidade e perguntas.
4. Executive Cockpit: decisões, governance e riscos.
5. Evolution Cockpit: evolução cognitiva e autopreservação.

Regra de segurança: demo é `PAPER_TRADING_SIMULATION_ONLY`; nenhuma aposta real é executada.
