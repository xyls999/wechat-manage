import pandas as pd
import os

# 创建测试数据（模拟你提供的Excel数据）
data = {
    '税率': ['17.00%', '16.00%', '13.00%', '17.00%', '16.00%', '13.00%'],
    '会计月': ['202501', '202501', '202501', '202502', '202502', '202502'],
    '供应商编码': ['00002', '00002', '00002', '00003', '00003', '00003'],
    '期初数量': [700, 0, 0, 500, 200, 0],
    '无税期初金额': [25695.57, 0, 0, 18000.00, 8000.00, 0],
    '期初金额': [29036, 0, 0, 21000, 9200, 0],
    '入库数量': [500, 740, 0, 600, 300, 100],
    '入库金额': [18500, 27800, 0, 22000, 11000, 3500],
    '无税入库金额': [15811.97, 23965.52, 0, 18803.42, 9482.76, 3097.35],
    '退货数量': [0, 0, 0, 10, 5, 0],
    '退货金额': [0, 0, 0, 370, 175, 0],
    '无税退货金额': [0, 0, 0, 316.24, 150.86, 0],
    '批发数量': [800, 500, 0, 700, 400, 50],
    '批发金额': [29600, 18800, 0, 25900, 15000, 1800],
    '无税批发金额': [25299.15, 16206.90, 0, 22136.75, 12931.03, 1592.92]
}

# 创建DataFrame
df = pd.DataFrame(data)

# 确保目录存在
os.makedirs('test_data', exist_ok=True)

# 保存为Excel文件
output_file = 'test_data/test_excel.xlsx'
df.to_excel(output_file, index=False, engine='openpyxl')

print(f"测试Excel文件已创建: {output_file}")
print(f"\n原始数据 ({len(df)} 行):")
print(df)

# 模拟处理逻辑
accounting_month_col = '会计月'
numeric_cols = [col for col in df.columns if col not in ['税率', '会计月', '供应商编码']]

# 转换数值列
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# 按会计月分组汇总
grouped_df = df.groupby(accounting_month_col, as_index=False)[numeric_cols].sum()

print(f"\n汇总后数据 ({len(grouped_df)} 行):")
print(grouped_df)

# 保存汇总后的文件
output_file_processed = 'test_data/test_excel_processed.xlsx'
grouped_df.to_excel(output_file_processed, index=False, engine='openpyxl')
print(f"\n汇总后的Excel文件已创建: {output_file_processed}")
