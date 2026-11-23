# Let me test, then close

Read this when a task is ready for me to try (stage 4) and when it's done (stage 5).

## Before I try it
1. If it's something I open (an app, a site, a bot), it needs a double-click launcher (Windows: `baslat.bat`, macOS: `baslat.command`), listed first in "Nasıl açılır" in `ILERLEME.md`; terminal commands are only a fallback. Keep "Nasıl açılır" up to date whenever how to start the project changes.
2. If "Testleri çalıştırma" in `ILERLEME.md` has a separate "Tüm testler" command, run it; fix what fails before going on.
3. For a code change, pick its risk level and review it as `inceleme.md` says. Try it yourself first, started the way I will start it: really run the launcher and see the project come up, not your own command. Check it as `dogrulama.md` says. If it opens in a browser or works with another program, also follow `canli-kontrol.md`.
4. Before telling me anything, run `python .waypoint/hooks/kontrol.py --bitti` and fix what it marks ❌ that you can, then run it again. Tell me its result in plain words, including what was skipped, not tested or not saved; while it ends with "Bitti DEĞİL", don't call the task done. On success, tell me the risk level and review result as `inceleme.md` says, then how I can try it step by step, then the closing block below. On failure, give the detailed findings from `dogrulama.md` and fix what you can before handover. It's not done until I say it works.

## Close
5. Update `ILERLEME.md`. Mark a plan item `[x]` only when each of its "bitti sayılır" checks ran for real on everything it claims. If one couldn't be tried, leave it `[ ]`, add "— kısmen: <what's untried>" and tell me; I decide whether to try it, narrow the claim or accept it. Then commit, give the closing block (its "Sırada:" names the next task), and remind me I can start a fresh session (with the exact command for your tool).

## Closing block
End every finished step (a commit that ends a step) and every handover with this, a few short lines, no more. The handover's "how to try it" and the step-5 reminder stay separate; don't repeat them here.
1. **Kanıt:** what you verified and how (opened or tried X; counts like "3/3"); whether tests ran ("Testler: geçti" / "test yok" / "çalışmadı, çünkü …"; never "geçti" when none ran); which "bitti sayılır" checks passed and which couldn't be tried. Facts only, never "iyi görünüyor". Where useful, run `python .waypoint/hooks/kontrol.py --bitti` instead of remembering. The deeper version is `kanit.md`; don't repeat its steps here.
2. **Düzelttim:** a problem inside the current task that isn't risky (your own bug, a missing piece, something you broke): fix it without asking and say "ayrıca X'i düzelttim". One round only: fix once and check again; if it's still broken, stop and tell me. A problem outside the current task (an old problem elsewhere, a new feature idea): don't fix it, say it in one sentence and park it (Focus in `KURALLAR.md`). A risky one (risk as in `inceleme.md`): ask first.
3. **Uyarı:** one sentence, only when real: a risk you saw, a better way, something likely to go badly. Nothing real, write nothing; no filler.
4. **Sırada:** the next step, in one sentence, without being asked.

If a step needs my answer (a risky fix, a product choice), that is the message's one question, put after the block. Don't build the parked idea or the next step until I agree.
