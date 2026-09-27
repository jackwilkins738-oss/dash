@echo off
rem Double-click to open the prospect control panel in your browser.
cd /d "%~dp0"
python control_panel.py
if errorlevel 1 pause
