#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════
# Arsenal — one-shot setup for the NYXUS web tools (GSL, RedForge, Forge,
# AI-Cyber-Defense-Trainer, CIPHER). Run ONCE in your own terminal.
#
#   bash ~/Arsenal/setup-apps.sh
#
# It: ensures Postgres is running, creates each app's role + database,
# installs deps, runs migrations, and seeds admin logins. sudo is used ONLY
# for the Postgres service/role step (it will prompt you). Idempotent — safe
# to re-run. Node/pnpm installs need NO sudo.
#
# Assumes the default Arch Postgres pg_hba (localhost = trust). If your
# pg_hba requires passwords, the app .env DATABASE_URLs already carry them.
# ════════════════════════════════════════════════════════════════════════
set -uo pipefail
VAULT="$HOME/GowskiNet-Vault"
FAIL=()
ok(){ printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn(){ printf '  \033[33m!\033[0m %s\n' "$*"; }
step(){ printf '\n\033[36m══ %s\033[0m\n' "$*"; }

# ── 1. Postgres up + initialized ────────────────────────────────────────
step "Postgres"
if ! sudo systemctl is-active --quiet postgresql; then
  if [ ! -s /var/lib/postgres/data/PG_VERSION ]; then
    warn "initializing Postgres data dir"
    sudo -u postgres initdb -D /var/lib/postgres/data
  fi
  sudo systemctl enable --now postgresql
fi
sudo systemctl is-active --quiet postgresql && ok "postgresql running" || { echo "Postgres failed to start"; exit 1; }

psql_su(){ sudo -u postgres psql -v ON_ERROR_STOP=1 -tAc "$1"; }
role_exists(){ [ "$(psql_su "SELECT 1 FROM pg_roles WHERE rolname='$1'")" = "1" ]; }
db_exists(){ [ "$(psql_su "SELECT 1 FROM pg_database WHERE datname='$1'")" = "1" ]; }
ensure_role_pw(){ role_exists "$1" || sudo -u postgres psql -c "CREATE ROLE \"$1\" LOGIN PASSWORD '$2';" >/dev/null; ok "role $1"; }
ensure_role_super(){ role_exists "$1" || sudo -u postgres psql -c "CREATE ROLE \"$1\" LOGIN SUPERUSER;" >/dev/null; ok "role $1 (superuser)"; }
ensure_db(){ db_exists "$1" || sudo -u postgres createdb -O "$2" "$1"; ok "db $1"; }

step "roles & databases"
ensure_role_pw   redforge redforge      ; ensure_db redforge         redforge
ensure_role_pw   forge    forge_local_dev; ensure_db forge            forge
ensure_role_super "$USER"                ; ensure_db cipher           "$USER"
ensure_db redforge_trainer "$USER"

# ── 2. per-app: install + migrate + seed ────────────────────────────────
setup_node_app(){ # $1=name  $2=dir  $3=do_seed(0/1)
  local name="$1" dir="$2" seed="$3"
  step "$name"
  [ -d "$dir" ] || { warn "$dir missing — skip"; FAIL+=("$name:missing"); return; }
  cd "$dir"
  [ -f .env ] && { set -a; . ./.env; set +a; }
  # These repos ship a Replit "use pnpm" preinstall guard that misfires in
  # non-interactive shells; --config.verify-deps-before-run=false stops
  # `pnpm run` from re-triggering install. Install is best-effort (deps are
  # usually already present) and never aborts the app.
  local PF="--config.verify-deps-before-run=false"
  if pnpm install --prefer-offline $PF >/dev/null 2>&1; then ok "$name deps installed"; else warn "$name: using existing node_modules (install guard skipped)"; fi
  if pnpm $PF --filter @workspace/db run push >/dev/null 2>&1; then ok "$name migrated"; else warn "$name: db push skipped/failed"; fi
  if [ "$seed" = "1" ]; then
    if pnpm $PF --filter @workspace/scripts run seed >/dev/null 2>&1; then ok "$name seeded"; else warn "$name: seed skipped/failed"; fi
  fi
}

setup_node_app RedForge "$VAULT/Security/RedForge"            0
setup_node_app Forge    "$VAULT/Security/Forge"               0
setup_node_app Trainer  "$VAULT/AI/AI-Cyber-Defense-Trainer"  1
setup_node_app CIPHER   "$VAULT/Security/CIPHER"              1

# ── 3. GSL (Python backend + Vite frontend) ─────────────────────────────
step "GSL"
G="$VAULT/Security/GSL"
if [ -d "$G/gsl-backend" ]; then
  cd "$G/gsl-backend"
  python3 -m venv .venv
  ./.venv/bin/pip install -q --upgrade pip
  if [ -f requirements.txt ]; then ./.venv/bin/pip install -q -r requirements.txt && ok "GSL backend venv ready"; else warn "GSL: no requirements.txt"; fi
  cd "$G"; pnpm install --prefer-offline --config.verify-deps-before-run=false >/dev/null 2>&1 && ok "GSL frontend deps installed" || warn "GSL frontend install failed"
else warn "GSL backend dir missing"; fi

# ── done ────────────────────────────────────────────────────────────────
step "DONE"
if [ ${#FAIL[@]} -eq 0 ]; then ok "all apps set up"; else warn "issues: ${FAIL[*]}"; fi
cat <<'NOTE'

Launch each app (from its dir, after `set -a; . ./.env; set +a`).
NOTE: add  --config.verify-deps-before-run=false  to any `pnpm run` (shown as $PF)
so the repo's preinstall guard doesn't misfire.
  export PF="--config.verify-deps-before-run=false"
  RedForge : PORT=5000 pnpm $PF --filter @workspace/api-server run dev   (UI: pnpm $PF --filter @workspace/redforge run dev)
  Forge    : pnpm $PF --filter @workspace/api-server run start           (serves API+SPA on :20000)
  Trainer  : PORT=8080 pnpm $PF --filter @workspace/api-server run dev:api (UI: pnpm $PF --filter @workspace/redforge run dev)
  CIPHER   : pnpm $PF --filter @workspace/api-server run dev             (UI: pnpm $PF --filter @workspace/cipher run dev)
  GSL      : bash gsl-backend/start.sh                                   (UI: pnpm $PF --filter @workspace/gsl dev)

Or just open the Arsenal hub:  arsenal
NOTE
