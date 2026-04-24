# easy_vpn Client 一键启动脚本（Windows PowerShell）
# 用法：右键 → "用 PowerShell 运行"，或执行 .\start.ps1 [--no-ui]
# 若提示执行策略限制，先运行：Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

param(
    [switch]$NoUI,
    [string]$UiHost = "127.0.0.1",
    [int]$UiPort    = 7070
)

$ErrorActionPreference = "Stop"
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir    = Join-Path $ScriptDir ".venv"
$ConfigFile = Join-Path $ScriptDir "config.yml"

function Write-Info  { param($msg) Write-Host "[INFO]  $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Write-Err   { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red }

# ── 检查 Python ──────────────────────────────────────────────────────────
$python = $null
foreach ($cmd in @("python", "python3")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]; $minor = [int]$Matches[2]
            if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 10)) {
                $python = $cmd
                Write-Info "Python: $ver"
                break
            } else {
                Write-Err "需要 Python 3.10+，当前 $ver"
                Read-Host "按 Enter 退出"
                exit 1
            }
        }
    } catch {}
}

if (-not $python) {
    Write-Err "未找到 Python，请从 https://www.python.org/downloads/ 安装 Python 3.10+"
    Write-Err "安装时请勾选 'Add Python to PATH'"
    Read-Host "按 Enter 退出"
    exit 1
}

# ── 检查配置文件 ─────────────────────────────────────────────────────────
if (-not (Test-Path $ConfigFile)) {
    $example = Join-Path $ScriptDir "config.example.yml"
    if (Test-Path $example) {
        Write-Warn "未找到 config.yml，已从 config.example.yml 复制，请编辑后重新运行"
        Copy-Item $example $ConfigFile
        Start-Process notepad $ConfigFile
        Write-Err "请先编辑 config.yml 填入 server url 和 token"
        Read-Host "按 Enter 退出"
        exit 1
    } else {
        Write-Err "未找到 config.yml，请参考 config.example.yml 创建"
        Read-Host "按 Enter 退出"
        exit 1
    }
}

# ── 创建/更新虚拟环境 ────────────────────────────────────────────────────
$venvPython = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Info "创建虚拟环境..."
    & $python -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        Write-Err "创建虚拟环境失败"
        Read-Host "按 Enter 退出"
        exit 1
    }
}

# ── 检查依赖 ─────────────────────────────────────────────────────────────
$reqs      = Join-Path $ScriptDir "requirements.txt"
$reqsStamp = Join-Path $VenvDir ".reqs_installed"
$needsInstall = $false

if (-not (Test-Path $reqsStamp)) {
    $needsInstall = $true
} else {
    $reqsMtime   = (Get-Item $reqs).LastWriteTime
    $stampMtime  = (Get-Item $reqsStamp).LastWriteTime
    if ($reqsMtime -gt $stampMtime) { $needsInstall = $true }
}

if ($needsInstall) {
    Write-Info "安装依赖..."
    $pip = Join-Path $VenvDir "Scripts\pip.exe"
    & $pip install -q -r $reqs
    if ($LASTEXITCODE -ne 0) {
        Write-Err "依赖安装失败，请检查网络连接"
        Read-Host "按 Enter 退出"
        exit 1
    }
    New-Item -ItemType File -Force $reqsStamp | Out-Null
} else {
    Write-Info "依赖已是最新，跳过安装"
}

# ── 构建参数 ─────────────────────────────────────────────────────────────
$mainPy = Join-Path $ScriptDir "main.py"
$runArgs = @("--config", $ConfigFile, "--ui-host", $UiHost, "--ui-port", $UiPort)
if ($NoUI) { $runArgs += "--no-ui" }

# ── 启动 ─────────────────────────────────────────────────────────────────
Write-Info "启动 easy_vpn client..."
if (-not $NoUI) { Write-Info "Web 管理界面：http://${UiHost}:${UiPort}" }
Write-Host ""

& $venvPython $mainPy @runArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Err "程序异常退出（exit code: $LASTEXITCODE）"
    Read-Host "按 Enter 退出"
}
