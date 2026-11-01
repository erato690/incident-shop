# Data Model

- **Cenario**: `id`, `titulo`, `servico`, `sintoma_inicio`, `sintoma_fim`, `janela` (`inicio`,
  `fim`), `efeito(minuto, rng) -> Efeito` (interno), `causa_raiz` (interno, nunca exposto).
- **Efeito** (interno): logs `(servico, nivel, mensagem)` e métricas `{(servico, metrica): valor}`
  que sobrescrevem o estado saudável naquele minuto.
- **RegistroLog**: `horario` (ISO -03:00), `servico`, `nivel` (`INFO|WARN|ERROR`), `mensagem`.
- **SerieMetrica**: `servico`, `metrica`, `unidade`, `resumo` (`min`, `max`, `media`, `ultimo`),
  `pontos` (`horario`, `valor`).
- **Deploy**: `horario`, `servico`, `versao`, `tag`, `commit` (7 caracteres, igual ao git),
  `autor`, `mensagem`.
- **Consulta** (eco nas respostas): `cenario`, `servico`, `inicio`, `fim` (+ `nivel` em logs,
  `metrica` em métricas).

Métricas por serviço (unidade):

| Métrica | Unidade | Serviços |
|---|---|---|
| `requisicoes` | req/min | todos (no `estoque-worker`: mensagens processadas/min) |
| `erros_5xx` | erros/min | todos |
| `latencia_p95` | ms | todos |
| `cpu` | % | todos |
| `memoria` | % | todos |
| `reinicios` | reinícios/min | todos |
| `conexoes_db` | conexões | pedidos-api, estoque-worker |
| `fila_mensagens` | mensagens | estoque-worker |

Regras: horário sempre no minuto cheio para métricas; logs com segundos determinísticos dentro
do minuto; ordem crescente de horário.
