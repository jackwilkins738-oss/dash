@echo off
rem Double-click to open the US prospect panel: its own folder (outreach-us), settings, inboxes and lists.
rem The UK panel (control_panel.bat) keeps running beside it on its own port.
cd /d "%~dp0"
git pull --ff-only --quiet 2>nul || echo Could not fetch the latest version - starting the one on this computer.
if not exist "..\outreach-us" mkdir "..\outreach-us"
set OUTREACH_DIR=outreach-us
python control_panel.py --port 8766
if errorlevel 1 pause
