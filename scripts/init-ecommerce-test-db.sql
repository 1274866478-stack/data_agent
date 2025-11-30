-- ================================================================
-- 电商业务测试数据库初始化脚本
-- 数据库名: ecommerce_test_db
-- 用途: 测试AI助手的电商数据分析能力
-- 场景: 在线零售商城，包含用户、商品、订单、评价等完整业务数据
-- ================================================================

-- 启用扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 删除已存在的表（方便重新初始化）
DROP TABLE IF EXISTS reviews CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS addresses CASCADE;

-- ================================================================
-- 1. 用户表
-- ================================================================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    gender VARCHAR(10),
    birth_date DATE,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    vip_level INTEGER DEFAULT 0,
    total_spent DECIMAL(12, 2) DEFAULT 0,
    is_active BOOLEAN DEFAULT true
);

INSERT INTO users (username, email, phone, gender, birth_date, registration_date, vip_level, total_spent) VALUES
('张伟', 'zhangwei@email.com', '13800138001', '男', '1990-05-15', '2023-01-10', 3, 15680.50),
('李娜', 'lina@email.com', '13800138002', '女', '1992-08-20', '2023-02-15', 2, 8920.00),
('王强', 'wangqiang@email.com', '13800138003', '男', '1988-03-12', '2023-01-20', 1, 3450.00),
('刘芳', 'liufang@email.com', '13800138004', '女', '1995-11-08', '2023-03-05', 2, 6780.00),
('陈明', 'chenming@email.com', '13800138005', '男', '1991-07-22', '2023-02-28', 1, 2340.00),
('赵丽', 'zhaoli@email.com', '13800138006', '女', '1993-09-18', '2023-04-12', 3, 12560.00),
('周杰', 'zhoujie@email.com', '13800138007', '男', '1989-12-30', '2023-01-25', 2, 7890.00),
('吴敏', 'wumin@email.com', '13800138008', '女', '1994-06-05', '2023-03-20', 1, 4120.00),
('孙强', 'sunqiang@email.com', '13800138009', '男', '1987-04-14', '2023-02-08', 3, 18900.00),
('郑红', 'zhenghong@email.com', '13800138010', '女', '1996-10-25', '2023-04-01', 2, 5670.00);

-- ================================================================
-- 2. 收货地址表
-- ================================================================
CREATE TABLE addresses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    province VARCHAR(50) NOT NULL,
    city VARCHAR(50) NOT NULL,
    district VARCHAR(50),
    detail_address TEXT NOT NULL,
    is_default BOOLEAN DEFAULT false
);

INSERT INTO addresses (user_id, province, city, district, detail_address, is_default) VALUES
(1, '上海市', '上海市', '浦东新区', '张江高科技园区祖冲之路2288号', true),
(2, '北京市', '北京市', '朝阳区', '望京SOHO塔1 10层', true),
(3, '广东省', '深圳市', '南山区', '科技园南区深南大道9988号', true),
(4, '浙江省', '杭州市', '西湖区', '文三路90号东部软件园', true),
(5, '江苏省', '南京市', '鼓楼区', '汉中路89号金鹰国际商城', true),
(6, '四川省', '成都市', '高新区', '天府大道中段1388号', true),
(7, '湖北省', '武汉市', '洪山区', '光谷大道61号智慧园', true),
(8, '陕西省', '西安市', '雁塔区', '高新路88号尚品国际', true),
(9, '上海市', '上海市', '徐汇区', '漕河泾开发区桂平路680号', true),
(10, '广东省', '广州市', '天河区', '珠江新城花城大道85号', true);

-- ================================================================
-- 3. 商品类别表
-- ================================================================
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    parent_id INTEGER,
    description TEXT,
    sort_order INTEGER DEFAULT 0
);

INSERT INTO categories (name, parent_id, description, sort_order) VALUES
('电子产品', NULL, '手机、电脑、数码配件等', 1),
('服装鞋包', NULL, '男装、女装、鞋类、箱包等', 2),
('家居生活', NULL, '家具、家纺、厨具等', 3),
('图书音像', NULL, '图书、电子书、音乐、影视等', 4),
('食品饮料', NULL, '零食、饮料、生鲜食品等', 5),
('手机通讯', 1, '智能手机、功能机、对讲机等', 10),
('电脑办公', 1, '笔记本、台式机、平板电脑等', 11),
('数码配件', 1, '耳机、充电器、数据线等', 12),
('男装', 2, '衬衫、T恤、裤子、外套等', 20),
('女装', 2, '连衣裙、上衣、裤子、外套等', 21);

