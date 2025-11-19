import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Azure OpenAI Configuration
    azure_openai_deployment_name: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "")
    azure_openai_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_openai_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")

    azure_openai_reasoning_deployment_name: str = os.getenv("AZURE_OPENAI_REASONING_DEPLOYMENT_NAME", "")
    azure_openai_reasoning_api_key: str = os.getenv("AZURE_OPENAI_REASONING_API_KEY", "")
    azure_openai_reasoning_endpoint: str = os.getenv("AZURE_OPENAI_REASONING_ENDPOINT", "")
    azure_openai_reasoning_api_version: str = os.getenv("AZURE_OPENAI_REASONING_API_VERSION", "2024-02-01")

    azure_openai_fast_deployment_name: str = os.getenv("AZURE_OPENAI_FAST_DEPLOYMENT_NAME", "")
    azure_openai_fast_api_key: str = os.getenv("AZURE_OPENAI_FAST_API_KEY", "")
    azure_openai_fast_endpoint: str = os.getenv("AZURE_OPENAI_FAST_ENDPOINT", "")
    azure_openai_fast_api_version: str = os.getenv("AZURE_OPENAI_FAST_API_VERSION", "2024-02-01")
    
    # Application Configuration
    base_path: str = "d:/repos/tf2avm"
    output_dir: str = "output"
    avm_index_url: str = "https://azure.github.io/Azure-Verified-Modules/indexes/terraform/tf-resource-modules/"
    
    # Storage Configuration
    storage_backend: str = os.getenv("STORAGE_BACKEND", "local")  # "local" or "azure"
    storage_local_base_path: str = os.getenv("STORAGE_LOCAL_BASE_PATH", "")  # Optional base path for local storage
    azure_storage_connection_string: str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    azure_storage_container: str = os.getenv("AZURE_STORAGE_CONTAINER", "tf2avm")
    azure_storage_prefix: str = os.getenv("AZURE_STORAGE_PREFIX", "")  # Optional prefix for all blobs
    
    # Agent Configuration
    max_iterations: int = 10
    timeout_seconds: int = 600  # 10 minutes timeout
    auto_handoff: bool = True   # Enable automatic handoffs
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()


def validate_environment() -> bool:
    """Validate required environment variables."""
    settings = get_settings()
    
    required_vars = [
        settings.azure_openai_deployment_name,
        settings.azure_openai_api_key,
        settings.azure_openai_endpoint,
    ]
    
    missing_vars = [var for var in required_vars if not var]
    if missing_vars:
        raise ValueError("Missing required environment variables. Check your .env file.")
    
    return True