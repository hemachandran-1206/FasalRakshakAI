#!/usr/bin/env bash
# Start FasalRakshak AI with one command: backend + website (+ optional public link).
#   ./run-demo.sh            local only   -> http://localhost:5173
#   ./run-demo.sh --public   also open a free Cloudflare quick tunnel and print its public address
#   ./run-demo.sh --build    rebuild the website first (needed after frontend code changes)
# Stop everything with Ctrl+C.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT=8000      # must match the proxy target in frontend/vite.config.js
WEB_PORT=5173
PUBLIC=0; BUILD=0
for arg in "$@"; do
  case "$arg" in
    --public) PUBLIC=1 ;;
    --build)  BUILD=1 ;;
    -h|--help) sed -n '2,6p' "$0"; exit 0 ;;
    *) echo "Unknown option: $arg (try --help)"; exit 2 ;;
  esac
done

LOGS="$ROOT/.demo-logs"; mkdir -p "$LOGS"
PIDS=()
# each component runs in its own process group (setsid) so npx/vite children are stopped too
stop_all() { for p in "${PIDS[@]:-}"; do [ -n "$p" ] && { kill -- "-$p" 2>/dev/null || kill "$p" 2>/dev/null; }; done; wait 2>/dev/null; }
die() { echo "ERROR: $*" >&2; stop_all; exit 1; }
trap 'echo; echo "Stopping..."; stop_all; exit 0' INT TERM

port_busy() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }
for p in "$BACKEND_PORT" "$WEB_PORT"; do
  port_busy "$p" && die "port $p is already in use. Close the old backend/website (or whatever uses it) and try again."
done
command -v curl >/dev/null || die "curl is required"
command -v npm  >/dev/null || die "npm (Node.js) is required"

# Python environment
if [ -f "$ROOT/.venv/bin/activate" ]; then source "$ROOT/.venv/bin/activate"
elif [ -f "$ROOT/backend/.venv/bin/activate" ]; then source "$ROOT/backend/.venv/bin/activate"; fi
command -v uvicorn >/dev/null || die "uvicorn not found. Activate your virtual environment or run: pip install -r backend/requirements.txt"
[ -f "$ROOT/backend/.env" ] || echo "NOTE: backend/.env not found, using development defaults (local database)."

# 1) backend
echo "Starting backend (first start downloads the AI models and can take a few minutes)..."
( cd "$ROOT/backend" && exec setsid uvicorn app.main:app --port "$BACKEND_PORT" ) >"$LOGS/backend.log" 2>&1 &
BACK=$!; PIDS+=("$BACK")
for i in $(seq 1 300); do
  curl -sf "http://127.0.0.1:$BACKEND_PORT/health" >/dev/null 2>&1 && break
  kill -0 "$BACK" 2>/dev/null || { tail -15 "$LOGS/backend.log"; die "backend stopped. Log: $LOGS/backend.log"; }
  [ "$i" = 300 ] && die "backend did not become ready in 5 minutes. Log: $LOGS/backend.log"
  sleep 1
done
echo "  backend ready on port $BACKEND_PORT"

# 2) website
cd "$ROOT/frontend" || die "frontend folder not found"
[ -d node_modules ] || { echo "Installing website packages..."; npm install >"$LOGS/npm-install.log" 2>&1 || die "npm install failed. Log: $LOGS/npm-install.log"; }
if [ "$BUILD" = 1 ] || [ ! -d dist ]; then
  echo "Building website..."; npm run build >"$LOGS/build.log" 2>&1 || { tail -15 "$LOGS/build.log"; die "build failed. Log: $LOGS/build.log"; }
fi
setsid npx vite preview --host --port "$WEB_PORT" --strictPort >"$LOGS/web.log" 2>&1 &
WEB=$!; PIDS+=("$WEB")
for i in $(seq 1 30); do
  curl -sf "http://127.0.0.1:$WEB_PORT/api/languages" >/dev/null 2>&1 && break
  kill -0 "$WEB" 2>/dev/null || { tail -10 "$LOGS/web.log"; die "website stopped. Log: $LOGS/web.log"; }
  [ "$i" = 30 ] && die "website did not start. Log: $LOGS/web.log"
  sleep 1
done
echo "  website ready"

# 3) optional public link
PUBLIC_URL=""
if [ "$PUBLIC" = 1 ]; then
  CF="$(command -v cloudflared || true)"; [ -z "$CF" ] && [ -x "$HOME/bin/cloudflared" ] && CF="$HOME/bin/cloudflared"
  [ -n "$CF" ] || die "cloudflared not found (expected ~/bin/cloudflared). See README, section 'Public link'."
  : >"$LOGS/tunnel.log"
  setsid "$CF" tunnel --protocol http2 --url "http://localhost:$WEB_PORT" >"$LOGS/tunnel.log" 2>&1 &
  TUN=$!; PIDS+=("$TUN")
  for i in $(seq 1 60); do
    PUBLIC_URL="$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$LOGS/tunnel.log" | head -1)"
    [ -n "$PUBLIC_URL" ] && break
    kill -0 "$TUN" 2>/dev/null || { tail -10 "$LOGS/tunnel.log"; die "tunnel stopped. Log: $LOGS/tunnel.log"; }
    sleep 1
  done
  [ -n "$PUBLIC_URL" ] || die "no public address after 60 s. Log: $LOGS/tunnel.log"
fi

echo
echo "=============================================================="
echo " FasalRakshak AI is running"
echo "   Local:   http://localhost:$WEB_PORT"
echo "   API docs: http://127.0.0.1:$BACKEND_PORT/docs"
[ -n "$PUBLIC_URL" ] && echo "   Public:  $PUBLIC_URL   (changes every run; may take a few seconds to open)"
echo "   Logs:    $LOGS"
echo " Press Ctrl+C to stop everything."
echo "=============================================================="
wait -n 2>/dev/null
echo "A component stopped unexpectedly. Check $LOGS"
stop_all
exit 1
