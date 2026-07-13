# Dashboard de Acertos (`/acertos`) — Design

**Status:** design aprovado, aguardando user review
**Data:** 2026-06-20
**Autor:** Dario (em sessão com Claude)

## Contexto

O analytis hoje gera predições probabilísticas (1X2, OU 2.5, BTTS) por modelo. Em produção temos três modelos com predições gravadas para os 39 jogos da Copa 2026: `dc-v1-no-decay` (Dixon-Coles), `xgb-1x2-v1` (XGBoost) e `ensemble-v1` (média ponderada). Conforme jogos vão acontecendo e resultados são ingeridos, dá pra comparar predição × resultado real.

Falta uma página que mostre essa comparação de forma acionável: % acerto por mercado, Brier score, comparação entre modelos, evolução ao longo das fases do torneio, e drill-down jogo-a-jogo.

A motivação do dono do produto é dupla: ver se o pipeline de predição está funcionando ("o XGBoost tá batendo o Dixon-Coles em OU?") e ter sinal pra ajustar decisões de aposta (Kelly + value bets) à medida que mais sample acumula.

## Escopo

### Dentro

- Página nova `/acertos` na SPA frontend.
- Endpoint novo `GET /v1/accuracy/summary?model=<name>` no backend FastAPI.
- 4 KPI cards por mercado: % acerto 1X2, % acerto OU 2.5, % acerto BTTS, Brier médio.
- Intervalo de confiança Wilson 95% em cada % acerto (mostrado como ±XXpp).
- ModelSelector dropdown com os 3 modelos atuais + qualquer modelo futuro com predições gravadas.
- Gráfico de série temporal (recharts `LineChart`) mostrando acerto cumulativo por fase do torneio (Grupo → Oitavas → Quartas → Semi → Final).
- Tabela de jogos finalizados com predição top, resultado real e badges hit/miss por mercado.
- Nav links em Header + BottomNav (grid-cols-6 no mobile).

### Fora (próximas iterações)

- ROI ou EV simulado (precisa odds + Kelly, é outra história).
- Filtros (range de datas, só jogos errados, agrupamento por confederação).
- Exportar CSV.
- Por player ou por team.

## Definições de "acerto"

Operacionalmente:

- **1X2**: `argmax({prob_home, prob_draw, prob_away})` é igual ao resultado real (`home_goals > away_goals` → home, `==` → draw, `<` → away).
- **OU 2.5**: `(prob_over_2_5 > 0.5)` é igual a `(home_goals + away_goals > 2.5)`. Limiar estrito em 0.5; predições com prob = 0.5 viram "abstenção" e não contam (caso de borda raro mas explícito).
- **BTTS**: `(prob_btts_yes > 0.5)` é igual a `(home_goals ≥ 1 ∧ away_goals ≥ 1)`. Mesmo limiar estrito.

## Definições de métricas

- **Brier por mercado (1X2)** — Brier multiclass: `Σ (prob_i − y_i)² / 3` onde `y_i` é one-hot do resultado real.
- **Brier OU/BTTS** — Brier binário: `(prob_positive − y)²` onde `y ∈ {0, 1}`.
- **Brier overall** — média dos Brier_market sobre todos os jogos × mercados (4 valores por match, n_matches matches).
- **Wilson CI 95%** — fórmula padrão com `z = 1.96`:
  ```
  center = (p + z² / (2n)) / (1 + z² / n)
  half   = z · sqrt(p(1-p)/n + z²/(4n²)) / (1 + z²/n)
  ci_low  = center − half
  ci_high = center + half
  ```
- **Cumulativo por fase** — para cada fase, a média de hits sobre todos os jogos cujo `match.kickoff_utc` ≤ último jogo daquela fase. Fases ordenadas: `group` → `round_of_16` → `quarterfinal` → `semifinal` → `final`.

## Normalização de fase

O campo `match.competition_round` (já no schema) vem do Football-Data com strings tipo `"GROUP_STAGE"`, `"LAST_16"`, `"QUARTER_FINALS"`, `"SEMI_FINALS"`, `"FINAL"`. O backend mapeia para um enum canônico `Phase`:

