# analytis — Frontend Design

**Data:** 2026-06-13
**Status:** Aprovado para implementação
**Stack:** Vite + React 18 + TypeScript + Tailwind CSS + shadcn/ui + TanStack Query + React Router + Recharts

---

## 1. Visão geral

Frontend web React do `analytis` — interface mobile-first para consultar previsões, value bets e CLV summary antes de apostar. Roda servido pelo próprio FastAPI (monolito), acessível em `http://localhost:8000/` direto do celular dentro de casa.

### 1.1 Propósito do usuário

Apostas próprias com foco em estudo e disciplina. O frontend serve como interface de leitura sobre o estado já produzido pelos comandos CLI (`analytis ingest`, `analytis train`, `analytis score`, `analytis odds fetch`, `analytis bets find-value`). Nenhuma operação destrutiva ou alteração de modelo é feita pela UI.

### 1.2 Escopo do MVP

Quatro telas:

- 🏠 **HomePage** — lista cronológica de jogos do dia
- ⚽ **MatchDetailPage** — detalhe completo de um jogo (previsões + odds + value bets)
- 💎 **ValueBetsPage** — lista agregada de value bets com filtros
- 📊 **ClvSummaryPage** — gráfico de CLV no tempo + métricas por modelo

Telas fora do escopo (v2): Configurações, Modelos/Promote, Histórico detalhado, PWA, Modo claro, i18n.

---

## 2. Princípios não-funcionais

1. **Mobile-first sempre.** Layout pensado em 375px primeiro, escala para desktop por progressive enhancement.
2. **Estado do servidor é fonte da verdade.** TanStack Query cacheia 30s, refetch on window focus, polling 60s em telas de lista. Sem duplicação de estado.
3. **Loading e erro tratados explicitamente.** Sem "Loading..." texto puro — skeletons no formato do conteúdo final. Erro 401 abre modal pra nova API key; erro 5xx mostra toast com retry.
4. **Estilo Vibrant consistente.** Sistema de design fechado (paleta + tipografia + componentes shadcn). Cores via tokens Tailwind, nunca hardcoded.
5. **Zero magia.** Sem SSR, sem RSC, sem GraphQL. Vite + React + fetch + Tailwind + componentes shadcn.
6. **Auth simples.** API key em `localStorage`, enviada como header `X-API-Key`. Sem login screen.

---

## 3. Arquitetura de alto nível

```
┌──────────────────────────────────────────────────────┐
│  Browser (Chrome no celular ou desktop)              │
│  http://localhost:8000/                              │
└────────────────────┬─────────────────────────────────┘
                     │ static files (HTML/JS/CSS bundled by Vite)
                     │ + fetch /v1/*
                     ▼
┌──────────────────────────────────────────────────────┐
│              FastAPI (existente)                     │
│  ├─ GET  /v1/competitions          (existe)          │
│  ├─ GET  /v1/matches/{id}/predictions (existe)       │
│  ├─ GET  /v1/matches/{id}/odds        (existe)       │
│  ├─ GET  /v1/matches/{id}/value-bets  (existe)       │
│  ├─ GET  /v1/bets/clv-summary         (existe)       │
│  ├─ GET  /v1/health                   (existe)       │
│  ├─ NEW  GET  /v1/matches?upcoming=true&days=7       │
│  └─ NEW  /assets/* + / (serve build estático React)  │
└──────────────────────────────────────────────────────┘
```

**Mudanças no backend:** uma nova rota (`GET /v1/matches?upcoming=true&days=7`) + wire-up de static files mount em `main.py`. Resto do backend intocado.

---

## 4. Estrutura de pastas + tooling

