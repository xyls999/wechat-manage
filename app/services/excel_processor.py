import pandas as pd
import os
from typing import Dict, Any, List
from datetime import datetime
import uuid

class ExcelProcessor:
    """Excel文件处理器：按会计月汇总数据"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.df = None
        
    def load_file(self):
        """加载Excel文件"""
        try:
            self.df = pd.read_excel(self.file_path, engine='openpyxl')
            return True
        except Exception as e:
            raise ValueError(f"文件读取失败: {str(e)}")
    
    def process_by_accounting_month(self) -> Dict[str, Any]:
        """
        按会计月汇总数据
        核心逻辑：
        1. 找到"会计月"列的位置
        2. 获取会计月列之后的所有列
        3. 识别其中可以汇总的数值列
        4. 按会计月分组，对数值列求和
        5. 保持会计月列+所有汇总后的数值列
        """
        if self.df is None:
            raise ValueError("请先加载文件")
        
        # 查找会计月列（可能的列名）
        accounting_month_col = None
        accounting_month_index = -1
        possible_names = ['会计月', '会计期间', '月份', '期间']
        
        for idx, col in enumerate(self.df.columns):
            if any(name in str(col) for name in possible_names):
                accounting_month_col = col
                accounting_month_index = idx
                break
        
        if accounting_month_col is None:
            raise ValueError("未找到'会计月'列，请确保Excel中包含该字段")
        
        # 获取会计月列之后的所有列
        all_cols_after_month = list(self.df.columns[accounting_month_index + 1:])
        
        if not all_cols_after_month:
            raise ValueError("会计月列之后没有数据列")
        
        # 识别数值列（会计月之后的列中，可以转换为数值的列）
        numeric_cols = []
        for col in all_cols_after_month:
            try:
                # 尝试转换为数值
                converted = pd.to_numeric(self.df[col], errors='coerce')
                # 如果至少有一个非空数值，就认为是数值列
                if converted.notna().any():
                    numeric_cols.append(col)
                    # 转换该列为float类型，NaN填充为0
                    self.df[col] = converted.fillna(0)
            except:
                # 转换失败，跳过该列
                continue
        
        if not numeric_cols:
            raise ValueError("会计月之后未找到可汇总的数值列")
        
        # 按会计月分组汇总所有数值列
        grouped_df = self.df.groupby(accounting_month_col, as_index=False)[numeric_cols].sum()
        
        # 重命名会计月列为统一名称（保持原列名）
        # grouped_df = grouped_df.rename(columns={accounting_month_col: '会计月'})
        
        # 生成汇总信息
        summary = {
            "totalRows": len(self.df),
            "groupedRows": len(grouped_df),
            "columns": list(grouped_df.columns),
            "accountingMonthCol": accounting_month_col,
            "numericCols": numeric_cols,
            "totalNumericCols": len(numeric_cols)
        }
        
        return {
            "df": grouped_df,
            "summary": summary
        }
    
    def save_processed_file(self, output_path: str, processed_df: pd.DataFrame) -> str:
        """保存处理后的文件"""
        try:
            processed_df.to_excel(output_path, index=False, engine='openpyxl')
            return output_path
        except Exception as e:
            raise ValueError(f"文件保存失败: {str(e)}")
    
    def preview_data(self, df: pd.DataFrame = None, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """预览数据"""
        if df is None:
            df = self.df
        
        if df is None:
            raise ValueError("没有可预览的数据")
        
        # 计算分页
        total = len(df)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        # 获取分页数据
        page_df = df.iloc[start_idx:end_idx]
        
        # 转换为字典列表
        rows = page_df.to_dict('records')
        
        # 处理NaN值
        for row in rows:
            for key, value in row.items():
                if pd.isna(value):
                    row[key] = 0 if isinstance(value, (int, float)) else ""
        
        return {
            "columns": list(df.columns),
            "rows": rows,
            "total": total,
            "page": page,
            "pageSize": page_size
        }
