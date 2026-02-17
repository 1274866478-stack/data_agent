# -*- coding: utf-8 -*-
import pandas as pd
import os

data_dir = r'C:\data_agent\data_storage\data-sources\default_tenant'
files = [f for f in os.listdir(data_dir) if f.endswith('.xlsx')]

with open(r'C:\data_agent\data_storage_sheets.txt', 'w', encoding='utf-8') as f:
    for filename in files[:10]:  # 检查前10个文件
        filepath = os.path.join(data_dir, filename)
        try:
            xl = pd.ExcelFile(filepath)
            f.write(f"\n=== {filename} ===\n")
            f.write(f"Sheets: {xl.sheet_names}\n")
        except Exception as e:
            f.write(f"\n=== {filename} === ERROR: {e}\n")

print("Done! Check data_storage_sheets.txt")
