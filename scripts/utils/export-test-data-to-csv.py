#!/usr/bin/env python3
"""
导出测试数据到CSV文件
从SQL数据生成CSV格式的测试数据文件
"""

import os
import csv
from datetime import datetime

# 输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "test_data_csv")

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==================== 数据定义 ====================

# 1. 地区数据
regions = [
    {"id": 1, "name": "East China", "country": "China"},
    {"id": 2, "name": "North China", "country": "China"},
    {"id": 3, "name": "South China", "country": "China"},
    {"id": 4, "name": "Southwest", "country": "China"},
    {"id": 5, "name": "Northwest", "country": "China"},
    {"id": 6, "name": "Northeast", "country": "China"},
]

# 2. 员工数据
employees = [
    {"id": 1, "name": "Zhang Wei", "email": "zhangwei@company.com", "department": "Sales", "position": "Sales Manager", "region_id": 1, "hire_date": "2020-03-15", "salary": 15000.00, "is_active": True},
    {"id": 2, "name": "Li Na", "email": "lina@company.com", "department": "Sales", "position": "Senior Sales", "region_id": 1, "hire_date": "2021-06-20", "salary": 12000.00, "is_active": True},
    {"id": 3, "name": "Wang Qiang", "email": "wangqiang@company.com", "department": "Sales", "position": "Sales Rep", "region_id": 2, "hire_date": "2022-01-10", "salary": 8000.00, "is_active": True},
    {"id": 4, "name": "Liu Fang", "email": "liufang@company.com", "department": "Sales", "position": "Senior Sales", "region_id": 3, "hire_date": "2021-09-05", "salary": 11000.00, "is_active": True},
    {"id": 5, "name": "Chen Ming", "email": "chenming@company.com", "department": "Sales", "position": "Sales Rep", "region_id": 4, "hire_date": "2023-02-28", "salary": 7500.00, "is_active": True},
    {"id": 6, "name": "Zhao Li", "email": "zhaoli@company.com", "department": "Marketing", "position": "Marketing Mgr", "region_id": 1, "hire_date": "2019-11-11", "salary": 16000.00, "is_active": True},
    {"id": 7, "name": "Zhou Jie", "email": "zhoujie@company.com", "department": "Tech", "position": "Tech Director", "region_id": 1, "hire_date": "2018-05-20", "salary": 25000.00, "is_active": True},
    {"id": 8, "name": "Wu Min", "email": "wumin@company.com", "department": "Sales", "position": "Sales Rep", "region_id": 5, "hire_date": "2023-07-15", "salary": 7000.00, "is_active": True},
]

# 3. 产品类别
categories = [
    {"id": 1, "name": "Electronics", "description": "Phones, computers, tablets"},
    {"id": 2, "name": "Office Supplies", "description": "Stationery, office equipment"},
    {"id": 3, "name": "Home Products", "description": "Furniture, decorations"},
    {"id": 4, "name": "Clothing", "description": "Apparel and accessories"},
    {"id": 5, "name": "Food & Beverage", "description": "Snacks, drinks, groceries"},
]

