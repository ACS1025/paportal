@echo off
title Robo Torre de Controle - PA Campinas
cls

:: 1. Entra na pasta correta (ajuste se o nome do seu OneDrive for diferente)
cd /d "C:\Users\komando.campinas\OneDrive\Automacao_SLA"

echo ======================================================
echo          MONITORAMENTO SLA - PA CAMPINAS
echo ======================================================
echo Local: %cd%
echo Iniciando...

:: 2. Tenta rodar o script
python painel_sla.py

:: 3. Se der erro, ele te avisa antes de fechar
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] O script parou de funcionar.
    echo Verifique se o arquivo credenciais.json esta na pasta.
    pause
)