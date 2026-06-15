@echo off
chcp 65001 >nul
title AIGC T2I Studio
echo.
echo   ========================================
echo     AIGC T2I Studio - 启动中...
echo   ========================================
echo.

call venv\Scripts\activate

echo   [启动] 数据集筛选服务（端口 8888）...
start "AIGC-筛选器" cmd /c "title AIGC-筛选器 && call venv\Scripts\activate && python filter_server.py"

echo   [启动] 主应用（端口 8000）...
echo.
echo   +-----------------------------+
echo   | 主应用：http://127.0.0.1:8000  |
echo   | 筛选器：http://127.0.0.1:8888  |
echo   +-----------------------------+
echo.
echo   按 Ctrl+C 停止，筛选器窗口请手动关闭
echo   ========================================
echo.

python -m uvicorn app:app --host 127.0.0.1 --port 8000
pause