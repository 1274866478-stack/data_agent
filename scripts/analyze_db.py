import pandas as pd
import os

# 读取Excel文件
file_path = 'scripts/test_database_optimized.xlsx'
xls = pd.ExcelFile(file_path)

print("=" * 60)
print("数据库结构分析")
print("=" * 60)

# 遍历每个工作表
for sheet_name in xls.sheet_names:
    print(f"\n【表名: {sheet_name}】")
    df = pd.read_excel(xls, sheet_name=sheet_name)
    print(f"  行数: {len(df)}")
    print(f"  列名: {list(df.columns)}")

    # 显示前几行数据
    print(f"  示例数据:")
    print(df.head(3).to_string(max_cols=8))
    print()
