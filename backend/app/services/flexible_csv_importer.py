"""
灵活的CSV导入器 - 支持任意格式的CSV文件

核心特性:
- 只要求必需列 (user_id, timestamp/event_time)
- 其他列自动打包为event_data
- 支持多种数据格式
"""

import pandas as pd
import json
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

from app.core.flexible_persistence import FlexiblePersistence
from app.core.data_parser import DataParser
from app.core.logger import app_logger


class FlexibleCSVImporter:
    """灵活的CSV导入器"""

    def __init__(self, db_path: str = "data/graph.db"):
        self.persistence = FlexiblePersistence(db_path)

    def import_behavior_data(
        self,
        csv_file: str,
        batch_size: int = 10000
    ) -> Dict[str, Any]:
        """导入行为数据CSV

        必需列:
        - user_id: 用户ID（结构化）
        - event_time 或 timestamp: 事件时间（结构化）

        其他列（包括event_type/action）:
        - 全部打包为event_data（非结构化文本）

        Args:
            csv_file: CSV文件路径
            batch_size: 批量插入大小

        Returns:
            导入结果统计
        """
        app_logger.info(f"开始导入行为数据: {csv_file}")

        # 读取CSV
        df = pd.read_csv(csv_file)
        total_rows = len(df)

        # 验证必需列
        if "user_id" not in df.columns:
            raise ValueError("缺少必需列: user_id")

        # 时间列（支持多种命名）
        time_col = None
        for col in ["event_time", "timestamp", "time", "datetime"]:
            if col in df.columns:
                time_col = col
                break

        if not time_col:
            raise ValueError("缺少时间列: event_time, timestamp, time 或 datetime")

        # 准备批量插入数据
        batch_data = []
        success_count = 0
        error_count = 0

        for idx, row in df.iterrows():
            try:
                # 提取结构化字段（只有user_id和event_time）
                user_id = str(row["user_id"])
                event_time = row[time_col]

                # 转换时间格式
                if isinstance(event_time, str):
                    try:
                        event_time = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
                    except:
                        event_time = pd.to_datetime(event_time)

                # 所有其他列（包括event_type/action）都打包为event_data
                excluded_cols = {"user_id", time_col}

                other_data = {}
                for col in df.columns:
                    if col not in excluded_cols and pd.notna(row[col]):
                        other_data[col] = row[col]

                        # 转换numpy类型为Python原生类型
                        if hasattr(other_data[col], 'item'):
                            other_data[col] = other_data[col].item()

                event_data = json.dumps(other_data, ensure_ascii=False)

                batch_data.append({
                    "user_id": user_id,
                    "event_time": event_time,
                    "event_data": event_data
                })

                # 批量插入
                if len(batch_data) >= batch_size:
                    inserted = self.persistence.batch_insert_behavior_events(batch_data)
                    success_count += inserted
                    batch_data = []
                    app_logger.info(f"已导入 {success_count}/{total_rows} 条记录")

            except Exception as e:
                app_logger.error(f"导入第 {idx+1} 行失败: {e}")
                error_count += 1

        # 插入剩余数据
        if batch_data:
            inserted = self.persistence.batch_insert_behavior_events(batch_data)
            success_count += inserted

        app_logger.info(f"行为数据导入完成: 成功 {success_count}, 失败 {error_count}")

        return {
            "total": total_rows,
            "success": success_count,
            "error": error_count
        }

    def import_user_profiles(
        self,
        csv_file: str,
        batch_size: int = 10000
    ) -> Dict[str, Any]:
        """导入用户画像CSV

        必需列:
        - user_id: 用户ID

        可选列:
        - 其他任意列: 自动打包为profile_data

        Args:
            csv_file: CSV文件路径
            batch_size: 批量插入大小

        Returns:
            导入结果统计
        """
        app_logger.info(f"开始导入用户画像: {csv_file}")

        # 读取CSV
        df = pd.read_csv(csv_file)
        total_rows = len(df)

        # 验证必需列
        if "user_id" not in df.columns:
            raise ValueError("缺少必需列: user_id")

        # 准备批量插入数据
        batch_data = []
        success_count = 0
        error_count = 0

        for idx, row in df.iterrows():
            try:
                # 提取user_id
                user_id = str(row["user_id"])

                # 其他列打包为profile_data
                profile_dict = {}
                for col in df.columns:
                    if col != "user_id" and pd.notna(row[col]):
                        profile_dict[col] = row[col]

                        # 转换numpy类型为Python原生类型
                        if hasattr(profile_dict[col], 'item'):
                            profile_dict[col] = profile_dict[col].item()

                profile_data = json.dumps(profile_dict, ensure_ascii=False)

                batch_data.append({
                    "user_id": user_id,
                    "profile_data": profile_data,
                    "profile_version": 1
                })

                # 批量插入
                if len(batch_data) >= batch_size:
                    inserted = self.persistence.batch_upsert_user_profiles(batch_data)
                    success_count += inserted
                    batch_data = []
                    app_logger.info(f"已导入 {success_count}/{total_rows} 条记录")

            except Exception as e:
                app_logger.error(f"导入第 {idx+1} 行失败: {e}")
                error_count += 1

        # 插入剩余数据
        if batch_data:
            inserted = self.persistence.batch_upsert_user_profiles(batch_data)
            success_count += inserted

        app_logger.info(f"用户画像导入完成: 成功 {success_count}, 失败 {error_count}")

        return {
            "total": total_rows,
            "success": success_count,
            "error": error_count
        }

    def export_behavior_data(
        self,
        output_file: str,
        user_id: str = None,
        limit: int = 100000
    ) -> int:
        """导出行为数据为CSV

        Args:
            output_file: 输出文件路径
            user_id: 用户ID过滤（可选）
            limit: 导出数量限制

        Returns:
            导出的记录数
        """
        app_logger.info(f"开始导出行为数据到: {output_file}")

        # 查询数据（不解析）
        events = self.persistence.query_behavior_events(
            user_id=user_id,
            limit=limit,
            parse=False
        )

        if not events:
            app_logger.warning("没有数据可导出")
            return 0

        # 构建DataFrame
        rows = []
        for event in events:
            row = {
                "user_id": event["user_id"],
                "event_time": event["event_time"],
            }

            # 解析event_data并展开
            try:
                event_data = json.loads(event["event_data_raw"])
                row.update(event_data)
            except:
                row["event_data"] = event["event_data_raw"]

            rows.append(row)

        df = pd.DataFrame(rows)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')

        app_logger.info(f"导出完成: {len(rows)} 条记录")
        return len(rows)

    def export_user_profiles(
        self,
        output_file: str,
        limit: int = 100000
    ) -> int:
        """导出用户画像为CSV

        Args:
            output_file: 输出文件路径
            limit: 导出数量限制

        Returns:
            导出的记录数
        """
        app_logger.info(f"开始导出用户画像到: {output_file}")

        # 查询所有用户（需要分页）
        with self.persistence._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, profile_data
                FROM user_profiles_v2
                LIMIT ?
            """, (limit,))

            rows = []
            for row in cursor.fetchall():
                user_id = row[0]
                profile_data_raw = row[1]

                profile_row = {"user_id": user_id}

                # 解析profile_data并展开
                try:
                    profile_data = json.loads(profile_data_raw)
                    profile_row.update(profile_data)
                except:
                    profile_row["profile_data"] = profile_data_raw

                rows.append(profile_row)

        if not rows:
            app_logger.warning("没有数据可导出")
            return 0

        df = pd.DataFrame(rows)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')

        app_logger.info(f"导出完成: {len(rows)} 条记录")
        return len(rows)