```
analytis/
├── src/analytis/          # backend Python (existe)
├── frontend/              # NEW — toda parte web
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── components.json    # config shadcn/ui
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx                    # entrypoint React
│   │   ├── App.tsx                     # provider tree + routes
│   │   ├── lib/
│   │   │   ├── api.ts                  # fetch client + types
│   │   │   ├── query-client.ts         # config TanStack Query
│   │   │   ├── auth.ts                 # API key from localStorage
│   │   │   └── utils.ts                # cn() helper (shadcn)
│   │   ├── components/
│   │   │   ├── ui/                     # shadcn primitives
│   │   │   ├── layout/
│   │   │   │   ├── Header.tsx          # desktop top
│   │   │   │   └── BottomNav.tsx       # mobile bottom
│   │   │   ├── matches/
│   │   │   │   ├── MatchCard.tsx
│   │   │   │   ├── MarketBars.tsx
│   │   │   │   ├── ScoreHeatmap.tsx
│   │   │   │   └── OddsTable.tsx
│   │   │   ├── bets/
│   │   │   │   └── ValueBetCard.tsx
│   │   │   └── clv/
│   │   │       └── CLVChart.tsx
│   │   ├── hooks/
│   │   │   ├── useMatches.ts
│   │   │   ├── useMatchPredictions.ts
│   │   │   ├── useMatchOdds.ts
│   │   │   ├── useMatchValueBets.ts
│   │   │   └── useClvSummary.ts
│   │   ├── pages/
│   │   │   ├── HomePage.tsx
│   │   │   ├── MatchDetailPage.tsx
│   │   │   ├── ValueBetsPage.tsx
│   │   │   └── ClvSummaryPage.tsx
│   │   └── styles/
│   │       └── globals.css             # Tailwind base + tokens
│   └── public/
│       └── favicon.svg
```

### 4.1 Tooling

| Categoria | Escolha | Por quê |
|---|---|---|
| Bundler | **Vite 5** | HMR instantâneo, build em <5s |
| Package manager | **pnpm** | Rápido, lockfile determinístico |
| TypeScript | **strict mode on** | `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes` |
| Linter | **ESLint + typescript-eslint** | Plugin React + a11y |
| Formatter | **Prettier** | Padrão defaults, idêntico ao Ruff do backend |
| Testes | **Vitest + React Testing Library** | "Pytest do Vite" — rápido, sem config |
| Pre-commit | hook `pnpm lint && pnpm typecheck` | Mesma disciplina que mypy+ruff do backend |

### 4.2 Build & deploy

- **Dev:** `pnpm dev` em `frontend/` — Vite serve `localhost:5173`, faz proxy `/v1/*` → `localhost:8000`.
- **Prod:** `pnpm build` gera `frontend/dist/`. FastAPI serve essa pasta como static files.
- **CLI nova no backend:** `analytis frontend build` chama `pnpm install && pnpm build`; `analytis frontend dev` roda `pnpm dev`.

---

## 5. Sistema de design — Vibrant Sportbook

### 5.1 Tokens de cor (em `tailwind.config.ts`)

```ts
colors: {
  bg: {
    base: "#0f172a",       // slate-900 — fundo
    elevated: "#1e1b4b",   // indigo-950 — cards
    overlay: "rgba(255,255,255,0.05)",  // glass cards
  },
  fg: {
    primary: "#f1f5f9",
    muted: "#94a3b8",
    subtle: "#475569",
  },
  brand: {
    primary: "#10b981",    // emerald-500
    accent: "#fbbf24",     // amber-400 — destaque/edge
    danger: "#ef4444",     // red-500
  },
  outcome: {
    home: "#10b981",
    draw: "#9ca3af",
    away: "#ef4444",
  },
  edge: {
    high: "#10b981",       // edge > 10%
    medium: "#fbbf24",     // 3-10%
    low: "#94a3b8",        // 0-3%
  },
}
```

### 5.2 Gradientes assinatura

```css
.gradient-edge { background: linear-gradient(90deg, #fbbf24, #f59e0b); }
.gradient-home { background: linear-gradient(90deg, #10b981, #34d399); }
.gradient-away { background: linear-gradient(90deg, #ef4444, #f87171); }
.text-gradient-brand {
  background: linear-gradient(90deg, #fbbf24, #10b981);
  -webkit-background-clip: text;
  color: transparent;
}
```

### 5.3 Tipografia

