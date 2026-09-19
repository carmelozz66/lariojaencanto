@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -c "import jinja2, markdown, yaml, PIL" 2>nul || pip install jinja2 markdown pyyaml pillow
python admin.py
pause
