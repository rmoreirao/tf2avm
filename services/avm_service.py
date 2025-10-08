import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from config.logging import get_logger
from config.settings import get_settings
from agents.avm_knowledge_agent import AVMKnowledgeAgent
from agents.avm_resource_details_agent import AVMResourceDetailsAgent
from schemas.models import AVMKnowledgeAgentResult, AVMResourceDetailsAgentResult


class AVMService:
    """
    AVMService - Wrapper service for AVM Agents with caching functionality.
    
    This service provides a unified interface to all AVM agents while implementing
    a local file-based cache to improve performance and reduce API calls.
    """
    
    def __init__(self, cache_enabled: bool = True, cache_ttl: int = 3000000):
        """
        Initialize the AVM Service.
        
        Args:
            cache_enabled: Whether to use caching functionality
            cache_ttl: Time to live for cache entries in seconds (default: 24 hours)
        """
        self.logger = get_logger(__name__)
        self.settings = get_settings()
        self.cache_enabled = cache_enabled
        self.cache_dir = Path("localCache")
        self.cache_ttl = cache_ttl
        
        # Create cache directory if it doesn't exist
        if self.cache_enabled:
            self.cache_dir.mkdir(exist_ok=True)
            self.logger.info(f"Cache directory initialized: {self.cache_dir}")
        
        # Initialize agents as None - will be created when needed
        self._avm_knowledge_agent: Optional[AVMKnowledgeAgent] = None
        self._avm_resource_details_agent: Optional[AVMResourceDetailsAgent] = None
    
    async def _get_avm_knowledge_agent(self) -> AVMKnowledgeAgent:
        """Get or create the AVM Knowledge Agent."""
        if self._avm_knowledge_agent is None:
            self._avm_knowledge_agent = await AVMKnowledgeAgent.create()
        return self._avm_knowledge_agent
    
    async def _get_avm_resource_details_agent(self) -> AVMResourceDetailsAgent:
        """Get or create the AVM Resource Details Agent."""
        if self._avm_resource_details_agent is None:
            self._avm_resource_details_agent = await AVMResourceDetailsAgent.create()
        return self._avm_resource_details_agent
    
    def _is_cache_valid(self, cache_file: Path) -> bool:
        """
        Check if a cache file exists and is still valid based on TTL.
        
        Args:
            cache_file: Path to the cache file
            
        Returns:
            True if cache is valid, False otherwise
        """
        if not cache_file.exists():
            return False
        
        # Check if file is within TTL
        file_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
        expiry_time = file_mtime + timedelta(seconds=self.cache_ttl)
        
        is_valid = datetime.now() < expiry_time
        
        if not is_valid:
            self.logger.debug(f"Cache file expired: {cache_file}")
        
        return is_valid
    
    def _load_cache(self, cache_file: Path) -> Optional[dict]:
        """
        Load data from cache file.
        
        Args:
            cache_file: Path to the cache file
            
        Returns:
            Cached data as dict or None if loading fails
        """
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.logger.debug(f"Cache hit: {cache_file}")
            return data
        except (json.JSONDecodeError, IOError) as e:
            self.logger.warning(f"Failed to load cache file {cache_file}: {e}")
            return None
    
    def _save_cache(self, cache_file: Path, data: dict) -> bool:
        """
        Save data to cache file.
        
        Args:
            cache_file: Path to the cache file
            data: Data to cache
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Cache saved: {cache_file}")
            return True
        except (IOError, TypeError) as e:
            self.logger.warning(f"Failed to save cache file {cache_file}: {e}")
            return False
    
    def _get_module_cache_filename(self, module_name: str, module_version: str) -> str:
        """
        Generate cache filename for AVM module details.
        
        Args:
            module_name: Name of the AVM module
            module_version: Version of the module
            
        Returns:
            Cache filename with version dots replaced by dashes
        """
        # Replace dots with dashes in version
        version_sanitized = module_version.replace(".", "-")
        return f"{module_name}_{version_sanitized}.json"
    
    async def fetch_avm_knowledge(self, use_cache: bool = True) -> AVMKnowledgeAgentResult:
        """
        Fetch AVM module knowledge from official sources.
        
        Args:
            use_cache: Whether to use cached data if available
            
        Returns:
            AVMKnowledgeAgentResult containing AVM modules information
        """
        cache_file = self.cache_dir / "avm_knowledge.json"
        
        # Try to load from cache first
        if use_cache and self.cache_enabled and self._is_cache_valid(cache_file):
            cached_data = self._load_cache(cache_file)
            if cached_data:
                try:
                    result = AVMKnowledgeAgentResult.model_validate(cached_data)
                    self.logger.info("AVM knowledge loaded from cache")
                    return result
                except Exception as e:
                    self.logger.warning(f"Failed to validate cached AVM knowledge: {e}")
        
        # Cache miss or disabled - fetch from agent
        self.logger.info("Fetching AVM knowledge from agent")
        agent = await self._get_avm_knowledge_agent()
        result: AVMKnowledgeAgentResult = await agent.fetch_avm_knowledge()

        # enrich each module with detailed info
        for module in result.modules:
            detail: AVMResourceDetailsAgentResult = await self.fetch_avm_resource_details(module.name, module.version, use_cache=True)  # Pre-fetch and cache each
            module.description = detail.module.description
            module.resources = detail.module.resources

        # Save to cache if enabled
        if self.cache_enabled:
            self._save_cache(cache_file, result.model_dump())
        
        self.logger.info(f"AVM knowledge fetched successfully: {len(result.modules)} modules")
        return result
    
    async def fetch_avm_resource_details(self, module_name: str, module_version: str, use_cache: bool = True) -> AVMResourceDetailsAgentResult:
        """
        Fetch AVM module details from Terraform Registry.
        
        Args:
            module_name: Name of the AVM module
            module_version: Version of the module
            use_cache: Whether to use cached data if available
            
        Returns:
            AVMResourceDetailsAgentResult containing detailed module information
        """
        cache_filename = self._get_module_cache_filename(module_name, module_version)
        cache_file = self.cache_dir / cache_filename
        
        # Try to load from cache first
        if use_cache and self.cache_enabled and self._is_cache_valid(cache_file):
            cached_data = self._load_cache(cache_file)
            if cached_data:
                try:
                    result = AVMResourceDetailsAgentResult.model_validate(cached_data)
                    self.logger.info(f"AVM module details loaded from cache: {module_name}@{module_version}")
                    return result
                except Exception as e:
                    self.logger.warning(f"Failed to validate cached module details for {module_name}@{module_version}: {e}")
        
        # Cache miss or disabled - fetch from agent
        self.logger.info(f"Fetching AVM module details from agent: {module_name}@{module_version}")
        agent = await self._get_avm_resource_details_agent()
        result = await agent.fetch_avm_resource_details(module_name, module_version)
        
        # Save to cache if enabled
        if self.cache_enabled:
            self._save_cache(cache_file, result.model_dump())
        
        self.logger.info(f"AVM module details fetched successfully: {module_name}@{module_version}")
        return result
    
    def clear_cache(self) -> bool:
        """
        Clear all cached data.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.cache_dir.exists():
                self.logger.info("Cache directory doesn't exist, nothing to clear")
                return True
            
            deleted_count = 0
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
                deleted_count += 1
            
            self.logger.info(f"Cache cleared: {deleted_count} files deleted")
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear cache: {e}")
            return False
    
    def clear_module_cache(self, module_name: str, module_version: str) -> bool:
        """
        Clear cache for a specific module.
        
        Args:
            module_name: Name of the AVM module
            module_version: Version of the module
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cache_filename = self._get_module_cache_filename(module_name, module_version)
            cache_file = self.cache_dir / cache_filename
            
            if cache_file.exists():
                cache_file.unlink()
                self.logger.info(f"Module cache cleared: {module_name}@{module_version}")
            else:
                self.logger.info(f"No cache found for module: {module_name}@{module_version}")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear module cache for {module_name}@{module_version}: {e}")
            return False
    
    def get_cache_info(self) -> dict:
        """
        Get information about the current cache state.
        
        Returns:
            Dictionary containing cache statistics
        """
        if not self.cache_enabled:
            return {"cache_enabled": False}
        
        cache_info = {
            "cache_enabled": True,
            "cache_directory": str(self.cache_dir),
            "cache_ttl_seconds": self.cache_ttl,
            "files": []
        }
        
        if self.cache_dir.exists():
            for cache_file in self.cache_dir.glob("*.json"):
                file_stat = cache_file.stat()
                file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
                is_valid = self._is_cache_valid(cache_file)
                
                cache_info["files"].append({
                    "filename": cache_file.name,
                    "size_bytes": file_stat.st_size,
                    "modified": file_mtime.isoformat(),
                    "is_valid": is_valid
                })
        
        return cache_info