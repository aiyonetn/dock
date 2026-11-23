# Research and reports

Read this before you research something and when you write a report.

1. Before researching, pick the related reports in `.waypoint/raporlar/` by file name and read only their summaries; open a full report only if needed. Reuse what's there; research only what's missing.
2. Write a report only for findings worth reusing later: comparing options, how a library, tool or outside program really behaves, an investigation that spans several tasks. A fix, a closed issue or a check result isn't a report: its record is the commit message, the issue comment and the task's "Günlük" line. Don't make a separate commit for a report; commit it with the work it belongs to.
3. A report goes in `.waypoint/raporlar/` as `YYYY-AA-GG-<konu>.md` (the commit check enforces the name), with a one-line "Günlük" entry in `ILERLEME.md` naming it.
4. Start each report with five short lines: `Bulgu:`, `Kanıt:` (with the versions it applies to), `Alternatif:`, `Belirsiz:`, `Kaynaklar:`.
5. A sub-agent that researched something writes a report and hands you its summary and path, not the whole text.
