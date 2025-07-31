import hashlib
import json
import time
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import pickle

class CacheManager:
    """
    Manages caching for content analysis results to improve performance and reduce API costs.
    """
    
    def __init__(self, cache_dir: str = "cache", max_cache_size_mb: int = 100, default_ttl_hours: int = 24):
        """
        Initialize the cache manager.
        
        Args:
            cache_dir: Directory to store cache files
            max_cache_size_mb: Maximum cache size in MB
            default_ttl_hours: Default time-to-live for cache entries in hours
        """
        self.cache_dir = cache_dir
        self.max_cache_size_bytes = max_cache_size_mb * 1024 * 1024
        self.default_ttl = timedelta(hours=default_ttl_hours)
        self.metadata_file = os.path.join(cache_dir, "cache_metadata.json")
        
        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)
        
        # Load or initialize metadata
        self.metadata = self._load_metadata()
        
        # Clean expired entries on initialization
        self._cleanup_expired()
    
    def get_cache_key(self, content: str, analysis_type: str = "general") -> str:
        """
        Generate a unique cache key for content and analysis type.
        
        Args:
            content: Content to analyze
            analysis_type: Type of analysis
            
        Returns:
            SHA256 hash as cache key
        """
        # Normalize content (remove extra whitespace, convert to lowercase)
        normalized_content = ' '.join(content.lower().split())
        key_data = f"{normalized_content}_{analysis_type}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached analysis result.
        
        Args:
            cache_key: Cache key to look up
            
        Returns:
            Cached result or None if not found/expired
        """
        if cache_key not in self.metadata:
            return None
        
        entry_info = self.metadata[cache_key]
        
        # Check if entry is expired
        if self._is_expired(entry_info):
            self.delete(cache_key)
            return None
        
        # Try to load the cached result
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        try:
            with open(cache_file, 'rb') as f:
                result = pickle.load(f)
            
            # Update access time
            self.metadata[cache_key]['last_accessed'] = datetime.now().isoformat()
            self._save_metadata()
            
            return result
        except (FileNotFoundError, pickle.PickleError, Exception):
            # If file is corrupted or missing, remove from metadata
            self.delete(cache_key)
            return None
    
    def set(self, cache_key: str, result: Dict[str, Any], ttl_hours: Optional[int] = None) -> bool:
        """
        Store analysis result in cache.
        
        Args:
            cache_key: Cache key
            result: Analysis result to cache
            ttl_hours: Time-to-live in hours (uses default if None)
            
        Returns:
            True if successfully cached, False otherwise
        """
        try:
            # Check cache size limits before adding
            if not self._ensure_cache_space():
                return False
            
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
            
            # Save the result
            with open(cache_file, 'wb') as f:
                pickle.dump(result, f)
            
            # Get file size
            file_size = os.path.getsize(cache_file)
            
            # Update metadata
            ttl = timedelta(hours=ttl_hours) if ttl_hours else self.default_ttl
            expires_at = datetime.now() + ttl
            
            self.metadata[cache_key] = {
                'created_at': datetime.now().isoformat(),
                'last_accessed': datetime.now().isoformat(),
                'expires_at': expires_at.isoformat(),
                'size_bytes': file_size,
                'hits': 0
            }
            
            self._save_metadata()
            return True
            
        except Exception as e:
            # Clean up partially created files
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
            if os.path.exists(cache_file):
                os.remove(cache_file)
            return False
    
    def delete(self, cache_key: str) -> bool:
        """
        Delete a cached entry.
        
        Args:
            cache_key: Cache key to delete
            
        Returns:
            True if deleted, False if not found
        """
        if cache_key not in self.metadata:
            return False
        
        # Remove file
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        try:
            if os.path.exists(cache_file):
                os.remove(cache_file)
        except OSError:
            pass  # File might already be deleted
        
        # Remove from metadata
        del self.metadata[cache_key]
        self._save_metadata()
        return True
    
    def clear(self) -> int:
        """
        Clear all cached entries.
        
        Returns:
            Number of entries cleared
        """
        count = len(self.metadata)
        
        # Remove all cache files
        for cache_key in list(self.metadata.keys()):
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
            try:
                if os.path.exists(cache_file):
                    os.remove(cache_file)
            except OSError:
                pass
        
        # Clear metadata
        self.metadata = {}
        self._save_metadata()
        
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_entries = len(self.metadata)
        total_size = sum(entry.get('size_bytes', 0) for entry in self.metadata.values())
        total_hits = sum(entry.get('hits', 0) for entry in self.metadata.values())
        
        # Count expired entries
        expired_count = sum(
            1 for entry in self.metadata.values()
            if self._is_expired(entry)
        )
        
        return {
            'total_entries': total_entries,
            'active_entries': total_entries - expired_count,
            'expired_entries': expired_count,
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'total_hits': total_hits,
            'cache_efficiency': (total_hits / max(total_entries, 1)) * 100,
            'max_size_mb': self.max_cache_size_bytes / (1024 * 1024)
        }
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load cache metadata from file."""
        try:
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_metadata(self):
        """Save cache metadata to file."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception:
            pass  # Fail silently for metadata save errors
    
    def _is_expired(self, entry_info: Dict[str, Any]) -> bool:
        """Check if a cache entry is expired."""
        try:
            expires_at = datetime.fromisoformat(entry_info['expires_at'])
            return datetime.now() > expires_at
        except (KeyError, ValueError):
            return True  # Treat malformed entries as expired
    
    def _cleanup_expired(self):
        """Remove expired cache entries."""
        expired_keys = [
            key for key, entry in self.metadata.items()
            if self._is_expired(entry)
        ]
        
        for key in expired_keys:
            self.delete(key)
    
    def _ensure_cache_space(self) -> bool:
        """
        Ensure there's enough space in cache by removing oldest entries if needed.
        
        Returns:
            True if space is available, False if cache is full and can't be cleaned
        """
        current_size = sum(entry.get('size_bytes', 0) for entry in self.metadata.values())
        
        if current_size >= self.max_cache_size_bytes:
            # Remove oldest entries (by last_accessed) until we have space
            entries_by_access = sorted(
                self.metadata.items(),
                key=lambda x: x[1].get('last_accessed', '1970-01-01')
            )
            
            for cache_key, entry_info in entries_by_access:
                self.delete(cache_key)
                current_size -= entry_info.get('size_bytes', 0)
                
                if current_size < self.max_cache_size_bytes * 0.8:  # Leave some headroom
                    break
            else:
                # If we still don't have space after removing all entries
                return current_size < self.max_cache_size_bytes
        
        return True