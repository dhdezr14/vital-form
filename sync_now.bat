@echo off
cd /d C:\vital-form-streamlit
call venv\Scripts\activate
echo.
echo Sincronizando ultimos 14 dias...
python sync_now.py --days 14
echo.
echo Listo. Presiona cualquier tecla para cerrar.
pause > nul
