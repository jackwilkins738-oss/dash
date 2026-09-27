@echo off
rem Double-click to open the prospect control panel in your browser.
rem It fetches the latest version first, and replaces an older panel that is still open.
cd /d "%~dp0"
git pull --ff-only --quiet 2>nul || echo Could not fetch the latest version - starting the one on this computer.
python control_panel.py
if errorlevel 1 pause
