# PWA Fase 2 — Web Push Notifications

**Status:** design aprovado, aguardando user review
**Data:** 2026-06-20
**Autor:** Dario (em sessão com Claude)

## Contexto

A PWA Fase 1 já está em produção: usuários instalam o analytis na home do iPhone como app nativo. Falta a parte que era a motivação original do dono do produto — receber notificações dos jogos da Copa 2026 (10 min antes do kickoff com a predição do modelo, e logo depois do apito final com a comparação predição × resultado real).

Web Push em iOS Safari foi liberado em iOS 16.4 (março 2023) e funciona exclusivamente quando o site está instalado como PWA. A Fase 1 é portanto prerrequisito desta fase.

Este spec cobre todo o pipeline: registro de subscription no browser, persistência no backend, agendamento + disparo por cron, e a UX de pedido de permissão. O escopo é deliberadamente conservador (sem per-match opt-in, sem horários silenciosos, sem customização por modelo) — é a versão mais simples que entrega o valor pedido pelo usuário.

## Escopo

### Dentro

- Service Worker registrado pela SPA com handler de evento `push` e `notificationclick`
- Pedido automático de permissão de notificação no primeiro open da PWA instalada
- Backend FastAPI:
  - Tabelas `push_subscription` e `match_notification`
  - Migration Alembic `0005_push_notifications`
  - Routes públicas: `GET /v1/push/vapid-public-key`, `POST /v1/push/subscribe`
  - CLI command `analytis push dispatch` executável dentro do container
  - Módulo `analytis.push` (vapid + dispatcher + bodies)
- Cron na VM a cada 1 minuto chamando o dispatcher
- 2 tipos de notificação:
  - **Pré-jogo** (10 minutos antes do kickoff): título com os times, body com as probabilidades 1X2 do `ensemble-v1`
  - **Pós-jogo** (até 2 horas após `status='finished'`): título com o placar final, body com a comparação predição × resultado
- Click na notificação abre `/matches/<id>` na PWA
- Geração one-shot do par VAPID (público + privado) localmente, valores no `.env.prod`

### Fora (próximas iterações)

- Per-match opt-in (assinar só jogos específicos)
- Notificações ao vivo (gol, intervalo, vermelho)
- Customização por usuário (qual modelo usar, qual probabilidade mínima)
- Horários silenciosos / "Do Not Disturb" in-app
- Histórico de notificações enviadas dentro do PWA
- Suporte a iOS < 16.4 (não tem Web Push)

## Decisões locked

- **Modelo das predições no body**: sempre `ensemble-v1` (default do dashboard)
- **Granularidade de inscrição**: todos os jogos automaticamente após aceitar permissão
- **Mute**: usuário usa as configurações nativas do iOS (long-press no app icon → Notifications)
- **Permissão**: pedida automaticamente no primeiro open da PWA standalone; não insiste se negada

## Arquitetura

```
  [iPhone PWA]                    [VM analytis-app]              [VM Postgres]

   Service Worker  ←─── push     FastAPI router                  push_subscription
        │                              │                         match_notification
        │ POST                         ▼                              ▲
        └───────────────►  POST /v1/push/subscribe ──────INSERT───────┘
                           GET  /v1/push/vapid-public-key

 [VM cron, 1 min]
        │
        ▼
   push-dispatcher.sh
        │
        ▼ docker exec app
   analytis push dispatch  ──┬─→ SELECT matches kickoff IN [now+9, now+11]
                             ├─→ SELECT matches recently finished
                             ├─→ SELECT subscriptions
                             ├─→ pywebpush → Apple/Google push services
                             └─→ INSERT match_notification (idempotência)
```

## Componentes

### Backend

**Schema (migration `migrations/versions/0005_push_notifications.py`):**

- `push_subscription`:
  - `id` UUID PK
  - `endpoint` TEXT UNIQUE NOT NULL
  - `p256dh` TEXT NOT NULL
  - `auth` TEXT NOT NULL
  - `user_agent` TEXT
  - `created_at` TIMESTAMPTZ DEFAULT NOW()
  - `last_seen_at` TIMESTAMPTZ DEFAULT NOW()

- `match_notification`:
  - `id` UUID PK
  - `match_id` UUID FK → match(id) ON DELETE CASCADE
  - `kind` TEXT CHECK (kind IN ('pre','post'))
  - `sent_at` TIMESTAMPTZ DEFAULT NOW()
  - `n_recipients` INTEGER NOT NULL
  - UNIQUE (match_id, kind)

**Módulos novos `src/analytis/push/`:**