# 4. 产品数据
products = [
    {"id": 1, "name": "iPhone 15 Pro", "category_id": 1, "sku": "ELEC-001", "price": 8999.00, "cost": 6500.00, "stock_quantity": 150, "is_available": True},
    {"id": 2, "name": "MacBook Pro 14", "category_id": 1, "sku": "ELEC-002", "price": 16999.00, "cost": 12000.00, "stock_quantity": 80, "is_available": True},
    {"id": 3, "name": "iPad Air", "category_id": 1, "sku": "ELEC-003", "price": 4799.00, "cost": 3200.00, "stock_quantity": 200, "is_available": True},
    {"id": 4, "name": "AirPods Pro", "category_id": 1, "sku": "ELEC-004", "price": 1899.00, "cost": 1200.00, "stock_quantity": 500, "is_available": True},
    {"id": 5, "name": "Huawei Mate 60", "category_id": 1, "sku": "ELEC-005", "price": 6999.00, "cost": 4800.00, "stock_quantity": 120, "is_available": True},
    {"id": 6, "name": "HP LaserJet Printer", "category_id": 2, "sku": "OFF-001", "price": 2599.00, "cost": 1800.00, "stock_quantity": 60, "is_available": True},
    {"id": 7, "name": "Ergonomic Office Chair", "category_id": 2, "sku": "OFF-002", "price": 1299.00, "cost": 800.00, "stock_quantity": 100, "is_available": True},
    {"id": 8, "name": "A4 Copy Paper 5-Pack", "category_id": 2, "sku": "OFF-003", "price": 89.00, "cost": 50.00, "stock_quantity": 1000, "is_available": True},
    {"id": 9, "name": "Smart Desk Lamp", "category_id": 3, "sku": "HOME-001", "price": 299.00, "cost": 150.00, "stock_quantity": 300, "is_available": True},
    {"id": 10, "name": "Air Purifier", "category_id": 3, "sku": "HOME-002", "price": 2499.00, "cost": 1600.00, "stock_quantity": 80, "is_available": True},
    {"id": 11, "name": "Sports T-Shirt", "category_id": 4, "sku": "CLO-001", "price": 199.00, "cost": 80.00, "stock_quantity": 500, "is_available": True},
    {"id": 12, "name": "Business Shirt", "category_id": 4, "sku": "CLO-002", "price": 399.00, "cost": 150.00, "stock_quantity": 300, "is_available": True},
    {"id": 13, "name": "Coffee Beans 1kg", "category_id": 5, "sku": "FOOD-001", "price": 168.00, "cost": 90.00, "stock_quantity": 200, "is_available": True},
    {"id": 14, "name": "Organic Green Tea 500g", "category_id": 5, "sku": "FOOD-002", "price": 128.00, "cost": 60.00, "stock_quantity": 400, "is_available": True},
]

# 5. 客户数据
customers = [
    {"id": 1, "name": "Shanghai Tech Ltd", "company": "SH Tech", "email": "contact@shtech.com", "phone": "021-12345678", "region_id": 1, "customer_type": "enterprise", "total_purchases": 258000.00},
    {"id": 2, "name": "Beijing Innovation Group", "company": "BJ Innovation", "email": "info@bjcx.com", "phone": "010-87654321", "region_id": 2, "customer_type": "enterprise", "total_purchases": 186000.00},
    {"id": 3, "name": "Guangzhou Trading Co", "company": "GZ Trading", "email": "sales@gzmy.com", "phone": "020-11223344", "region_id": 3, "customer_type": "vip", "total_purchases": 95000.00},
    {"id": 4, "name": "Chengdu Digital Shop", "company": "CD Digital", "email": "shop@cdsm.com", "phone": "028-55667788", "region_id": 4, "customer_type": "regular", "total_purchases": 45000.00},
    {"id": 5, "name": "Xian Office Supplies", "company": "XA Office", "email": "order@xabg.com", "phone": "029-99887766", "region_id": 5, "customer_type": "regular", "total_purchases": 32000.00},
    {"id": 6, "name": "Hangzhou E-commerce", "company": "HZ E-com", "email": "buy@hzds.com", "phone": "0571-12121212", "region_id": 1, "customer_type": "vip", "total_purchases": 128000.00},
    {"id": 7, "name": "Shenzhen Smart Tech", "company": "SZ Smart", "email": "tech@szzn.com", "phone": "0755-34343434", "region_id": 3, "customer_type": "enterprise", "total_purchases": 312000.00},
    {"id": 8, "name": "Wuhan Education Group", "company": "WH Edu", "email": "edu@whjy.com", "phone": "027-56565656", "region_id": 4, "customer_type": "vip", "total_purchases": 78000.00},
    {"id": 9, "name": "Tianjin Manufacturing", "company": "TJ Mfg", "email": "mfg@tjzz.com", "phone": "022-78787878", "region_id": 2, "customer_type": "regular", "total_purchases": 54000.00},
    {"id": 10, "name": "Nanjing Retail", "company": "NJ Retail", "email": "retail@njls.com", "phone": "025-90909090", "region_id": 1, "customer_type": "regular", "total_purchases": 28000.00},
]

