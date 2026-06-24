@echo off
cd /d C:\vital-form-streamlit

echo Preparando deploy a Streamlit Cloud...
echo.

REM Copiar triathlon_final.db como triathlon.db (DB limpia con todos los datos)
if exist data\triathlon_final.db (
    copy /Y data\triathlon_final.db data\triathlon.db
    echo [OK] data\triathlon.db actualizada desde triathlon_final.db
) else (
    echo [WARN] triathlon_final.db no encontrado, usando triathlon.db existente
)

echo.
echo Subiendo al repositorio de GitHub...
call venv\Scripts\activate
git pull origin main --rebase
git add data\triathlon.db App.py sync_now.py .github\workflows\sync.yml
git commit -m "deploy: DB consolidada + sync por deporte + zonas FC dinamicas" 2>nul || echo (nada nuevo que commitear)
git push origin main

echo.
echo [LISTO] Cambios subidos a GitHub.
echo.
echo Pasos siguientes en Streamlit Cloud:
echo  1. Ve a https://share.streamlit.io
echo  2. Crea una nueva app apuntando a: dhdezr14/vital-form / App.py
echo  3. En Settings > Secrets agrega:
echo       INTERVALS_API_KEY = tu_api_key
echo       INTERVALS_ATHLETE_ID = i347382
echo.
pause
