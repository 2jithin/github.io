#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd -- "$script_dir/.." && pwd)"
archive_path="$project_dir/portfolio.zip"

command -v zip >/dev/null 2>&1 || {
  echo "Error: zip is not installed." >&2
  exit 1
}

rm -f -- "$archive_path"

(
  cd -- "$project_dir"
  zip -rq "$archive_path" . \
    -x '.git/*' \
       '.venv/*' \
       '*/__pycache__/*' \
       '.DS_Store' \
       '*/.DS_Store' \
       'portfolio.zip' \
       '*.zip'
)

echo "Created: $archive_path"
