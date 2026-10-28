@echo off
rem GEH 2026 - scheduled: 31 Oct 2026 01:00 JST (= 30 Oct 12:00 PM ET = 16:00 UTC)
rem Tags the last commit on origin/main made BEFORE the sprint start, so the tag is
rem correct even if this task runs late (PC asleep, logged out). Does not touch the
rem working tree, so in-progress sprint work is never affected.

setlocal
set LOG=C:\Users\Garrett\Projects\geh-brief03-pawacast\sprint-start-tag-run.log

echo === %date% %time% === > "%LOG%"

"C:\Program Files\Git\bin\bash.exe" -lc "cd /c/Users/Garrett/Projects/geh-brief03-pawacast && git fetch origin main --quiet && SHA=$(git rev-list -n1 --first-parent --before=2026-10-30T16:00:00Z origin/main) && test -n \"$SHA\" && git -c user.name=PollPower -c user.email=dev@pollpower.energy tag -a geh2026-sprint-start -m 'GEH 2026 sprint start, 30 Oct 2026 12:00 PM ET (last commit before 16:00 UTC)' $SHA && git push origin refs/tags/geh2026-sprint-start && git log -1 --format='geh2026-sprint-start -> %%H  %%cI  %%s' $SHA > sprint-start-tag.txt && cat sprint-start-tag.txt" >> "%LOG%" 2>&1

echo === done %date% %time% === >> "%LOG%"
endlocal
