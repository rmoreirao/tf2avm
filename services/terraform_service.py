import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any

from config.logging import get_logger


@dataclass
class TerraformValidationResult:
    """Result of Terraform validation operation."""
    success: bool
    error_message: Optional[str] = None
    validation_data: Optional[Dict[str, Any]] = None


@dataclass
class TerraformVersionResult:
    """Result of Terraform version check operation."""
    available: bool
    version_or_error: Optional[str] = None


class TerraformService:
    """
    TerraformService - Service for interacting with Terraform CLI.
    
    This service provides functionality to validate Terraform configurations
    using the terraform CLI commands.
    """
    
    def __init__(self):
        """Initialize the Terraform Service."""
        self.logger = get_logger(__name__)
    
    def validate_terraform(self, directory: str) -> TerraformValidationResult:
        """
        Validate Terraform configuration in the specified directory.
        
        Runs 'terraform init' followed by 'terraform validate -json' to validate
        the Terraform configuration.
        
        Args:
            directory: Path to the directory containing Terraform files
            
        Returns:
            TerraformValidationResult: Result object containing validation status and details
        """
        directory_path = Path(directory)
        
        if not directory_path.exists():
            error_msg = f"Directory does not exist: {directory}"
            self.logger.error(error_msg)
            return TerraformValidationResult(False, error_msg)
        
        if not directory_path.is_dir():
            error_msg = f"Path is not a directory: {directory}"
            self.logger.error(error_msg)
            return TerraformValidationResult(False, error_msg)
        
        # Check if directory contains any .tf files
        tf_files = list(directory_path.glob("*.tf"))
        if not tf_files:
            error_msg = f"No .tf files found in directory: {directory}"
            self.logger.warning(error_msg)
            return TerraformValidationResult(False, error_msg)
        
        try:
            # Step 1: Run terraform init
            self.logger.info(f"Running terraform init in {directory}")
            init_result = subprocess.run(
                ["terraform", "init"],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if init_result.returncode != 0:
                error_msg = f"Terraform init failed: {init_result.stderr}"
                self.logger.error(error_msg)
                return TerraformValidationResult(False, error_msg)
            
            self.logger.info("Terraform init completed successfully")
            
            # Step 2: Run terraform validate -json
            self.logger.info(f"Running terraform validate in {directory}")
            validate_result = subprocess.run(
                ["terraform", "validate", "-json"],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=120  # 2 minutes timeout
            )
            
            # Parse JSON output
            validation_json = None
            if validate_result.stdout:
                try:
                    validation_json = json.loads(validate_result.stdout)
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Failed to parse terraform validate JSON output: {e}")
                    validation_json = {"raw_output": validate_result.stdout}
            
            if validate_result.returncode != 0:
                # Extract error message from JSON if available, otherwise use stderr
                error_msg = "Terraform validation failed"
                
                if validation_json and "error_count" in validation_json:
                    errors = []
                    if "diagnostics" in validation_json:
                        for diagnostic in validation_json["diagnostics"]:
                            if diagnostic.get("severity") == "error":
                                detail = diagnostic.get("detail", "Unknown error")
                                summary = diagnostic.get("summary", "")
                                range_info = ""
                                if "range" in diagnostic:
                                    filename = diagnostic["range"].get("filename", "")
                                    start_line = diagnostic["range"].get("start", {}).get("line", "")
                                    range_info = f" ({filename}:{start_line})" if filename and start_line else ""
                                
                                error_detail = f"{summary}: {detail}{range_info}".strip(": ")
                                errors.append(error_detail)
                    
                    if errors:
                        error_msg = f"Terraform validation failed with {len(errors)} error(s):\n" + "\n".join(f"  - {err}" for err in errors)
                    else:
                        error_msg = f"Terraform validation failed: {validate_result.stderr}"
                else:
                    error_msg = f"Terraform validation failed: {validate_result.stderr}"
                
                self.logger.error(error_msg)
                return TerraformValidationResult(False, error_msg, validation_json)
            
            self.logger.info("Terraform validation completed successfully")
            return TerraformValidationResult(True, validation_data=validation_json)
            
        except subprocess.TimeoutExpired as e:
            error_msg = f"Terraform command timed out: {e}"
            self.logger.error(error_msg)
            return TerraformValidationResult(False, error_msg)
            
        except FileNotFoundError:
            error_msg = "Terraform CLI not found. Please ensure Terraform is installed and available in PATH."
            self.logger.error(error_msg)
            return TerraformValidationResult(False, error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error during Terraform validation: {str(e)}"
            self.logger.error(error_msg)
            return TerraformValidationResult(False, error_msg)
    
    def check_terraform_installed(self) -> TerraformVersionResult:
        """
        Check if Terraform CLI is installed and accessible.
        
        Returns:
            TerraformVersionResult: Result object containing availability status and version/error info
        """
        try:
            result = subprocess.run(
                ["terraform", "version"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0] if result.stdout else "Unknown version"
                self.logger.info(f"Terraform CLI found: {version_line}")
                return TerraformVersionResult(True, version_line)
            else:
                error_msg = f"Terraform version check failed: {result.stderr}"
                self.logger.error(error_msg)
                return TerraformVersionResult(False, error_msg)
                
        except FileNotFoundError:
            error_msg = "Terraform CLI not found in PATH"
            self.logger.error(error_msg)
            return TerraformVersionResult(False, error_msg)
            
        except Exception as e:
            error_msg = f"Error checking Terraform installation: {str(e)}"
            self.logger.error(error_msg)
            return TerraformVersionResult(False, error_msg)