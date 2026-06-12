#!/bin/sh
set -eu

mkdir -p data/erp_exports logs config

if [ ! -f config/erp_rpa.local.json ] && [ -f config/erp_rpa.local.json.example ]; then
  cp config/erp_rpa.local.json.example config/erp_rpa.local.json
fi

exec python main_erp.py
