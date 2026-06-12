#!/bin/sh
set -eu

mkdir -p data/erp_exports logs config

if [ ! -f config/erp_rpa.local.json ] && [ -f config/erp_rpa.local.json.example ]; then
  cp config/erp_rpa.local.json.example config/erp_rpa.local.json
fi

python - <<'PY'
import json
from pathlib import Path

path = Path("config/erp_rpa.local.json")
if path.exists():
    data = json.loads(path.read_text(encoding="utf-8"))
    data["headful"] = False
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

exec python main_erp.py