# 6. 订单数据
orders = [
    {"id": 1, "order_no": "ORD-2024-0001", "customer_id": 1, "employee_id": 1, "order_date": "2024-01-05", "status": "delivered", "total_amount": 35996.00, "discount_amount": 1000.00, "payment_method": "Bank Transfer"},
    {"id": 2, "order_no": "ORD-2024-0002", "customer_id": 2, "employee_id": 3, "order_date": "2024-01-08", "status": "delivered", "total_amount": 16999.00, "discount_amount": 500.00, "payment_method": "Credit"},
    {"id": 3, "order_no": "ORD-2024-0003", "customer_id": 3, "employee_id": 4, "order_date": "2024-01-12", "status": "delivered", "total_amount": 8999.00, "discount_amount": 0.00, "payment_method": "Alipay"},
    {"id": 4, "order_no": "ORD-2024-0004", "customer_id": 6, "employee_id": 2, "order_date": "2024-01-18", "status": "delivered", "total_amount": 22798.00, "discount_amount": 800.00, "payment_method": "WeChat"},
    {"id": 5, "order_no": "ORD-2024-0005", "customer_id": 7, "employee_id": 4, "order_date": "2024-02-03", "status": "delivered", "total_amount": 51997.00, "discount_amount": 2000.00, "payment_method": "Bank Transfer"},
    {"id": 6, "order_no": "ORD-2024-0006", "customer_id": 4, "employee_id": 5, "order_date": "2024-02-14", "status": "delivered", "total_amount": 4799.00, "discount_amount": 0.00, "payment_method": "COD"},
    {"id": 7, "order_no": "ORD-2024-0007", "customer_id": 1, "employee_id": 1, "order_date": "2024-02-20", "status": "delivered", "total_amount": 9598.00, "discount_amount": 300.00, "payment_method": "Credit"},
    {"id": 8, "order_no": "ORD-2024-0008", "customer_id": 8, "employee_id": 2, "order_date": "2024-03-05", "status": "delivered", "total_amount": 12997.00, "discount_amount": 500.00, "payment_method": "Bank Transfer"},
    {"id": 9, "order_no": "ORD-2024-0009", "customer_id": 5, "employee_id": 5, "order_date": "2024-03-12", "status": "delivered", "total_amount": 2599.00, "discount_amount": 0.00, "payment_method": "Alipay"},
    {"id": 10, "order_no": "ORD-2024-0010", "customer_id": 9, "employee_id": 3, "order_date": "2024-03-22", "status": "delivered", "total_amount": 6998.00, "discount_amount": 200.00, "payment_method": "WeChat"},
    {"id": 11, "order_no": "ORD-2024-0011", "customer_id": 2, "employee_id": 1, "order_date": "2024-04-02", "status": "delivered", "total_amount": 33998.00, "discount_amount": 1500.00, "payment_method": "Credit"},
    {"id": 12, "order_no": "ORD-2024-0012", "customer_id": 10, "employee_id": 2, "order_date": "2024-04-15", "status": "delivered", "total_amount": 1788.00, "discount_amount": 0.00, "payment_method": "Alipay"},
    {"id": 13, "order_no": "ORD-2024-0013", "customer_id": 3, "employee_id": 4, "order_date": "2024-04-25", "status": "delivered", "total_amount": 13998.00, "discount_amount": 400.00, "payment_method": "Bank Transfer"},
    {"id": 14, "order_no": "ORD-2024-0014", "customer_id": 6, "employee_id": 2, "order_date": "2024-05-08", "status": "delivered", "total_amount": 25497.00, "discount_amount": 1000.00, "payment_method": "WeChat"},
    {"id": 15, "order_no": "ORD-2024-0015", "customer_id": 7, "employee_id": 4, "order_date": "2024-05-18", "status": "delivered", "total_amount": 41996.00, "discount_amount": 1800.00, "payment_method": "Bank Transfer"},
    {"id": 16, "order_no": "ORD-2024-0016", "customer_id": 1, "employee_id": 1, "order_date": "2024-05-28", "status": "delivered", "total_amount": 8999.00, "discount_amount": 300.00, "payment_method": "Credit"},
    {"id": 17, "order_no": "ORD-2024-0017", "customer_id": 4, "employee_id": 5, "order_date": "2024-06-05", "status": "delivered", "total_amount": 3798.00, "discount_amount": 0.00, "payment_method": "COD"},
    {"id": 18, "order_no": "ORD-2024-0018", "customer_id": 8, "employee_id": 3, "order_date": "2024-06-15", "status": "delivered", "total_amount": 17998.00, "discount_amount": 600.00, "payment_method": "Bank Transfer"},
    {"id": 19, "order_no": "ORD-2024-0019", "customer_id": 2, "employee_id": 1, "order_date": "2024-06-25", "status": "delivered", "total_amount": 27997.00, "discount_amount": 1200.00, "payment_method": "Credit"},
    {"id": 20, "order_no": "ORD-2024-0020", "customer_id": 5, "employee_id": 5, "order_date": "2024-07-03", "status": "delivered", "total_amount": 5198.00, "discount_amount": 0.00, "payment_method": "Alipay"},
    {"id": 21, "order_no": "ORD-2024-0021", "customer_id": 9, "employee_id": 3, "order_date": "2024-07-12", "status": "delivered", "total_amount": 8999.00, "discount_amount": 200.00, "payment_method": "WeChat"},
    {"id": 22, "order_no": "ORD-2024-0022", "customer_id": 10, "employee_id": 2, "order_date": "2024-07-22", "status": "delivered", "total_amount": 2997.00, "discount_amount": 0.00, "payment_method": "Alipay"},
    {"id": 23, "order_no": "ORD-2024-0023", "customer_id": 3, "employee_id": 4, "order_date": "2024-08-05", "status": "delivered", "total_amount": 18898.00, "discount_amount": 700.00, "payment_method": "Bank Transfer"},
    {"id": 24, "order_no": "ORD-2024-0024", "customer_id": 6, "employee_id": 2, "order_date": "2024-08-15", "status": "delivered", "total_amount": 32497.00, "discount_amount": 1300.00, "payment_method": "WeChat"},
    {"id": 25, "order_no": "ORD-2024-0025", "customer_id": 7, "employee_id": 4, "order_date": "2024-08-25", "status": "delivered", "total_amount": 25797.00, "discount_amount": 1000.00, "payment_method": "Bank Transfer"},
    {"id": 26, "order_no": "ORD-2024-0026", "customer_id": 1, "employee_id": 1, "order_date": "2024-09-02", "status": "delivered", "total_amount": 16999.00, "discount_amount": 500.00, "payment_method": "Credit"},
    {"id": 27, "order_no": "ORD-2024-0027", "customer_id": 4, "employee_id": 5, "order_date": "2024-09-12", "status": "delivered", "total_amount": 6998.00, "discount_amount": 0.00, "payment_method": "COD"},
    {"id": 28, "order_no": "ORD-2024-0028", "customer_id": 8, "employee_id": 3, "order_date": "2024-09-22", "status": "delivered", "total_amount": 11897.00, "discount_amount": 400.00, "payment_method": "Bank Transfer"},
    {"id": 29, "order_no": "ORD-2024-0029", "customer_id": 2, "employee_id": 1, "order_date": "2024-10-05", "status": "delivered", "total_amount": 35996.00, "discount_amount": 1500.00, "payment_method": "Credit"},
    {"id": 30, "order_no": "ORD-2024-0030", "customer_id": 5, "employee_id": 5, "order_date": "2024-10-15", "status": "delivered", "total_amount": 4188.00, "discount_amount": 0.00, "payment_method": "Alipay"},
    {"id": 31, "order_no": "ORD-2024-0031", "customer_id": 9, "employee_id": 3, "order_date": "2024-10-25", "status": "shipped", "total_amount": 13998.00, "discount_amount": 500.00, "payment_method": "WeChat"},
    {"id": 32, "order_no": "ORD-2024-0032", "customer_id": 10, "employee_id": 2, "order_date": "2024-11-02", "status": "shipped", "total_amount": 8999.00, "discount_amount": 200.00, "payment_method": "Alipay"},
    {"id": 33, "order_no": "ORD-2024-0033", "customer_id": 3, "employee_id": 4, "order_date": "2024-11-10", "status": "shipped", "total_amount": 22798.00, "discount_amount": 900.00, "payment_method": "Bank Transfer"},
    {"id": 34, "order_no": "ORD-2024-0034", "customer_id": 6, "employee_id": 2, "order_date": "2024-11-18", "status": "confirmed", "total_amount": 41996.00, "discount_amount": 1700.00, "payment_method": "WeChat"},
    {"id": 35, "order_no": "ORD-2024-0035", "customer_id": 7, "employee_id": 4, "order_date": "2024-11-25", "status": "pending", "total_amount": 51997.00, "discount_amount": 2000.00, "payment_method": "Bank Transfer"},
]

