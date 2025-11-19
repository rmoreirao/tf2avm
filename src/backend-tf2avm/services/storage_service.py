"""
Storage Service - Unified interface for local and cloud storage backends.

Provides pluggable storage backends supporting local filesystem and Azure Blob Storage,
enabling flexible artifact persistence without changing orchestration logic.
"""

import asyncio
import json
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol
from datetime import datetime

from config.logging import get_logger


class StorageError(Exception):
    """Base exception for storage operations."""
    pass


class StorageBackend(Protocol):
    """Protocol defining the interface for storage backends."""
    
    async def read_text(self, path: str) -> str:
        """Read text content from a file."""
        ...
    
    async def write_text(self, path: str, content: str) -> None:
        """Write text content to a file."""
        ...
    
    async def read_bytes(self, path: str) -> bytes:
        """Read binary content from a file."""
        ...
    
    async def write_bytes(self, path: str, content: bytes) -> None:
        """Write binary content to a file."""
        ...
    
    async def read_json(self, path: str) -> Dict[str, Any]:
        """Read and parse JSON from a file."""
        ...
    
    async def write_json(self, path: str, data: Dict[str, Any]) -> None:
        """Write JSON data to a file."""
        ...
    
    async def exists(self, path: str) -> bool:
        """Check if a path exists."""
        ...
    
    async def list_files(self, path: str, pattern: str = "*") -> List[str]:
        """List files in a directory matching a pattern."""
        ...
    
    async def copy_file(self, source: str, destination: str) -> None:
        """Copy a file from source to destination."""
        ...
    
    async def ensure_dir(self, path: str) -> None:
        """Ensure a directory exists."""
        ...
    
    async def delete(self, path: str) -> None:
        """Delete a file or directory."""
        ...


