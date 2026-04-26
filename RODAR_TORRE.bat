@echo off
title Robo Torre de Controle - AUTO RECOVERY
:inicio
cls
cd /d "C:\Users\komando.campinas\OneDrive\Projetos_automacao\Automacao_SLA"

echo ==========================================================
echo           INICIANDO MONITORAMENTO - PA CAMPINAS
echo ==========================================================
echo [%date% %time%] - Ligando o motor...

:: Executa o robô
python painel_sla.py

echo ==========================================================
echo ⚠️ O robô parou ou travou! Reiniciando em 10 segundos...
echo ==========================================================
timeout /t 10
goto inicio