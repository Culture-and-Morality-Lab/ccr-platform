#!/usr/bin/env bash
# PostToolUse hook: fast syntax check on any edited Python file.
# Catches broken edits immediately instead of at the next test run.

input="$(cat)"
file_path="$(printf '%s' "$input" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("file_path",""))' 2>/dev/null)"

if [[ "$file_path" == *.py && -f "$file_path" ]]; then
  if ! python3 -m py_compile "$file_path" 2>/tmp/pyc_err; then
    echo "SYNTAX ERROR in $file_path:" >&2
    cat /tmp/pyc_err >&2
    exit 2
  fi
fi

# Project style rule: no em dashes in any source/text file (CLAUDE.md hard rules).
case "$file_path" in
  *.py|*.js|*.jsx|*.css|*.md|*.yaml|*.yml|*.sh|*.html)
    if [[ -f "$file_path" ]] && grep -q $'\xe2\x80\x94' "$file_path"; then
      echo "EM DASH found in $file_path. Project rule: no em dashes - use a hyphen or restructure the sentence." >&2
      exit 2
    fi
    ;;
esac
exit 0
