@echo off
REM build_exe.bat
REM Gera o executavel da identificacao facial (CampusPark_Reconhecimento.exe).
REM Rode com duplo clique ou pelo PowerShell, dentro de CampusPark\campuspark.
REM Resultado: dist\CampusPark_Reconhecimento\CampusPark_Reconhecimento.exe

cd /d "%~dp0"

REM usa o Python do venv do projeto, se existir
set PY=python
if exist "venv\Scripts\python.exe" set PY=venv\Scripts\python.exe

echo [1/4] Instalando dependencias e o PyInstaller...
%PY% -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto erro

echo [2/4] Limpando build anterior...
if exist "dist\CampusPark_Reconhecimento" rmdir /s /q "dist\CampusPark_Reconhecimento"
if exist "build\pyi" rmdir /s /q "build\pyi"

echo [3/4] Gerando o executavel (pode levar alguns minutos)...
%PY% -m PyInstaller --noconfirm --clean --console ^
  --name CampusPark_Reconhecimento ^
  --distpath dist --workpath build\pyi --specpath build ^
  --paths . ^
  --collect-submodules apps --collect-submodules config --collect-submodules core ^
  --collect-submodules integrations --collect-submodules rest_framework ^
  --hidden-import django.db.backends.postgresql ^
  --hidden-import psycopg --hidden-import psycopg_binary ^
  --add-data "resources\models;resources\models" ^
  reconhecimento_app.py
if errorlevel 1 goto erro

echo [4/4] Copiando o .env para junto do executavel...
if exist ".env" (
  copy /Y ".env" "dist\CampusPark_Reconhecimento\.env" >nul
) else (
  echo ATENCAO: .env nao encontrado. Copie-o manualmente para dist\CampusPark_Reconhecimento\
)

echo.
echo Pronto: dist\CampusPark_Reconhecimento\CampusPark_Reconhecimento.exe
echo Atencao: o .env copiado tem a senha do banco. Nao compartilhe a pasta com terceiros.
pause
exit /b 0

:erro
echo.
echo FALHOU. Veja a mensagem acima.
pause
exit /b 1
