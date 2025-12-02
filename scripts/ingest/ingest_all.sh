#!/usr/bin/env bash
set -euo pipefail

LIST_FILE="${1:-examples/transcripts/sources.txt}"
OUT="out/chunks.jsonl"

echo "==> Using list: $LIST_FILE"
[ -f "$LIST_FILE" ] || { echo "Missing $LIST_FILE"; exit 1; }

ingest_url () {
  local url="$1"
  echo ">> URL: $url"
  if python raglite.py ingest-youtube --url "$url" --out "$OUT"; then
    echo "   ✓ transcript ingested"
  else
    echo "   ⚠ no transcript; fetching auto-captions"
    local vid
    vid="$(yt-dlp --print id --skip-download "$url" | head -n 1 || true)"
    yt-dlp --skip-download --write-auto-sub --sub-lang en --sub-format vtt -o "%(id)s.%(ext)s" "$url" || true
    local f=""
    if [[ -n "$vid" ]]; then
      f="$(ls "${vid}".en*.vtt 2>/dev/null | head -n 1 || true)"
    fi
    if [[ -z "$f" ]]; then
      f="$(ls *.en*.vtt 2>/dev/null | tail -n 1 || true)"
    fi
    if [[ -n "$f" ]]; then
      python raglite.py ingest-transcript --path "$f" --out "$OUT"
      echo "   ✓ auto-captions ingested ($f)"
    else
      echo "   ✗ failed to locate .vtt for $url"
    fi
  fi
}

while IFS= read -r item || [[ -n "${item:-}" ]]; do
  # strip trailing spaces; skip empty or commented lines
  item="${item%%[[:space:]]*}"
  [[ -z "$item" || "${item:0:1}" == "#" ]] && continue

  if [[ "$item" =~ ^https?:// ]]; then
    ingest_url "$item"
  else
    if [[ -f "$item" ]]; then
      case "$item" in
        *.vtt|*.srt|*.txt)
          echo ">> transcript: $item"
          python raglite.py ingest-transcript --path "$item" --out "$OUT"
          ;;
        *.pdf|*.docx|*.md|*.markdown|*.txt)
          echo ">> document:  $item"
          python raglite.py ingest-docs --path "$item" --out "$OUT"
          ;;
        *)https://mini-rag-production.up.railway.app/app/#ingest
          echo "?? unsupported file: $item"
          ;;
      esac
    else
      echo "!! missing file: $item"
    fi
  fi
done < "$LIST_FILE"

wc -l "$OUT"
echo "==> Done."