| Football-Data | Phase enum    | Display                |
|---------------|---------------|------------------------|
| GROUP_STAGE   | group         | "Grupo"                |
| LAST_16       | round_of_16   | "Oitavas"              |
| QUARTER_FINALS| quarterfinal  | "Quartas"              |
| SEMI_FINALS   | semifinal     | "Semi"                 |
| FINAL         | final         | "Final"                |
| THIRD_PLACE   | semifinal     | (agregado em semi)     |

Qualquer valor desconhecido vai pra `group` com warning no log.

## Backend

### Endpoint

`GET /v1/accuracy/summary`

**Query params:**
- `model` (opcional). Se ausente, escolhe o primeiro `model_version` (alfabético por `name`) com `n_predictions > 0`.

**Ordem do `available_models` na resposta:** alfabética por `name` (determinística — facilita testes e o dropdown na UI fica previsível).

**Auth:** `Depends(require_api_key)` (mesmo padrão dos outros endpoints).

**Response (200) — schema completo:**

```json
{
  "model": {
    "id": "uuid",
    "name": "ensemble-v1",
    "family": "ensemble"
  },
  "available_models": [
    {"id": "...", "name": "dc-v1-no-decay", "family": "dixon-coles", "n_predictions": 39},
    {"id": "...", "name": "xgb-1x2-v1", "family": "xgboost", "n_predictions": 39},
    {"id": "...", "name": "ensemble-v1", "family": "ensemble", "n_predictions": 39}
  ],
  "kpis": {
    "n_matches_evaluated": 12,
    "markets": {
      "1x2":  { "hits": 7, "n": 12, "rate": 0.583, "ci_low": 0.319, "ci_high": 0.806, "brier_avg": 0.198 },
      "ou":   { "hits": 8, "n": 12, "rate": 0.667, "ci_low": 0.394, "ci_high": 0.864, "brier_avg": 0.245 },
      "btts": { "hits": 6, "n": 12, "rate": 0.500, "ci_low": 0.248, "ci_high": 0.752, "brier_avg": 0.252 }
    },
    "brier_overall": 0.232
  },
  "timeseries": [
    {"phase": "group",        "n": 8,  "cumulative": {"1x2": 0.625, "ou": 0.750, "btts": 0.500}},
    {"phase": "round_of_16",  "n": 10, "cumulative": {"1x2": 0.600, "ou": 0.700, "btts": 0.500}},
    {"phase": "quarterfinal", "n": 12, "cumulative": {"1x2": 0.583, "ou": 0.667, "btts": 0.500}},
    {"phase": "semifinal",    "n": 12, "cumulative": {"1x2": 0.583, "ou": 0.667, "btts": 0.500}},
    {"phase": "final",        "n": 12, "cumulative": {"1x2": 0.583, "ou": 0.667, "btts": 0.500}}
  ],
  "matches": [
    {
      "match_id": "uuid",
      "kickoff_utc": "2026-06-14T18:00:00Z",
      "home_team": "Brazil",
      "away_team": "Argentina",
      "home_goals": 2,
      "away_goals": 1,
      "phase": "round_of_16",
      "predictions": {
        "1x2":  {"predicted": "home", "predicted_prob": 0.539, "actual": "home", "hit": true,  "brier": 0.21},
        "ou":   {"predicted": "over", "predicted_prob": 0.620, "actual": "over", "hit": true,  "brier": 0.14},
        "btts": {"predicted": "yes",  "predicted_prob": 0.711, "actual": "yes",  "hit": true,  "brier": 0.08}
      }
    }
  ]
}
```

**Response (404) — modelo não existe:**
```json
{"detail": "model 'ghost' not found or has no predictions"}
```

**Arquivos:**
- Create: `src/analytis/api/routes/accuracy.py` — handler do endpoint
- Create: `src/analytis/application/accuracy_summary.py` — use case que agrega
- Modify: `src/analytis/api/main.py` — incluir o router
- Create: `tests/integration/api/test_accuracy_summary.py`

### Lógica de agregação (pseudocódigo)

