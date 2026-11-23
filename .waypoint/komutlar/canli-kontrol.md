# Live check — try it for real before "let me test"

Runs at workflow step 4 when the change is something I open in a browser (a site, a web app), or when it works with another program (reads a browser tab, another app's window or controls, a device, an outside service). Skip it for things with neither (a pure calculation, a script with no outside program).

## Something I open in a browser
1. Use any browser tool you have. Start the project with its launcher as `teslim.md` step 3 says and open it. Run the launcher in the background and stop what it started when you're done.
2. Do the task's "bitti sayılır" steps for real: click, type, submit. Also check that nothing on the page is obviously broken (errors in the console, blank areas, broken layout).

## Something that works with another program
1. Run the real code path against the real program on this machine, not a fake (a test with a fake only proves your guess about the program). Prefer read-only calls; keys or clicks follow `dogrulama.md`.
2. Do it for each program it claims to support, separately (e.g. Chrome, Edge, Brave), runs counted as in `dogrulama.md` step 3 (3 each for the new version) ("Brave 3/3, Edge 0/3"). If a call costs money (a paid API, paid credits), ask me first how many runs to do.
3. Try the states that change what the program gives: the cases from `dogrulama.md` (`http` and `https`, non-ASCII text) plus the program's own variants (another profile or language, an error or warning page). If you need a state you can't reach yourself (a page open, a setting on), ask me for that state instead of assuming it.

## Both
4. Report what you tried and saw, and fix what's wrong, in the closing block of `teslim.md` (Kanıt / Düzelttim). Show a screenshot if you can.
5. Couldn't check (no tool, the page didn't open, the program isn't on this machine): say plainly "Canlı bakamadım" and why, and name what's untried. Never say it works if you didn't see it.
