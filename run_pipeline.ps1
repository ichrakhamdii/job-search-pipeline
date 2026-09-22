$ErrorActionPreference = "Continue"
Set-Location "C:\Users\PC\Desktop\pro_projects\project_1"
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$logFile = "output\run_log_$timestamp.txt"
python main.py *> $logFile
