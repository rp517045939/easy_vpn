
# easy_vpn Client 开机自启 安装/卸载脚本
# 用法：
#   .\autostart.ps1           安装开机自启（登录后自动在后台运行）
#   .\autostart.ps1 -Remove   卸载开机自启
#   .\autostart.ps1 -Status   查看任务状态

param(
    [switch]$Remove,
    [switch]$Status
)

$TaskName  = "easy_vpn_client"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Info { param($m) Write-Host "[INFO]  $m" -ForegroundColor Cyan }
function Write-Ok   { param($m) Write-Host "[OK]    $m" -ForegroundColor Green }
function Write-Err  { param($m) Write-Host "[ERROR] $m" -ForegroundColor Red }

# ── 查看状态 ─────────────────────────────────────────────────────────────
if ($Status) {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task) {
        $info = Get-ScheduledTaskInfo -TaskName $TaskName
        Write-Ok  "任务已注册：$TaskName"
        Write-Info "状态：$($task.State)"
        Write-Info "上次运行：$($info.LastRunTime)"
        Write-Info "上次结果：$($info.LastTaskResult)"
        Write-Info "下次运行：$($info.NextRunTime)"
    } else {
        Write-Err "未找到任务：$TaskName（尚未安装开机自启）"
    }
    exit 0
}

# ── 卸载 ─────────────────────────────────────────────────────────────────
if ($Remove) {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Ok "已删除开机自启任务：$TaskName"
    } else {
        Write-Err "未找到任务：$TaskName"
    }
    exit 0
}

# ── 安装 ─────────────────────────────────────────────────────────────────

# 检查虚拟环境
$venvPython  = Join-Path $ScriptDir ".venv\Scripts\python.exe"
$mainPy      = Join-Path $ScriptDir "main.py"
$configFile  = Join-Path $ScriptDir "config.yml"

if (-not (Test-Path $venvPython)) {
    Write-Err "虚拟环境不存在，请先运行 .\start.ps1 安装依赖后再执行本脚本"
    Read-Host "按 Enter 退出"
    exit 1
}

if (-not (Test-Path $configFile)) {
    Write-Err "config.yml 不存在，请先参考 config.example.yml 创建配置文件"
    Read-Host "按 Enter 退出"
    exit 1
}

# 使用 python.exe（有控制台窗口，可直接查看日志并手动关闭）
$executor = $venvPython
Write-Info "执行器：$executor"

# 构建任务：登录后后台运行，保留 Web UI（localhost:7070 可查看状态）
$action   = New-ScheduledTaskAction `
    -Execute $executor `
    -Argument "`"$mainPy`" --config `"$configFile`"" `
    -WorkingDirectory $ScriptDir

$trigger  = New-ScheduledTaskTrigger -AtLogOn

# 无限运行时限；崩溃后 1 分钟内最多重启 3 次；AC/电池均运行
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit    ([TimeSpan]::Zero) `
    -RestartCount          3 `
    -RestartInterval       (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable    `
    -RunOnlyIfNetworkAvailable:$false `
    -DontStopIfGoingOnBatteries

# PS 5.1 无对应参数，直接设属性来允许电池模式下启动
$settings.DisallowStartIfOnBatteries = $false

# 删除旧任务（如果存在）再重新注册
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask `
    -TaskName   $TaskName `
    -Action     $action `
    -Trigger    $trigger `
    -Settings   $settings `
    -RunLevel   Limited `
    -Description "easy_vpn 内网穿透客户端，开机自启" | Out-Null

if ($?) {
    Write-Ok  "开机自启已安装！任务名：$TaskName"
    Write-Info "下次登录 Windows 时将自动在后台启动"
    Write-Info "Web 管理界面：http://127.0.0.1:7070"
    Write-Info ""
    Write-Info "其他操作："
    Write-Info "  立即启动  → Start-ScheduledTask  '$TaskName'"
    Write-Info "  立即停止  → Stop-ScheduledTask   '$TaskName'"
    Write-Info "  查看状态  → .\autostart.ps1 -Status"
    Write-Info "  卸载自启  → .\autostart.ps1 -Remove"
} else {
    Write-Err "注册失败，请尝试以管理员身份运行本脚本"
    Read-Host "按 Enter 退出"
    exit 1
}
