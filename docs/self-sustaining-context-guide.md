# Self-Sustaining `context.md` Guide

A **self-sustaining `context.md`** is a small file that Claude Code loads into
its context *every* session and then *curates itself* — Claude decides what
belongs in it. It's the lightest possible "compounding memory" for a single
project, and it's the generic cousin of this vault's own `wiki/hot.md`.

## Quick start

From the project you want to give a memory to:

```bash
bash bin/setup-context.sh          # wire the current directory
bash bin/setup-context.sh --check  # show what's wired, change nothing
```

That creates `context.md`, makes `CLAUDE.md` import it, and (optionally) adds a
Stop-hook reminder. Open a new session and Claude will already have read it.

## The mechanism (three honest parts)

A file cannot literally update itself. "Self-sustaining" means **Claude,
following a directive it re-reads every session, rewrites the file.** The setup
wires exactly that loop:

| Part | How | Why this and not something else |
|------|-----|--------------------------------|
| **Load** | `@context.md` imported from `CLAUDE.md` | Imported memory is loaded on *every* session **and survives context compaction** — a `SessionStart` hook's stdout does not. This is the most robust load path. |
| **Instruct** | A directive comment at the top of `context.md` | Because the file is always loaded, its own instructions are always in front of Claude. This is where "what Claude *thinks* belongs" comes from — you hand it the judgment, it exercises it. |
| **Reinforce** | An optional `Stop` hook | Fires when Claude finishes a turn *and* the git working tree changed (via `git status --porcelain`). Emits a one-line nudge to fold anything durable into `context.md`. Guarded so clean turns and non-git dirs stay silent. |

### Why not just a `SessionStart` hook that `cat`s the file?

You can (`hooks.json` in this repo does that for `hot.md`). But hook-injected
text is **lost on compaction**, so long sessions forget it. Importing via
`CLAUDE.md` avoids that. Use a `SessionStart` hook instead of an import only
when you want *dynamic* content (e.g. `git log -3`, current branch) rather than
a stable curated file.

## What Claude puts in it

The seed file ships with a directive and four sections Claude keeps current:

- **What this is** — one-liner on the project.
- **How to work here** — build/test/run commands, conventions, things that bite.
- **Current focus** — what's in progress; cleared when done.
- **Durable facts & decisions** — non-obvious things worth remembering.

The directive tells Claude to keep the whole file tight (aim < 400 words),
**prune** stale lines, and treat it as a **cache, not a journal** (overwrite,
don't append forever). You can edit these sections yourself anytime — it's your
file; Claude just maintains it.

## Guardrails

- **No secrets.** The directive says so; the file is plaintext and usually
  committed. Keep tokens/keys out.
- **It's committed by default** so the memory travels with the repo and the team
  shares it. Add `context.md` to `.gitignore` if you want it personal — but then
  it won't sync across machines/clones.
- **Idempotent setup.** Re-running `setup-context.sh` never clobbers a curated
  `context.md` and never double-adds the import or hook.
- **Turn it off.** Delete the `@context.md` line from `CLAUDE.md` (stops
  loading) and/or remove the `Stop` block from `.claude/settings.json` (stops
  the nudge). `--no-hook` skips the hook at setup time.

## Relationship to this vault's `hot.md`

`wiki/hot.md` is the *same idea at larger scale*: a hot cache maintained across
autoresearch passes, loaded by the `SessionStart`/`PostCompact`/`Stop` hooks in
`hooks/hooks.json`. `context.md` is the stripped-down, project-agnostic version
for any repo that isn't a full wiki vault. Use `hot.md` inside a vault;
use `context.md` everywhere else.
