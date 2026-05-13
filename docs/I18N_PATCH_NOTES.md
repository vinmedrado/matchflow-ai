# MatchFlow v7 — i18n Patch Notes

Patch aplicado para adicionar suporte de idioma PT/EN/ES no frontend sem recriar o projeto.

## Alterações principais

- Mantido e ampliado o seletor de idioma existente.
- Idiomas disponíveis: Português, English e Español.
- Idioma padrão: Português.
- Idioma salvo em `localStorage` via chave `matchflow_language`.
- Adicionado seletor de idioma também na landing page pública.
- Adicionada camada `TranslationRuntime` para traduzir textos hardcoded que ainda estavam espalhados nas páginas premium.
- Corrigido `.env.example` do frontend com `VITE_API_BASE=http://127.0.0.1:8000`, compatível com `src/api/client.js`.

## Validação

- Build do frontend executado com sucesso usando `npm install` + `npm run build`.

## Observação

O patch prioriza a interface visual do frontend. Textos dinâmicos vindos da API/backend podem continuar no idioma original do payload até serem internacionalizados na camada de resposta.
