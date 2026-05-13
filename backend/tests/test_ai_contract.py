from __future__ import annotations


def test_ai_ask_answer_contract(client, auth_headers):
    response = client.post(
        '/api/ai/ask',
        json={'question': 'Qual é o status geral da base?'},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body['ok'] is True
    assert body['mode'] in ['ollama', 'fallback']
    assert 'model' in body
    assert 'answer' in body
    assert 'summary' in body['answer']
    assert 'insights' in body['answer']
    assert 'technical_notes' in body['answer']
    assert isinstance(body['answer']['summary'], str)
    assert isinstance(body['answer']['insights'], list)
    assert isinstance(body['answer']['technical_notes'], list)
    assert 'resumo' not in body['answer']
    assert 'observacoes_tecnicas' not in body['answer']