| Token | Família | Tamanho mobile | Uso |
|---|---|---|---|
| `font-display` | **Inter** (700, tight) | 24px | Logo "ANALYTIS", H1 |
| `font-heading` | Inter (600) | 18-20px | Títulos, times |
| `font-body` | Inter (400) | 14px | Texto geral |
| `font-mono` | **JetBrains Mono** | 12-14px | Odds, probs, % |
| `font-label` | Inter (500, uppercase, wide) | 10-11px | Tags |

Carregados do Google Fonts.

### 5.4 Componentes shadcn/ui usados

`Card` (com variante `glass`), `Button` (variants: default, ghost, gradient), `Badge` (variants: outcome, edge, live), `Tabs`, `Dialog`, `Skeleton`, `Sheet`. Instalados via CLI shadcn conforme a fase exigir.

### 5.5 Iconografia

**Lucide React**: `Zap` (live), `Gem` (value bet), `TrendingUp` (CLV positivo), `Clock` (kickoff), `Filter` (filtros), `ChevronLeft` (voltar).

### 5.6 Spacing e layout

Escala Tailwind padrão. Regras:
- Cards: `p-4` mobile, `p-6` desktop
- Gap entre cards: `gap-3` mobile, `gap-4` desktop
- Padding lateral do app: `px-4` mobile, `max-w-3xl mx-auto` desktop

---

## 6. Roteamento e telas

### 6.1 Rotas

React Router v6 declarativas em `src/App.tsx`:

```tsx
<Routes>
  <Route path="/" element={<HomePage />} />
  <Route path="/matches/:matchId" element={<MatchDetailPage />} />
  <Route path="/bets" element={<ValueBetsPage />} />
  <Route path="/clv" element={<ClvSummaryPage />} />
  <Route path="*" element={<NotFoundPage />} />
</Routes>
```

URLs limpas, compartilháveis na rede local.

### 6.2 Navegação

- **Mobile (≤ 768px):** bottom nav fixo com 3 ícones (`Home`, `Gem` para `/bets`, `TrendingUp` para `/clv`). Item ativo recebe gradiente brand. Um quarto ícone `Settings` aparece mas, no MVP, dispara um Toast "Em breve" — placeholder pra v2.
- **Desktop (> 768px):** header top com as mesmas 3 entradas + logo "ANALYTIS" clicável (volta pra `/`). Settings idem placeholder.

### 6.3 HomePage `/`

- Header sticky: "Jogos · 13 jun 2026" + filtro de data (Hoje / Amanhã / Semana)
- Lista de cards ordenados por kickoff
- Cada card: bandeirinhas + nomes truncados, hora local, barra 3-cores com %, badge "💎 N value bets" se houver, status badge (live/in 2h/finished)
- Click → `/matches/:matchId`
- Pull-to-refresh no mobile

### 6.4 MatchDetailPage `/matches/:matchId`

Header sticky: bandeirinhas + nomes + hora + status.

Componente `Tabs` shadcn com 3 tabs:

- **Previsões:** barras 1X2 grandes, OU 2.5, BTTS, heatmap visual de placares (grid colorido), comparação ensemble vs DC vs mercado
- **Odds:** tabela `Bookmaker × Outcome × Decimal Odds`, melhor preço por outcome destacado em verde
- **💎 Bets:** cards ValueBetCard com edge dourado, kelly, stake sugerido

### 6.5 ValueBetsPage `/bets`

- Filtros (Sheet drawer no mobile, sidebar fixa no desktop): modelo, mercado, edge mínimo, casa
- Lista ValueBetCard ordenada por edge desc
- Click no card → `/matches/:matchId?tab=bets`

### 6.6 ClvSummaryPage `/clv`

- 3 stat cards: total bets, mean CLV (verde se > 0), mean edge
- Gráfico de linha Recharts: CLV cumulativo no tempo, linha de zero em destaque
- Tabela por modelo: nome × n_bets × mean_clv × median_edge

### 6.7 Estados especiais

