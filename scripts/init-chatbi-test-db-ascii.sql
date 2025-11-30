-- ================================================================
-- ChatBI Test Database Initialization Script
-- User: dev@dataagent.local
-- Purpose: Test AI Assistant ChatBI functionality
-- ================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS employees CASCADE;
DROP TABLE IF EXISTS regions CASCADE;

-- 1. Regions
CREATE TABLE regions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    country VARCHAR(50) DEFAULT 'China'
);

INSERT INTO regions (name, country) VALUES
('East China', 'China'), ('North China', 'China'), ('South China', 'China'),
('Southwest', 'China'), ('Northwest', 'China'), ('Northeast', 'China');

-- 2. Employees
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE,
    department VARCHAR(50),
    position VARCHAR(50),
    region_id INTEGER REFERENCES regions(id),
    hire_date DATE,
    salary DECIMAL(10, 2),
    is_active BOOLEAN DEFAULT true
);

INSERT INTO employees (name, email, department, position, region_id, hire_date, salary) VALUES
('Zhang Wei', 'zhangwei@company.com', 'Sales', 'Sales Manager', 1, '2020-03-15', 15000.00),
('Li Na', 'lina@company.com', 'Sales', 'Senior Sales', 1, '2021-06-20', 12000.00),
('Wang Qiang', 'wangqiang@company.com', 'Sales', 'Sales Rep', 2, '2022-01-10', 8000.00),
('Liu Fang', 'liufang@company.com', 'Sales', 'Senior Sales', 3, '2021-09-05', 11000.00),
('Chen Ming', 'chenming@company.com', 'Sales', 'Sales Rep', 4, '2023-02-28', 7500.00),
('Zhao Li', 'zhaoli@company.com', 'Marketing', 'Marketing Mgr', 1, '2019-11-11', 16000.00),
('Zhou Jie', 'zhoujie@company.com', 'Tech', 'Tech Director', 1, '2018-05-20', 25000.00),
('Wu Min', 'wumin@company.com', 'Sales', 'Sales Rep', 5, '2023-07-15', 7000.00);

-- 3. Categories
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT
);

INSERT INTO categories (name, description) VALUES
('Electronics', 'Phones, computers, tablets'),
('Office Supplies', 'Stationery, office equipment'),
('Home Products', 'Furniture, decorations'),
('Clothing', 'Apparel and accessories'),
('Food & Beverage', 'Snacks, drinks, groceries');

-- 4. Products
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    category_id INTEGER REFERENCES categories(id),
    sku VARCHAR(50) UNIQUE,
    price DECIMAL(10, 2) NOT NULL,
    cost DECIMAL(10, 2),
    stock_quantity INTEGER DEFAULT 0,
    is_available BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO products (name, category_id, sku, price, cost, stock_quantity) VALUES
('iPhone 15 Pro', 1, 'ELEC-001', 8999.00, 6500.00, 150),
('MacBook Pro 14', 1, 'ELEC-002', 16999.00, 12000.00, 80),
('iPad Air', 1, 'ELEC-003', 4799.00, 3200.00, 200),
('AirPods Pro', 1, 'ELEC-004', 1899.00, 1200.00, 500),
('Huawei Mate 60', 1, 'ELEC-005', 6999.00, 4800.00, 120),
('HP LaserJet Printer', 2, 'OFF-001', 2599.00, 1800.00, 60),
('Ergonomic Office Chair', 2, 'OFF-002', 1299.00, 800.00, 100),
('A4 Copy Paper 5-Pack', 2, 'OFF-003', 89.00, 50.00, 1000),
('Smart Desk Lamp', 3, 'HOME-001', 299.00, 150.00, 300),
('Air Purifier', 3, 'HOME-002', 2499.00, 1600.00, 80),
('Sports T-Shirt', 4, 'CLO-001', 199.00, 80.00, 500),
('Business Shirt', 4, 'CLO-002', 399.00, 150.00, 300),
('Coffee Beans 1kg', 5, 'FOOD-001', 168.00, 90.00, 200),
('Organic Green Tea 500g', 5, 'FOOD-002', 128.00, 60.00, 400);

