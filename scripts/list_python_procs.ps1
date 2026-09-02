Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
    Select-Object ProcessId, ParentProcessId, CommandLine |
    Format-List
