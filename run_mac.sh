#!/usr/bin/env bash
# ==============================================================================
# PolSci & IR MA AI Ügynök — Automatikus Indító Script (2020 Mac Optimalizált)
# Támogatja mind a 2020-as Apple Silicon (M1), mind a 2020-as Intel Mac gépeket.
# ==============================================================================

set -e

cd "$(dirname "$0")"

echo "======================================================================"
echo "  PolSci & IR MA AI Ügynök (Magyar + Európai Mesterszak Összehasonlító)"
echo "  2020 Mac Helyi Indító (Ollama + FastAPI Webes Felület)"
echo "======================================================================"

ARCH="$(uname -m)"
OS_NAME="$(uname -s)"
DEFAULT_MODEL="qwen2.5:3b"

if [ "$OS_NAME" = "Darwin" ]; then
  RAM_BYTES="$(sysctl -n hw.memsize 2>/dev/null || echo 8589934592)"
  RAM_GB=$((RAM_BYTES / 1073741824))
  echo "-> Észlelt Mac hardver: macOS ($ARCH) | Memória: ${RAM_GB} GB RAM"
  if [ "$ARCH" = "x86_64" ] && [ "$RAM_GB" -le 8 ]; then
    echo "-> 2020 Intel Mac (8GB RAM) profil aktiválva: Alacsony memóriahasználat (qwen2.5:3b)"
    DEFAULT_MODEL="qwen2.5:3b"
  elif [ "$ARCH" = "arm64" ]; then
    echo "-> 2020 Apple Silicon M1 profil aktiválva: Metal GPU gyorsítás ($DEFAULT_MODEL)"
  fi
fi

export OLLAMA_MODEL="${OLLAMA_MODEL:-$DEFAULT_MODEL}"
export PORT="${PORT:-8000}"

# 1. Ollama ellenőrzése és indítása
if command -v ollama >/dev/null 2>&1; then
  echo "-> Ollama telepítve van. Szerver állapot ellenőrzése..."
  if ! curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "-> Ollama háttérszerver indítása (ollama serve)..."
    nohup ollama serve >/tmp/ollama_polsci.log 2>&1 &
    sleep 3
  fi

  if ! ollama list 2>/dev/null | grep -q "${OLLAMA_MODEL%%:*}"; then
    echo "-> Ajánlott könnyűsúlyú modell letöltése (${OLLAMA_MODEL}, ~1.9 GB)..."
    ollama pull "$OLLAMA_MODEL" || true
  fi
else
  echo "----------------------------------------------------------------------"
  echo "FIGYELEM: Az 'ollama' még nincs telepítve ezen a Mac-en."
  echo "Az alkalmazás Hibrid Determinisztikus módban így is azonnal elindul!"
  echo "A teljes helyi LLM módhoz telepítsd az Ollama-t:"
  echo "  • Homebrew-val:  brew install --cask ollama"
  echo "  • Vagy töltsd le: https://ollama.com/download/mac"
  echo "----------------------------------------------------------------------"
fi

# 2. Python virtuális környezet (.venv) létrehozása és csomagok telepítése
if [ ! -d ".venv" ]; then
  echo "-> Python virtuális környezet (.venv) létrehozása..."
  python3 -m venv .venv
fi

source .venv/bin/activate
echo "-> Függőségek ellenőrzése..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# 3. Böngésző automatikus megnyitása Mac-en
URL="http://127.0.0.1:${PORT}"
echo ""
echo "======================================================================"
echo "  Az AI Ügynök Webes Felülete elindult: ${URL}"
echo "  Leállításhoz nyomj Ctrl+C-t ebben az ablakban."
echo "======================================================================"

if [ "$OS_NAME" = "Darwin" ]; then
  (sleep 2 && open "$URL") &
fi

exec python3 -m uvicorn app:app --host 127.0.0.1 --port "$PORT"
