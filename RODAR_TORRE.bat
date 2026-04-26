@echo off
title Robo Torre de Controle
cls

:: 1. Entra na pasta onde o robô realmente está
cd /d "C:\Users\komando.campinas\OneDrive\Projetos_automacao\Automacao_SLA"

echo ==========================================================
echo           INICIANDO MONITORAMENTO - PA CAMPINAS
echo ==========================================================
echo Local: %cd%

:: 2. Executa o robô
python painel_sla.py

pause