-- ================================================================
-- 4. 商品表
-- ================================================================
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    category_id INTEGER REFERENCES categories(id),
    sku VARCHAR(50) UNIQUE NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    original_price DECIMAL(10, 2),
    stock INTEGER DEFAULT 0,
    sales_count INTEGER DEFAULT 0,
    rating DECIMAL(3, 2) DEFAULT 5.00,
    review_count INTEGER DEFAULT 0,
    brand VARCHAR(100),
    description TEXT,
    is_on_sale BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO products (name, category_id, sku, price, original_price, stock, sales_count, rating, review_count, brand, description) VALUES
('iPhone 15 Pro Max 256GB', 6, 'PHONE-001', 9999.00, 10999.00, 150, 328, 4.85, 156, 'Apple', '6.7英寸超视网膜XDR显示屏，A17 Pro芯片'),
('华为Mate 60 Pro 512GB', 6, 'PHONE-002', 6999.00, 7999.00, 200, 445, 4.90, 223, '华为', '6.82英寸OLED曲面屏，麒麟9000S芯片'),
('小米14 Ultra 16GB+512GB', 6, 'PHONE-003', 6499.00, 6999.00, 180, 267, 4.75, 134, '小米', '6.73英寸2K屏，骁龙8 Gen3芯片'),
('MacBook Pro 14英寸 M3', 7, 'LAPTOP-001', 14999.00, 15999.00, 80, 156, 4.95, 89, 'Apple', '14.2英寸Liquid视网膜XDR显示屏，M3芯片'),
('联想ThinkPad X1 Carbon', 7, 'LAPTOP-002', 12999.00, 13999.00, 60, 98, 4.80, 52, '联想', '14英寸2.8K OLED屏，Intel酷睿Ultra 7'),
('iPad Air 第5代 256GB', 7, 'TABLET-001', 4799.00, 5299.00, 120, 234, 4.88, 118, 'Apple', '10.9英寸液态视网膜显示屏，M1芯片'),
('AirPods Pro 第2代', 8, 'AUDIO-001', 1899.00, 1999.00, 500, 892, 4.92, 445, 'Apple', '主动降噪，自适应通透模式，空间音频'),
('索尼WH-1000XM5降噪耳机', 8, 'AUDIO-002', 2499.00, 2799.00, 300, 567, 4.87, 289, '索尼', '业界领先降噪，30小时续航'),
('罗技MX Master 3S鼠标', 8, 'MOUSE-001', 699.00, 799.00, 400, 678, 4.83, 334, '罗技', '人体工学设计，8000DPI传感器'),
('男士商务衬衫', 9, 'CLOTH-001', 299.00, 399.00, 800, 1234, 4.65, 567, '海澜之家', '纯棉免烫，多色可选'),
('女士连衣裙', 10, 'CLOTH-002', 399.00, 599.00, 600, 987, 4.70, 456, 'ONLY', '雪纺面料，优雅气质'),
('运动跑鞋', 2, 'SHOE-001', 599.00, 799.00, 500, 765, 4.78, 389, '耐克', '气垫减震，透气舒适'),
('智能手表', 1, 'WATCH-001', 1999.00, 2499.00, 250, 445, 4.72, 223, 'Apple', 'Apple Watch Series 9，健康监测'),
('无线充电器', 8, 'CHARGER-001', 199.00, 299.00, 1000, 1567, 4.68, 789, '小米', '20W快充，多设备兼容'),
('蓝牙音箱', 8, 'SPEAKER-001', 399.00, 499.00, 350, 534, 4.75, 267, 'JBL', '360度环绕音效，防水设计');

-- ================================================================
-- 5. 订单表
-- ================================================================
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    order_no VARCHAR(50) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id),
    address_id INTEGER REFERENCES addresses(id),
    total_amount DECIMAL(12, 2) NOT NULL,
    discount_amount DECIMAL(10, 2) DEFAULT 0,
    shipping_fee DECIMAL(8, 2) DEFAULT 0,
    final_amount DECIMAL(12, 2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    payment_method VARCHAR(20),
    payment_time TIMESTAMP,
    shipping_time TIMESTAMP,
    completed_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    remark TEXT
);