- `__init__.py`
- `vapid.py` — `VapidConfig` dataclass (carrega 3 envs: `ANALYTIS_VAPID_PRIVATE_KEY`, `ANALYTIS_VAPID_PUBLIC_KEY`, `ANALYTIS_VAPID_SUBJECT`)
- `bodies.py` — `build_pre_payload(match, ensemble_pred) -> dict`, `build_post_payload(match, ensemble_pred) -> dict`. Cada retorna `{title, body, url}` que vão pro payload do push
- `dispatcher.py` — classe `PushDispatcher(session_factory, vapid_config)` com método `async def dispatch() -> DispatchResult`. Faz queries, monta payloads, chama `pywebpush` em loop, trata `WebPushException` (410 → DELETE; outros → log warn)

**Repositório novo `src/analytis/persistence/repositories/push_subscription.py`:**

- `create_or_update(subscription_dto)`
- `delete_by_endpoint(endpoint)`
- `list_all() -> list[PushSubscription]`

**Routes novas `src/analytis/api/routes/push.py`:**

- `GET /v1/push/vapid-public-key` (sem `require_api_key`) → retorna `{"public_key": "<base64>"}`
- `POST /v1/push/subscribe` (sem `require_api_key`) → body Pydantic com `endpoint`, `p256dh`, `auth`, `user_agent` opcional. Valida `endpoint` contém um dos hosts conhecidos (`fcm.googleapis.com`, `web.push.apple.com`, `wns2-*.notify.windows.com`); rejeita com 400 se não.

**CLI command `src/analytis/cli/push.py`:**

- `analytis push dispatch` — invoca o `PushDispatcher`, imprime resumo (X jogos pre, Y jogos post, Z subscriptions, W erros)
- `analytis push generate-vapid-keys` — utility command que imprime chave pública e privada em base64 para colar no `.env`. Roda localmente uma vez.

**Dependências Python adicionadas:**

- `pywebpush` (~0.15) — envia o push HTTP com payload cifrado
- `py-vapid` (~1.9) — gera/valida claims JWT VAPID

### Frontend

**Arquivos novos:**

- `frontend/public/sw.js` — service worker minimal:
  ```js
  self.addEventListener('push', e => {
    if (!e.data) return;
    const data = e.data.json();
    e.waitUntil(self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/icon-192.png',
      badge: '/icon-192.png',
      data: { url: data.url ?? '/' },
    }));
  });

  self.addEventListener('notificationclick', e => {
    e.notification.close();
    e.waitUntil(clients.openWindow(e.notification.data?.url ?? '/'));
  });
  ```
- `frontend/src/lib/push.ts` — funções `enablePush()` e `isSubscribed()`. `enablePush()` faz tudo: `fetch vapid-key → Notification.requestPermission → register SW → pushManager.subscribe → POST /v1/push/subscribe`
- `frontend/src/components/PushPrompt.tsx` — componente sem UI persistente:
  - No mount: detecta `display-mode: standalone` + `Notification.permission`
  - Se standalone + permission='default' + não tem flag localStorage 'push_asked' → mostra modal "Receber notificações dos jogos da Copa?" com [Sim] [Mais tarde]
  - Sim → chama `enablePush()`, marca `push_asked=true`
  - Mais tarde → só marca `push_asked=true` (sem chamar requestPermission, pra não pedir)
  - Se standalone + permission='granted' + não tem subscription → registra silenciosamente
- Modificação em `frontend/src/App.tsx`: monta `<PushPrompt />` no nível root

### Deploy

