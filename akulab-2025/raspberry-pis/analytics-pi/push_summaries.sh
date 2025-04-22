#!/usr/bin/env bash
#
# push_summaries.sh
#
# 1) Copies all daily summary HTML files to the GitHub Pages repo
# 2) Auto-generates an index.html listing all summaries
# 3) Commits and pushes them

set -euo pipefail

REPO_DIR="/home/analyticspi/Gits/akulab2025"
SRC_DIR="/home/analyticspi/logs/daily_summaries"
DEST_DIR="${REPO_DIR}/docs/daily_summaries"

echo "📁 Ensuring destination directory exists: $DEST_DIR"
mkdir -p "$DEST_DIR"

echo "🔄 Copying all summaries from $SRC_DIR to $DEST_DIR ..."
cp "$SRC_DIR"/*.html "$DEST_DIR/" 2>/dev/null || {
  echo "⚠️ No summaries to copy. Exiting."
  exit 0
}

echo "📝 Generating index.html in $DEST_DIR ..."
INDEX_FILE="${DEST_DIR}/index.html"

{
  echo "<!DOCTYPE html>"
  echo "<html>"
  echo "<head>"
  echo "  <meta charset=\"utf-8\">"
  echo "  <title>Daily Summaries</title>"
  echo "</head>"
  echo "<body>"
  echo "  <h1>Daily Summaries</h1>"
  echo "  <ul>"
  # Sort them alphabetically or chronologically (depending on file naming).
  for file in $(ls "$DEST_DIR"/*.html | sort); do
    filename=$(basename "$file")
    [[ "$filename" == "index.html" ]] && continue
    echo "    <li><a href=\"$filename\">$filename</a></li>"
  done
  echo "  </ul>"
  echo "</body>"
  echo "</html>"
} > "$INDEX_FILE"

cd "$REPO_DIR"
echo "📍 Changed to repository: $(pwd)"

# Stage any changed or new HTML files
echo "➕ Staging changes..."
git add docs/daily_summaries/*.html

# Check if there is anything to commit
if git diff --cached --quiet; then
  echo "✅ No new or modified summaries to commit."
  exit 0
fi

# Commit and push
COMMIT_MSG="🔄 Add/update daily summaries on $(date +%F_%T)"
echo "✅ Committing: $COMMIT_MSG"
git commit -m "$COMMIT_MSG"

echo "🚀 Pushing to origin/main..."
git push origin main
echo "✅ Done!"

