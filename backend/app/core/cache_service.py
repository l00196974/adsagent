"""
缓存服务 - 提供TTL缓存机制

用于缓存频繁访问的数据，减少数据库查询
"""

import time
from typing import Any, Optional, Dict, Callable
from functools import wraps
from collections import OrderedDict
from threading import Lock
import hashlib
import json

from app.core.logger import app_logger


class CacheService:
    """简单的内存缓存服务（支持LRU驱逐和容量限制）"""

    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        """
        Args:
            default_ttl: 默认缓存过期时间（秒），默认5分钟
            max_size: 最大缓存条目数，默认1000
        """
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值或None（如果不存在或已过期）
        """
        with self._lock:
            if key not in self.cache:
                return None

            entry = self.cache[key]
            if time.time() > entry["expires_at"]:
                # 缓存已过期，删除
                del self.cache[key]
                return None

            # LRU: 移到末尾表示最近使用
            self.cache.move_to_end(key)
            app_logger.debug(f"缓存命中: {key}")
            return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None使用默认值
        """
        if ttl is None:
            ttl = self.default_ttl

        with self._lock:
            # 达到容量限制时，驱逐最旧的条目（LRU）
            if len(self.cache) >= self.max_size and key not in self.cache:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                app_logger.debug(f"缓存已满，驱逐最旧条目: {oldest_key}")

            self.cache[key] = {
                "value": value,
                "expires_at": time.time() + ttl,
                "created_at": time.time()
            }

            # 移到末尾表示最新
            self.cache.move_to_end(key)
            app_logger.debug(f"缓存设置: {key}, TTL={ttl}秒")

    def delete(self, key: str) -> None:
        """删除缓存

        Args:
            key: 缓存键
        """
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                app_logger.debug(f"缓存删除: {key}")

    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            count = len(self.cache)
            self.cache.clear()
            app_logger.info(f"缓存已清空: {count}个条目")

    def cleanup_expired(self) -> int:
        """清理过期缓存

        Returns:
            清理的条目数
        """
        with self._lock:
            now = time.time()
            expired_keys = [
                key for key, entry in self.cache.items()
                if now > entry["expires_at"]
            ]

            for key in expired_keys:
                del self.cache[key]

            if expired_keys:
                app_logger.info(f"清理过期缓存: {len(expired_keys)}个条目")

            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息

        Returns:
            统计信息字典
        """
        with self._lock:
            now = time.time()
            active_count = sum(
                1 for entry in self.cache.values()
                if now <= entry["expires_at"]
            )
            expired_count = len(self.cache) - active_count

            return {
                "total_entries": len(self.cache),
                "active_entries": active_count,
                "expired_entries": expired_count,
                "default_ttl": self.default_ttl,
                "max_size": self.max_size
            }

    @staticmethod
    def make_key(*args, **kwargs) -> str:
        """生成缓存键

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            缓存键字符串
        """
        # 将参数序列化为JSON字符串
        key_data = {
            "args": args,
            "kwargs": kwargs
        }
        key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)

        # 使用MD5生成短键
        return hashlib.md5(key_str.encode()).hexdigest()


# 全局缓存实例（默认TTL=5分钟，最大1000条目）
_cache_service = CacheService(default_ttl=300, max_size=1000)


def get_cache_service() -> CacheService:
    """获取全局缓存服务实例"""
    return _cache_service


def cached(ttl: Optional[int] = None, key_prefix: str = ""):
    """缓存装饰器

    Args:
        ttl: 缓存过期时间（秒），None使用默认值
        key_prefix: 缓存键前缀

    Example:
        @cached(ttl=60, key_prefix="user_profile")
        def get_user_profile(user_id: str):
            # 查询数据库
            return profile
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache_service()

            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{CacheService.make_key(*args, **kwargs)}"

            # 尝试从缓存获取
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # 执行函数
            result = func(*args, **kwargs)

            # 存入缓存
            cache.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator


class SequenceCacheService:
    """序列挖掘专用缓存服务"""

    def __init__(self, cache_service: Optional[CacheService] = None):
        self.cache = cache_service or get_cache_service()

    def get_sequences(self, limit: int = 1000) -> Optional[Any]:
        """获取缓存的序列数据

        Args:
            limit: 序列数量限制

        Returns:
            序列列表或None
        """
        key = f"sequences:limit_{limit}"
        return self.cache.get(key)

    def set_sequences(self, sequences: Any, limit: int = 1000, ttl: int = 300) -> None:
        """缓存序列数据

        Args:
            sequences: 序列列表
            limit: 序列数量限制
            ttl: 过期时间（秒）
        """
        key = f"sequences:limit_{limit}"
        self.cache.set(key, sequences, ttl)

    def get_patterns(self, min_support: int, max_length: int) -> Optional[Any]:
        """获取缓存的模式数据

        Args:
            min_support: 最小支持度
            max_length: 最大长度

        Returns:
            模式列表或None
        """
        key = f"patterns:support_{min_support}_length_{max_length}"
        return self.cache.get(key)

    def set_patterns(self, patterns: Any, min_support: int, max_length: int, ttl: int = 600) -> None:
        """缓存模式数据

        Args:
            patterns: 模式列表
            min_support: 最小支持度
            max_length: 最大长度
            ttl: 过期时间（秒）
        """
        key = f"patterns:support_{min_support}_length_{max_length}"
        self.cache.set(key, patterns, ttl)

    def invalidate_sequences(self) -> None:
        """使序列缓存失效"""
        # 简单实现：清空所有缓存
        # 更好的实现：只清空sequences相关的缓存
        self.cache.clear()

    def invalidate_patterns(self) -> None:
        """使模式缓存失效"""
        # 简单实现：清空所有缓存
        self.cache.clear()
