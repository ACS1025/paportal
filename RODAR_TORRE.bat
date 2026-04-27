@echo off
title Robo Torre de Controle - LIMPEZA TOTAL
:inicio
cls
cd /d "C:\Users\komando.campinas\OneDrive\Projetos_automacao\Automacao_SLA"

echo ==========================================================
echo           MATANDO PROCESSOS ANTIGOS (PYTHON/CHROME)
echo ==========================================================
taskkill /f /im python.exe /t >nul 2>&1
taskkill /f /im chrome.exe /t >nul 2>&1

echo ==========================================================
echo           INICIANDO VERSÃO LIMPA
echo ==========================================================
echo Pasta Atual: %cd%

:: O comando -B impede a criação de cache novo
python -B painel_sla.py

echo ==========================================================
echo ⚠️ Robô parou. Reiniciando em 10 segundos...
echo ==========================================================
timeout /t 10
goto inicio