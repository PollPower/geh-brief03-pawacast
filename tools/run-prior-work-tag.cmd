@echo off
rem GEH 2026 — scheduled: 29 Oct 2026 00:05 JST
rem Runs tag_prior_work.sh via git-bash with the PollPower gh login,
rem then copies the manifest into this repo and pushes it.

setlocal
set LOG=C:\Users\Garrett\Projects\geh-brief03-pawacast\prior-work-tags-run.log
set SCRIPT=C:\Users\Garrett\.openclaw\workspace\scratch\tag_prior_work.sh
set MANIFEST=C:\Users\Garrett\.openclaw\workspace\scratch\prior-work-tags.txt
set DEST=C:\Users\Garrett\Projects\geh-brief03-pawacast\prior-work-tags.txt

echo === %date% %time% === > "%LOG%"
"C:\Program Files\Git\bin\bash.exe" -lc "cd /c/Users/Garrett/.openclaw/workspace/scratch && bash tag_prior_work.sh" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo TAG SCRIPT FAILED, exit=%errorlevel% >> "%LOG%"
  exit /b %errorlevel%
)

copy /y "%MANIFEST%" "%DEST%" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo COPY FAILED, exit=%errorlevel% >> "%LOG%"
  exit /b %errorlevel%
)

"C:\Program Files\Git\bin\bash.exe" -lc "cd /c/Users/Garrett/Projects/geh-brief03-pawacast && git add prior-work-tags.txt && git -c user.name=PollPower -c user.email=dev@pollpower.energy commit -m 'Prior-work tag manifest' && git push origin main" >> "%LOG%" 2>&1

echo === done %date% %time% === >> "%LOG%"
endlocal
