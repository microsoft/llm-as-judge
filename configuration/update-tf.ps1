# Load subscription_id from terraform.tfvars
$tfvarsFile = "terraform.tfvars"
if (!(Test-Path $tfvarsFile)) {
    Write-Error "terraform.tfvars not found."
    exit 1
}

$tfvarsContent = Get-Content $tfvarsFile -Raw
if ($tfvarsContent -match 'subscription_id\s*=\s*"([^"]+)"') {
    $subscriptionId = $matches[1]
    Write-Host "Subscription ID loaded: $subscriptionId"
} else {
    Write-Error "subscription_id not found in terraform.tfvars."
    exit 1
}

# Backup the existing Terraform state file if it exists
$stateFile = "terraform.tfstate"
if (Test-Path $stateFile) {
    $backupFile = "terraform.tfstate.backup_" + (Get-Date -Format "yyyyMMddHHmmss")
    Copy-Item $stateFile $backupFile
    Write-Host "Existing state file backed up to $backupFile"
}

# Function to attempt importing a resource; if it fails, log and continue
function Import-Resource {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ResourceAddress,
        
        [Parameter(Mandatory = $true)]
        [string]$ResourceID
    )
    try {
        # Use -ErrorAction Stop so that non-terminating errors become terminating.
        terraform import $ResourceAddress $ResourceID -ErrorAction Stop
        Write-Host "Imported $ResourceAddress successfully."
    }
    catch {
        Write-Host "Failed to import $ResourceAddress. It may not exist. Error: $_"
    }
}

# Import Resource Group
Import-Resource "azurerm_resource_group.llm_as_judge" "/subscriptions/$subscriptionId/resourceGroups/LLM-As-Judge"

# Import Container Registry
Import-Resource "azurerm_container_registry.acr" "/subscriptions/$subscriptionId/resourceGroups/LLM-As-Judge/providers/Microsoft.ContainerRegistry/registries/judgescontainers"

# Import Cosmos DB Account
Import-Resource "azurerm_cosmosdb_account.cosmosdb" "/subscriptions/$subscriptionId/resourceGroups/LLM-As-Judge/providers/Microsoft.DocumentDB/databaseAccounts/judge-container"

# Import Storage Account
Import-Resource "azurerm_storage_account.storage" "/subscriptions/$subscriptionId/resourceGroups/LLM-As-Judge/providers/Microsoft.Storage/storageAccounts/judgesfiles"

# Import Cognitive Accounts
# Update the OpenAI account name if it includes a dynamic suffix.
Import-Resource "azurerm_cognitive_account.openai" "/subscriptions/$subscriptionId/resourceGroups/LLM-As-Judge/providers/Microsoft.CognitiveServices/accounts/judges-openai-<suffix>"
Import-Resource "azurerm_cognitive_account.speech" "/subscriptions/$subscriptionId/resourceGroups/LLM-As-Judge/providers/Microsoft.CognitiveServices/accounts/judges-speech-tools"
Import-Resource "azurerm_cognitive_account.vision" "/subscriptions/$subscriptionId/resourceGroups/LLM-As-Judge/providers/Microsoft.CognitiveServices/accounts/judges-vision-tools"

# Import Container App Environment
Import-Resource "azurerm_container_app_environment.env" "/subscriptions/$subscriptionId/resourceGroups/LLM-As-Judge/providers/Microsoft.App/managedEnvironments/judges-containers-env"

# Import Container App
Import-Resource "azurerm_container_app.app" "/subscriptions/$subscriptionId/resourceGroups/LLM-As-Judge/providers/Microsoft.App/containerApps/judges-containers"

Write-Host "Resource import process completed. Use 'terraform state list' to review your state."
