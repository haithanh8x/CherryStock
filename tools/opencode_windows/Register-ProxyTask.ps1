param([string]$Profile = "data-app-sit", [string]$Region = "ap-southeast-1")
$ErrorActionPreference = "Stop"
$name = "CherryStock-BedrockProxy"
if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) { throw "Task already exists; inspect it before replacing." }
if ($Profile -notmatch '^[A-Za-z0-9_.-]+$' -or $Region -notmatch '^[a-z0-9-]+$') { throw "Invalid profile/region." }
$script = Join-Path $PSScriptRoot "Start-BedrockProxy.ps1"
if (-not (Test-Path (Join-Path $PSScriptRoot ".venv\Scripts\python.exe"))) { throw "Run Install.ps1 first." }
$user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument ("-NoProfile -File `"$script`" -Profile $Profile -Region $Region -LogToFile") -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $user
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Principal $principal -Settings $settings | Out-Null
Write-Host "Registered per-user logon task $name. Not started. No password stored."