class LocalFileStorageBackend:
    """Local filesystem storage backend using pathlib and async I/O."""
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize local file storage backend.
        
        Args:
            base_path: Optional base directory for all operations
        """
        self.logger = get_logger(__name__)
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.logger.info(f"LocalFileStorageBackend initialized with base_path: {self.base_path}")
    
    def _resolve_path(self, path: str) -> Path:
        """Resolve a relative path against base_path."""
        resolved = self.base_path / path
        return resolved
    
    async def read_text(self, path: str) -> str:
        """Read text content from a file."""
        file_path = self._resolve_path(path)
        try:
            # Use asyncio.to_thread for async file I/O without aiofiles dependency
            content = await asyncio.to_thread(file_path.read_text, encoding="utf-8")
            self.logger.debug(f"Read text from {path}")
            return content
        except FileNotFoundError:
            raise StorageError(f"File not found: {path}")
        except Exception as e:
            raise StorageError(f"Failed to read text from {path}: {e}")
    
    async def write_text(self, path: str, content: str) -> None:
        """Write text content to a file."""
        file_path = self._resolve_path(path)
        try:
            # Ensure parent directory exists
            await asyncio.to_thread(file_path.parent.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(file_path.write_text, content, encoding="utf-8")
            self.logger.debug(f"Wrote text to {path}")
        except Exception as e:
            raise StorageError(f"Failed to write text to {path}: {e}")
    
    async def read_bytes(self, path: str) -> bytes:
        """Read binary content from a file."""
        file_path = self._resolve_path(path)
        try:
            content = await asyncio.to_thread(file_path.read_bytes)
            self.logger.debug(f"Read bytes from {path}")
            return content
        except FileNotFoundError:
            raise StorageError(f"File not found: {path}")
        except Exception as e:
            raise StorageError(f"Failed to read bytes from {path}: {e}")
    
    async def write_bytes(self, path: str, content: bytes) -> None:
        """Write binary content to a file."""
        file_path = self._resolve_path(path)
        try:
            await asyncio.to_thread(file_path.parent.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(file_path.write_bytes, content)
            self.logger.debug(f"Wrote bytes to {path}")
        except Exception as e:
            raise StorageError(f"Failed to write bytes to {path}: {e}")
    
    async def read_json(self, path: str) -> Dict[str, Any]:
        """Read and parse JSON from a file."""
        try:
            content = await self.read_text(path)
            data = json.loads(content)
            self.logger.debug(f"Read JSON from {path}")
            return data
        except json.JSONDecodeError as e:
            raise StorageError(f"Failed to parse JSON from {path}: {e}")
        except Exception as e:
            raise StorageError(f"Failed to read JSON from {path}: {e}")
    
    async def write_json(self, path: str, data: Dict[str, Any]) -> None:
        """Write JSON data to a file."""
        try:
            content = json.dumps(data, indent=2, ensure_ascii=False)
            await self.write_text(path, content)
            self.logger.debug(f"Wrote JSON to {path}")
        except Exception as e:
            raise StorageError(f"Failed to write JSON to {path}: {e}")
    
    async def exists(self, path: str) -> bool:
        """Check if a path exists."""
        file_path = self._resolve_path(path)
        exists = await asyncio.to_thread(file_path.exists)
        return exists
    
    async def list_files(self, path: str, pattern: str = "*") -> List[str]:
        """List files in a directory matching a pattern."""
        dir_path = self._resolve_path(path)
        try:
            if not await asyncio.to_thread(dir_path.exists):
                return []
            
            if not await asyncio.to_thread(dir_path.is_dir):
                raise StorageError(f"Path is not a directory: {path}")
            
            files = await asyncio.to_thread(lambda: [str(f.relative_to(self.base_path)) for f in dir_path.glob(pattern)])
            self.logger.debug(f"Listed {len(files)} files in {path} with pattern {pattern}")
            return files
        except Exception as e:
            raise StorageError(f"Failed to list files in {path}: {e}")
    
    async def copy_file(self, source: str, destination: str) -> None:
        """Copy a file from source to destination."""
        source_path = self._resolve_path(source)
        dest_path = self._resolve_path(destination)
        try:
            await asyncio.to_thread(dest_path.parent.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(shutil.copy2, source_path, dest_path)
            self.logger.debug(f"Copied file from {source} to {destination}")
        except FileNotFoundError:
            raise StorageError(f"Source file not found: {source}")
        except Exception as e:
            raise StorageError(f"Failed to copy file from {source} to {destination}: {e}")
    
    async def ensure_dir(self, path: str) -> None:
        """Ensure a directory exists."""
        dir_path = self._resolve_path(path)
        try:
            await asyncio.to_thread(dir_path.mkdir, parents=True, exist_ok=True)
            self.logger.debug(f"Ensured directory exists: {path}")
        except Exception as e:
            raise StorageError(f"Failed to create directory {path}: {e}")
    
    async def delete(self, path: str) -> None:
        """Delete a file or directory."""
        file_path = self._resolve_path(path)
        try:
            if await asyncio.to_thread(file_path.is_dir):
                await asyncio.to_thread(shutil.rmtree, file_path)
            else:
                await asyncio.to_thread(file_path.unlink)
            self.logger.debug(f"Deleted {path}")
        except FileNotFoundError:
            self.logger.warning(f"Path not found for deletion: {path}")
        except Exception as e:
            raise StorageError(f"Failed to delete {path}: {e}")


class AzureBlobStorageBackend:
    """Azure Blob Storage backend using azure-storage-blob."""
    
    def __init__(
        self,
        connection_string: str,
        container_name: str,
        prefix: Optional[str] = None
    ):
        """
        Initialize Azure Blob Storage backend.
        
        Args:
            connection_string: Azure Storage connection string
            container_name: Container name for blob storage
            prefix: Optional prefix for all blob paths (e.g., "runs/")
        """
        self.logger = get_logger(__name__)
        self.connection_string = connection_string
        self.container_name = container_name
        self.prefix = prefix.rstrip("/") + "/" if prefix else ""
        
        try:
            from azure.storage.blob.aio import BlobServiceClient
            self._blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            self._container_client = self._blob_service_client.get_container_client(container_name)
            self.logger.info(f"AzureBlobStorageBackend initialized: container={container_name}, prefix={self.prefix}")
        except ImportError:
            raise StorageError(
                "azure-storage-blob package not installed. "
                "Install with: pip install azure-storage-blob"
            )
        except Exception as e:
            raise StorageError(f"Failed to initialize Azure Blob Storage: {e}")
    
    def _get_blob_path(self, path: str) -> str:
        """Get full blob path with prefix."""
        # Normalize path separators
        normalized = path.replace("\\", "/")
        return f"{self.prefix}{normalized}"
    
    async def _ensure_container_exists(self) -> None:
        """Ensure the container exists."""
        try:
            await self._container_client.create_container()
            self.logger.info(f"Created container: {self.container_name}")
        except Exception:
            # Container already exists or no permission to create
            pass
    
    async def read_text(self, path: str) -> str:
        """Read text content from a blob."""
        blob_path = self._get_blob_path(path)
        try:
            blob_client = self._container_client.get_blob_client(blob_path)
            download_stream = await blob_client.download_blob()
            content = await download_stream.readall()
            self.logger.debug(f"Read text from blob: {blob_path}")
            return content.decode("utf-8")
        except Exception as e:
            if "BlobNotFound" in str(e):
                raise StorageError(f"Blob not found: {path}")
            raise StorageError(f"Failed to read text from blob {path}: {e}")
    
    async def write_text(self, path: str, content: str) -> None:
        """Write text content to a blob."""
        blob_path = self._get_blob_path(path)
        try:
            from azure.storage.blob import ContentSettings
            await self._ensure_container_exists()
            blob_client = self._container_client.get_blob_client(blob_path)
            await blob_client.upload_blob(
                content.encode("utf-8"),
                overwrite=True,
                content_settings=ContentSettings(content_type="text/plain; charset=utf-8")
            )
            self.logger.debug(f"Wrote text to blob: {blob_path}")
        except Exception as e:
            raise StorageError(f"Failed to write text to blob {path}: {e}")
    
    async def read_bytes(self, path: str) -> bytes:
        """Read binary content from a blob."""
        blob_path = self._get_blob_path(path)
        try:
            blob_client = self._container_client.get_blob_client(blob_path)
            download_stream = await blob_client.download_blob()
            content = await download_stream.readall()
            self.logger.debug(f"Read bytes from blob: {blob_path}")
            return content
        except Exception as e:
            if "BlobNotFound" in str(e):
                raise StorageError(f"Blob not found: {path}")
            raise StorageError(f"Failed to read bytes from blob {path}: {e}")
    
    async def write_bytes(self, path: str, content: bytes) -> None:
        """Write binary content to a blob."""
        blob_path = self._get_blob_path(path)
        try:
            from azure.storage.blob import ContentSettings
            await self._ensure_container_exists()
            blob_client = self._container_client.get_blob_client(blob_path)
            await blob_client.upload_blob(
                content,
                overwrite=True,
                content_settings=ContentSettings(content_type="application/octet-stream")
            )
            self.logger.debug(f"Wrote bytes to blob: {blob_path}")
        except Exception as e:
            raise StorageError(f"Failed to write bytes to blob {path}: {e}")
    
    async def read_json(self, path: str) -> Dict[str, Any]:
        """Read and parse JSON from a blob."""
        try:
            content = await self.read_text(path)
            data = json.loads(content)
            self.logger.debug(f"Read JSON from blob: {path}")
            return data
        except json.JSONDecodeError as e:
            raise StorageError(f"Failed to parse JSON from blob {path}: {e}")
        except Exception as e:
            raise StorageError(f"Failed to read JSON from blob {path}: {e}")
    
    async def write_json(self, path: str, data: Dict[str, Any]) -> None:
        """Write JSON data to a blob."""
        try:
            from azure.storage.blob import ContentSettings
            await self._ensure_container_exists()
            blob_path = self._get_blob_path(path)
            content = json.dumps(data, indent=2, ensure_ascii=False)
            blob_client = self._container_client.get_blob_client(blob_path)
            await blob_client.upload_blob(
                content.encode("utf-8"),
                overwrite=True,
                content_settings=ContentSettings(content_type="application/json; charset=utf-8")
            )
            self.logger.debug(f"Wrote JSON to blob: {blob_path}")
        except Exception as e:
            raise StorageError(f"Failed to write JSON to blob {path}: {e}")
    
    async def exists(self, path: str) -> bool:
        """Check if a blob exists."""
        blob_path = self._get_blob_path(path)
        try:
            blob_client = self._container_client.get_blob_client(blob_path)
            return await blob_client.exists()
        except Exception as e:
            self.logger.warning(f"Failed to check existence of blob {path}: {e}")
            return False
    
    async def list_files(self, path: str, pattern: str = "*") -> List[str]:
        """List blobs with a given prefix."""
        blob_prefix = self._get_blob_path(path) if path else self.prefix
        if blob_prefix and not blob_prefix.endswith("/"):
            blob_prefix += "/"
        
        try:
            blobs = []
            async for blob in self._container_client.list_blobs(name_starts_with=blob_prefix):
                # Remove prefix to return relative paths
                relative_path = blob.name
                if self.prefix and relative_path.startswith(self.prefix):
                    relative_path = relative_path[len(self.prefix):]
                
                # Simple pattern matching (supports "*" wildcard and extensions)
                if pattern == "*":
                    blobs.append(relative_path)
                elif pattern.startswith("*."):
                    # Extension matching like "*.txt"
                    ext = pattern[1:]  # Remove the *
                    if relative_path.endswith(ext):
                        blobs.append(relative_path)
                elif pattern.startswith("*"):
                    # Suffix matching
                    suffix = pattern[1:]
                    if relative_path.endswith(suffix):
                        blobs.append(relative_path)
                else:
                    # Exact or prefix matching
                    if relative_path == pattern or relative_path.startswith(pattern):
                        blobs.append(relative_path)
            
            self.logger.debug(f"Listed {len(blobs)} blobs with prefix {blob_prefix}")
            return blobs
        except Exception as e:
            raise StorageError(f"Failed to list blobs with prefix {path}: {e}")
    
    async def copy_file(self, source: str, destination: str) -> None:
        """Copy a blob from source to destination."""
        source_blob_path = self._get_blob_path(source)
        dest_blob_path = self._get_blob_path(destination)
        
        try:
            await self._ensure_container_exists()
            source_blob_client = self._container_client.get_blob_client(source_blob_path)
            dest_blob_client = self._container_client.get_blob_client(dest_blob_path)
            
            # Copy blob
            source_url = source_blob_client.url
            await dest_blob_client.start_copy_from_url(source_url)
            
            self.logger.debug(f"Copied blob from {source} to {destination}")
        except Exception as e:
            raise StorageError(f"Failed to copy blob from {source} to {destination}: {e}")
    
    async def ensure_dir(self, path: str) -> None:
        """Ensure a directory exists (no-op for blob storage - directories are virtual)."""
        # In blob storage, directories are virtual and created implicitly
        self.logger.debug(f"ensure_dir called for {path} (no-op for Azure Blob)")
        pass
    
    async def delete(self, path: str) -> None:
        """Delete a blob or all blobs with a prefix."""
        blob_path = self._get_blob_path(path)
        try:
            # Try to delete as single blob first
            blob_client = self._container_client.get_blob_client(blob_path)
            await blob_client.delete_blob()
            self.logger.debug(f"Deleted blob: {blob_path}")
        except Exception:
            # If single blob deletion fails, try prefix-based deletion (directory-like)
            try:
                prefix = blob_path if blob_path.endswith("/") else blob_path + "/"
                deleted_count = 0
                async for blob in self._container_client.list_blobs(name_starts_with=prefix):
                    blob_client = self._container_client.get_blob_client(blob.name)
                    await blob_client.delete_blob()
                    deleted_count += 1
                
                if deleted_count > 0:
                    self.logger.debug(f"Deleted {deleted_count} blobs with prefix {prefix}")
                else:
                    self.logger.warning(f"No blobs found for deletion: {path}")
            except Exception as e:
                raise StorageError(f"Failed to delete blob(s) at {path}: {e}")
    
    async def close(self) -> None:
        """Close the blob service client."""
        try:
            await self._blob_service_client.close()
            self.logger.debug("Closed Azure Blob Storage client")
        except Exception as e:
            self.logger.warning(f"Failed to close blob service client: {e}")


class StorageService:
    """
    Unified storage service with pluggable backends.
    
    Factory class that creates and manages storage backends based on configuration.
    """
    
    def __init__(self, backend: StorageBackend):
        """
        Initialize storage service with a specific backend.
        
        Args:
            backend: Storage backend implementation
        """
        self.backend = backend
        self.logger = get_logger(__name__)
    
    @classmethod
    def from_settings(cls, settings) -> "StorageService":
        """
        Create StorageService from application settings.
        
        Args:
            settings: Application settings object
            
        Returns:
            StorageService instance with appropriate backend
        """
        logger = get_logger(__name__)
        storage_backend = getattr(settings, "storage_backend", "local").lower()
        
        if storage_backend == "azure":
            connection_string = getattr(settings, "azure_storage_connection_string", None)
            container_name = getattr(settings, "azure_storage_container", "tf2avm")
            prefix = getattr(settings, "azure_storage_prefix", None)
            
            if not connection_string:
                raise ValueError(
                    "Azure storage backend selected but AZURE_STORAGE_CONNECTION_STRING not set"
                )
            
            logger.info(f"Initializing Azure Blob Storage backend: container={container_name}")
            backend = AzureBlobStorageBackend(
                connection_string=connection_string,
                container_name=container_name,
                prefix=prefix
            )
        else:
            # Default to local filesystem
            base_path = getattr(settings, "storage_local_base_path", None)
            logger.info(f"Initializing Local File Storage backend: base_path={base_path or 'cwd'}")
            backend = LocalFileStorageBackend(base_path=base_path)
        
        return cls(backend)
    
    # Delegate all operations to the backend
    async def read_text(self, path: str) -> str:
        """Read text content from storage."""
        return await self.backend.read_text(path)
    
    async def write_text(self, path: str, content: str) -> None:
        """Write text content to storage."""
        await self.backend.write_text(path, content)
    
    async def read_bytes(self, path: str) -> bytes:
        """Read binary content from storage."""
        return await self.backend.read_bytes(path)
    
    async def write_bytes(self, path: str, content: bytes) -> None:
        """Write binary content to storage."""
        await self.backend.write_bytes(path, content)
    
    async def read_json(self, path: str) -> Dict[str, Any]:
        """Read and parse JSON from storage."""
        return await self.backend.read_json(path)
    
    async def write_json(self, path: str, data: Dict[str, Any]) -> None:
        """Write JSON data to storage."""
        await self.backend.write_json(path, data)
    
    async def exists(self, path: str) -> bool:
        """Check if a path exists in storage."""
        return await self.backend.exists(path)
    
    async def list_files(self, path: str, pattern: str = "*") -> List[str]:
        """List files in storage matching a pattern."""
        return await self.backend.list_files(path, pattern)
    
    async def copy_file(self, source: str, destination: str) -> None:
        """Copy a file within storage."""
        await self.backend.copy_file(source, destination)
    
    async def ensure_dir(self, path: str) -> None:
        """Ensure a directory exists in storage."""
        await self.backend.ensure_dir(path)
    
    async def delete(self, path: str) -> None:
        """Delete a file or directory from storage."""
        await self.backend.delete(path)
