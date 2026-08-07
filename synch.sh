#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(dirname "$PROJECT_DIR")"
PROJECT_NAME="$(basename "$PROJECT_DIR")"

usage() {
    cat <<'EOF'
Usage: ./synch.sh <command> [arguments]

Commands:
  status              Show Git state, project linkage, and LEAN login status.
  test                Run the local deterministic unit tests.
  pull                Pull the linked QuantConnect project after a clean-tree check.
  push                Push committed local files to QuantConnect after confirmation.
  backtest [args...]  Run a cloud backtest without implicitly pushing local changes.

The local Git checkout is the source of truth. Pull and push intentionally
refuse to run while the working tree contains uncommitted changes.
EOF
}

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Required command not found: $1" >&2
        exit 1
    fi
}

require_clean_tree() {
    if [[ -n "$(git -C "$PROJECT_DIR" status --porcelain)" ]]; then
        echo "Refusing to synchronize a dirty working tree." >&2
        echo "Commit, stash, or discard local changes first:" >&2
        git -C "$PROJECT_DIR" status --short >&2
        exit 1
    fi
}

cloud_project_id() {
    python3 -c \
        'import json, sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["cloud-id"])' \
        "$PROJECT_DIR/config.json"
}

show_status() {
    git -C "$PROJECT_DIR" status --short --branch
    echo
    echo "Project directory: $PROJECT_DIR"
    echo "QuantConnect project ID: $(cloud_project_id)"
    echo "LEAN CLI: $(command -v lean 2>/dev/null || echo 'not installed')"

    if command -v lean >/dev/null 2>&1; then
        echo
        lean whoami || true
    fi
}

pull_cloud() {
    require_command lean
    require_clean_tree

    local backup_branch
    backup_branch="backup/pre-qc-pull-$(date -u +%Y%m%dT%H%M%SZ)"
    git -C "$PROJECT_DIR" branch "$backup_branch" HEAD
    echo "Created recovery branch: $backup_branch"

    (
        cd "$WORKSPACE_DIR"
        lean cloud pull --project "$(cloud_project_id)"
    )

    echo
    echo "QuantConnect pull complete. Review the resulting Git diff:"
    git -C "$PROJECT_DIR" status --short --branch
    git -C "$PROJECT_DIR" diff --stat
}

push_cloud() {
    require_command lean
    require_clean_tree

    echo "This will overwrite the linked QuantConnect project with committed local files."
    read -r -p "Push $PROJECT_NAME to QuantConnect? [y/N] " reply

    if [[ "$reply" != "y" && "$reply" != "Y" ]]; then
        echo "Push cancelled."
        exit 0
    fi

    (
        cd "$WORKSPACE_DIR"
        lean cloud push --project "$PROJECT_DIR"
    )
}

run_cloud_backtest() {
    require_command lean
    require_clean_tree

    (
        cd "$WORKSPACE_DIR"
        lean cloud backtest "$(cloud_project_id)" "$@"
    )
}

command_name="${1:-status}"

case "$command_name" in
    status)
        show_status
        ;;
    test)
        cd "$PROJECT_DIR"
        PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
        ;;
    pull)
        pull_cloud
        ;;
    push)
        push_cloud
        ;;
    backtest)
        shift
        run_cloud_backtest "$@"
        ;;
    help|-h|--help)
        usage
        ;;
    *)
        echo "Unknown command: $command_name" >&2
        usage >&2
        exit 2
        ;;
esac
