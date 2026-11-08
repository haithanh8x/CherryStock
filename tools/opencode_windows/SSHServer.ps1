param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('--start', '--stop')]
    [string]$Action
)

$ErrorActionPreference = "Stop"

$service = Get-Service -Name sshd -ErrorAction SilentlyContinue
if (-not $service) {
    throw "OpenSSH Server (sshd) was not found. Install the Windows OpenSSH Server capability first."
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    try {
        $shell = (Get-Process -Id $PID).Path
        $process = Start-Process -FilePath $shell -Verb RunAs -Wait -PassThru -ArgumentList @(
            '-NoProfile', '-File', ('"{0}"' -f $PSCommandPath), '-Action', $Action
        )
    } catch {
        throw "Could not elevate via UAC. Approve the prompt or run PowerShell as Administrator. $_"
    }
    if ($process.ExitCode -ne 0) {
        throw "Elevated script exited with code $($process.ExitCode). Run PowerShell as Administrator for details."
    }
    if ($Action -eq '--stop') {
        Write-Warning "Stopping sshd may disconnect active SSH sessions."
    }
    Get-Service -Name sshd | Select-Object Name, Status, StartType
    exit 0
}

if ($Action -eq '--start' -and $service.Status -ne 'Running') {
    Start-Service -Name sshd
} elseif ($Action -eq '--stop' -and $service.Status -ne 'Stopped') {
    Write-Warning "Stopping sshd may disconnect active SSH sessions."
    Stop-Service -Name sshd
}
Get-Service -Name sshd | Select-Object Name, Status, StartType