-- 5. Customers
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    company VARCHAR(200),
    email VARCHAR(255),
    phone VARCHAR(20),
    region_id INTEGER REFERENCES regions(id),
    customer_type VARCHAR(20) DEFAULT 'regular',
    total_purchases DECIMAL(12, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO customers (name, company, email, phone, region_id, customer_type, total_purchases) VALUES
('Shanghai Tech Ltd', 'SH Tech', 'contact@shtech.com', '021-12345678', 1, 'enterprise', 258000.00),
('Beijing Innovation Group', 'BJ Innovation', 'info@bjcx.com', '010-87654321', 2, 'enterprise', 186000.00),
('Guangzhou Trading Co', 'GZ Trading', 'sales@gzmy.com', '020-11223344', 3, 'vip', 95000.00),
('Chengdu Digital Shop', 'CD Digital', 'shop@cdsm.com', '028-55667788', 4, 'regular', 45000.00),
('Xian Office Supplies', 'XA Office', 'order@xabg.com', '029-99887766', 5, 'regular', 32000.00),
('Hangzhou E-commerce', 'HZ E-com', 'buy@hzds.com', '0571-12121212', 1, 'vip', 128000.00),
('Shenzhen Smart Tech', 'SZ Smart', 'tech@szzn.com', '0755-34343434', 3, 'enterprise', 312000.00),
('Wuhan Education Group', 'WH Edu', 'edu@whjy.com', '027-56565656', 4, 'vip', 78000.00),
('Tianjin Manufacturing', 'TJ Mfg', 'mfg@tjzz.com', '022-78787878', 2, 'regular', 54000.00),
('Nanjing Retail', 'NJ Retail', 'retail@njls.com', '025-90909090', 1, 'regular', 28000.00);

-- 6. Orders
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    order_no VARCHAR(50) UNIQUE NOT NULL,
    customer_id INTEGER REFERENCES customers(id),
    employee_id INTEGER REFERENCES employees(id),
    order_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    total_amount DECIMAL(12, 2),
    discount_amount DECIMAL(10, 2) DEFAULT 0,
    payment_method VARCHAR(30),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO orders (order_no, customer_id, employee_id, order_date, status, total_amount, discount_amount, payment_method) VALUES
('ORD-2024-0001', 1, 1, '2024-01-05', 'delivered', 35996.00, 1000.00, 'Bank Transfer'),
('ORD-2024-0002', 2, 3, '2024-01-08', 'delivered', 16999.00, 500.00, 'Credit'),
('ORD-2024-0003', 3, 4, '2024-01-12', 'delivered', 8999.00, 0.00, 'Alipay'),
('ORD-2024-0004', 6, 2, '2024-01-18', 'delivered', 22798.00, 800.00, 'WeChat'),
('ORD-2024-0005', 7, 4, '2024-02-03', 'delivered', 51997.00, 2000.00, 'Bank Transfer'),
('ORD-2024-0006', 4, 5, '2024-02-14', 'delivered', 4799.00, 0.00, 'COD'),
('ORD-2024-0007', 1, 1, '2024-02-20', 'delivered', 9598.00, 300.00, 'Credit'),
('ORD-2024-0008', 8, 2, '2024-03-05', 'delivered', 12997.00, 500.00, 'Bank Transfer'),
('ORD-2024-0009', 5, 5, '2024-03-12', 'delivered', 2599.00, 0.00, 'Alipay'),
('ORD-2024-0010', 9, 3, '2024-03-22', 'delivered', 6998.00, 200.00, 'WeChat'),
('ORD-2024-0011', 2, 1, '2024-04-02', 'delivered', 33998.00, 1500.00, 'Credit'),
('ORD-2024-0012', 10, 2, '2024-04-15', 'delivered', 1788.00, 0.00, 'Alipay'),
('ORD-2024-0013', 3, 4, '2024-04-25', 'delivered', 13998.00, 400.00, 'Bank Transfer'),
('ORD-2024-0014', 6, 2, '2024-05-08', 'delivered', 25497.00, 1000.00, 'WeChat'),
('ORD-2024-0015', 7, 4, '2024-05-18', 'delivered', 41996.00, 1800.00, 'Bank Transfer'),
('ORD-2024-0016', 1, 1, '2024-05-28', 'delivered', 8999.00, 300.00, 'Credit'),
('ORD-2024-0017', 4, 5, '2024-06-05', 'delivered', 3798.00, 0.00, 'COD'),
('ORD-2024-0018', 8, 3, '2024-06-15', 'delivered', 17998.00, 600.00, 'Bank Transfer'),
('ORD-2024-0019', 2, 1, '2024-06-25', 'delivered', 27997.00, 1200.00, 'Credit'),
('ORD-2024-0020', 5, 5, '2024-07-03', 'delivered', 5198.00, 0.00, 'Alipay'),
('ORD-2024-0021', 9, 3, '2024-07-12', 'delivered', 8999.00, 200.00, 'WeChat'),
('ORD-2024-0022', 10, 2, '2024-07-22', 'delivered', 2997.00, 0.00, 'Alipay'),
('ORD-2024-0023', 3, 4, '2024-08-05', 'delivered', 18898.00, 700.00, 'Bank Transfer'),
('ORD-2024-0024', 6, 2, '2024-08-15', 'delivered', 32497.00, 1300.00, 'WeChat'),
('ORD-2024-0025', 7, 4, '2024-08-25', 'delivered', 25797.00, 1000.00, 'Bank Transfer'),
('ORD-2024-0026', 1, 1, '2024-09-02', 'delivered', 16999.00, 500.00, 'Credit'),
('ORD-2024-0027', 4, 5, '2024-09-12', 'delivered', 6998.00, 0.00, 'COD'),
('ORD-2024-0028', 8, 3, '2024-09-22', 'delivered', 11897.00, 400.00, 'Bank Transfer'),
('ORD-2024-0029', 2, 1, '2024-10-05', 'delivered', 35996.00, 1500.00, 'Credit'),
('ORD-2024-0030', 5, 5, '2024-10-15', 'delivered', 4188.00, 0.00, 'Alipay'),
('ORD-2024-0031', 9, 3, '2024-10-25', 'shipped', 13998.00, 500.00, 'WeChat'),
('ORD-2024-0032', 10, 2, '2024-11-02', 'shipped', 8999.00, 200.00, 'Alipay'),
('ORD-2024-0033', 3, 4, '2024-11-10', 'shipped', 22798.00, 900.00, 'Bank Transfer'),
('ORD-2024-0034', 6, 2, '2024-11-18', 'confirmed', 41996.00, 1700.00, 'WeChat'),
('ORD-2024-0035', 7, 4, '2024-11-25', 'pending', 51997.00, 2000.00, 'Bank Transfer');

-- 7. Order Items
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(12, 2) NOT NULL
);

INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES
(1, 1, 4, 8999.00, 35996.00),
(2, 2, 1, 16999.00, 16999.00),
(3, 1, 1, 8999.00, 8999.00),
(4, 3, 2, 4799.00, 9598.00),
(4, 5, 2, 6999.00, 13998.00),
(5, 2, 3, 16999.00, 50997.00),
(5, 8, 10, 89.00, 890.00),
(6, 3, 1, 4799.00, 4799.00),
(7, 4, 5, 1899.00, 9495.00),
(8, 6, 5, 2599.00, 12995.00),
(9, 6, 1, 2599.00, 2599.00),
(10, 5, 1, 6999.00, 6999.00),
(11, 2, 2, 16999.00, 33998.00),
(12, 8, 20, 89.00, 1780.00),
(13, 5, 2, 6999.00, 13998.00),
(14, 1, 2, 8999.00, 17998.00),
(14, 4, 4, 1899.00, 7596.00),
(15, 2, 2, 16999.00, 33998.00),
(15, 4, 4, 1899.00, 7596.00),
(16, 1, 1, 8999.00, 8999.00),
(17, 4, 2, 1899.00, 3798.00),
(18, 2, 1, 16999.00, 16999.00),
(18, 8, 10, 89.00, 890.00),
(19, 1, 3, 8999.00, 26997.00),
(20, 6, 2, 2599.00, 5198.00),
(21, 1, 1, 8999.00, 8999.00),
(22, 7, 2, 1299.00, 2598.00),
(22, 11, 2, 199.00, 398.00),
(23, 1, 2, 8999.00, 17998.00),
(23, 9, 3, 299.00, 897.00),
(24, 2, 1, 16999.00, 16999.00),
(24, 3, 2, 4799.00, 9598.00),
(24, 4, 3, 1899.00, 5697.00),
(25, 1, 2, 8999.00, 17998.00),
(25, 4, 4, 1899.00, 7596.00),
(26, 2, 1, 16999.00, 16999.00),
(27, 5, 1, 6999.00, 6999.00),
(28, 3, 2, 4799.00, 9598.00),
(28, 9, 5, 299.00, 1495.00),
(28, 8, 9, 89.00, 801.00),
(29, 1, 4, 8999.00, 35996.00),
(30, 3, 1, 4799.00, 4799.00),
(31, 5, 2, 6999.00, 13998.00),
(32, 1, 1, 8999.00, 8999.00),
(33, 3, 3, 4799.00, 14397.00),
(33, 4, 4, 1899.00, 7596.00),
(34, 2, 2, 16999.00, 33998.00),
(34, 4, 4, 1899.00, 7596.00),
(35, 2, 3, 16999.00, 50997.00);

