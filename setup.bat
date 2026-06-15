@echo off
chcp 65001 >nul
title AIGC T2I Studio - 环境安装
echo.
echo   ========================================
echo     AIGC T2I Studio - 一键安装
echo   ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] Python 已安装
    goto :install_deps
)

echo   [!] 未检测到 Python，正在自动下载安装...
echo.
echo   下载地址：https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
echo.
echo   如果下载失败，请手动安装 Python 3.8+ 后重试。
echo   官网：https://www.python.org/downloads/
echo   安装时务必勾选 "Add Python to PATH"
echo.
start https://www.python.org/downloads/
echo.
echo   安装完成后请重新运行本脚本。
pause
exit /b 0

:install_deps
echo.
echo   [1/2] 创建虚拟环境...
python -m venv venv
call venv\Scripts\activate

echo.
echo   [2/2] 安装依赖...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo   [OK] 初始化配置...
if not exist .env copy .env.example .env

echo.
echo   ========================================
echo     安装完成！
echo.
echo     接下来：
echo     1. 用记事本打开 .env 修改配置
echo     2. 双击 run.bat 启动
echo   ========================================
echo.
pause
