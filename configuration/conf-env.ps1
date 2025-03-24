function ExecuteCommand($command) {
    Write-Host "Executing: $command"
    Invoke-Expression $command
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error executing command: $LASTEXITCODE"
        Write-Host "Error output: $($error[0])"
        exit $LASTEXITCODE
    }
}

# Go to the financial_analyst_py folder
$rootFolder = (Get-Item -Path "$PSScriptRoot\..").FullName
try {
    Set-Location -Path "$rootFolder\src"
} catch {
    Write-Host "Error changing directory: $_"
}

# Configure the package to use local .venv
$command = "poetry config virtualenvs.in-project true"
ExecuteCommand $command

# Select Python 3.10 as the package version
$command = "poetry env use python3.12"
ExecuteCommand $command

# Select Python 3.10 as the package version
$command = "poetry install"
ExecuteCommand $command
