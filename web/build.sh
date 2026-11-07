#!/usr/bin/env bash
# Build the browser version of Wizard Duel into web/dist/.
#
#   pip install pygbag certifi
#   bash web/build.sh            # build only
#   bash web/build.sh --serve    # build, then play it at http://localhost:8000
#
# web/dist/ is what gets published to GitHub Pages.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
STAGE="$(mktemp -d)/wizard-duel"

# Only the game itself goes into the web build (not design/, .venv/, ...)
mkdir -p "$STAGE"
cp "$ROOT"/{main,wizard_duel,wizard_art,scene_art,sound}.py "$STAGE"/
cp -R "$ROOT/assets" "$STAGE"/

# Some Python installs (e.g. python.org on macOS) can't verify HTTPS certificates
# on their own; pygbag downloads its page template, so point it at certifi's.
export SSL_CERT_FILE="${SSL_CERT_FILE:-$("$PYTHON" -m certifi 2>/dev/null || true)}"

ARGS=(--title "Wizard Duel" --template "$ROOT/web/wizard-duel.tmpl")
"$PYTHON" -m pygbag --build "${ARGS[@]}" "$STAGE"

rm -rf "$ROOT/web/dist"
cp -R "$STAGE/build/web" "$ROOT/web/dist"
touch "$ROOT/web/dist/.nojekyll"        # tell GitHub Pages to serve files as-is
echo "Built: $ROOT/web/dist"

if [[ "${1:-}" == "--serve" ]]; then
    "$PYTHON" -m pygbag "${ARGS[@]}" "$STAGE"
fi
