@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
title eais-sdk-agent

if not exist ".env" (
  echo.
  echo   [INFO] .env not found. Running without LLM ^(rule-based questions^).
  echo   Copy .env.example to .env and put your OPENAI_API_KEY in it to enable the agent.
  echo.
)

python app.py
pause
