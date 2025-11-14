#!/usr/bin/env bash
# Usage: GH_TOKEN=... ./post_issues.sh <owner> <repo> <json-file>
# Example: GH_TOKEN=... ./post_issues.sh PetrefiedThunder Prep scripts/post_merge_validation.json
#
# Creates GitHub issues from a JSON specification using the GitHub REST API.
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 <owner> <repo> <json-file>" >&2
  exit 1
fi

OWNER="$1"
REPO="$2"
FILE="$3"

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required but was not found in PATH" >&2
  exit 1
fi

if [[ ! -f "$FILE" ]]; then
  echo "JSON file '$FILE' not found" >&2
  exit 1
fi

if [[ -z "${GH_TOKEN:-}" ]]; then
  echo "GH_TOKEN environment variable must be set" >&2
  exit 1
fi

while IFS= read -r row; do
  title=$(jq -r '.title' <<<"$row")
  body=$(jq -r '.body' <<<"$row")
  labels=$(jq -r '.labels' <<<"$row")

  payload=$(jq -n --arg title "$title" --arg body "$body" --argjson labels "$labels" \
    '{title: $title, body: $body, labels: $labels}')

  curl -sS -X POST "https://api.github.com/repos/${OWNER}/${REPO}/issues" \
    -H "Authorization: Bearer ${GH_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -d "$payload" >/dev/null

done < <(jq -c '.[]' "$FILE")

echo "Created issues defined in ${FILE} for ${OWNER}/${REPO}."
