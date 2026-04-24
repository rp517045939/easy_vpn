@echo off
chcp 65001 > nul
:: easy_vpn Client 一键启动脚本（Windows）
:: 用法：双击运行，或在命令提示符中执行 start.bat [--no-ui]

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"
set "CONFIG=%SCRIPT_DIR%config.yml"
set "EXTRA_ARGS=%*"

:: ── 检查 Python ──────────────────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到 Python，请先从 https://www.python.org/downloads/ 安装 Python 3.10+
    echo         安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
echo [INFO]  Python: %PY_VER%

:: 验证 Python 版本 >= 3.10
for /f "tokens=1,2 delims=." %%a in ("%PY_VER%") do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)
if %PY_MAJOR% LSS 3 (
    echo [ERROR] 需要 Python 3.10 或更高版本，当前版本：%PY_VER%
    pause
    exit /b 1
)
if %PY_MAJOR% EQU 3 if %PY_MINOR% LSS 10 (
    echo [ERROR] 需要 Python 3.10 或更高版本，当前版本：%PY_VER%
    pause
    exit /b 1
)

:: ── 检查配置文件 ─────────────────────────────────────────────────────────
if not exist "%CONFIG%" (
    if exist "%SCRIPT_DIR%config.example.yml" (
        echo [WARN]  未找到 config.yml，已从 config.example.yml 复制，请编辑后重新运行
        copy "%SCRIPT_DIR%config.example.yml" "%CONFIG%" >nul
        echo [ERROR] 请先编辑 config.yml 填入 server url 和 token
        notepad "%CONFIG%"
        pause
        exit /b 1
    ) else (
        echo [ERROR] 未找到 config.yml，请参考 config.example.yml 创建
        pause
        exit /b 1
    )
)

:: ── 创建/更新虚拟环境 ────────────────────────────────────────────────────
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [INFO]  创建虚拟环境...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] 创建虚拟环境失败
        pause
        exit /b 1
    )
)

:: ── 检查依赖 ─────────────────────────────────────────────────────────────
set "REQS=%SCRIPT_DIR%requirements.txt"
set "REQS_STAMP=%VENV_DIR%\.reqs_installed"
set "NEEDS_INSTALL=0"

if not exist "%REQS_STAMP%" set "NEEDS_INSTALL=1"
if "%NEEDS_INSTALL%"=="0" (
    for %%f in ("%REQS%")     do set "REQS_TIME=%%~tf"
    for %%f in ("%REQS_STAMP%") do set "STAMP_TIME=%%~tf"
    if "!REQS_TIME!" GTR "!STAMP_TIME!" set "NEEDS_INSTALL=1"
)

if "%NEEDS_INSTALL%"=="1" (
    echo [INFO]  安装依赖...
    "%VENV_DIR%\Scripts\python" -m pip install -q -r "%REQS%"
    if errorlevel 1 (
        echo [ERROR] 依赖安装失败，请检查网络或手动执行：
        echo         "%VENV_DIR%\Scripts\python" -m pip install -r "%REQS%"
        pause
        exit /b 1
    )
    echo. > "%REQS_STAMP%"
) else (
    echo [INFO]  依赖已是最新，跳过安装
)

:: ── 启动 ─────────────────────────────────────────────────────────────────
echo [INFO]  启动 easy_vpn client...
echo [INFO]  Web 管理界面：http://127.0.0.1:7070
echo.
"%VENV_DIR%\Scripts\python" "%SCRIPT_DIR%main.py" --config "%CONFIG%" %EXTRA_ARGS%

if errorlevel 1 (
    echo.
    echo [ERROR] 程序异常退出，按任意键关闭...
    pause >nul
)
endlocal
