"""
内存监控工具

提供内存使用监控、警告和限制功能
"""
import psutil
import os
from typing import Dict, Optional
from app.core.logger import app_logger


class MemoryMonitor:
    """内存监控器"""

    def __init__(self, warning_threshold_mb: int = 2048, critical_threshold_mb: int = 4096):
        """
        初始化内存监控器

        Args:
            warning_threshold_mb: 警告阈值 (MB)
            critical_threshold_mb: 严重阈值 (MB)
        """
        self.warning_threshold = warning_threshold_mb * 1024 * 1024  # 转换为字节
        self.critical_threshold = critical_threshold_mb * 1024 * 1024
        self.process = psutil.Process(os.getpid())

    def get_memory_usage(self) -> Dict[str, float]:
        """
        获取当前进程的内存使用情况

        Returns:
            包含内存使用信息的字典:
            - rss_mb: 物理内存使用 (MB)
            - vms_mb: 虚拟内存使用 (MB)
            - percent: 内存使用百分比
        """
        mem_info = self.process.memory_info()
        mem_percent = self.process.memory_percent()

        return {
            "rss_mb": mem_info.rss / (1024 * 1024),
            "vms_mb": mem_info.vms / (1024 * 1024),
            "percent": mem_percent
        }

    def check_memory(self) -> Optional[str]:
        """
        检查内存使用情况并返回警告信息

        Returns:
            如果超过阈值,返回警告信息;否则返回None
        """
        mem_info = self.process.memory_info()
        rss_bytes = mem_info.rss

        if rss_bytes >= self.critical_threshold:
            msg = f"严重警告: 内存使用达到 {rss_bytes / (1024 * 1024):.1f} MB (阈值: {self.critical_threshold / (1024 * 1024):.1f} MB)"
            app_logger.error(msg)
            return msg
        elif rss_bytes >= self.warning_threshold:
            msg = f"警告: 内存使用达到 {rss_bytes / (1024 * 1024):.1f} MB (阈值: {self.warning_threshold / (1024 * 1024):.1f} MB)"
            app_logger.warning(msg)
            return msg

        return None

    def log_memory_usage(self, context: str = ""):
        """
        记录当前内存使用情况

        Args:
            context: 上下文信息 (例如: "开始挖掘", "完成挖掘")
        """
        usage = self.get_memory_usage()
        app_logger.info(
            f"内存使用 [{context}]: "
            f"RSS={usage['rss_mb']:.1f}MB, "
            f"VMS={usage['vms_mb']:.1f}MB, "
            f"Percent={usage['percent']:.1f}%"
        )

    def is_memory_critical(self) -> bool:
        """
        检查内存是否达到严重阈值

        Returns:
            如果达到严重阈值返回True
        """
        mem_info = self.process.memory_info()
        return mem_info.rss >= self.critical_threshold


# 全局实例 (2GB警告, 4GB严重)
memory_monitor = MemoryMonitor(warning_threshold_mb=2048, critical_threshold_mb=4096)
