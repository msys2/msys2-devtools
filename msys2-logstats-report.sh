#!/bin/bash
# journalctl CONTAINER_NAME=msys2-repo-traefik-1 --since "7 days ago" --output=cat > logs.txt

set -e

LOGS="$1"
OUTPUT=logs-report.md

date -I > "$OUTPUT"

echo '<details><summary>CI vs non-CI requests</summary>' >> "$OUTPUT"
echo '' >> "$OUTPUT"
echo '```' >> "$OUTPUT"
./msys2-logstats --show-summary "$LOGS" >> "$OUTPUT"
echo '```' >> "$OUTPUT"
echo '' >> "$OUTPUT"
echo '</details>' >> "$OUTPUT"

echo '<details><summary>All requests</summary>' >> "$OUTPUT"
echo '' >> "$OUTPUT"
echo '```' >> "$OUTPUT"
./msys2-logstats "$LOGS" >> "$OUTPUT"
echo '```' >> "$OUTPUT"
echo '' >> "$OUTPUT"
echo '</details>' >> "$OUTPUT"

echo '<details><summary>Without CI/cloud requests</summary>' >> "$OUTPUT"
echo '' >> "$OUTPUT"
echo '```' >> "$OUTPUT"
./msys2-logstats --skip-ci "$LOGS" >> "$OUTPUT"
echo '```' >> "$OUTPUT"
echo '' >> "$OUTPUT"
echo '</details>' >> "$OUTPUT"
