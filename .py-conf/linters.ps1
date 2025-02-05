$rootFolder = (Get-Item -Path "$PSScriptRoot\..\src").FullName
try {
    Set-Location -Path $rootFolder
} catch {
    Write-Host "Error changing directory: $_"
}

$configurationFile = Join-Path -Path $rootFolder -ChildPath "\pyproject.toml"
$appDirectory = Join-Path -Path $rootFolder -ChildPath "\app"

isort --sp=$configurationFile $rootFolder
black --config $configurationFile $rootFolder
pylint --rcfile=$configurationFile $appDirectory
