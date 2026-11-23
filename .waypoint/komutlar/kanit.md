# `kanıt` — how do you know?

Runs when I type `kanıt` / `nasıl bildin` / `neyi denemedin` (or ask "emin misin?", "nereden biliyorsun?").

1. Take your last claim that something is done, fixed, working, passing or covered. Don't start new work or fix anything yet.
2. Don't answer from memory: re-check the facts that can be re-checked now (run `python .waypoint/hooks/kontrol.py --bitti` for a "done" claim; read-only checks and tests only; nothing that changes things).
3. **How you know:** for each part of the claim, the check you really ran and its result (command and output line, a count like "3/3", a screenshot or link). Mark which parts you **checked** and which you only **assume** (from reading code, a test with a fake, "it should").
4. **Scope first:** if the claim says "all" or "every" (all tests, every page, both systems, every endpoint), first list the real parts by searching the project (test folders, packages, routes, systems the plan names), then show which the claim covers. A part not covered is a finding, not a footnote.
5. **What you didn't try:** the cases, inputs, systems or paths you didn't run, and why; say "denemedim" plainly. "(Denenmeyen yok)" only after step 4. How to check well: `dogrulama.md`.
6. If a quick check would turn an assumption into evidence, offer it in one line each; run anything that changes something only after I say "evet".
7. Keep it to about 8 plain lines, most important gap first.
