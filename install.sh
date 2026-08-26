#!/usr/bin/env bash
# Installer/updater: prepara un host Ubuntu/Debian da zero (Docker, rete,
# reverse proxy, immagine desktop) e porta su DeskHub.
# Rilanciabile in sicurezza: se trova gia' un'installazione, aggiorna
# invece di ripartire da zero.
#
# Uso:
#   curl -fsSL https://raw.githubusercontent.com/FedericoCasillo/deskhub/master/install.sh | bash
#
# Variabili opzionali (per uso non interattivo):
#   TARGET_DIR      cartella dove clonare il progetto (default: ~/deskhub)
#   DATA_DIR        cartella dati desktop (default: ~/deskhub-data)
#   HTTPS_PORT      porta pubblica del reverse proxy (default: 8443)
#   MANAGER_INITIAL_ADMIN_USER      utente amministratore iniziale della webapp
#   MANAGER_INITIAL_ADMIN_PASSWORD  password dell'amministratore iniziale
#   SKIP_TRAEFIK    se =1, non tocca il reverse proxy (usane uno gia' tuo)
#   MANAGER_SOURCE  pull (default, scarica lo snapshot pinnato da GHCR) o
#                   build (ricostruisci sempre da sorgente)

set -euo pipefail

REPO_URL="https://github.com/FedericoCasillo/deskhub.git"
TARGET_DIR="${TARGET_DIR:-$HOME/deskhub}"

