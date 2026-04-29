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

echo "📝 Generating year-grouped index pages in $DEST_DIR ..."

# Collect all summary files and group by year
declare -A year_files
for file in $(ls "$DEST_DIR"/*_summary.html 2>/dev/null | sort); do
  filename=$(basename "$file")
  year=$(echo "$filename" | cut -d'-' -f1)
  if [[ "$year" =~ ^[0-9]{4}$ ]]; then
    year_files["$year"]+="$filename "
  fi
done

# Generate per-year index pages
for year in $(echo "${!year_files[@]}" | tr ' ' '\n' | sort); do
  YEAR_INDEX="${DEST_DIR}/${year}_summaries.html"
  {
    echo "<!DOCTYPE html>"
    echo "<html>"
    echo "<head>"
    echo "  <meta charset=\"utf-8\">"
    echo "  <title>Auklab Daily Summaries - $year</title>"
    echo "  <style>"
    echo "    body { font-family: Arial, sans-serif; margin: 20px; }"
    echo "    h1 { color: #333; }"
    echo "    a { color: #0066cc; text-decoration: none; }"
    echo "    a:hover { text-decoration: underline; }"
    echo "    .back-link { margin-top: 20px; }"
    echo "  </style>"
    echo "</head>"
    echo "<body>"
    echo "  <h1>Auklab Daily Summaries - $year</h1>"
    echo "  <ul>"
    for filename in ${year_files["$year"]}; do
      echo "    <li><a href=\"$filename\">$filename</a></li>"
    done
    echo "  </ul>"
    echo "  <div class=\"back-link\"><a href=\"index.html\">← Back to all years</a></div>"
    echo "</body>"
    echo "</html>"
  } > "$YEAR_INDEX"
  echo "  ✅ Generated: ${year}_summaries.html"
done

# Generate main index.html with year links
INDEX_FILE="${DEST_DIR}/index.html"
{
  echo "<!DOCTYPE html>"
  echo "<html>"
  echo "<head>"
  echo "  <meta charset=\"utf-8\">"
  echo "  <title>Auklab Daily Summaries</title>"
  echo "  <style>"
  echo "    body { font-family: Arial, sans-serif; margin: 20px; }"
  echo "    h1 { color: #333; }"
  echo "    a { color: #0066cc; text-decoration: none; }"
  echo "    a:hover { text-decoration: underline; }"
  echo "    .year-item { margin: 10px 0; }"
  echo "  </style>"
  echo "</head>"
  echo "<body>"
  echo "  <h1>Auklab Daily Summaries</h1>"
  echo "  <ul>"
  for year in $(echo "${!year_files[@]}" | tr ' ' '\n' | sort -r); do
    echo "    <li class=\"year-item\"><a href=\"${year}_summaries.html\">📅 $year daily summaries</a></li>"
  done
  echo "  </ul>"
  echo "</body>"
  echo "</html>"
} > "$INDEX_FILE"
echo "  ✅ Generated: index.html"

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

