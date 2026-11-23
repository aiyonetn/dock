# Risk level and independent review

Read this when a code change is finished, before you hand it over (`teslim.md`) or call it done. Tests and real use (`dogrulama.md`) still run; a review never replaces them.

## 1. Pick the risk level

Judge by what the change can break, not by its size or the tool used. Unsure between two levels: take the higher one.

- **Low / medium** (no review): docs, comments, text, layout, or ordinary code and features I use. Tests and real use (`dogrulama.md`) only.
- **High:** it deletes, moves or migrates data; logins, permissions or security; payments; how the project installs, updates or starts; Git hooks or CI; removing or weakening a test; anything outside the project (sending, publishing, a shared service). Review, the old/new comparison (`dogrulama.md` step 1), and before the step that can't be undone tell me in 2–3 plain lines how it would be undone and what can't be. With no test command in the project, add a test for the risky part first (`testler.md`), or tell me why it can't be tested and how you checked it instead. Anything irreversible waits for my OK (`KURALLAR.md` "Always").

Name the level and why in one line of the handover ("Risk: yüksek — eski kayıtları siliyor"). A high-risk change isn't done until its review and checks are finished and I've said it works.

## 2. High risk: off the main branch

Build it on `deney/<name>`, not on the main branch; its commits are still pushed as a backup, but the main branch doesn't change. Merge it into the main branch only when all of these hold: the review is done, the tests passed (or "test yok" and how you checked instead), I've had the undo note, and I said yes to one plain question ("Hazır ve denendi; ana sürüme alayım mı?"). Merge with a normal merge (no force push, no history rewrite), then push the main branch yourself (`git push`): the hook pushes commits, not merges. If I said no or not yet, leave it as it is and park it in "Sonra yapılacaklar".

## 3. Independent review (high only)

1. **Who reviews:** not the one who wrote it. If your tool has sub-agents, start a fresh one with no memory of the work and give it: the task's goal and "bitti sayılır", the diff (`git diff` of the task's commits), the files it touches, the test results, and the "Kurallar" in `DERSLER.md`. Without sub-agents, do a separate pass yourself, reading only the diff and those inputs, and say in the handover that it wasn't independent ("inceleme aynı oturumda yapıldı").
2. **What to ask for:** only concrete problems someone can reproduce: file and line, how to trigger it, what goes wrong, severity (kritik / orta / düşük). Have it check four things in the change, opening other files only to see its effect: does it do what the goal and "bitti sayılır" ask; does the logic, followed step by step, reach a wrong result or skip a step; what happens on edge cases (empty data, bad input, a lost connection, stopping halfway); does it break anything it didn't touch, lose data or open a security hole. No style or taste comments; "no problems found" is a valid answer.
3. **Check each finding** before acting: reproduce it or point at the code that causes it. One you can't confirm is "doğrulanmadı", not a bug. Close each as `düzeltildi`, `yanlış alarm`, `bilerek böyle` (say why) or `çözülemedi`. After a fix, rerun the tests.
4. **Rounds:** after a fix, review again only what changed since the last round. After 3 rounds with findings still coming, stop and tell me plainly (`hata.md` step 4).
5. **Report** in one handover line ("İnceleme: 2 bulgu, 1 düzeltildi, 1 yanlış alarm"). A `kritik` finding left `çözülemedi` keeps the task open until I decide. No new file for it; a false alarm that teaches something goes to `DERSLER.md`.