-- 订单状态: pending(待付款), paid(已付款), shipped(已发货), completed(已完成), cancelled(已取消)
INSERT INTO orders (order_no, user_id, address_id, total_amount, discount_amount, shipping_fee, final_amount, status, payment_method, payment_time, shipping_time, completed_time, created_at) VALUES
('ORD202401001', 1, 1, 9999.00, 500.00, 0, 9499.00, 'completed', '支付宝', '2024-01-15 10:30:00', '2024-01-16 09:00:00', '2024-01-20 14:30:00', '2024-01-15 10:25:00'),
('ORD202401002', 2, 2, 2499.00, 100.00, 15.00, 2414.00, 'completed', '微信支付', '2024-01-18 15:20:00', '2024-01-19 10:00:00', '2024-01-23 16:45:00', '2024-01-18 15:15:00'),
('ORD202401003', 3, 3, 1899.00, 0, 15.00, 1914.00, 'completed', '支付宝', '2024-01-20 11:10:00', '2024-01-21 08:30:00', '2024-01-25 10:20:00', '2024-01-20 11:05:00'),
('ORD202402004', 1, 1, 4799.00, 200.00, 0, 4599.00, 'completed', '支付宝', '2024-02-05 09:45:00', '2024-02-06 11:00:00', '2024-02-10 15:30:00', '2024-02-05 09:40:00'),
('ORD202402005', 4, 4, 6999.00, 300.00, 0, 6699.00, 'completed', '微信支付', '2024-02-10 14:30:00', '2024-02-11 09:00:00', '2024-02-15 11:20:00', '2024-02-10 14:25:00'),
('ORD202402006', 5, 5, 1299.00, 50.00, 15.00, 1264.00, 'completed', '支付宝', '2024-02-15 16:20:00', '2024-02-16 10:00:00', '2024-02-20 14:00:00', '2024-02-15 16:15:00'),
('ORD202403007', 6, 6, 12999.00, 500.00, 0, 12499.00, 'completed', '支付宝', '2024-03-01 10:00:00', '2024-03-02 09:00:00', '2024-03-06 16:30:00', '2024-03-01 09:55:00'),
('ORD202403008', 2, 2, 6499.00, 200.00, 0, 6299.00, 'completed', '微信支付', '2024-03-05 13:40:00', '2024-03-06 10:00:00', '2024-03-10 15:20:00', '2024-03-05 13:35:00'),
('ORD202403009', 7, 7, 7890.00, 300.00, 0, 7590.00, 'shipped', '支付宝', '2024-03-10 11:20:00', '2024-03-11 09:00:00', NULL, '2024-03-10 11:15:00'),
('ORD202404010', 8, 8, 4120.00, 150.00, 15.00, 3985.00, 'shipped', '微信支付', '2024-04-01 15:30:00', '2024-04-02 10:00:00', NULL, '2024-04-01 15:25:00'),
('ORD202404011', 9, 9, 18900.00, 800.00, 0, 18100.00, 'paid', '支付宝', '2024-04-05 09:00:00', NULL, NULL, '2024-04-05 08:55:00'),
('ORD202404012', 10, 10, 5670.00, 200.00, 15.00, 5485.00, 'paid', '微信支付', '2024-04-08 14:20:00', NULL, NULL, '2024-04-08 14:15:00'),
('ORD202404013', 1, 1, 1582.00, 50.00, 15.00, 1547.00, 'pending', NULL, NULL, NULL, NULL, '2024-04-10 10:30:00'),
('ORD202404014', 3, 3, 1236.00, 0, 15.00, 1251.00, 'cancelled', NULL, NULL, NULL, NULL, '2024-04-12 16:00:00');

-- ================================================================
-- 6. 订单明细表
-- ================================================================
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    product_id INTEGER REFERENCES products(id),
    product_name VARCHAR(200) NOT NULL,
    sku VARCHAR(50) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    quantity INTEGER NOT NULL,
    subtotal DECIMAL(12, 2) NOT NULL
);

INSERT INTO order_items (order_id, product_id, product_name, sku, price, quantity, subtotal) VALUES
(1, 1, 'iPhone 15 Pro Max 256GB', 'PHONE-001', 9999.00, 1, 9999.00),
(2, 8, '索尼WH-1000XM5降噪耳机', 'AUDIO-002', 2499.00, 1, 2499.00),
(3, 7, 'AirPods Pro 第2代', 'AUDIO-001', 1899.00, 1, 1899.00),
(4, 6, 'iPad Air 第5代 256GB', 'TABLET-001', 4799.00, 1, 4799.00),
(5, 2, '华为Mate 60 Pro 512GB', 'PHONE-002', 6999.00, 1, 6999.00),
(6, 10, '男士商务衬衫', 'CLOTH-001', 299.00, 3, 897.00),
(6, 14, '无线充电器', 'CHARGER-001', 199.00, 2, 398.00),
(7, 5, '联想ThinkPad X1 Carbon', 'LAPTOP-002', 12999.00, 1, 12999.00),
(8, 3, '小米14 Ultra 16GB+512GB', 'PHONE-003', 6499.00, 1, 6499.00),
(9, 4, 'MacBook Pro 14英寸 M3', 'LAPTOP-001', 14999.00, 1, 14999.00),
(10, 11, '女士连衣裙', 'CLOTH-002', 399.00, 2, 798.00),
(10, 12, '运动跑鞋', 'SHOE-001', 599.00, 3, 1797.00),
(10, 9, '罗技MX Master 3S鼠标', 'MOUSE-001', 699.00, 2, 1398.00),
(11, 1, 'iPhone 15 Pro Max 256GB', 'PHONE-001', 9999.00, 1, 9999.00),
(11, 7, 'AirPods Pro 第2代', 'AUDIO-001', 1899.00, 2, 3798.00),
(11, 13, '智能手表', 'WATCH-001', 1999.00, 2, 3998.00),
(12, 8, '索尼WH-1000XM5降噪耳机', 'AUDIO-002', 2499.00, 1, 2499.00),
(12, 15, '蓝牙音箱', 'SPEAKER-001', 399.00, 3, 1197.00),
(12, 14, '无线充电器', 'CHARGER-001', 199.00, 5, 995.00),
(13, 10, '男士商务衬衫', 'CLOTH-001', 299.00, 2, 598.00),
(13, 14, '无线充电器', 'CHARGER-001', 199.00, 3, 597.00),
(14, 11, '女士连衣裙', 'CLOTH-002', 399.00, 2, 798.00),
(14, 14, '无线充电器', 'CHARGER-001', 199.00, 2, 398.00);