-- 8. Create Views for ChatBI queries
CREATE OR REPLACE VIEW v_sales_summary AS
SELECT
    DATE_TRUNC('month', o.order_date) AS month,
    COUNT(DISTINCT o.id) AS order_count,
    SUM(o.total_amount) AS total_sales,
    SUM(o.discount_amount) AS total_discount,
    AVG(o.total_amount) AS avg_order_value
FROM orders o
WHERE o.status != 'cancelled'
GROUP BY DATE_TRUNC('month', o.order_date)
ORDER BY month;

CREATE OR REPLACE VIEW v_product_ranking AS
SELECT
    p.id AS product_id,
    p.name AS product_name,
    c.name AS category_name,
    SUM(oi.quantity) AS total_sold,
    SUM(oi.subtotal) AS total_revenue,
    COUNT(DISTINCT oi.order_id) AS order_count
FROM products p
JOIN categories c ON p.category_id = c.id
LEFT JOIN order_items oi ON p.id = oi.product_id
GROUP BY p.id, p.name, c.name
ORDER BY total_revenue DESC NULLS LAST;

CREATE OR REPLACE VIEW v_customer_value AS
SELECT
    c.id AS customer_id,
    c.name AS customer_name,
    c.company,
    c.customer_type,
    r.name AS region_name,
    COUNT(o.id) AS order_count,
    SUM(o.total_amount) AS total_spent,
    AVG(o.total_amount) AS avg_order_value,
    MAX(o.order_date) AS last_order_date
FROM customers c
JOIN regions r ON c.region_id = r.id
LEFT JOIN orders o ON c.id = o.customer_id AND o.status != 'cancelled'
GROUP BY c.id, c.name, c.company, c.customer_type, r.name;

CREATE OR REPLACE VIEW v_employee_performance AS
SELECT
    e.id AS employee_id,
    e.name AS employee_name,
    e.position,
    r.name AS region_name,
    COUNT(o.id) AS order_count,
    SUM(o.total_amount) AS total_sales,
    AVG(o.total_amount) AS avg_order_value
FROM employees e
JOIN regions r ON e.region_id = r.id
LEFT JOIN orders o ON e.id = o.employee_id AND o.status != 'cancelled'
WHERE e.department = 'Sales'
GROUP BY e.id, e.name, e.position, r.name;

