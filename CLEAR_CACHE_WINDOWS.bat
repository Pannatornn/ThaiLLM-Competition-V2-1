@echo off
cd /d "%~dp0"
if exist runtime\cache rmdir /s /q runtime\cache
echo Cache cleared.
pause
