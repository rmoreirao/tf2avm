from semantic_kernel.functions import kernel_function
from pathlib import Path
import json
import re
from datetime import datetime


class FileSystemPlugin:
    """Plugin for file system operations."""
    
    def __init__(self, base_path: str = "d:/repos/tf2avm"):
        self.base_path = Path(base_path)

    @kernel_function(
        description="Read all Terraform (.tf) files from a specified directory path. Returns a dictionary of file paths and their contents.",
        name="read_tf_files",
    )
    def read_tf_files(self, directory_path: str) -> str:
        """Read all .tf files from the specified directory and return as JSON string."""
        search_path = Path(directory_path) if directory_path else self.base_path
        tf_files = {}
        
        for tf_file in search_path.glob("**/*.tf"):
            try:
                with open(tf_file, "r", encoding="utf-8") as f:
                    tf_files[str(tf_file.relative_to(search_path))] = f.read()
            except Exception as e:
                print(f"Error reading {tf_file}: {e}")
        
        return json.dumps(tf_files, indent=2)

    @kernel_function(
        description="Write content to a file in the specified output directory. Returns the path to the created file.",
        name="write_file",
    )
    def write_file(self, output_dir: str, filename: str, content: str) -> str:
        """Write content to a file in the output directory and return the file path."""
        file_path = Path(output_dir) / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return str(file_path)

    @kernel_function(
        description="Create a directory if it doesn't exist. Returns the directory path.",
        name="create_directory",
    )
    def create_directory(self, directory_path: str) -> str:
        """Create a directory and return its path."""
        dir_path = Path(directory_path)
        dir_path.mkdir(parents=True, exist_ok=True)
        return str(dir_path)

    @kernel_function(
        description="Copy files from source directory to destination directory.",
        name="copy_files",
    )
    def copy_files(self, source_dir: str, dest_dir: str) -> str:
        """Copy all files from source to destination directory."""
        import shutil
        
        source_path = Path(source_dir)
        dest_path = Path(dest_dir)
        dest_path.mkdir(parents=True, exist_ok=True)
        
        copied_files = []
        for file_path in source_path.glob("**/*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(source_path)
                dest_file = dest_path / relative_path
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, dest_file)
                copied_files.append(str(relative_path))
        
        return f"Copied {len(copied_files)} files to {dest_dir}"

    @kernel_function(
        description="Parse Terraform file content and extract resources, variables, outputs.",
        name="parse_terraform_file",
    )
    def parse_terraform_file(self, file_content: str) -> str:
        """Parse Terraform file content and extract key components."""
        # Simple regex-based parsing for Terraform components
        result = {
            "resources": [],
            "variables": [],
            "outputs": [],
            "locals": []
        }
        
        # Extract resources
        resource_pattern = r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{'
        for match in re.finditer(resource_pattern, file_content):
            result["resources"].append({
                "type": match.group(1),
                "name": match.group(2)
            })
        
        # Extract variables
        variable_pattern = r'variable\s+"([^"]+)"\s*\{'
        for match in re.finditer(variable_pattern, file_content):
            result["variables"].append(match.group(1))
        
        # Extract outputs
        output_pattern = r'output\s+"([^"]+)"\s*\{'
        for match in re.finditer(output_pattern, file_content):
            result["outputs"].append(match.group(1))
        
        # Extract locals
        locals_pattern = r'locals\s*\{'
        if re.search(locals_pattern, file_content):
            result["locals"].append("locals_block_found")
        
        return json.dumps(result, indent=2)

    @kernel_function(
        description="Generate a timestamped output directory path.",
        name="generate_output_dir",
    )
    def generate_output_dir(self, base_output_dir: str) -> str:
        """Generate a timestamped output directory path."""
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        output_dir = Path(base_output_dir) / timestamp
        return str(output_dir)