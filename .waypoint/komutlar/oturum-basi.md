# Session start

Do this at the start of every session, before anything else.

1. Run `python .waypoint/hooks/kontrol.py --ozet` and read its output instead of opening `ILERLEME.md` and `DERSLER.md` whole. Open a file, or better search one section of it, only when you need a detail the summary cut or left out. If the command fails, read `ILERLEME.md` and "Kurallar" in `DERSLER.md` instead.
2. If git doesn't match `ILERLEME.md` (a session cut off midway, work done in another tool), tell me in one line.
3. No git repo yet: run `git init`, then `git config core.hooksPath .waypoint/hooks`, and tell me. Keep `.obsidian/` in `.gitignore`.
4. Blank `ILERLEME.md`: stage 0 if the folder has code (`mevcut-proje.md`), otherwise stage 1 (`sorgula.md`).
5. Briefly tell me what we did last, where we are, and the next step. If the summary shows an unfinished `Aktif sorgulama` draft, use its confirmed answers and open questions to resume `komutlar/sorgula.md` from the next unanswered question; don't restart the interview or treat its draft as an approved goal.
6. If the summary names a newer Waypoint version, add one line saying so and ask whether to update (`guncelleme.md`).
