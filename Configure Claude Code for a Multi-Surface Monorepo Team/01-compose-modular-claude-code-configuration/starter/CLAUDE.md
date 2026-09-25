# E-Commerce Platform — Shared Claude Code Conventions

This file is the **project-level** entry point for the e-commerce monorepo. Every teammate's Claude session loads it automatically.

## Scope: what belongs here vs. elsewhere

| Scope | Path | Purpose |
| :--- | :--- | :--- |
| **Project-level** | `./CLAUDE.md`, `.claude/standards/`, `.claude/rules/` | Conventions for entire repo. Lived in git. Shared with the whole team. |
| **User-level** | `~/.claude/CLAUDE.md`, `~/.claude/commands/`, `~/.claude/skills/` | Personal preferences. **NOT shared with teammates via version control** — they stay on your machine and never reach teammates. |
| **Directory-level** | `path/CLAUDE.md` inside a subfolder | Conventions narrower than the whole repo. We prefer `.claude/rules/` with `path` instead, so cross-cutting conventions work cleanly. |

If something would only matter to you, like your preferred commit-message style or a personal editor keybinding, put it under `~/.claude/`. Anything the whole team should agree on goes here in `./CLAUDE.md` or under `.claude/standards/`.

## Shared standards (modular via @-imports)

The actual conventions live in focused files so this entry point stays scannable:

@.claude/standards/frontend.md

@.claude/standards/api.md

@.claude/standards/database.md

@.claude/standards/testing.md

Path-scoped rules in `.claude/rules/` layer on top of these standards and activate only when Claude is editing matching files.

## Repository layout

- `src/components/` — React components and frontend UI.
- `src/api/` — API handlers.
- `src/` — Shared frontend application code.
- `.claude/standards/` — Shared project-wide engineering standards.
- `.claude/rules/` — Path-scoped Claude Code rules.
- `tests/` — Automated tests.

## Troubleshooting

If Claude Code hierarchy or rule-loading behavior looks incorrect, run `/memory` to inspect the loaded project instructions.