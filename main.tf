terraform {
  required_version = ">= 1.3.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.5.0, < 4.0.0"
    }
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
  }
}

module "naming" {
  source  = "Azure/naming/azurerm"
  version = ">= 0.3.0"
}

resource "azurerm_resource_group" "llm_as_judge" {
  name     = "LLM-As-Judge"
  location = "East US"
}

resource "random_string" "suffix" {
  length  = 5
  numeric = false
  special = false
  upper   = false
}

module "openai" {
    source = "Azure/openai/azurerm"
    version = "0.1.5"

    resource_group_name = azurerm_resource_group.llm_as_judge.name
    location = azurerm_resource_group.llm_as_judge.location
    account_name = "exampleopenaiaccount"
}

resource "azurerm_container_registry" "acr" {
  name                = "judgescontainers"
  resource_group_name = azurerm_resource_group.llm_as_judge.name
  location            = azurerm_resource_group.llm_as_judge.location
  sku                 = "Basic"
  admin_enabled       = true
}

resource "azurerm_cosmosdb_account" "cosmosdb" {
  name                = "judge-container"
  resource_group_name = azurerm_resource_group.llm_as_judge.name
  location            = azurerm_resource_group.llm_as_judge.location
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"
  consistency_policy {
    consistency_level = "Session"
  }
  geo_location {
    location          = azurerm_resource_group.llm_as_judge.location
    failover_priority = 0
  }
  capabilities {
    name = "EnableServerless"
  }
  network_acl_bypass_for_azure_services = false
}

resource "azurerm_storage_account" "storage" {
  name                     = "judgesfiles"
  resource_group_name      = azurerm_resource_group.llm_as_judge.name
  location                 = azurerm_resource_group.llm_as_judge.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "openai" "azure_openai" {
  name                = "judges-models"
  resource_group_name = azurerm_resource_group.llm_as_judge.name
  location            = azurerm_resource_group.llm_as_judge.location
  sku                 = "S0"
}

resource "azurerm_cognitive_account" "speech" {
  name                = "judges-speech-tools"
  resource_group_name = azurerm_resource_group.llm_as_judge.name
  location            = azurerm_resource_group.llm_as_judge.location
  kind                = "SpeechServices"
  sku_name            = "S0"
}

resource "azurerm_cognitive_account" "vision" {
  name                = "judges-vision-tools"
  resource_group_name = azurerm_resource_group.llm_as_judge.name
  location            = azurerm_resource_group.llm_as_judge.location
  kind                = "ComputerVision"
  sku_name            = "S0"
}

resource "azurerm_container_app_environment" "env" {
  name                = "judges-containers-env"
  resource_group_name = azurerm_resource_group.llm_as_judge.name
  location            = azurerm_resource_group.llm_as_judge.location
}

resource "azurerm_container_app" "app" {
  name                = "judges-containers"
  resource_group_name = azurerm_resource_group.llm_as_judge.name
  location            = azurerm_resource_group.llm_as_judge.location
  container_app_environment_id = azurerm_container_app_environment.env.id
  revision_mode       = "Single"

  template {
    container {
      name   = "judge-container"
      image  = "${azurerm_container_registry.acr.login_server}/judge-container:latest"
      cpu    = "0.5"
      memory = "1.0Gi"

      env {
        name  = "BLOB_CONNECTION_STRING"
        value = "BlobEndpoint=https://judgesfiles.blob.core.windows.net/;QueueEndpoint=https://judgesfiles.queue.core.windows.net/;FileEndpoint=https://judgesfiles.file.core.windows.net/;TableEndpoint=https://judgesfiles.table.core.windows.net/;SharedAccessSignature=${azurerm_storage_account.storage.primary_access_key}"
      }
      env {
        name  = "COSMOS_ENDPOINT"
        value = azurerm_cosmosdb_account.cosmosdb.endpoint
      }
      env {
        name  = "COSMOS_KEY"
        value = azurerm_cosmosdb_account.cosmosdb.primary_master_key
      }
      env {
        name  = "GPT4_KEY"
        value = azurerm_openai.openai.primary_key
      }
      env {
        name  = "GPT4_URL"
        value = azurerm_openai.openai.endpoint
      }
      env {
        name  = "AI_SPEECH_URL"
        value = azurerm_cognitive_account.speech.endpoint
      }
      env {
        name  = "AI_SPEECH_KEY"
        value = azurerm_cognitive_account.speech.primary_access_key
      }
    }
  }
}

resource "null_resource" "upload_image" {
  provisioner "local-exec" {
    command = ".py-conf/conf-image.ps1 -gitRepositoryAddress ${path.module} -imageRepositoryName ${azurerm_container_registry.acr.name} -imageName judge-container"
  }
  depends_on = [azurerm_container_registry.acr]
}
