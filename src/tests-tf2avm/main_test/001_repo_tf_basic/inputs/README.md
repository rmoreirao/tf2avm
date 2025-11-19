# Azure Web Application Infrastructure

This Terraform configuration creates a complete Azure web application infrastructure based on the provided architecture diagram.

## Architecture Components

- **Resource Group**: Container for all resources
- **App Service Plan**: Linux-based hosting plan
- **Web App**: ReactJS frontend application
- **API App**: .NET Core backend API
- **Key Vault**: Secure storage for secrets and connection strings
- **Cosmos DB**: NoSQL database with SQL API
- **Azure Monitor**: Log Analytics and Application Insights for monitoring

## File Structure

- `main.tf` - Provider configuration and resource group
- `app-service.tf` - App Service Plan, Web App, and API App
- `security.tf` - Key Vault and access policies
- `storage.tf` - Cosmos DB account, database, and container
- `monitoring.tf` - Log Analytics workspace and Application Insights
- `variables.tf` - Input variables with defaults
- `outputs.tf` - Output values for important resources

## Prerequisites

1. Azure CLI installed and authenticated
2. Terraform installed (>= 1.0)
3. Appropriate Azure permissions to create resources

## Deployment

1. Initialize Terraform:
```bash
terraform init
```

2. Review the planned changes:
```bash
terraform plan
```

3. Apply the configuration:
```bash
terraform apply
```

## Configuration

Key variables can be customized in `variables.tf` or by creating a `terraform.tfvars` file:

```hcl
resource_group_name = "my-webapp-rg"
location = "West Europe"
web_app_name = "my-unique-webapp-name"
api_app_name = "my-unique-api-name"
```

## Security Features

- **Managed Identity**: Both Web App and API use system-assigned managed identities
- **Key Vault Integration**: Connection strings stored securely in Key Vault
- **Access Policies**: Proper access control for Key Vault secrets

## Monitoring

- **Application Insights**: Application performance monitoring
- **Log Analytics**: Centralized logging for all services
- **Diagnostic Settings**: Automatic log collection from all resources

## Post-Deployment

After deployment, you'll need to:

1. Deploy your ReactJS application to the Web App
2. Deploy your .NET API to the API App
3. Configure Application Insights in your applications
4. Set up any additional application settings as needed

## Cleanup

To destroy all resources:
```bash
terraform destroy
```