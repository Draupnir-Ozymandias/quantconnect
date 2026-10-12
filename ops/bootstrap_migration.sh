#!/usr/bin/env bash
set -euo pipefail
umask 077
if [[ $# -ne 3 ]]; then
    echo 'Usage: bash bootstrap.sh /absolute/python3.14 /absolute/new/project/path MANIFEST_SHA256' >&2
    exit 2
fi
QCRL_PYTHON="$1"
QCRL_DESTINATION="$2"
QCRL_MANIFEST_SHA256="$3"
QCRL_PACKAGE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[[ "$QCRL_PYTHON" == /* && "$QCRL_DESTINATION" == /* ]] || { echo 'Absolute paths required.' >&2; exit 2; }
"$QCRL_PYTHON" -I -c 'import platform,sys,sysconfig; assert sys.version_info[:3]==(3,14,6), "Python 3.14.6 required"; assert not sysconfig.get_config_var("Py_GIL_DISABLED"), "Standard GIL build required"; assert platform.system()=="Darwin" and platform.machine()=="x86_64", "Intel macOS required"'
"$QCRL_PYTHON" -I "$QCRL_PACKAGE/project_migration.py" install --package "$QCRL_PACKAGE" --destination "$QCRL_DESTINATION" --expected-manifest-sha256 "$QCRL_MANIFEST_SHA256"
"$QCRL_PYTHON" -I -m venv "$QCRL_DESTINATION/.venv"
"$QCRL_DESTINATION/.venv/bin/python" -I -m pip --isolated install --no-index --no-deps "$QCRL_PACKAGE/websockets-15.0.1-py3-none-any.whl"
cd "$QCRL_DESTINATION"
"$QCRL_DESTINATION/.venv/bin/python" -m unittest discover -s tests -q
git status --short --branch
echo 'Bootstrap complete. No cloud sync, collectors, credentials or jobs were imported.'
