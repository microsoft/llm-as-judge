# LLM as Judge

LLM as Judge is a framework for implementing a pattern where Large Language Models (LLMs) act as judges to evaluate content, responses, or code based on defined criteria. This project provides a complete solution with API endpoints, Azure deployment support, and configurable judge assemblies.

## Features

- **Judge Orchestration**: Create and manage multiple judges with different evaluation criteria
- **Assembly System**: Group judges into assemblies for comprehensive evaluations
- **FastAPI Backend**: RESTful API for managing judges and performing evaluations
- **Azure Integration**: Built-in support for Azure Cognitive Services, Cosmos DB, and Container Apps
- **Statistical Analysis**: Includes plugins for statistical analysis and data operations
- **Infrastructure as Code**: Terraform support for easy deployment to Azure

## Architecture

The system consists of:

1. **Judges**: Individual LLM instances configured with specific evaluation criteria
2. **Assemblies**: Collections of judges that work together to provide comprehensive evaluations
3. **API Layer**: FastAPI application for managing judges and assemblies, and processing evaluation requests
4. **Storage Layer**: Azure Cosmos DB for storing judge configurations and evaluation results
5. **Plugins**: Extensions for statistical analysis, data processing, and other functions

## Judge Visualization

The LLM as Judge framework offers two distinct visual approaches:

### Judge Assembly

This approach groups multiple specialized judges into assemblies that handle different evaluation criteria. It promotes modularity, allowing tailored assemblies for various tasks.

![Judge Assembly Diagram](.static/judge_assembly.png)

### Super Judge

The Super Judge model centralizes the evaluation process within a single, advanced judge. It streamlines management while integrating multiple evaluation strategies.

![Super Judge Diagram](.static/super_judge.png)

Each approach presents unique advantages. The Judge Assembly enables flexible scalability and specialization, whereas the Super Judge focuses on simplicity and unified decision-making.

## Getting Started

### Prerequisites

- Python 3.12 or higher
- Poetry for dependency management
- Azure account with necessary permissions
- Azure CLI installed
- Terraform installed

### Local Setup

1. Clone the repository:

```
git clone https://github.com/your-username/llm-as-judge.git
cd llm-as-judge
```

2. Configure the environment:

```
./configuration/conf-env.ps1
```

3. Run linters to verify code quality:

```
./configuration/linters.ps1
```

4. Export requirements (if needed):

```
./configuration/export-requirements.ps1
```

## Provisioning Infrastructure with Terraform

### Authentication

Login to your Azure account:

```
az login
```

### Configuration

1. Create a `terraform.tfvars` file based on the sample:

```
cp terraform.tfvars.sample terraform.tfvars
```

2. Edit the `terraform.tfvars` file with your subscription and tenant IDs:

```
subscription_id = "your-subscription-id"
tenant_id       = "your-tenant-id"
```

### Deployment

1. Initialize Terraform:

```
terraform init
```

2. Create an execution plan:

```
terraform plan -out=tfplan
```

3. Apply the configuration:

```
terraform apply -var-file="terraform.tfvars"
```

### Updating Existing Resources

To import existing resources into Terraform state:

```
./configuration/update-tf.ps1
```

## Using the API

The API provides several endpoints for managing judges and performing evaluations:

### Judge Configuration

- `GET /list-judges` - List all judges
- `POST /create-judge` - Create a new judge
- `PUT /update-judge/{judge_id}` - Update an existing judge
- `DELETE /delete-judge/{judge_id}` - Delete a judge

### Assembly Configuration

- `GET /list-assemblies` - List all judge assemblies
- `POST /create-assembly` - Create a new assembly
- `PUT /update-assembly/{assembly_id}` - Update an existing assembly
- `DELETE /delete-assembly/{assembly_id}` - Delete an assembly

### Judge Execution

- `POST /evaluate` - Execute a judging evaluation

### Example Evaluation Request

```json
{
  "id": "assembly_id",
  "prompt": "The content to evaluate",
  "method": "assembly"
}
```

## Development

### Project Structure

- `src/app/` - Main application code
  - `judges.py` - Judge implementation and orchestration
  - `main.py` - FastAPI application
  - `plugins/` - Additional functionality plugins
  - `schemas/` - Data models and validation
- `src/tests/` - Test cases
- `configuration/` - Setup and configuration scripts
- `terraform.tf` - Infrastructure as code

### Running Tests

```
cd src
poetry run pytest
```

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft 
trademarks or logos is subject to and must follow 
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
