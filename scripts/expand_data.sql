-- 生成50000条新订单，集中在2024年，具有季节性波动
-- Step 1: 生成订单数据
WITH generated_data AS (
    SELECT 
        50000 + n as id,
        'ORD2024' || LPAD((50000 + n)::text, 8, '0') as order_no,
        1 + floor(random() * 10000)::int as user_id,
        1 + floor(random() * 5000)::int as address_id,
        (10000 + floor(random() * 4000000))::bigint as total_amount,
        (floor(random() * 2000))::bigint as discount_amount,
        CASE WHEN random() > 0.3 THEN 0 ELSE (500 + floor(random() * 1000))::bigint END as shipping_fee,
        random() as rnd_status,
        random() as rnd_payment,
        random() as rnd_date,
        random() as rnd_time,
        n
    FROM generate_series(1, 50000) as n
)
INSERT INTO orders (id, order_no, user_id, address_id, total_amount, discount_amount, shipping_fee, final_amount, status, payment_method, payment_time, shipping_time, completed_time, created_at, remark)
SELECT 
    id,
    order_no,
    user_id,
    address_id,
    total_amount,
    discount_amount,
    shipping_fee,
    total_amount - discount_amount + shipping_fee as final_amount,
    -- 订单状态分布
    CASE 
        WHEN rnd_status < 0.70 THEN 'completed'
        WHEN rnd_status < 0.85 THEN 'shipped'
        WHEN rnd_status < 0.95 THEN 'pending_shipment'
        ELSE 'pending_payment'
    END as status,
    -- 支付方式分布
    CASE 
        WHEN rnd_payment < 0.40 THEN 'alipay'
        WHEN rnd_payment < 0.75 THEN 'wechat'
        WHEN rnd_payment < 0.90 THEN 'credit_card'
        ELSE 'bank_transfer'
    END as payment_method,
    -- 创建时间：2024年全年，带季节性波动
    (timestamp '2024-01-01 00:00:00' + 
        CASE 
            WHEN rnd_date < 0.15 THEN interval '304 days' + (rnd_time * interval '15 days')  -- 双11高峰期
            WHEN rnd_date < 0.28 THEN interval '334 days' + (rnd_time * interval '20 days')  -- 双12高峰期
            WHEN rnd_date < 0.38 THEN interval '165 days' + (rnd_time * interval '10 days')  -- 618活动
            WHEN rnd_date < 0.42 THEN interval '31 days' + (rnd_time * interval '14 days')   -- 春节（低谷）
            ELSE (rnd_time * interval '365 days')  -- 其他时间均匀分布
        END + (random() * interval '23 hours'))::timestamp as payment_time,
    NULL as shipping_time,
    NULL as completed_time,
    (timestamp '2024-01-01 00:00:00' + 
        CASE 
            WHEN rnd_date < 0.15 THEN interval '304 days' + (rnd_time * interval '15 days')
            WHEN rnd_date < 0.28 THEN interval '334 days' + (rnd_time * interval '20 days')
            WHEN rnd_date < 0.38 THEN interval '165 days' + (rnd_time * interval '10 days')
            WHEN rnd_date < 0.42 THEN interval '31 days' + (rnd_time * interval '14 days')
            ELSE (rnd_time * interval '365 days')
        END)::timestamp as created_at,
    NULL as remark
FROM generated_data;

-- Step 2: 更新发货时间和完成时间（对于已发货和已完成的订单）
UPDATE orders 
SET 
    shipping_time = payment_time + (random() * interval '3 days'),
    completed_time = CASE 
        WHEN status = 'completed' THEN payment_time + (random() * interval '3 days') + (random() * interval '7 days')
        ELSE NULL
    END
WHERE id > 50000 AND status IN ('shipped', 'completed');

-- Step 3: 生成对应的order_items (每个订单1-3个商品)
WITH order_items_gen AS (
    SELECT 
        o.id as order_id,
        generate_series(1, 1 + floor(random() * 3)::int) as item_seq,
        1 + floor(random() * 500)::int as product_id,
        1 + floor(random() * 5)::int as quantity,
        (1000 + floor(random() * 50000))::bigint as unit_price
    FROM orders o 
    WHERE o.id > 50000
)
INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, discount_amount, subtotal, created_at)
SELECT 
    100000 + row_number() OVER () as id,
    order_id,
    product_id,
    quantity,
    unit_price,
    (floor(random() * 200))::bigint as discount_amount,
    quantity * unit_price as subtotal,
    (SELECT created_at FROM orders WHERE id = order_id) as created_at
FROM order_items_gen;

-- 输出统计信息
SELECT 'Orders count:' as metric, COUNT(*) as value FROM orders
UNION ALL
SELECT 'Order_items count:', COUNT(*) FROM order_items
UNION ALL
SELECT '2024 orders count:', COUNT(*) FROM orders WHERE EXTRACT(YEAR FROM created_at) = 2024;