- **`deploy/cron/push-dispatcher.sh`**:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  exec 9>/tmp/push-dispatcher.lock
  flock -n 9 || exit 0  # silently skip if another instance running
  cd /opt/analytis
  docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod \
    exec -T app analytis push dispatch >> /opt/analytis/logs/push-dispatcher.log 2>&1
  ```
- **`deploy/finish.sh`**: adiciona cron `* * * * * root /opt/analytis/deploy/cron/push-dispatcher.sh`
- **`deploy/.env.prod.example`**: adiciona placeholders `ANALYTIS_VAPID_PRIVATE_KEY=<run analytis push generate-vapid-keys>`, `ANALYTIS_VAPID_PUBLIC_KEY=...`, `ANALYTIS_VAPID_SUBJECT=mailto:techeasy376@gmail.com`
- **`deploy/.env.prod`**: receberá os valores reais

## Data Flow

### Fluxo de subscription

1. Usuário abre a PWA pela primeira vez (instalada via Fase 1)
2. `PushPrompt` detecta `display-mode: standalone` + `Notification.permission === 'default'` + `localStorage.push_asked !== 'true'`
3. Modal "Receber notificações dos jogos?" — usuário clica Sim
4. `enablePush()`:
   - GET `/v1/push/vapid-public-key` → `pubKey` base64
   - `await Notification.requestPermission()` → iOS exibe popup nativo → `'granted'`
   - `await navigator.serviceWorker.register('/sw.js')` → registration
   - `await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(pubKey) })` → subscription com `{endpoint, keys: {p256dh, auth}}`
   - POST `/v1/push/subscribe` com `{endpoint, p256dh, auth, user_agent: navigator.userAgent}`
5. Backend `subscribe` route:
   - Valida `endpoint` host (whitelist)
   - `INSERT INTO push_subscription (...) ON CONFLICT (endpoint) DO UPDATE SET last_seen_at=NOW(), p256dh=EXCLUDED.p256dh, auth=EXCLUDED.auth`
   - Retorna 201
6. Frontend grava `localStorage.push_subscribed=true` (atalho para `isSubscribed()` futuro)

### Fluxo de disparo do push

Cron dispara a cada minuto `/opt/analytis/deploy/cron/push-dispatcher.sh`. O script tenta um `flock` e, se outro já estiver rodando (raro), sai com 0 silenciosamente. Caso contrário chama `docker compose exec app analytis push dispatch`, que:

1. Busca matches com `kickoff_utc BETWEEN NOW() + 9min AND NOW() + 11min` E sem `match_notification` `kind='pre'`
2. Busca matches com `status='finished' AND kickoff_utc > NOW() - 2 hours` E sem `match_notification` `kind='post'`
3. Para cada match em pre e em post:
   - Resolve a predição `ensemble-v1` no DB (caso não exista, pula com log warn)
   - Monta payload `{title, body, url}` via `bodies.build_pre_payload` / `build_post_payload`
   - Lista subscriptions (`SELECT * FROM push_subscription`)
   - Para cada subscription, chama `pywebpush(subscription_info=..., data=json_payload, vapid_private_key=..., vapid_claims={sub: VAPID_SUBJECT, aud: <endpoint origin>})`
   - Captura `WebPushException`: se `e.response.status_code == 410`, `DELETE FROM push_subscription WHERE endpoint=...`; senão log warn e segue
   - Conta sucessos
   - Insere `match_notification (match_id, kind, sent_at=NOW(), n_recipients=success_count)` — UNIQUE garante que paralelos não duplicam
4. Imprime resumo no stdout (capturado pelo log)

## Error handling + segurança

**Segurança:**

- VAPID private key vive em `.env.prod` (gitignored). O codebase nunca tem referência ao valor literal.
- O endpoint `GET /v1/push/vapid-public-key` retorna só a chave **pública** — não há segredo a esconder ali.
- `POST /v1/push/subscribe` valida o host do `endpoint` contra um whitelist (`fcm.googleapis.com`, `web.push.apple.com`, `wns2-*.notify.windows.com`). Rejeita 400 caso contrário, evitando que adversários cadastrem endpoints arbitrários para spam ou amplificação.
- Notificações não carregam PII — só dados públicos (nomes de times, probabilidades, placar).
- HTTPS-only (já configurado via nginx + Let's Encrypt).

**Erros e fallbacks:**

- `pywebpush` 410 Gone → subscription invalidada, DELETE da tabela. Próximo dispatch nunca mais tenta.
- `pywebpush` 5xx ou timeout → log warn, NÃO deleta. Próximo cron tenta de novo após ~1 min.
- VAPID keys ausentes no env → CLI aborta com mensagem clara e exit 1; cron loga e tenta de novo a cada minuto até serem definidas (esse estado é setup incompleto, não bug).
- DB indisponível → CLI aborta com SQLAlchemy error e exit 1; cron loga e tenta de novo.
- Race entre crons (`flock` falhar): o segundo cron sai silenciosamente sem tentar; nunca deve ocorrer pois o lock é por arquivo local.
- Race no banco (duas execuções da CLI conseguindo o lock): a UNIQUE em `match_notification (match_id, kind)` faz a segunda receber `IntegrityError` e abortar a transação dela; nenhum subscriber recebe duplicado.
- `Notification.requestPermission()` retorna `'denied'` no frontend: PushPrompt marca `localStorage.push_asked=true`, não pede de novo. Usuário pode reativar manualmente nos settings do iOS depois.

**Não tratados (limitações aceitas):**

- Se o jogo for remarcado para outro horário depois da janela [9, 11] minutos já ter passado, a notificação pré-jogo não é re-enviada (UNIQUE no `(match_id, 'pre')` impede). Para uma Copa do Mundo onde remarcações são raras isso é aceitável.
- Se o cron estiver fora do ar (ex: VM reiniciando) quando uma janela passa, aquela notificação é perdida. Aceitável; não vamos persistir e replayar pushes.

## Testing

### Unit

- `tests/unit/push/test_bodies.py`:
  - `test_build_pre_payload_home_win_prediction`
  - `test_build_pre_payload_draw_prediction`
  - `test_build_pre_payload_neutral_venue` (sem indicação de mando)
  - `test_build_pre_payload_missing_prediction_raises`
  - `test_build_post_payload_correct_winner`
  - `test_build_post_payload_wrong_winner`
  - `test_build_post_payload_btts_correct`
  - `test_build_post_payload_url_includes_match_id`
- `tests/unit/push/test_vapid.py`:
  - `test_vapid_config_from_env`
  - `test_vapid_config_missing_key_raises`

### Integration

- `tests/integration/api/test_push_routes.py`:
  - `test_get_vapid_public_key_no_auth_required`
  - `test_subscribe_with_valid_endpoint_creates_row`
  - `test_subscribe_rejects_invalid_host_400`
  - `test_subscribe_same_endpoint_twice_updates_last_seen`
- `tests/integration/push/test_dispatcher.py`:
  - Usa `unittest.mock.patch` em `pywebpush.webpush` para evitar chamadas externas
  - `test_dispatch_sends_pre_for_match_in_window`
  - `test_dispatch_skips_already_notified_match` (UNIQUE)
  - `test_dispatch_410_deletes_subscription`
  - `test_dispatch_5xx_keeps_subscription`
  - `test_dispatch_post_for_recently_finished_match`

### E2E manual (dono do produto)

Após deploy:

1. Atualizar a PWA já instalada (puxa o novo SW). Hard-refresh.
2. Abrir a PWA — modal "Receber notificações?" → Sim → iOS popup nativo → permitir
3. Confirmar via `psql` que linha foi inserida em `push_subscription`
4. Seed manual: `UPDATE match SET kickoff_utc = NOW() + INTERVAL '10 minutes' WHERE id = '<algum-match-scheduled>'`
5. Aguardar até 1 min — notificação chega no lockscreen
6. Click na notificação — PWA abre na página `/matches/<id>` correto
7. Confirmar via `psql` que `match_notification` (kind='pre') foi inserido

### Critérios de aceitação

- ✅ Migration `0005_push_notifications` aplicada em prod
- ✅ Routes `/v1/push/vapid-public-key` e `/v1/push/subscribe` funcionando
- ✅ SW registrado e respondendo ao evento `push`
- ✅ Modal de permissão aparece na primeira visita da PWA instalada
- ✅ Notificação real chega no iPhone para um jogo de teste
- ✅ Click na notificação abre a página correta
- ✅ Subscriptions inválidas (410) são removidas automaticamente
- ✅ Idempotência: cron repetido não envia 2x
- ✅ Todos os testes unit + integration verdes
- ✅ Cron `analytis-push` instalada e rodando a cada 1 min sem erro

## Decisões justificadas

- **Cron de 1 min ao invés de scheduler in-process** — consistência com o `daily-rescore` que já existe; sobrevive a restart do uvicorn; granularidade de 1 min é mais que suficiente para "10 min antes" e "logo após o jogo".
- **Subscription sem `user_id`** — não há sistema de contas no analytis. Cada device é uma subscription, todas recebem todos os pushes. Para Copa do Mundo com algumas dezenas de jogos isso é aceitável.
- **Whitelist de hosts de endpoint** — evita um adversário cadastrar endpoint malicioso para amplificação ou spam. Os hosts conhecidos cobrem 99% dos browsers reais (Chrome/Edge → FCM, Safari → Apple, Firefox → próprio, mas a maioria dos usuários iOS vai pro Apple endpoint).
- **`flock` no cron** — segurança barata contra overlap. Em estado normal nunca dispara, mas se um ciclo de dispatch demorar > 1 min (raro), evita race condition.
- **`localStorage.push_asked` ao invés de outro mecanismo** — leve, sobrevive a reload, é per-device (correto para web push).
- **Notification body via Pydantic em `bodies.py` ao invés de inline na route/dispatcher** — testabilidade, separação de concern (formatação vs. transporte).

## Próximos passos depois desta fase

- Dashboard de "minhas notificações" (histórico)
- Per-match opt-in com toggle na página do jogo
- Notificações ao vivo (gol marcado) via webhook do Football-Data ou polling
- Customização de quais modelos mostrar no body
