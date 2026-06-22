#!/usr/bin/env bash
# Remove QUANT historical sync cron entries (called automatically when pipeline completes).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${ROOT}/backend/venv/bin/python"

cd "${ROOT}/backend"
"${PY}" -c "
from data.sync_completion import uninstall_sync_cron, COMPLETE_FLAG
removed = uninstall_sync_cron()
print('Cron entries removed.' if removed else 'No sync cron entries found.')
if COMPLETE_FLAG.exists():
    print(f'Completion flag: {COMPLETE_FLAG}')
"