```python
async def execute(model_name: str | None) -> AccuracySummary:
    available = await list_models_with_prediction_counts(session)
    if not available:
        raise EmptyDB

    model = pick_model(model_name, available)  # 404 se model_name não está
    finished_matches = await load_finished_matches_with_predictions(session, model.id)

    kpis = compute_kpis(finished_matches)              # hits, rates, CI, brier
    timeseries = compute_timeseries(finished_matches)  # cumulative per phase
    matches = serialize_matches(finished_matches)       # detail rows

    return AccuracySummary(model, available, kpis, timeseries, matches)
```

## Frontend

### Files

**Create:**
- `frontend/src/pages/AccuracyPage.tsx` — página principal
- `frontend/src/hooks/useAccuracySummary.ts` — react-query hook
- `frontend/src/components/accuracy/KpiCard.tsx`
- `frontend/src/components/accuracy/ModelSelector.tsx`
- `frontend/src/components/accuracy/AccuracyChart.tsx`
- `frontend/src/components/accuracy/MatchAccuracyTable.tsx`
- `frontend/src/pages/__tests__/AccuracyPage.test.tsx`

**Modify:**
- `frontend/src/App.tsx` — rota `/acertos`
- `frontend/src/components/layout/Header.tsx` — nav item
- `frontend/src/components/layout/BottomNav.tsx` — nav item + `grid-cols-6`
- `frontend/src/lib/api.ts` — `fetchAccuracySummary(model?)` + tipos TS

### Layout

Mobile-first vertical, container `max-w-3xl space-y-6`:

```
Header ANALYTIS

H2 Acertos
[ModelSelector ▾]  12 jogos avaliados

[KpiCard 1X2 58.3% ±24pp]
[KpiCard OU2.5 66.7% ±24pp]
[KpiCard BTTS 50.0% ±25pp]
[KpiCard Brier 0.232 (color: green/yellow/red)]

[AccuracyChart — line chart, 3 lines, x=phase, y=0-100%]

[Jogos]
  - MatchAccuracyCard 1 (clickable → /matches/:id)
  - MatchAccuracyCard 2
  - ...
```

### Estados

- **Loading**: Skeleton em cada componente (reaproveita o `<Skeleton />` que já temos).
- **Empty** (`n_matches_evaluated === 0`): mensagem "Nenhum jogo com resultado disponível pra esse modelo ainda" + CTA "Ver jogos" → `/`.
- **Erro de rede / 500**: card de erro + botão "Tentar novamente" que invalida a query.
- **401**: dispara o `OPEN_API_KEY_DIALOG_EVENT` (handler global já existe).

### Cores do Brier card

| Brier | Cor (Tailwind) | Significado |
|-------|---------------|------------|
| < 0.20 | `text-green-500` | Bom (melhor que coin flip por margem clara) |
| 0.20 – 0.30 | `text-yellow-500` | Marginal (perto de coin flip) |
| > 0.30 | `text-red-500` | Ruim |

Brier teórico de coin flip uniforme 1X2: ~0.25. Brier de modelo overconfident pode passar de 0.30.

### Chart specifics

- `recharts` `<ResponsiveContainer height={240}>` com `<LineChart>`.
- 3 séries: `1x2` (azul), `ou` (verde), `btts` (roxo) — escolher cores que contrastem no dark theme.
- X axis: `dataKey="phase"` categórico, ticks formatados com labels PT-BR ("Grupo", "Oitavas", etc.).
- Y axis: domain `[0, 1]`, ticks em 0%/25%/50%/75%/100%.
- Tooltip: mostra `n` e o valor formatado por série.
- Legend: bottom, horizontal.

### Tabela

Não é `<table>` tradicional — lista de cards (mobile-first). Cada card:

```
[card]
  data       Brasil vs Argentina    2-1
  Oitavas
  1X2: ✓ home (53.9%)   OU: ✓ over (62.0%)   BTTS: ✓ yes (71.1%)
[/card]
```

Click no card → `useNavigate()('/matches/:id')`.

## Testing

### Backend (`tests/integration/api/test_accuracy_summary.py`)

Fixtures: 4 matches sintéticos com resultados conhecidos + 3 modelos com predições. Casos:

