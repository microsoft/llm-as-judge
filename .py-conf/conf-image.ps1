param(
    [Parameter(Mandatory=$true)][string]$gitRepositoryAddress,
    [Parameter(Mandatory=$true)][string]$imageRepositoryName,
    [Parameter(Mandatory=$true)][string]$imageName,
    [Parameter(Mandatory=$false)][string]$imageVersion
)

# Check if the imageVersion variable is set, if not, set it to "latest"
if (-not $imageVersion) {
    $imageVersion = "latest"
}

# Set the working directory to the root of the repository
Set-Location -Path $gitRepositoryAddress

# Read the .env file. You might want to add this.
$envFile = Get-Content "src\backend\.env"

# # Extract the username and password from the .env file
$usernameLine = $envFile | Where-Object { $_ -match "^ACR_USER = " }
$passwordLine = $envFile | Where-Object { $_ -match "^ACR_PASSWORD = " }

# Check if the username and password lines were found
if ($null -ne $usernameLine -and $null -ne $passwordLine) {
    $username = $usernameLine.Split("= ")[3].Trim().Replace('"', '')
    $password = $passwordLine.Split("= ")[3].Trim().Replace('"', '')

    # Login to Azure Container Registry
    az acr login --name $repositoryName --username ${username} --password ${password}

    # Build the Docker image
    docker build -t ${imageName} --file .docker-images/${imageName}/dockerfile .
    docker login "$repositoryName.azurecr.io"

    # Tag the Docker image
    $tag = "${imageName}:${imageVersion}"
    docker tag $imageName "$repositoryName.azurecr.io/$imageName"

    # Push the Docker image
    docker push "$repositoryName.azurecr.io/$tag"
} else {
    Write-Host "Error: Could not find ACR_USER or ACR_PASSWORD in the .env file."
}
