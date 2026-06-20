# Deploy — Oracle Cloud Infrastructure (Always Free)

Plano de deploy do **analytis** (FastAPI backend + Vite frontend + Postgres) em uma VM ARM Ampere A1 do Oracle Cloud Free Tier.

---

## 0. Por que esta topologia

- **Always Free Ampere A1**: 4 OCPU + 24 GB RAM + 200 GB disco. Suficiente pra rodar tudo num único host com docker-compose. Não expira como o trial de US$300.
- **Postgres em container no mesmo host**: o Autonomous Database do OCI é Oracle DB, não Postgres — incompatível com a stack. Mantemos o Postgres dockerizado, com volume persistente e backup diário pro Object Storage.
- **Nginx reverse proxy + Certbot**: TLS gratuito via Let's Encrypt, serve frontend estático (`vite build`) e faz proxy do `/v1/*` pro FastAPI.
- **Tudo num docker-compose**: simples de operar, fácil de reproduzir local. Resiliência vem de `restart: unless-stopped` + cron de backup.

---

## 1. Provisionamento da VM (console OCI)

1. **Compute → Instances → Create**:
   - Image: **Canonical Ubuntu 22.04** (ARM build)
   - Shape: **VM.Standard.A1.Flex** — 4 OCPU / 24 GB RAM
   - Networking: VCN default, **subnet pública**, atribuir IP público
   - SSH: cole sua chave pública
