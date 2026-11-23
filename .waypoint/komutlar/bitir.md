# `bitir` / `bugünlük bu kadar`

Do these in order:

1. If "Testleri çalıştırma" has a separate "Tüm testler" command, run it, unless it already passed after the last code change (e.g. at handover); if it fails, tell me plainly what broke.
2. Record unrecorded lessons in `DERSLER.md`.
3. Update `ILERLEME.md` If commits warned that a section is long, move the old items now (`ILERLEME_ARSIV.md`, old lessons to `DERS_ARSIV.md`).
4. Run `python .waypoint/hooks/kontrol.py --temizlik` (it only lists, deletes nothing). If it lists leftover copies, worktrees or `deney/` / `is/` branches, ask me once in one plain message which to delete, with your recommendation (merged branches and copies of finished work: delete). Delete only what I approve: copy folders by deleting them, worktrees with `git worktree remove` (never `--force`), merged branches with `git branch -d`. Before deleting an unmerged branch, tell me what's in it that isn't on the main branch. Leave copies another tool still uses (e.g. under `.codex/worktrees` for an unfinished task).
5. Commit.
6. Tell me in plain words what we did today and which lessons were recorded, if any.