- **Empty:** ilustração simples (Lucide grande) + frase explicativa + CTA
- **401:** Dialog modal pedindo API key, salva em `localStorage.analytis_api_key`
- **Erro de rede:** Toast com retry
- **Loading:** Skeleton no formato do conteúdo final

---

## 7. Data layer

### 7.1 Client de API (`src/lib/api.ts`)

```ts
import { getApiKey } from "./auth";

const BASE = "/v1";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const apiKey = getApiKey();
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "X-API-Key": apiKey ?? "",
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail);
  }
  return res.json();
}

// Types mirror FastAPI responses
export interface Match {
  id: string;
  home_team: string;
  away_team: string;
  kickoff_utc: string;
  status: "scheduled" | "live" | "finished" | "postponed" | "cancelled";
  home_goals: number | null;
  away_goals: number | null;
  is_home_neutral: boolean;
}

export interface Prediction {
  market: string;
  outcome: string;
  prob: number;
  ci_low: number;
  ci_high: number;
  model_version: string;
  created_at: string;
}

// Restantes a serem detalhados na implementação (espelham FastAPI responses):
//  - OddsQuoteResponse, OddsResponse, BestPerOutcome
//  - ValueBetResponse, ValueBetsList
//  - ClvSummary, ClvSummaryList
// Cada um é deduzível pelas rotas do backend em src/analytis/api/routes/{odds,value_bets}.py

export const api = {
  listUpcomingMatches: (days = 7) =>
    request<{ items: Match[] }>(`/matches?upcoming=true&days=${days}`),
  getMatchPredictions: (matchId: string) =>
    request<{ match_id: string; predictions: Prediction[] }>(
      `/matches/${matchId}/predictions`
    ),
  getMatchOdds: (matchId: string) =>
    request(`/matches/${matchId}/odds`),
  getMatchValueBets: (matchId: string) =>
    request(`/matches/${matchId}/value-bets`),
  getClvSummary: () => request(`/bets/clv-summary`),
};

export { ApiError };
```

### 7.2 TanStack Query

`src/lib/query-client.ts`:

```ts
import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: true,
      retry: (failures, err) => {
        if ((err as any)?.status === 401) return false;
        return failures < 2;
      },
    },
  },
});
```

Cada endpoint vira um hook em `src/hooks/`. Convenção de `queryKey`: `[endpoint, ...args]`.

```ts
// src/hooks/useMatchPredictions.ts
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useMatchPredictions(matchId: string) {
  return useQuery({
    queryKey: ["match-predictions", matchId],
    queryFn: () => api.getMatchPredictions(matchId),
    enabled: !!matchId,
  });
}
```

### 7.3 Polling automático

`/` (jogos) e `/bets`: refetch a cada 60s (`refetchInterval: 60_000`).

### 7.4 Tratamento de erro global

`<ErrorBoundary>` no `App.tsx` com fallback amigável. `ApiError` com status 401 dispara `<ApiKeyDialog>`.

### 7.5 Auth (`src/lib/auth.ts`)

```ts
const KEY = "analytis_api_key";
export const getApiKey = () => localStorage.getItem(KEY);
export const setApiKey = (k: string) => localStorage.setItem(KEY, k);
export const clearApiKey = () => localStorage.removeItem(KEY);
```

Primeiro acesso sem key → `<ApiKeyDialog>` abre automaticamente.

---

## 8. Roadmap em fases

