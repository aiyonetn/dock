# Focus & Workflow Rules

Autonomous, evidence-based development: work on your own, check your own work, report what you verified and what you didn't.
I don't read code and get distracted easily: keep it plain and short.

The rules below always apply. When a situation below names a file in `.waypoint/komutlar/`, follow it (when to open it: see "Project files").

## Language & communication

- Talk to me in plain Turkish (in plain English if I write in English); explain any unavoidable technical term briefly in parentheses.
- Don't show me code. Tell me what changed and what it gives me.
- Be brief: at most one question per message, with your recommendation. If I skip a question, park it in "Sonra yapılacaklar" with "(cevap bekleniyor)"; remove it once I answer.
- If I have to do something myself, give me exact step-by-step instructions.
- `ILERLEME.md` and `DERSLER.md` are in Turkish; `HARITA.md` may be English; commit messages are English.
- On Windows never write files with PowerShell `>` / `Set-Content`: it breaks Turkish letters (the commit check catches it only afterward).

## Project files

In `.waypoint/`, the only place for project knowledge (other memory systems may hold only personal or cross-project facts about me). Fill the forms and keep their sections; if one (or `hooks/`) is missing, tell me to reinstall Waypoint.
- `ILERLEME.md`: goal, how to run, decisions, plan, log. Update it once when a task is done (and in `bitir`), not after every step; one short "Günlük" line per day, edited rather than added to (the commit check says when lines are too long or the file is too big).
- `DERSLER.md`: lessons and my project rules. When I state a project preference ("bu projede hep böyle olsun"), add it as a one-line rule to "Kurallar".
- `HARITA.md`: a short table of contents, important files and entry points (format in its top comment). Search it for what you need instead of reading it whole; if it disagrees with the code, trust the code and fix the map.
- `raporlar/`: research worth reusing later, not a record of each fix.
- Read this file and each `komutlar/` file once per session, the first time it's needed, and follow it from memory afterwards; for `ILERLEME.md` and `DERSLER.md` the session-start summary (`oturum-basi.md`) replaces reading them whole. Open one again only if it changed since, or your context was summarized and you need it now; a new task or message isn't a reason. For one detail, search the file instead of reading it whole.

## Always

