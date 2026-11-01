# Research: Contrato da API da loja

## Decisão 1: linha do tempo única, sem estado
- **Decisão**: cada cenário ocupa uma janela absoluta própria; consultas por `servico`, `inicio`,
  `fim` e `cenario` opcional.
- **Razão**: determinismo para gravar `dados_dummy/`; mesma consulta funciona com serviços
  reais (que só conhecem tempo absoluto). Jev, confiança 0.94.
- **Alternativas**: rotas por cenário com minutos relativos (sem tempo absoluto, quebra a regra
  "deploy antes do sintoma"); manter estado com relógio real (gravação lenta e não determinística).

## Decisão 2: versão da conversa `erro_investigado`
- **Decisão**: tag real `pedidos-api/v3.2.0`; a sessão do agente troca `v3.8.1` no texto.
- **Razão**: tags imutáveis; `comparar_versoes` usa o GitHub real. Jev, confiança 0.98.

## Decisão 3: rota com estado `POST /cenarios/{id}`
- **Decisão**: removida do contrato 1.0; injeção de falha documentada para a opção 2.
- **Razão**: nenhum consumidor; escopo mínimo. Jev 0.66; conductor decidiu (opção A).

## Decisão 4: semente por cenário e minuto
- **Decisão**: `Random(crc32(f"{cenario}:{minuto}"))` em vez de um gerador por cenário.
- **Razão**: o valor de um minuto não depende de quais minutos foram consultados antes.

## Decisão 5: fuso e formato de horário
- **Decisão**: ISO 8601 com `-03:00` nas respostas; entrada sem fuso vale como -03:00.

## Decisão 6: filtro `nivel` exato
- **Decisão**: `nivel=ERROR` devolve só ERROR (não "ERROR ou mais grave").
- **Razão**: só três níveis; filtro exato é previsível para a ferramenta.

## Decisão 7: limites
- **Decisão**: janela até 6 horas (422 acima); `limite` de logs padrão 500, máximo 5000.
- **Razão**: série por minuto de 6 horas = 360 pontos por métrica; resposta pequena.