log() { printf '\n\033[1;32m==>\033[0m %s\n' "$1"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$1"; }
die() { printf '\033[1;31mErrore:\033[0m %s\n' "$1" >&2; exit 1; }

command -v apt-get >/dev/null 2>&1 || die "Questo installer supporta solo host Debian/Ubuntu (apt-get non trovato)."

CURRENT_USER="$(id -un)"

# --- 1. pacchetti di base -------------------------------------------------
log "Controllo pacchetti di sistema (docker.io, docker-compose-v2, git, openssl)..."
NEEDED_PKGS=()
for pkg in docker.io docker-compose-v2 git openssl ca-certificates; do
  dpkg -s "$pkg" >/dev/null 2>&1 || NEEDED_PKGS+=("$pkg")
done

if [ "${#NEEDED_PKGS[@]}" -gt 0 ]; then
  log "Installo: ${NEEDED_PKGS[*]}"
  sudo apt-get update
  sudo apt-get install -y "${NEEDED_PKGS[@]}"
else
  log "Tutti i pacchetti di sistema sono gia' presenti."
fi

sudo systemctl enable --now docker >/dev/null 2>&1 || true

JUST_ADDED_TO_DOCKER_GROUP=0
if ! id -nG "$CURRENT_USER" | grep -qw docker; then
  log "Aggiungo $CURRENT_USER al gruppo docker (serve un nuovo login per usarlo senza sudo in futuro)."
  sudo usermod -aG docker "$CURRENT_USER"
  JUST_ADDED_TO_DOCKER_GROUP=1
fi

DOCKER="sudo docker"

# --- 2. codice sorgente ----------------------------------------------------
if [ -d "$TARGET_DIR/.git" ]; then
  log "Trovata installazione esistente in $TARGET_DIR, aggiorno..."
  git -C "$TARGET_DIR" pull --ff-only
else
  log "Clono il progetto in $TARGET_DIR..."
  git clone "$REPO_URL" "$TARGET_DIR"
fi
cd "$TARGET_DIR"

# Catturato qui, prima che qualunque sezione successiva possa creare .env da
# zero (la 3.5 per il segreto Traefik, la 6 per DATA_DIR): serve alla sezione
# 7 per distinguere un .env davvero preesistente (da aggiornare) da uno
# appena creato in questa stessa esecuzione (che non e' affatto "una
# versione precedente").
ENV_PREEXISTING=0
[ -f .env ] && ENV_PREEXISTING=1

# --- 3. rete condivisa -------------------------------------------------
PROXY_NETWORK="${PROXY_NETWORK:-deskhub-proxy}"
if ! $DOCKER network inspect "$PROXY_NETWORK" >/dev/null 2>&1; then
  log "Creo la rete Docker $PROXY_NETWORK..."
  $DOCKER network create "$PROXY_NETWORK" >/dev/null
fi

# --- 3.5 segreto condiviso Traefik<->manager ------------------------------
# Protegge l'endpoint interno che genera il routing dinamico verso i
# desktop (contiene i token di sessione attivi in chiaro, va protetto da
# accesso pubblico). Generato una sola volta e riusato ai rilanci, come il
# certificato TLS qui sotto: se cambiasse ad ogni riavvio invaliderebbe le
# sessioni desktop gia' aperte in altre schede senza motivo.
if [ -f .env ] && grep -q '^TRAEFIK_INTERNAL_SECRET=' .env; then
  TRAEFIK_INTERNAL_SECRET="$(grep -m1 '^TRAEFIK_INTERNAL_SECRET=' .env | cut -d= -f2-)"
else
  log "Genero il segreto interno Traefik<->manager..."
  TRAEFIK_INTERNAL_SECRET="$(openssl rand -hex 32)"
  if [ -f .env ]; then
    echo "TRAEFIK_INTERNAL_SECRET=${TRAEFIK_INTERNAL_SECRET}" >> .env
  else
    echo "TRAEFIK_INTERNAL_SECRET=${TRAEFIK_INTERNAL_SECRET}" > .env
  fi
fi

# --- 4. certificato TLS persistente per il reverse proxy -----------------
# Senza un certificato esplicito, Traefik userebbe il proprio self-signed
# interno — che pero' si rigenera (nuova chiave, nuovo seriale) ad ogni
# reload della configurazione dinamica, cioe' ad ogni creazione/avvio/arresto
# /eliminazione di un desktop. Il cambio invalida la fiducia gia' data dal
# browser e rompe le connessioni websocket gia' aperte (schermo nero finche'
# non si ricarica la pagina e si riaccetta il certificato). Generato una sola
# volta e riusato per tutta la vita dell'installazione: se esiste gia' (anche
# da un rilancio di questo script) non viene toccato.
if [ "${SKIP_TRAEFIK:-0}" != "1" ]; then
  CERT_DIR="deploy/traefik/certs"
  if [ ! -f "$CERT_DIR/cert.pem" ] || [ ! -f "$CERT_DIR/key.pem" ]; then
    log "Genero il certificato TLS persistente del reverse proxy..."
    mkdir -p "$CERT_DIR"
    CERT_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
    CERT_SAN="DNS:localhost,IP:127.0.0.1"
    [ -n "$CERT_IP" ] && CERT_SAN="${CERT_SAN},IP:${CERT_IP}"
    openssl req -x509 -nodes -newkey rsa:2048 -sha256 -days 3650 \
      -keyout "$CERT_DIR/key.pem" -out "$CERT_DIR/cert.pem" \
      -subj "/CN=deskhub" -addext "subjectAltName=${CERT_SAN}"
    chmod 600 "$CERT_DIR/key.pem"
  else
    log "Certificato TLS del reverse proxy gia' presente, non lo tocco."
  fi
fi

# --- 5. reverse proxy (Traefik) ----------------------------------------
if [ "${SKIP_TRAEFIK:-0}" != "1" ]; then
  log "Avvio/aggiorno il reverse proxy (Traefik)..."
  HTTPS_PORT="${HTTPS_PORT:-8443}"
  # Scritto su file invece che passato come variabile d'ambiente al comando:
  # "VAR=val $DOCKER compose ..." non funziona perche' $DOCKER e' "sudo
  # docker" e sudo, per policy di default, resetta l'ambiente ripulendolo
  # delle variabili assegnate inline (env_reset) — la variabile non
  # arriverebbe mai al processo compose eseguito come root. Un file .env in
  # questa cartella invece viene letto da disco da docker compose stesso,
  # a prescindere da sudo.
  cat > deploy/traefik/.env <<EOF
TRAEFIK_HTTPS_PORT=$HTTPS_PORT
TRAEFIK_IMAGE=${TRAEFIK_IMAGE:-}
TRAEFIK_INTERNAL_SECRET=$TRAEFIK_INTERNAL_SECRET
PROXY_NETWORK=$PROXY_NETWORK
EOF
  (cd deploy/traefik && $DOCKER compose up -d)
else
  warn "SKIP_TRAEFIK=1: presumo tu abbia gia' un reverse proxy configurato sulla rete $PROXY_NETWORK, con TRAEFIK_INTERNAL_SECRET impostato allo stesso modo."
fi

# --- 6. cartella dati dedicata -------------------------------------------
if [ -f .env ] && grep -q '^DATA_DIR=' .env; then
  # .env gia' presente con DATA_DIR gia' configurato: lo riuso, non tocco le credenziali.
  DATA_DIR="$(grep -m1 '^DATA_DIR=' .env | cut -d= -f2-)"
else
  DATA_DIR="${DATA_DIR:-$HOME/deskhub-data}"
  echo "DATA_DIR=$DATA_DIR" >> .env
fi
mkdir -p "$DATA_DIR"

# --- 7. file .env ------------------------------------------------------
# L'autenticazione e' gestita dalla webapp stessa (login, utenti, ruoli), non
# piu' da Traefik: qui serve solo bootstrare il primo utente admin, e solo se
# non esiste ancora nessun utente (rilevato dal manager stesso al boot, non
# da qui: install.sh non sa se il primo login e' gia' avvenuto).
NEEDS_ADMIN_BOOTSTRAP=0
if grep -q '^MANAGER_INITIAL_ADMIN_USER=' .env 2>/dev/null; then
  log "Trovato .env esistente, mantengo le credenziali gia' configurate."
elif [ "$ENV_PREEXISTING" = "1" ]; then
  warn "Trovato un .env di una versione precedente (autenticazione via Traefik): l'accesso ora e' gestito dalla webapp."
  NEEDS_ADMIN_BOOTSTRAP=1
else
  NEEDS_ADMIN_BOOTSTRAP=1
fi

if [ "$NEEDS_ADMIN_BOOTSTRAP" = "1" ]; then
  log "Configurazione dell'amministratore iniziale della webapp."
  MANAGER_INITIAL_ADMIN_USER="${MANAGER_INITIAL_ADMIN_USER:-}"
  if [ -z "$MANAGER_INITIAL_ADMIN_USER" ]; then
    read -rp "Nome utente amministratore [admin]: " MANAGER_INITIAL_ADMIN_USER
    MANAGER_INITIAL_ADMIN_USER="${MANAGER_INITIAL_ADMIN_USER:-admin}"
  fi

  MANAGER_INITIAL_ADMIN_PASSWORD="${MANAGER_INITIAL_ADMIN_PASSWORD:-}"
  if [ -z "$MANAGER_INITIAL_ADMIN_PASSWORD" ]; then
    while true; do
      read -rsp "Password: " MANAGER_INITIAL_ADMIN_PASSWORD; echo
      read -rsp "Conferma password: " MANAGER_INITIAL_ADMIN_PASSWORD_CONFIRM; echo
      [ "$MANAGER_INITIAL_ADMIN_PASSWORD" = "$MANAGER_INITIAL_ADMIN_PASSWORD_CONFIRM" ] && [ -n "$MANAGER_INITIAL_ADMIN_PASSWORD" ] && break
      warn "Le password non coincidono o sono vuote, riprova."
    done
  fi

  # Docker Compose interpola i "$" nei file .env: raddoppio ogni "$" della
  # password nel caso ne contenga, per evitare che venga svuotato.
  PASSWORD_ESCAPED="${MANAGER_INITIAL_ADMIN_PASSWORD//\$/\$\$}"

  if [ -f .env ]; then
    grep -v '^MANAGER_HTPASSWD=\|^MANAGER_INITIAL_ADMIN_USER=\|^MANAGER_INITIAL_ADMIN_PASSWORD=' .env > .env.tmp || true
    mv .env.tmp .env
    {
      echo "MANAGER_INITIAL_ADMIN_USER=${MANAGER_INITIAL_ADMIN_USER}"
      echo "MANAGER_INITIAL_ADMIN_PASSWORD=${PASSWORD_ESCAPED}"
    } >> .env
    log "File .env aggiornato."
  else
    cat > .env <<EOF
DATA_DIR=$DATA_DIR
MANAGER_INITIAL_ADMIN_USER=${MANAGER_INITIAL_ADMIN_USER}
MANAGER_INITIAL_ADMIN_PASSWORD=${PASSWORD_ESCAPED}
EOF
    log "File .env creato."
  fi

  unset MANAGER_INITIAL_ADMIN_PASSWORD MANAGER_INITIAL_ADMIN_PASSWORD_CONFIRM
fi

# --- 8. immagine e avvio del manager -------------------------------------
# Default: scarica lo snapshot pinnato per digest pubblicato su GHCR (stesso
# meccanismo dell'immagine webtop), cosi' un'installazione normale dipende
# solo da GitHub e GHCR e non deve mai buildare nulla in locale. MANAGER_SOURCE
# =build (opt-in, es. per chi modifica il codice) forza la build da sorgente.
MANAGER_PINNED_IMAGE="ghcr.io/federicocasillo/deskhub-manager@sha256:30ec269d23b75773ea12114fa5dc021ab270211b5e045829da456b411b748b48"
MANAGER_LOCAL_IMAGE="deskhub-manager:latest"

if [ "${MANAGER_SOURCE:-pull}" = "build" ]; then
  log "Build dell'immagine del manager da sorgente (MANAGER_SOURCE=build)..."
  $DOCKER compose build
elif $DOCKER pull "$MANAGER_PINNED_IMAGE" >/dev/null 2>&1; then
  log "Scaricata l'immagine pinnata del manager."
  $DOCKER tag "$MANAGER_PINNED_IMAGE" "$MANAGER_LOCAL_IMAGE"
else
  warn "Pull dell'immagine pinnata del manager non riuscito, la builderò da sorgente."
  $DOCKER compose build
fi

log "Avvio del manager..."
$DOCKER compose up -d

# Una volta che il manager ha creato l'admin iniziale (file utenti presente
# in DATA_DIR), la password in chiaro non serve piu': la tolgo da .env
# invece di lasciarla li' per sempre. Attendo qualche secondo che il
# container faccia il bootstrap al boot prima di controllare.
if grep -q '^MANAGER_INITIAL_ADMIN_PASSWORD=' .env 2>/dev/null; then
  for _ in $(seq 1 10); do
    [ -f "$DATA_DIR/.manager-users.json" ] && break
    sleep 1
  done
  if [ -f "$DATA_DIR/.manager-users.json" ]; then
    grep -v '^MANAGER_INITIAL_ADMIN_PASSWORD=' .env > .env.tmp && mv .env.tmp .env
    log "Bootstrap admin completato: rimossa la password in chiaro da .env."
  else
    warn "Non riesco a confermare il bootstrap dell'admin: lascio MANAGER_INITIAL_ADMIN_PASSWORD in .env, controlla i log del manager ('$DOCKER compose logs manager')."
  fi
fi

HTTPS_PORT="${HTTPS_PORT:-8443}"
HOST_HINT="$(hostname -I 2>/dev/null | awk '{print $1}')"
HOST_HINT="${HOST_HINT:-<ip-del-server>}"

cat <<EOF

============================================================
 Installazione completata.

 Apri:  https://${HOST_HINT}:${HTTPS_PORT}/manager/
 (accetta il certificato self-signed del reverse proxy)

 I dati dei desktop vivono in: ${DATA_DIR}

 Per aggiornare in futuro, rilancia questo stesso script:
   $TARGET_DIR/install.sh
============================================================
EOF

if [ "$JUST_ADDED_TO_DOCKER_GROUP" = "1" ]; then
  warn "Fai logout/login (o 'newgrp docker') perche' l'appartenenza al gruppo docker sia attiva nella tua shell."
fi
