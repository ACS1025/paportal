@echo off
title Robo Torre de Controle - VERSAO LIMPA
:inicio
cls
cd /d "C:\Users\komando.campinas\OneDrive\Projetos_automacao\Automacao_SLA"

echo ==========================================================
echo           INICIANDO MOTOR NOVO: motor_torre.py
echo ==========================================================

:: O comando -B limpa o cache. Aponte para o novo nome:
python -B motor_torre.py

echo ==========================================================
echo Robô parou! Reiniciando em 10 segundos...
echo ==========================================================
timeout /t 10
goto inicio