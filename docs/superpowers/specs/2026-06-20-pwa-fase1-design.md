# PWA Fase 1 — Installable + Ícone

**Status:** design aprovado, aguardando user review
**Data:** 2026-06-20
**Autor:** Dario (em sessão com Claude)

## Contexto

O analytis hoje é uma SPA React servida via FastAPI + nginx. Já está em produção em `https://analytis.zyntra.company` com HTTPS válido. Não tem nenhum suporte a PWA: sem manifest, sem service worker, sem `apple-touch-icon`, sem meta tags específicas de mobile-web-app.

O dono do produto quer que, no iPhone, ao "Adicionar à Tela de Início" pelo Safari, o ícone que aparece na home seja o ícone visual do projeto (um "A" formado por 3 barras crescentes em gradiente ciano → roxo sobre fundo navy) e que ao tocar nele a app abra em modo fullscreen (sem barra do Safari), parecendo um app nativo.

Notificações push (que tecnicamente exigem service worker + permissão + backend de subscriptions) **ficam para Fase 2**, em PR separado, depois de Fase 1 estar validada em produção. Justificativa do split: iOS PWA install tem comportamento sutil (versão do iOS, primeiro vs segundo open, Safari vs outros browsers) e ter o install validado isoladamente elimina ambiguidade quando push der bug.

## Escopo

### Dentro

- Gerar 5 variantes do ícone (`180, 192, 256, 384, 512`) a partir do PNG 1024×1024 fornecido pelo dono do produto (gerado via ChatGPT, salvo em `C:\Users\PC Gamer\Downloads\ChatGPT Image 20 de jun. de 2026, 16_54_49.png`).
- Criar `frontend/public/manifest.webmanifest`.
- Adicionar meta tags Apple-específicas em `frontend/index.html`.
- Script único `frontend/scripts/generate-icons.mjs` (rodado uma vez localmente, PNGs commitados — não roda em build).

### Fora (vai pra Fase 2)

- Service Worker (`sw.js`, registro, lifecycle).
- Permissão de notificações.
- Backend de subscriptions (`POST /v1/push/subscribe`, tabela `push_subscription`).
- Cron de disparo de push (10min antes do kickoff, fim do jogo).
- Offline support / cache de assets.

## Resultado funcional

Após Fase 1:
- Usuário abre `analytis.zyntra.company` no Safari iOS, toca em compartilhar → "Adicionar à Tela de Início".
- O ícone que aparece na home é o ícone gradient ciano→roxo (não favicon genérico).
- O nome abaixo do ícone é "Analytis" (sem cortar).
- Ao tocar no ícone, abre em modo `standalone` — sem barra do Safari, status bar do iOS em estilo `black-translucent` sobre o fundo `#0f172a`.
- Splash screen durante o load é `#0f172a` (não branco).
- Lighthouse PWA audit relata "Installable" verde.

## Estrutura de arquivos

```
frontend/
├── public/
│   ├── icon-1024.png            # original (copiar dos Downloads)
│   ├── icon-512.png             # gerado
│   ├── icon-384.png             # gerado
│   ├── icon-256.png             # gerado
│   ├── icon-192.png             # gerado
│   ├── icon-180.png             # gerado (apple-touch-icon)
│   └── manifest.webmanifest     # novo
├── scripts/
│   └── generate-icons.mjs       # novo, run once
└── index.html                   # editado
```

## Componentes

### 1. Script de geração de ícones (`frontend/scripts/generate-icons.mjs`)

Roda 1 vez via `pnpm gen:icons` (atalho em `package.json#scripts`). Lê `public/icon-1024.png`, gera as 5 variantes via `sharp`.

`sharp` é adicionado como `devDependencies` (~30 MB instalado, **não vai pro bundle de produção** — só usado no script offline). O build do Vite e o runtime continuam sem nenhuma dep nova.

Comportamento esperado: idempotente (rodar de novo sobrescreve sem erro), exit code 0 em sucesso, mensagem clara de erro se o source 1024 estiver faltando.

### 2. `frontend/public/manifest.webmanifest`

```json
{
  "name": "Analytis",
  "short_name": "Analytis",
  "description": "Predições probabilísticas + value bets de futebol",
  "lang": "pt-BR",
  "start_url": "/",
  "display": "standalone",
  "orientation": "portrait",
  "background_color": "#0f172a",
  "theme_color": "#0f172a",
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any" },
    { "src": "/icon-256.png", "sizes": "256x256", "type": "image/png", "purpose": "any" },
    { "src": "/icon-384.png", "sizes": "384x384", "type": "image/png", "purpose": "any" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any" }
  ]
}
```