1. `test_returns_404_when_model_not_found` — `?model=ghost` → 404 com detalhe claro
2. `test_returns_only_finished_matches` — matches `scheduled` não contam pra hits/brier
3. `test_1x2_argmax_correctness` — probs `[0.6, 0.2, 0.2]` em jogo 2-1 (home win) → hit=true
4. `test_ou_threshold_at_0.5` — predição prob_over=0.51 em jogo 1-1 (over=false) → hit=false
5. `test_btts_threshold_at_0.5` — predição prob_btts_yes=0.49 em jogo 2-1 (BTTS=true) → hit=false (limiar estrito)
6. `test_brier_avg_calculation` — 2 jogos com Brier 0.2 e 0.4 → brier_avg = 0.3
7. `test_wilson_ci_with_small_n` — n=3, hits=2 → CI bate fórmula conhecida
8. `test_timeseries_cumulative_monotonic_in_n` — `n` em cada fase só pode crescer ou ficar igual
9. `test_default_model_picks_first_with_predictions` — sem `?model`, retorna primeiro modelo (alfabético) com `n_predictions > 0`
10. `test_phase_normalization` — `competition_round="LAST_16"` no DB → `phase="round_of_16"` na resposta

### Frontend (`frontend/src/pages/__tests__/AccuracyPage.test.tsx`)

Reaproveita `test/test-utils.tsx`. Casos:

1. `renders header + skeletons on loading` — `isLoading=true` mostra skeletons
2. `renders all KPI cards from API response` — passa mock data, confere os 4 valores e ±pp
3. `Brier card color reflects threshold` — passa brier=0.18 → green; 0.28 → yellow; 0.35 → red
4. `empty state when n_matches_evaluated is 0` — render mostra "Nenhum jogo..."
5. `ModelSelector changes invalidate the query` — clicar opção dispara refetch com novo `model`
6. `match card click navigates to /matches/:id` — userEvent + memory router, verifica navigate chamado

Não testados (intencionalmente):
- AccuracyChart visual (recharts é estável, custo de RTL não vale)
- Endpoint via prod (smoke test no deploy basta)

### Critérios de aceitação

- ✅ Backend: 10/10 testes passando
- ✅ Frontend: 6/6 testes + typecheck limpo
- ✅ Smoke prod: `GET https://analytis.zyntra.company/v1/accuracy/summary` retorna 200 com `available_models` listando 3 modelos
- ✅ Visual no iPhone (PWA instalada): `/acertos` carrega, chart renderiza, nav items aparecem em Header + BottomNav

## Decisões justificadas

- **Wilson CI ao invés de normal** — com n=12 jogos (sample atual no início da Copa), a fórmula normal `p ± 1.96·sqrt(p(1-p)/n)` produz limites fora de [0,1] frequentemente. Wilson é a forma padrão de calcular CI binomial pra pequenas amostras e sempre fica em [0,1].
- **Limiar estrito > 0.5 (não ≥)** — predições exatamente em 0.5 não têm sinal direcional; tratar como hit seria gerar viés artificial. Edge case raro com floats, mas explicitar.
- **THIRD_PLACE agregado em semifinal** — disputa de 3º lugar é jogo single, agregar com semi simplifica eixo X do chart sem perder muito.
- **Default model = primeiro alfabético com predições** — escolha determinística e estável (não favorece um modelo específico). Frontend pode override via URL `?model=`.
- **MatchAccuracyTable como cards, não `<table>`** — em mobile, table com 6 colunas vira ilegível. Cards verticais com badges são mais escaneáveis no celular.
- **Chart com domínio Y [0,1] fixo** — comparações entre fases ficam consistentes; auto-scale enganaria visualmente.

## Deploy

- Vai junto com o polish (title + maskable, já commitado `ad56c12`) no próximo `bash deploy/deploy.sh`.
- Espera ~10 min total (build local + upload de 1.3 GB + load + finish.sh).

## Próximos passos depois desta fase

- **PWA Fase 2 — Web Push** (spec separado): notificação 10min antes do kickoff + fim do jogo. Depende deste dashboard porque a notificação de fim do jogo ideal mostra também "minha predição era X, resultado foi Y, hit/miss".
- **Cron diário de re-ingest + re-score** (sem brainstorm, direto): mantém o dashboard atualizado conforme jogos terminam.
