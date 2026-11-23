# Tests

I can't tell when a change breaks an old feature, so tests do it for me. Read this when you add or change tests or set the test command.

1. Put the test command as one line in backticks under "Testleri çalıştırma" in `ILERLEME.md`. The pre-commit hook runs it before every commit, so it must finish on its own (no watch mode) and quickly (aim for under a minute). When you set or change it, run it once yourself and see it finish, and see it fail once on a deliberately broken check, so a wrong path or a command that tests nothing isn't trusted.
2. If the full suite is slower, put a fast subset there and the full command on the next line as ``Tüm testler: `...` ``; run the full suite at the end of each task and in `bitir`.
3. Commits wait at most 5 minutes for the tests. If the command really needs longer, add a line `Süre: 10 dk` (at most 30) under it; the hook prints the limit before the tests start. Wait for the commit in one go, up to that limit, instead of checking on it again and again.
4. If a folder holds things the test command never exercises and no tested code uses (a design draft, a static site), add `Testsiz: docs/taslak/, site/` under it; a commit that changes only those folders and notes skips the tests. Never list a folder the tests cover or code depends on.