| Fase | Entrega | Esforço |
|---|---|---|
| **A. Fundação** | Estrutura `frontend/`, Vite + TS + Tailwind + shadcn, ESLint/Prettier/Vitest, paleta Vibrant em tokens, layout shell (Header desktop + BottomNav mobile), proxy `/v1` em dev | ~3-4h |
| **B. Data layer** | `lib/api.ts` com tipos e funções; `lib/auth.ts` + `ApiKeyDialog`; query-client; hooks `useMatches`, `useMatchPredictions`, `useMatchOdds`, `useMatchValueBets`, `useClvSummary` | ~2h |
| **C. HomePage** | Filtros de data, lista de MatchCard com bandeirinhas + barras + badges; skeleton; empty state; polling 60s | ~3h |
| **D. MatchDetailPage** | Header sticky, 3 tabs, MarketBars, ScoreHeatmap, OddsTable, lista de ValueBetCard | ~5h |
| **E. ValueBetsPage** | Lista agregada, Sheet de filtros, ordenação por edge | ~3h |
| **F. ClvSummaryPage** | Stat cards, CLVChart com Recharts, tabela por modelo | ~2h |
| **G. Backend wiring** | Nova rota `GET /v1/matches?upcoming=true&days=N`, FastAPI servindo `frontend/dist/`, CLI `analytis frontend build/dev` | ~2h |
| **H. Polish + tests** | Vitest dos hooks de API, smoke tests Testing Library de cada Page, refinamento visual final | ~3h |

**Total estimado: ~22-25h** (~4-5 dias part-time).

---

## 9. Critérios de aceitação

### 9.1 Funcional

- [ ] `pnpm dev` no `frontend/` sobe em `localhost:5173` com proxy `/v1 → :8000`
- [ ] `pnpm build` gera `frontend/dist/` < 500KB gzipped
- [ ] `analytis api serve` sozinho serve frontend + API em `localhost:8000`
- [ ] No primeiro acesso, `ApiKeyDialog` abre pedindo a key; ela persiste no `localStorage`
- [ ] HomePage lista jogos das próximas 24h com previsões resumidas
- [ ] Click num MatchCard navega pra `/matches/<id>` com 3 tabs funcionais
- [ ] ValueBetsPage mostra todos os +EV ordenados; filtros funcionam
- [ ] ClvSummaryPage mostra gráfico Recharts com CLV cumulativo
- [ ] Bottom nav mobile / Header desktop alterna entre as 4 telas
- [ ] Erro 401 abre modal; erro 5xx mostra toast com retry

### 9.2 Qualidade

- [ ] `pnpm typecheck` clean (tsc strict)
- [ ] `pnpm lint` clean (ESLint + a11y)
- [ ] `pnpm test` passa (≥ 1 teste por hook de API + smoke test de cada Page)
- [ ] Lighthouse mobile ≥ 90 Performance, ≥ 95 Accessibility
- [ ] Funciona offline com cache de React Query (UI carrega, dados ficam staled)

### 9.3 Visual

- [ ] Estilo Vibrant aplicado em todos os componentes (gradientes em CTAs/badges)
- [ ] Mobile (375px) sem scroll lateral em nenhuma tela
- [ ] Desktop (≥ 1024px) com containers centrados em `max-w-3xl`
- [ ] Skeleton loaders no lugar de spinners

---

## 10. Fora de escopo (decisões explícitas)

- ❌ Login / multi-usuário — API key fixa no localStorage; sem fluxo de auth real
- ❌ In-play / live updates via WebSocket — só polling de 60s
- ❌ Tela de modelos / promote — v2
- ❌ Tela de configurações — v2 (kelly/bankroll continuam vindos do CLI)
- ❌ PWA / instalação no celular — v2
- ❌ Modo claro — só dark Vibrant
- ❌ i18n / pt-br — texto em inglês onde já estiver no backend, português onde inventarmos UI

---

## 11. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| FastAPI rotas `/v1/*` conflitam com static files | Mount static **depois** de incluir todos os routers; usar `html=True` pra SPA fallback |
| Bundle inchando (>500KB) | Code-splitting por rota com `React.lazy`; tree-shaking via Vite; charts só na ClvSummaryPage |
| Tipos manuais ficam desatualizados quando backend muda | Centralizar em `src/lib/api.ts`; testes Vitest dos hooks pegam shape errado em runtime |
| API key vaza visualmente (form sem masking) | Input do `ApiKeyDialog` com `type="password"`; nunca logar a key |
| Polling de 60s consome free tier do The Odds API se houver fetch backend | Polling no frontend lê só DB local; ingestão de odds continua sob `analytis odds fetch` manual ou cron |