- **Bugs:** a bug I report isn't a new topic: fix it now. Fix small, safe bugs (yours or ones you find) without asking, then tell me in one line; ask first only if the fix is risky, irreversible or changes how the product works.
- **Decisions:** "Kararlar" (`ILERLEME.md` or `ILERLEME_ARSIV.md`) is settled: don't re-research or reverse it without a concrete new reason. For a product choice, give me 2–3 one-line options and say which you'd pick. "Kararlar" gets only what I approved and your technical choices (what, why, docs link), one line each.
- **Tests:** never change or delete a test just to make it pass (a new expected value counts); if the feature really changed, ask me before touching it. A test that passed before your change and fails after it usually points to another bug: look for it first. If something breaks and you can't fix it, tell me plainly what broke.
- **Hooks:** never bypass them (`--no-verify`); if they block, fix what their message says (a cause your task didn't make: `komutlar/hata.md`).
- **Commits:** Commit every working step without asking, then tell me in one plain line what was saved, and end every finished step with the short closing block from `komutlar/teslim.md` (evidence, fixes, a warning only if real, "Sırada:"). For the last test run before a commit, stage everything first and run `python .waypoint/hooks/kontrol.py --dogrula` instead of the test command, then commit right away: the commit won't run the tests again. With a GitHub remote, the post-commit hook pushes (standing permission); if the push failed, tell me. Ask before force-pushing, rewriting history, deleting branches or anything irreversible; revert a broken step only with my OK.
- **Branches:** work on the main branch. High-risk work (`komutlar/inceleme.md`) and risky experiments go on `deney/<name>` (still backed up, main untouched), parallel jobs each on `is/<name>`; tell me, and merge or delete them only with my OK.

## When…

- **…a session starts:** `komutlar/oturum-basi.md`.
- **…something breaks** (an error, a failing test or check, or I say "çalışmıyor" / "yapamadım" / "açamadım"): `komutlar/hata.md`.
- **…you're about to change code:** `komutlar/kod-degisikligi.md`.
- **…you add or change tests, or set the test command:** `komutlar/testler.md`.
- **…you research something** (not for an ordinary fix or closed issue): `komutlar/rapor.md`.
- **…a code change is finished, before handover:** `komutlar/inceleme.md` (risk level, independent review).
- **…a task is ready for me to try, or done:** `komutlar/teslim.md`.
- **…you check or review a change, or report a problem you found:** `komutlar/dogrulama.md`.

## Workflow

0. **Existing project** (code exists, forms blank): `komutlar/mevcut-proje.md`.
1. **Idea → Goal:** `komutlar/sorgula.md` (what it does, who uses it, what must work to call it done). Confirm with me, then write the goal.
2. **Plan:** if you lack technical knowledge for a good plan, first `komutlar/arastirma.md`. Then split the goal into tasks that each end with something I can try ("bitti sayılır: …"), and decide the code folders (grouped by job, at most two levels; the root keeps only entry points and config) and list them in `HARITA.md`. Don't start without my approval.
3. **Build:** one task at a time. Before a big new feature: `komutlar/sorgula.md`, then `komutlar/arastirma.md`. Stop and ask only for a new product decision, work clearly beyond the plan, or a risky, irreversible or shared-system step.
4. **Let me test** and **5. Close:** `komutlar/teslim.md`.

## Focus

- If I bring up something new outside the current task ("bir de şunu ekleyelim"), don't start it; ask whether to park it or switch to it (a bug isn't new: see Always).
- Each "Sonra yapılacaklar" item stays one line; a longer idea becomes `<name> → ayrıntı: FIKIRLER.md › <name>` with details under `## <name>` in `.waypoint/FIKIRLER.md` (the commit check keeps the two in sync).

## Commands

Each also works in English (in brackets). A one-word short form (`sos`, `next`…) counts as a command only when it is my whole message; `anladın mı`, `anm`, `am`, `??` and `???` also count at the end of a message, after a space (`… ekle ??`, but not `neden bozuldu??`).

- **`neredeyiz` / `kayboldum` / `özet` / `ne yapıyorduk` [`where are we` / `where`]:** stop and summarize the goal, the plan (done and current task), what's happening now, the next step, and questions waiting for my answer.
- **`sos` / `sadece soru` / `???` [`just a question` / `ask`]:** only answer; don't change files, run commands that change anything, or commit.
- **`anladın mı` / `anm` / `am` / `??` [`got it?`]:** don't act yet. In 3–4 plain lines say what you understood (in your own words), what you'll change, what you won't touch and how I'll try it; if something is unclear, ask one question. Change nothing until I say "evet"; if I correct you, say it again.
- **`nep` / `ne yaptık` [`what did we do` / `recap`]:** in 1–3 plain sentences, your last action and what it gives me.
- **`snv` / `sırada ne var` [`what's next` / `next`]:** only the next step, in one sentence.
- **`parket <fikir>` / `sonraya ekle <fikir>` [`park <idea>`]:** add it to "Sonra yapılacaklar" (see Focus), confirm in one line, continue.
- **`liste` [`list`]:** done tasks, then remaining tasks and "Sonra yapılacaklar", as short lists.
- **`nasıl açarım` [`how do I run it` / `run`]:** show the "Nasıl açılır" steps as they are.
- **`sorgula` [`clarify`]:** `komutlar/sorgula.md` for the current idea or feature.
- **`eksik` / `ne eksik` [`what's missing`]:** `komutlar/eksik.md`.
- **`kanıt` / `nasıl bildin` / `neyi denemedin` [`proof` / `how do you know`]:** `komutlar/kanit.md`.
- **`bitir` / `bugünlük bu kadar` [`finish`]:** `komutlar/bitir.md`.
- **`Waypoint'i güncelle` [`update Waypoint`], or "Waypoint güncellemesi var" appears:** `komutlar/guncelleme.md`. Never update without my OK.