-- ================================================================
-- 7. 商品评价表
-- ================================================================
CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    product_id INTEGER REFERENCES products(id),
    user_id INTEGER REFERENCES users(id),
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    content TEXT,
    images TEXT[],
    is_anonymous BOOLEAN DEFAULT false,
    helpful_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO reviews (order_id, product_id, user_id, rating, content, is_anonymous, helpful_count, created_at) VALUES
(1, 1, 1, 5, '非常满意！iPhone 15 Pro Max的性能真的很强大，拍照效果也很棒，钛金属边框手感一流。', false, 45, '2024-01-21 10:00:00'),
(2, 8, 2, 5, '索尼大法好！降噪效果确实业界领先，音质也非常出色，长时间佩戴也很舒适。', false, 32, '2024-01-24 15:30:00'),
(3, 7, 3, 5, 'AirPods Pro 2代的降噪和音质都比一代提升明显，空间音频体验很棒！', false, 28, '2024-01-26 11:20:00'),
(4, 6, 1, 5, 'iPad Air配合Apple Pencil使用体验极佳，M1芯片性能强劲，屏幕显示效果出色。', false, 23, '2024-02-11 14:00:00'),
(5, 2, 4, 5, '华为Mate 60 Pro的拍照能力真的很强，尤其是夜景模式，电池续航也很给力。', false, 38, '2024-02-16 09:30:00'),
(6, 10, 5, 4, '衬衫质量不错，免烫效果还可以，就是尺码稍微偏大一点。', false, 15, '2024-02-21 16:45:00'),
(7, 5, 6, 5, 'ThinkPad的品质一如既往的好，键盘手感极佳，OLED屏幕显示效果惊艳。', false, 19, '2024-03-07 10:15:00'),
(8, 3, 2, 4, '小米14 Ultra的徕卡影像系统很强，但是手机有点重，长时间握持会累。', false, 21, '2024-03-11 13:40:00'),
(6, 14, 5, 5, '无线充电器很好用，充电速度快，支持多设备同时充电，性价比高。', false, 12, '2024-02-22 10:00:00'),
(10, 11, 8, 4, '连衣裙面料舒适，款式也很好看，就是颜色和图片稍有色差。', false, 8, '2024-04-03 15:20:00');

-- ================================================================
-- 创建索引以提高查询性能
-- ================================================================
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_vip_level ON users(vip_level);
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_brand ON products(brand);
CREATE INDEX idx_products_sales ON products(sales_count DESC);
CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created ON orders(created_at DESC);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);
CREATE INDEX idx_reviews_product ON reviews(product_id);
CREATE INDEX idx_reviews_user ON reviews(user_id);

-- ================================================================
-- 数据统计视图
-- ================================================================
CREATE OR REPLACE VIEW sales_summary AS
SELECT
    DATE_TRUNC('month', o.created_at) as month,
    COUNT(DISTINCT o.id) as order_count,
    COUNT(DISTINCT o.user_id) as customer_count,
    SUM(o.final_amount) as total_revenue,
    AVG(o.final_amount) as avg_order_value
FROM orders o
WHERE o.status != 'cancelled'
GROUP BY DATE_TRUNC('month', o.created_at)
ORDER BY month DESC;

-- ================================================================
-- 完成提示
-- ================================================================
SELECT '电商测试数据库初始化完成！' as message,
       (SELECT COUNT(*) FROM users) as user_count,
       (SELECT COUNT(*) FROM products) as product_count,
       (SELECT COUNT(*) FROM orders) as order_count,
       (SELECT COUNT(*) FROM reviews) as review_count;

