@echo off
REM Roda o projeto Django localmente no Windows (sem Docker)
cd /d "%~dp0\.."

echo === Ambiente local ===
if not exist "venv" (
  echo Criando venv...
  python -m venv venv
)
call venv\Scripts\activate.bat

echo Instalando dependencias...
pip install -q -r requirements.txt

echo Aplicando migracoes...
python manage.py migrate --noinput

echo.
echo Servidor em: http://127.0.0.1:8000/
echo   Teste: http://127.0.0.1:8000/teste/
echo   Login: http://127.0.0.1:8000/login/  (teste / 123456)
echo.
python manage.py runserver 0.0.0.0:8000
pause
