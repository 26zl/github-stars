#!/usr/bin/env bash
# Refresh starred.tsv from GitHub, then regenerate README.md. Needs gh auth.
set -euo pipefail
cd "$(dirname "$0")"
OWNER="${GITHUB_REPOSITORY_OWNER:-$(gh api user --jq .login)}"
export OWNER
gh api "users/$OWNER/starred" --paginate --jq '.[] | select(.private | not) | [.full_name, (.language // ""), .stargazers_count, ((.topics // [])[:6] | join(",")), ((.description // "") | gsub("[\u0000-\u001f\u202a-\u202e\u2066-\u2069]"; " ") | if length > 140 then .[0:139] + "…" else . end)] | @tsv' > starred.tsv.tmp
mv starred.tsv.tmp starred.tsv
python3 categorize.py
echo "Updated README.md from $(wc -l < starred.tsv | tr -d ' ') starred repos."
