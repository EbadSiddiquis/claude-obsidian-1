#!/usr/bin/env bash
# setup-context.sh — give any Claude Code project a self-sustaining context.md.
#
# A "self-sustaining context.md" is a small file that is (a) ALWAYS loaded into
# Claude's context every session and (b) curated by Claude itself over time —
# Claude decides what belongs in it. This script wires the minimal, robust loop:
#
#   LOAD    `@context.md` imported from CLAUDE.md  -> always in context, and it
#           survives context compaction (only CLAUDE.md-imported text does).
#   CURATE  a directive inside context.md tells Claude to maintain it; an
#           optional Stop hook reinforces it when the working tree changed.
#
# Honest boundary: a file cannot update itself. "Self-sustaining" means Claude,
# following a standing directive it re-reads every session, rewrites the file.
# The wiring guarantees the file is LOADED and Claude is REMINDED; the judgment
# of what to keep is Claude's — that is the point.
#
# Usage:
#   bash bin/setup-context.sh                 # wire the current directory
#   bash bin/setup-context.sh --dir PATH      # wire another project
#   bash bin/setup-context.sh --no-hook       # skip the Stop-hook reinforcement
#   bash bin/setup-context.sh --check         # report state, write nothing
#
# Exit codes: 0 success · 2 usage error · 3 missing dependency

set -euo pipefail

TARGET="$PWD"
ADD_HOOK=1
CHECK_ONLY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --dir)      TARGET="${2:?--dir needs a path}"; shift 2 ;;
    --no-hook)  ADD_HOOK=0; shift ;;
    --check)    CHECK_ONLY=1; shift ;;
    -h|--help)  sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "setup-context: unknown arg '$1'" >&2; exit 2 ;;
  esac
done

[ -d "$TARGET" ] || { echo "setup-context: not a directory: $TARGET" >&2; exit 2; }
TARGET="$(cd "$TARGET" && pwd)"

CONTEXT="$TARGET/context.md"
CLAUDEMD="$TARGET/CLAUDE.md"
SETTINGS_DIR="$TARGET/.claude"
SETTINGS="$SETTINGS_DIR/settings.json"

have_import()  { [ -f "$CLAUDEMD" ] && grep -qE '(^|[^`])@context\.md' "$CLAUDEMD"; }
have_context() { [ -f "$CONTEXT" ]; }
have_hook()    { [ -f "$SETTINGS" ] && grep -q 'CONTEXT_UPDATE' "$SETTINGS"; }

if [ "$CHECK_ONLY" = "1" ]; then
  echo "self-sustaining context.md — status for: $TARGET"
  echo "  context.md present ......... $(have_context && echo yes || echo NO)"
  echo "  CLAUDE.md imports it ....... $(have_import  && echo yes || echo NO)"
  echo "  Stop-hook reinforcement .... $(have_hook    && echo yes || echo 'no')"
  exit 0
fi

# ── 1. seed context.md (only if absent — never clobber a curated file) ────────
if have_context; then
  echo "· context.md already exists — left untouched"
else
  cat > "$CONTEXT" <<'SEED'
<!-- This file is loaded into Claude Code's context every session (imported by
     CLAUDE.md). It is Claude's durable working memory for this project.

     DIRECTIVE TO CLAUDE — maintain this file:
     - You have already read this by the time you act. Treat it as what a
       competent teammate would want to know before touching this project.
     - When you learn something that will STILL MATTER next session — an
       architecture decision, where a thing lives, a non-obvious gotcha, a
       convention, a user preference, the current focus — record it here.
     - Prune what is stale or wrong. Keep the whole file tight (aim < 400
       words). It is a cache, not a journal: overwrite, don't append forever.
     - YOU decide what belongs here. That judgment is the point of this file.
     - Do not put secrets here. Do not narrate edits to the user unless asked. -->

# Project Context

## What this is
<!-- one or two lines: what this project/repo is and who it's for -->

## How to work here
<!-- build/test/run commands, conventions, things that bite -->

## Current focus
<!-- what's actively in progress; clear it when done -->

## Durable facts & decisions
<!-- non-obvious things worth remembering across sessions -->
SEED
  echo "✓ created $CONTEXT"
fi

# ── 2. import it from CLAUDE.md so it is always loaded (survives compaction) ──
if have_import; then
  echo "· CLAUDE.md already imports @context.md"
else
  {
    printf '\n<!-- self-sustaining context: always-loaded working memory -->\n'
    printf '@context.md\n'
  } >> "$CLAUDEMD"
  [ -s "$CLAUDEMD" ] && echo "✓ added '@context.md' import to $CLAUDEMD" \
                     || echo "✓ created $CLAUDEMD importing @context.md"
fi

# ── 3. optional Stop-hook reinforcement (nudge only when the tree changed) ────
if [ "$ADD_HOOK" = "0" ]; then
  echo "· skipped Stop-hook reinforcement (--no-hook)"
elif have_hook; then
  echo "· Stop-hook reinforcement already present"
else
  command -v python3 >/dev/null 2>&1 || { echo "setup-context: python3 required to merge settings.json" >&2; exit 3; }
  mkdir -p "$SETTINGS_DIR"
  [ -f "$SETTINGS" ] || echo '{}' > "$SETTINGS"
  CMD='cd "$CLAUDE_PROJECT_DIR" 2>/dev/null || exit 0; [ -d .git ] || exit 0; [ -z "$(git status --porcelain 2>/dev/null)" ] && exit 0; echo "CONTEXT_UPDATE: files changed this session. If you learned something durable a future session would need (decisions, where things live, gotchas, current focus, preferences), update context.md now — keep it tight (<400 words), prune stale lines, overwrite not append. If nothing durable, do nothing."'
  SETTINGS="$SETTINGS" CMD="$CMD" python3 - <<'PY'
import json, os, sys
path, cmd = os.environ["SETTINGS"], os.environ["CMD"]
try:
    data = json.load(open(path))
    if not isinstance(data, dict): raise ValueError
except Exception:
    print(f"setup-context: {path} is not valid JSON — fix or remove it first", file=sys.stderr); sys.exit(2)
hooks = data.setdefault("hooks", {})
stop  = hooks.setdefault("Stop", [])
stop.append({"matcher": "", "hooks": [{"type": "command", "command": cmd}]})
json.dump(data, open(path, "w"), indent=2)
open(path, "a").write("\n")
PY
  echo "✓ added Stop-hook reinforcement to $SETTINGS"
fi

echo
echo "Done. context.md will load every session and Claude will curate it as it works."
echo "Inspect anytime with:  bash bin/setup-context.sh --check --dir \"$TARGET\""