2. **Security List** da subnet → adicionar **ingress rules**:
   - `0.0.0.0/0` TCP **80** (HTTP — Let's Encrypt challenge)
   - `0.0.0.0/0` TCP **443** (HTTPS)
   - `<seu-ip>/32` TCP **22** (SSH — restrinja!)
3. **Reservar IP público estático** (Networking → Reserved Public IPs) — necessário pro DNS A-record.

## 2. Bootstrap do host

```bash
ssh ubuntu@<ip-publico>

# Pacotes base
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose-v2 git ufw fail2ban certbot
sudo usermod -aG docker ubuntu && newgrp docker

# Firewall do host (defesa em profundidade — Security List já bloqueia, mas iptables do Oracle Linux/Ubuntu costuma estar restritivo)
sudo ufw default deny incoming
sudo ufw allow OpenSSH
sudo ufw allow 80,443/tcp
sudo ufw enable

# Oracle Ubuntu vem com iptables travado por padrão — liberar 80/443:
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

## 3. Domínio + DNS

- Registrar (ou usar existente) domínio. Ex.: `analytis.example.com`.
- DNS provider → **A-record** apontando pro IP reservado da VM.
- Aguardar propagação (`dig analytis.example.com` retornar o IP).

## 4. Estrutura do repositório a adicionar

Criar no projeto (não existe ainda):

```
deploy/
├── Dockerfile.backend          # imagem do FastAPI
├── Dockerfile.frontend         # multi-stage: build Vite → nginx servindo dist/
├── docker-compose.prod.yml     # postgres + backend + frontend + nginx-proxy + certbot
├── nginx/
│   ├── nginx.conf              # reverse proxy: /v1 → backend:8000, / → frontend
│   └── certbot-renew.sh        # script de renovação automática
├── .env.prod.example           # template das envs de produção (sem segredos)
└── backup/
    └── pg-backup.sh            # pg_dump diário → OCI Object Storage (rclone)
```

### 4.1 Dockerfile.backend (esboço)
- Base `python:3.12-slim`
- `uv sync --frozen --no-dev`
- `CMD ["uv", "run", "uvicorn", "analytis.api.app:app", "--host", "0.0.0.0", "--port", "8000"]`

### 4.2 Dockerfile.frontend (esboço)
- **Stage 1**: `node:20-alpine` → `pnpm install --frozen-lockfile && pnpm build` → gera `dist/`
- **Stage 2**: `nginx:alpine` copia `dist/` pra `/usr/share/nginx/html`

### 4.3 docker-compose.prod.yml (serviços)
- `postgres`: `postgres:16-alpine`, volume `pgdata`, **sem porta exposta** (só rede interna)
- `backend`: build `./` com `Dockerfile.backend`, lê `.env.prod`, depende de `postgres`, expõe `8000` só na rede interna
- `frontend`: build com `Dockerfile.frontend`, expõe `80` interno
- `nginx-proxy`: `nginx:alpine`, expõe `80:80` e `443:443`, monta `./nginx/nginx.conf` e os certificados do Certbot
- `certbot`: container `certbot/certbot`, volume compartilhado pra `/etc/letsencrypt`

### 4.4 nginx.conf (reverse proxy)
- `server_name analytis.example.com`
- `location /v1/` → `proxy_pass http://backend:8000/v1/`
- `location /` → `proxy_pass http://frontend:80/`
- HTTP→HTTPS redirect, HSTS, gzip, cache estático

## 5. Primeira subida na VM

```bash
# Clonar
git clone <repo-url> /opt/analytis && cd /opt/analytis

# Configurar envs
cp deploy/.env.prod.example deploy/.env.prod
nano deploy/.env.prod   # preencher API keys, ANALYTIS_API_KEY=dariokrugerjunior1999, senha do postgres etc.

# Apontar frontend pro domínio (build-time): VITE_API_BASE_URL=https://analytis.example.com
# (frontend/src/lib/api.ts já lê de import.meta.env, conferir/criar .env.production)

# Subir certificado inicial (modo standalone — antes do nginx existir)
sudo certbot certonly --standalone -d analytis.example.com --email seu@email.com --agree-tos -n

# Subir stack
docker compose -f deploy/docker-compose.prod.yml up -d

# Aplicar migrations
docker compose -f deploy/docker-compose.prod.yml exec backend uv run analytis db migrate

# Smoke test
curl https://analytis.example.com/v1/health
curl -H "X-API-Key: dariokrugerjunior1999" https://analytis.example.com/v1/models
```

## 6. Operação contínua

### 6.1 Renovação TLS
- Cron `0 3 * * *` rodando `certbot renew --quiet && docker compose exec nginx-proxy nginx -s reload`.

### 6.2 Backup Postgres
- Cron diário às 04:00: `pg_dump` → `gzip` → upload pro OCI Object Storage (bucket privado) via `oci-cli` ou `rclone`.
- Retenção: 7 daily + 4 weekly.

### 6.3 Logs
- `docker compose logs -f --tail=200` pra debug rápido.
- (Opcional, futuro) Promtail + Grafana Cloud free tier.

### 6.4 Updates
```bash
cd /opt/analytis && git pull
docker compose -f deploy/docker-compose.prod.yml build
docker compose -f deploy/docker-compose.prod.yml up -d
docker compose -f deploy/docker-compose.prod.yml exec backend uv run analytis db migrate
```

## 7. Custos & limites Always Free

- VM A1 Flex 4 OCPU / 24 GB: **grátis**
- 200 GB block storage: **grátis**
- 10 GB Object Storage (backups): **grátis**
- Tráfego de saída 10 TB/mês: **grátis**
- Domínio: ~US$10/ano (Cloudflare, Namecheap)

**Gotcha conhecido**: o OCI Free Tier eventualmente recupera VMs ociosas em regiões cheias. Mitigação: manter CPU > 20% via cron leve (`stress-ng -c 1 -t 10s`) ou aceitar e recriar.

---

## 8. Provisionamento 100% via terminal (alternativa ao console)

Tudo da `Seção 1` pode ser feito via `oci-cli` + `cloud-init`, depois que a conta OCI existir e tiver uma chave de API cadastrada (one-shot).

### 8.1 Setup local do oci-cli (uma única vez)

```bash
# Instala oci-cli (Windows: pip install oci-cli ; macOS: brew install oci-cli)
bash -c "$(curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)"

# Auth via browser (gera keypair local + faz upload do pub key automaticamente)
oci setup bootstrap
# → abre browser, você loga no OCI, ele cria o arquivo ~/.oci/config

# Verifica
oci iam region list --output table
```

### 8.2 Script `deploy/provision-oci.sh` (eu gero)

Cria via API:
- **VCN** `analytis-vcn` (CIDR `10.0.0.0/16`)
- **Internet Gateway** + **route table** com default route `0.0.0.0/0`
- **Subnet pública** `10.0.1.0/24`
- **Security List** com ingress rules (22 do seu IP, 80 e 443 de `0.0.0.0/0`)
- **Reserved Public IP** (printa o IP no final pra você atualizar o DNS)
- **Instância A1 Flex** (4 OCPU / 24 GB) com Ubuntu 22.04 ARM e `cloud-init.yaml` anexado

Saída do script: IP público + comando SSH.

### 8.3 `deploy/cloud-init.yaml` (eu gero)

Roda no primeiro boot da VM:
1. `apt update && apt install docker.io docker-compose-v2 git ufw certbot`
2. Configura UFW + iptables (libera 80/443)
3. Cria user `analytis`, clona o repo em `/opt/analytis`
4. **Para aqui** — espera você fazer `scp deploy/.env.prod ubuntu@<ip>:/opt/analytis/deploy/.env.prod` (segredos não vão no repo nem no cloud-init)

### 8.4 Fluxo completo de deploy inicial

```bash
# 1. Local — provisiona infra
bash deploy/provision-oci.sh
# → imprime: "VM ready. Public IP: 150.x.x.x. Update DNS A-record now."

# 2. Atualiza DNS (Cloudflare/Namecheap/etc) apontando para o IP

# 3. Envia segredos pra VM (nunca commitar)
scp deploy/.env.prod ubuntu@150.x.x.x:/opt/analytis/deploy/.env.prod

# 4. Aguarda propagação DNS
dig +short analytis.example.com  # deve retornar 150.x.x.x

# 5. SSH e finaliza (eu deixo um `deploy/finish.sh` na VM via cloud-init)
ssh ubuntu@150.x.x.x 'bash /opt/analytis/deploy/finish.sh analytis.example.com seu@email.com'
# → finish.sh:
#    - certbot certonly --standalone -d $DOMAIN --email $EMAIL --agree-tos -n
#    - docker compose -f deploy/docker-compose.prod.yml up -d --build
#    - docker compose exec backend uv run analytis db migrate
#    - curl https://$DOMAIN/v1/health
```

Total: **~5 minutos** depois da conta OCI estar pronta. Você nunca mais precisa do console web pra deploy.

### 8.5 Updates subsequentes (a partir do segundo deploy)

Roda local:
```bash
ssh ubuntu@<ip> 'cd /opt/analytis && git pull && docker compose -f deploy/docker-compose.prod.yml up -d --build && docker compose exec backend uv run analytis db migrate'
```

Ou roda `deploy/redeploy.sh <ip>` que faz o mesmo.

---

## 9. Próximos passos (ordem sugerida)

1. Você roda `oci setup bootstrap` local (sub-seção 8.1) — me confirma quando estiver feito.
2. Você me passa: **(a)** domínio, **(b)** região OCI, **(c)** seu IP público (`curl ifconfig.me`) pra liberar SSH só pra você.
3. Eu gero num PR: `deploy/Dockerfile.backend`, `deploy/Dockerfile.frontend`, `deploy/docker-compose.prod.yml`, `deploy/nginx/nginx.conf`, `deploy/provision-oci.sh`, `deploy/cloud-init.yaml`, `deploy/finish.sh`, `deploy/.env.prod.example`, `deploy/backup/pg-backup.sh`.
4. Você executa `provision-oci.sh` → atualiza DNS → `scp .env.prod` → `finish.sh`.
5. Configura crons de backup + renovação TLS (instruções no PR).

Me confirme: **(a)** qual domínio vai usar, **(b)** região OCI preferida (sa-saopaulo-1 / us-ashburn-1), **(c)** se vai querer build do front com `VITE_API_BASE_URL` apontando pro domínio final agora ou se quer manter relativo. Aí já começo a gerar os arquivos do `deploy/`.