### 3. Meta tags em `frontend/index.html` (dentro do `<head>`)

```html
<link rel="manifest" href="/manifest.webmanifest" />
<link rel="apple-touch-icon" href="/icon-180.png" />
<meta name="apple-mobile-web-app-capable" content="yes" />
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
<meta name="apple-mobile-web-app-title" content="Analytis" />
```

A meta `theme-color` em `#0f172a` já existe no `index.html` — mantida.

## Decisões justificadas

- **`display: standalone`** (em vez de `fullscreen` ou `minimal-ui`) — abre sem barra do Safari mas mantém status bar do iOS, equilibrando "parece app" com usabilidade (usuário ainda vê hora, bateria, sinal).
- **`orientation: portrait`** — a UI é mobile-first vertical; landscape não está testado e não traz valor pra esse caso de uso.
- **`status-bar-style: black-translucent`** — status bar do iOS fica transparente sobre o fundo navy, sem barra preta sólida no topo.
- **Não incluir `icon-1024.png` no manifest.icons** — iOS ignora tamanhos acima de 180 (usa só `apple-touch-icon`); Android usa até 512. Incluir 1024 apenas como source para gerar os outros.
- **Sharp via script offline em vez de plugin Vite** — `sharp` entra como `devDependencies` e roda só localmente; build do Vite e runtime ficam idênticos. Trade-off: PNGs gerados ficam no git (cresce o repo em ~600 KB total), em troca o build de produção não tem custo de gerar imagens.

## Data flow

Estática. Não há request runtime envolvido no install:

```
Safari iOS
   |
   |-- GET /                       → index.html (com novas meta tags)
   |-- GET /manifest.webmanifest   → JSON
   |-- GET /icon-180.png           → 180×180 PNG
   |
   v
[Adicionar à Tela de Início]
   |
   v
Home screen com ícone + nome "Analytis"
   |
   v
[tap] → abre /  em modo standalone (sem Safari chrome)
```

## Error handling

Mínimo, porque o escopo não tem fluxo dinâmico:

- **Script de geração**: se `public/icon-1024.png` faltar, falha rápido com mensagem clara (`source 1024×1024 não encontrado, copie o PNG do Downloads para public/icon-1024.png`).
- **Manifest mal formatado**: pego em build local (Vite valida JSON) ou via Lighthouse no dev (erro visível em DevTools → Application → Manifest).
- **Meta tags conflitantes ou inválidas**: HTML mantém compatibilidade backward — se algum atributo for ignorado pelo Safari, degrada para comportamento default sem quebrar.

## Testing

### Local (desktop Chrome)
- DevTools → Application → Manifest lista os 4 ícones sem erro.
- Lighthouse PWA audit ≥ 90, critério "Installable" verde.

### Local (mobile preview)
- Chrome DevTools → device toolbar → iPhone 14 viewport → recarrega → confere ícones no Application panel.

### Produção (iPhone real)
- Safari → `https://analytis.zyntra.company` → compartilhar → Adicionar à Tela de Início.
- Confere: ícone visual correto, nome "Analytis" sem cortar.
- Tap no ícone da home → abre standalone (sem barra), status bar translucida.

### Regressão
- Site continua idêntico no navegador convencional (favicon, título, navegação) — manifest é metadata adicional, não muda comportamento desktop.

## Critérios de aceitação

- ✅ Ícone visual aparece corretamente em "Adicionar à Tela de Início" no iPhone (Safari ≥ iOS 16).
- ✅ Nome do ícone é "Analytis" (não cortado, não com placeholder genérico).
- ✅ Tap no ícone da home abre fullscreen sem barra do Safari.
- ✅ Splash screen `#0f172a` (não branco) durante load.
- ✅ Lighthouse PWA score ≥ 90; flag "Installable" verde.
- ✅ Comportamento da web normal (Chrome desktop, mobile Safari sem instalar) inalterado.

## Deploy

Faz parte do mesmo deploy da página `/metodologia` (já buildada localmente, esperando push). `deploy/deploy.sh` cobre:
1. `docker save` da imagem (já feito — `/tmp/analytis-app.tar.gz` pronto).
2. `scp` para VM.
3. `docker load` + `compose up -d` (recria container `app` com novo dist).

Validação manual em iPhone real após deploy.

## Próximos passos (depois desta fase)

- **Fase 2 — Web Push notifications**: spec separado, depende desta estar validada em produção.
- **Dashboard de acertos** (`/acertos`): spec separado, independente de PWA.
- **Cron de re-score diário**: implementação direta, sem brainstorm necessário (puro backend).
