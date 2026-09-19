@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== PUBLICAR LA WEB =====
echo.

where git >nul 2>nul
if errorlevel 1 (
  echo No se encuentra Git. Instala Git para Windows desde https://git-scm.com/download/win
  pause & exit /b 1
)

echo [1/3] Regenerando la web...
python build.py
if errorlevel 1 ( echo ERROR al generar la web. & pause & exit /b 1 )

if not exist ".git" (
  git init -b main >nul
  git remote add origin https://github.com/carmelozz66/lariojaencanto.git
)
for /f "delims=" %%i in ('git config user.name') do set HAYNOMBRE=%%i
if not defined HAYNOMBRE git config user.name "carmelozz66"
for /f "delims=" %%i in ('git config user.email') do set HAYCORREO=%%i
if not defined HAYCORREO git config user.email "carmelozz66@users.noreply.github.com"

echo.
echo [2/3] Guardando los cambios...
git add -A
git commit -m "Actualizacion %date% %time%" >nul 2>nul
if errorlevel 1 echo (No hay cambios nuevos que guardar; se vuelve a enviar por si acaso.)

echo.
echo [3/3] Enviando a GitHub (la primera vez se abrira una ventana para iniciar sesion)...
git push -u origin main
if errorlevel 1 (
  echo.
  echo ERROR al enviar. Revisa la conexion o el inicio de sesion en GitHub.
  pause & exit /b 1
)

echo.
echo ===== LISTO =====
echo En 1-2 minutos estara publicada en:
echo https://carmelozz66.github.io/lariojaencanto/
echo.
pause
