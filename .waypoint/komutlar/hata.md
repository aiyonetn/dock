# When something breaks

Read this when there's an error, a failing test or check, or I say "çalışmıyor" / "yapamadım" / "açamadım". Fix it now (see "Always" in `KURALLAR.md`).

1. Read the project's log file first (named under "Nasıl açılır" in `ILERLEME.md`, e.g. `logs/hata.log`). If the error left no trace there, fix that too.
2. Then read the rest of the local evidence: the full message, other logs, versions.
3. If the cause isn't clear or involves a library, framework, API, tool or OS version, check `raporlar/` first (`rapor.md`), then search the exact error with those versions (official docs, changelogs, issues first) if you can browse. Apply an outside fix only if it matches what you see here.
4. After 3 failed attempts on the same problem, stop, explain plainly and propose a different approach.
   If a commit is blocked by something this task didn't cause (changes you didn't make, a test that already failed before your change), don't leave the work uncommitted and just report it. If the hook's message gives a way that keeps my changes, use it. Otherwise ask me once, with your recommendation (commit those changes separately, or fix the old test first); never weaken the test. If I don't answer, park it in "Sonra yapılacaklar" with "(cevap bekleniyor)" and don't ask again in this session.
   If a commit or test fails because `sh` can't start (`NtCreateDirectoryObject`, `couldn't create signal pipe`, `0xC0000022`, often in a sandbox on Windows), don't ask for wider permission or skip the checks: run `python .waypoint/hooks/kontrol.py --kutu-uyumu`, then commit again. If only the push fails there, the commit is safe: tell me it isn't on GitHub yet. `cannot spawn …waypoint-hooks-py…` means `python` is no longer on PATH: have me reinstall Python with "Add python.exe to PATH".
5. A `fix:` commit must include a test file that catches the bug (a new test or an extended one); the commit check refuses it otherwise. Only if no test can be written, or an existing test already caught it unchanged, add `(no test: <reason>)` to the message.
6. Record a lesson in `DERSLER.md`, in the same commit as the fix, only when it teaches something the fix itself doesn't show: it took more than 2 attempts; the cause was hard to find or surprising; I couldn't follow a step you gave me; or you changed approach because of my feedback. A bug fixed on the first try with a plain cause needs no lesson, even if I reported it. Tell me in one line when you add one.
7. When a kind of lesson recurs, turn it into a one-line rule in "Kurallar" and delete the old entries.
