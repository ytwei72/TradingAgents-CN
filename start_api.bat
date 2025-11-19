@echo off
echo 启动 TradingAgents API 服务器...
cd /d %~dp0
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
