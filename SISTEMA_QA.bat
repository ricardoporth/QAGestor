@echo off
:: Garante que o script rode a partir da pasta do projeto, nao importa onde o atalho esteja
cd /d %~dp0
:: ===================================================================
::  SCRIPT SIMPLIFICADO PARA INICIAR O SISTEMA DE FINANÇAS
::  (Sem necessidade de ambiente virtual)
:: ===================================================================
title Iniciando Sistema de Finanças...

echo.
echo ===============================================================
echo  INICIANDO APLICACAO DE FINANCAS (STREAMLIT)
echo ===============================================================
echo.

:: -------------------------------------------------------------------
::  1. INICIAR A APLICACAO
:: -------------------------------------------------------------------
echo Iniciando o servidor Streamlit...
echo.

:: O comando 'start' abre uma NOVA janela de terminal.
:: 'cmd /k' executa o comando e MANTÉM a janela aberta para vermos os logs.
start "Sistema de QA - Streamlit" cmd /k "python -m streamlit run "app.py""

:: -------------------------------------------------------------------
::  2. ABRIR O NAVEGADOR
:: -------------------------------------------------------------------
echo.
echo Aguardando 4 segundos para o servidor iniciar...
timeout /t 4 /nobreak >nul

echo Abrindo a aplicacao no seu navegador...
:: A porta padrão do Streamlit é a 8501
start http://localhost:8502

echo.
echo ===============================================================
echo  Tudo pronto! A aplicacao esta rodando em sua propria janela.
echo ===============================================================
echo.

timeout /t 6