@echo off
REM add_fitdays.bat - Sube nuevas mediciones Fitdays a la nube
REM Uso: copia el/los .csv nuevos a la carpeta Fitdays\ y ejecuta este bat.
REM GitHub Actions consolida, actualiza la BD y Streamlit Cloud redeploya solo.

cd /d C:\vital-form-streamlit

echo.
echo Subiendo mediciones Fitdays nuevas a GitHub...
echo.

git pull origin main --rebase
git add Fitdays\*.csv
git diff --cached --quiet && echo (no hay CSVs nuevos que subir) && goto :end
git commit -m "data: nuevas mediciones Fitdays"
git push origin main

echo.
echo [LISTO] CSVs subidos. GitHub Actions integrara los datos a la BD
echo         (tarda ~1-2 min) y Streamlit Cloud redeploya automaticamente.
echo Puedes ver el progreso en:
echo   https://github.com/dhdezr14/vital-form/actions

:end
echo.
pause
