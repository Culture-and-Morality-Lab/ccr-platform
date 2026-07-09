#!/usr/bin/env bash
# PreToolUse hook: block edits to golden expected outputs and the runtime data dir.
# Golden outputs change only via explicit human action (design doc §16 / CLAUDE.md hard rules).
# Exit 2 = block the tool call and show stderr to Claude.

input="$(cat)"
file_path="$(printf '%s' "$input" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("file_path",""))' 2>/dev/null)"

case "$file_path" in
  *"evals/expected_outputs/"*)
    echo "BLOCKED: $file_path is a golden expected output. Golden files change only via explicit human approval - ask Deva to update it manually or approve a regeneration script." >&2
    exit 2
    ;;
  *"backend/data/"*)
    echo "BLOCKED: $file_path is runtime data (uploads/DB), not source. Never edit runtime data directly." >&2
    exit 2
    ;;
esac
exit 0
