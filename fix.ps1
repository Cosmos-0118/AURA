(Get-Content -Path scripts\windows\aura.ps1) -replace '\$pid\b', '$procId' | Set-Content -Path scripts\windows\aura.ps1
(Get-Content -Path scripts\windows\aura.ps1) -replace '\$pidFile\b', '$procIdFile' | Set-Content -Path scripts\windows\aura.ps1
