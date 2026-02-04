#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
电商测试数据库 Excel 文件生成脚本
生成 test_database_optimized.xlsx，包含大量演示数据

数据量规划：
- users: 1000+
- addresses: 1000+
- categories: 20-30
- products: 1000+
- orders: 5000+
- order_items: 15000+
- reviews: 3000+
"""

import pandas as pd
from faker import Faker
import random
from datetime import datetime, timedelta
from decimal import Decimal
import os

# 初始化 Faker (中文)
fake = Faker('zh_CN')
Faker.seed(42)
random.seed(42)

# ============================================
# 配置参数
# ============================================
OUTPUT_FILE = 'scripts/test_database_optimized.xlsx'
USER_COUNT = 1000
PRODUCT_COUNT = 1000
ORDER_COUNT = 5000
REVIEW_RATIO = 0.6  # 60% 的订单有评价

# 日期范围
DATE_START = datetime(2023, 1, 1)
DATE_END = datetime(2024, 12, 31)

# ============================================
# 数据模板
# ============================================

# 省份城市映射
PROVINCE_CITIES = {
    '北京市': ['东城区', '西城区', '朝阳区', '海淀区', '丰台区', '石景山区'],
    '上海市': ['黄浦区', '徐汇区', '长宁区', '静安区', '普陀区', '虹口区', '浦东新区'],
    '广东省': ['广州市', '深圳市', '珠海市', '佛山市', '东莞市', '中山市'],
    '浙江省': ['杭州市', '宁波市', '温州市', '嘉兴市', '湖州市', '绍兴市'],
    '江苏省': ['南京市', '无锡市', '徐州市', '常州市', '苏州市', '南通市'],
    '四川省': ['成都市', '绵阳市', '自贡市', '攀枝花市', '泸州市', '德阳市'],
    '湖北省': ['武汉市', '黄石市', '十堰市', '宜昌市', '襄阳市', '鄂州市'],
    '陕西省': ['西安市', '铜川市', '宝鸡市', '咸阳市', '渭南市', '延安市'],
    '山东省': ['济南市', '青岛市', '淄博市', '枣庄市', '东营市', '烟台市'],
    '河南省': ['郑州市', '开封市', '洛阳市', '平顶山市', '安阳市', '鹤壁市'],
    '福建省': ['福州市', '厦门市', '莆田市', '三明市', '泉州市', '漳州市'],
    '辽宁省': ['沈阳市', '大连市', '鞍山市', '抚顺市', '本溪市', '丹东市'],
    '湖南省': ['长沙市', '株洲市', '湘潭市', '衡阳市', '邵阳市', '岳阳市'],
    '安徽省': ['合肥市', '芜湖市', '蚌埠市', '淮南市', '马鞍山市', '淮北市'],
    '重庆市': ['万州区', '涪陵区', '渝中区', '大渡口区', '江北区', '沙坪坝区'],
    '天津市': ['和平区', '河东区', '河西区', '南开区', '河北区', '红桥区'],
    '河北省': ['石家庄市', '唐山市', '秦皇岛市', '邯郸市', '邢台市', '保定市'],
    '山西省': ['太原市', '大同市', '阳泉市', '长治市', '晋城市', '朔州市'],
    '江西省': ['南昌市', '景德镇市', '萍乡市', '九江市', '新余市', '鹰潭市'],
    '广西': ['南宁市', '柳州市', '桂林市', '梧州市', '北海市', '防城港市'],
    '云南省': ['昆明市', '曲靖市', '玉溪市', '保山市', '昭通市', '丽江市'],
    '贵州省': ['贵阳市', '六盘水市', '遵义市', '安顺市', '毕节市', '铜仁市'],
    '吉林省': ['长春市', '吉林市', '四平市', '辽源市', '通化市', '白山市'],
    '黑龙江省': ['哈尔滨市', '齐齐哈尔市', '鸡西市', '鹤岗市', '双鸭山市', '大庆市'],
    '内蒙古自治区': ['呼和浩特市', '包头市', '乌海市', '赤峰市', '通辽市', '鄂尔多斯市'],
    '甘肃省': ['兰州市', '嘉峪关市', '金昌市', '白银市', '天水市', '武威市'],
    '海南省': ['海口市', '三亚市', '三沙市', '儋州市', '琼海市', '文昌市'],
    '宁夏': ['银川市', '石嘴山市', '吴忠市', '固原市', '中卫市'],
    '青海省': ['西宁市', '海东市'],
    '西藏': ['拉萨市', '日喀则市'],
}

# 商品类别结构
CATEGORIES_DATA = [
    # 一级分类
    ('电子产品', None, '手机、电脑、数码配件等', 1),
    ('服装鞋包', None, '男装、女装、鞋类、箱包等', 2),
    ('家居生活', None, '家具、家纺、厨具等', 3),
    ('图书音像', None, '图书、电子书、音乐、影视等', 4),
    ('食品饮料', None, '零食、饮料、生鲜食品等', 5),
    ('美妆护肤', None, '化妆品、护肤品、个人护理等', 6),
    ('运动户外', None, '运动器材、户外装备、健身器材等', 7),
    ('母婴用品', None, '奶粉、尿布、童装、玩具等', 8),

    # 二级分类 - 电子产品
    ('手机通讯', 1, '智能手机、功能机、对讲机等', 10),
    ('电脑办公', 1, '笔记本、台式机、平板电脑等', 11),
    ('数码配件', 1, '耳机、充电器、数据线等', 12),
    ('摄影摄像', 1, '相机、摄像机、无人机等', 13),
    ('智能设备', 1, '智能手表、智能音箱、智能家居等', 14),

    # 二级分类 - 服装鞋包
    ('男装', 2, '衬衫、T恤、裤子、外套等', 20),
    ('女装', 2, '连衣裙、上衣、裤子、外套等', 21),
    ('鞋类', 2, '男鞋、女鞋、运动鞋、皮鞋等', 22),
    ('箱包', 2, '手提包、双肩包、旅行箱等', 23),
    ('配饰', 2, '腰带、围巾、帽子、手套等', 24),

    # 二级分类 - 家居生活
    ('家具', 3, '沙发、床、衣柜、餐桌等', 30),
    ('家纺', 3, '床品、窗帘、地毯、毛巾等', 31),
    ('厨具', 3, '锅具、刀具、餐具、保鲜盒等', 32),
    ('生活日用', 3, '纸品、清洁用品、收纳用品等', 33),
    ('灯具', 3, '台灯、吊灯、落地灯、装饰灯等', 34),

    # 二级分类 - 图书音像
    ('图书', 4, '文学、小说、经管、教育等', 40),
    ('电子书', 4, 'kindle电子书、有声读物等', 41),
    ('音乐', 4, 'CD、黑胶、音乐周边等', 42),
    ('影视', 4, 'DVD、蓝光、影视周边等', 43),

    # 二级分类 - 食品饮料
    ('零食', 5, '坚果、糖果、饼干、膨化等', 50),
    ('饮料', 5, '茶饮、咖啡、果汁、功能饮料等', 51),
    ('生鲜', 5, '水果、蔬菜、肉禽、水产等', 52),
    ('调味品', 5, '油盐酱醋、香料、调味酱等', 53),

    # 二级分类 - 美妆护肤
    ('面部护肤', 6, '面膜、乳液、精华、面霜等', 60),
    ('彩妆', 6, '口红、粉底、眼影、睫毛膏等', 61),
    ('香水', 6, '女士香水、男士香水、中性香水等', 62),
    ('个人护理', 6, '洗发、沐浴、口腔护理等', 63),

    # 二级分类 - 运动户外
    ('运动器材', 7, '跑步机、健身车、哑铃等', 70),
    ('户外装备', 7, '帐篷、睡袋、登山包等', 71),
    ('运动服饰', 7, '运动服、运动鞋、运动配件等', 72),

    # 二级分类 - 母婴用品
    ('奶粉喂养', 8, '奶粉、辅食、营养品等', 80),
    ('尿布湿巾', 8, '纸尿裤、湿巾、棉柔巾等', 81),
    ('童装童鞋', 8, '婴儿服、儿童服装、童鞋等', 82),
    ('玩具', 8, '益智玩具、积木、玩偶等', 83),
]

# 品牌列表
BRANDS = {
    10: ['Apple', '华为', '小米', 'OPPO', 'vivo', '三星', '荣耀', '一加', '真我', '摩托罗拉'],
    11: ['Apple', '联想', '戴尔', '华硕', '惠普', '微软', 'ThinkPad', '宏碁', '雷神', '机械革命'],
    12: ['Apple', '索尼', 'JBL', 'BOSE', '小米', '华为', '罗技', '雷蛇', '铁三角', '漫步者'],
    13: ['索尼', '佳能', '尼康', '富士', '大疆', 'GoPro', '奥林巴斯', '松下', '理光', '飞思'],
    14: ['Apple', '华为', '小米', '亚马逊', '百度', '阿里巴巴', '京东', '科大讯飞'],
    20: ['海澜之家', '七匹狼', '利郎', '雅戈尔', '九牧王', '杉杉', '罗蒙', '劲霸'],
    21: ['ONLY', 'VERO MODA', '欧时力', '太平鸟', '拉夏贝尔', '森马', '美特斯邦威', '韩都衣舍'],
    22: ['耐克', '阿迪达斯', '李宁', '安踏', '新百伦', '亚瑟士', '匹克', '特步'],
    23: ['新秀丽', '美旅', '外交官', '路易威登', '古驰', 'Coach', 'Michael Kors', 'Kate Spade'],
    24: ['七匹狼', '金利来', '皮尔卡丹', '恒源祥', '鄂尔多斯'],
    30: ['宜家', '顾家', '左右', '曲美', '红苹果', '全友', '林氏木业', '联邦'],
    31: ['罗莱', '富安娜', '水星', '博洋', '梦洁', '康尔馨', '雅兰'],
    32: ['双立人', '菲仕乐', 'WMF', '苏泊尔', '爱仕达', '康宁', '膳魔师', '象印'],
    33: ['维达', '清风', '心相印', '洁柔', '蓝月亮', '立白', '威露士', '滴露'],
    34: ['飞利浦', '欧普', '雷士', '三雄极光', '松下', 'Yeelight'],
    40: ['人民邮电', '机械工业', '清华大学', '北京大学', '中信', '浙江人民', '上海人民'],
    41: ['kindle', '微信读书', '掌阅', 'QQ阅读', '多看阅读'],
    42: ['环球', '华纳', '索尼音乐', '杰威尔', '英皇娱乐'],
    43: ['迪士尼', '华纳兄弟', '环球影业', '派拉蒙', '索尼影业'],
    50: ['三只松鼠', '百草味', '良品铺子', '来伊份', '洽洽', '旺旺', '徐福记', '奥利奥'],
    51: ['农夫山泉', '康师傅', '统一', '王老吉', '加多宝', '红牛', '星巴克', '雀巢'],
    52: ['天天果园', '易果生鲜', '盒马', '每日优鲜', '本来生活'],
    53: ['海天', '李锦记', '老干妈', '太太乐', '厨邦', '家乐', '味好美'],
    60: ['雅诗兰黛', '兰蔻', '欧莱雅', '资生堂', '玉兰油', '碧欧泉', '科颜氏', '悦木之源'],
    61: ['MAC', '迪奥', '香奈儿', 'YSL', '阿玛尼', 'Tom Ford', '纪梵希', 'NARS'],
    62: ['香奈儿', '迪奥', '爱马仕', '古驰', '祖马龙', 'Jo Malone', '汤姆·福特'],
    63: ['沙宣', '飘柔', '潘婷', '海飞丝', '舒肤佳', '多芬', '力士', '欧乐B'],
    70: ['舒华', '爱康', '乔山', '必艾奇', '麦瑞克', 'Keep', '小米'],
    71: ['探路者', '迪卡侬', '北面', '哥伦比亚', '牧高笛', '凯乐石', '瑞士军刀'],
    72: ['耐克', '阿迪达斯', '李宁', '安踏', 'Under Armour', 'Puma', '迪卡侬'],
    80: ['飞鹤', '伊利', '蒙牛', '惠氏', '美赞臣', '雅培', '雀巢', '贝拉米'],
    81: ['帮宝适', '好奇', '大王', '尤妮佳', '安儿乐', '妈咪宝贝', '茵茵'],
    82: ['巴拉巴拉', '安奈儿童装', 'MQD', '江博士', 'ABC Kids', '戴维贝拉'],
    83: ['乐高', '费雪', '芭比', '迪士尼', '孩之宝', '美泰', 'Hape', '布鲁可'],
}

# 商品名称模板
PRODUCT_TEMPLATES = {
    10: ['{brand} {model}手机', '{brand} {model} 5G智能手机', '{brand} {model} 骁龙8Gen3旗舰', '{brand} {model} 256GB',
          '{brand} {model} Pro版', '{brand} {model} Ultra', '{brand} 折叠屏 {model}'],
    11: ['{brand} {model} 笔记本电脑', '{brand} {model} 轻薄本', '{brand} {model} 游戏本', '{brand} {model} 商务本',
          '{brand} {model} i7处理器', '{brand} {model} 16GB内存', '{brand} {model} 2K屏'],
    12: ['{brand} {model} 蓝牙耳机', '{brand} {model} 降噪耳机', '{brand} {model} 充电宝', '{brand} {model} 数据线',
          '{brand} {model} 手机壳', '{brand} {model} 无线充电器', '{brand} {model} 转换器'],
    13: ['{brand} {model} 相机', '{brand} {model} 微单', '{brand} {model} 运动相机', '{brand} {model} 无人机',
          '{brand} {model} 镜头', '{brand} {model} 稳定器'],
    14: ['{brand} {model} 智能手表', '{brand} {model} 蓝牙音箱', '{brand} {model} 智能手环', '{brand} {model} 路由器',
          '{brand} {model} 扫地机器人', '{brand} {model} 空气净化器'],
    20: ['{brand} {type} 长袖衬衫', '{brand} {type} T恤', '{brand} {type} 西装裤', '{brand} {type} 夹克',
          '{brand} {type} 卫衣', '{brand} {type} 羽绒服', '{brand} {type} 西装'],
    21: ['{brand} {type} 连衣裙', '{brand} {type} 针织衫', '{brand} {type} 半身裙', '{brand} {type} 大衣',
          '{brand} {type} 毛衣', '{brand} {type} 衬衫', '{brand} {type} 风衣'],
    22: ['{brand} {type} 跑鞋', '{brand} {type} 篮球鞋', '{brand} {type} 板鞋', '{brand} {type} 休闲鞋',
          '{brand} {type} 凉鞋', '{brand} {type} 靴子'],
    23: ['{brand} {type} 双肩包', '{brand} {type} 单肩包', '{brand} {type} 手提包', '{brand} {type} 旅行箱',
          '{brand} {type} 钱包', '{brand} {type} 背包'],
    24: ['{brand} {type} 腰带', '{brand} {type} 围巾', '{brand} {type} 帽子', '{brand} {type} 手套',
          '{brand} {type} 袜子', '{brand} {type} 领带'],
}

PRODUCT_TYPES = {
    20: ['商务', '休闲', '修身', '宽松', '免烫', '透气'],
    21: ['气质', '修身', '韩版', '复古', '简约', '优雅'],
    22: ['透气', '减震', '轻便', '防滑', '耐磨'],
    23: ['大容量', '轻薄', '防水', '复古', '简约'],
    24: ['真皮', 'PU皮', '棉质', '羊毛'],
}

# 评价内容模板
REVIEW_TEMPLATES = {
    5: [
        '非常满意！{product}质量很好，物流也很快。',
        '超级棒！{product}超出了我的预期，强烈推荐！',
        '质量非常好，{product}做工精细，包装也很用心。',
        '{product}收到了，和描述一致，性价比很高！',
        '五星好评！{product}真的很不错，会回购。',
        '太满意了！{product}质量好，价格实惠，服务态度也好。',
        '{product}很不错，使用体验很好，推荐购买。',
        '质量一流，{product}物美价廉，值得购买！',
        '非常棒的购物体验，{product}品质有保障。',
        '{product}收到了，非常喜欢，质量超出预期！',
    ],
    4: [
        '{product}质量不错，就是物流有点慢。',
        '整体还好，{product}性价比可以接受。',
        '{product}还不错，有点小瑕疵但不影响使用。',
        '质量可以，{product}和图片基本一致。',
        '{product}还行，价格合理，服务也OK。',
    ],
    3: [
        '{product}一般吧，没有想象中那么好。',
        '质量还行，{product}就是包装不太好。',
        '{product}中规中矩，无功无过。',
    ],
    2: [
        '{product}质量一般，不太推荐。',
        '有点失望，{product}和描述有点出入。',
    ],
    1: [
        '质量太差了，{product}不推荐购买。',
        '非常不满意，{product}和图片完全不一样。',
    ],
}

# ============================================
# 辅助函数
# ============================================


def random_date(start, end):
    """生成随机日期"""
    delta = end - start
    random_days = random.randint(0, delta.days)
    return start + timedelta(days=random_days)


def random_datetime(start, end):
    """生成随机日期时间"""
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)


def generate_phone():
    """生成随机手机号"""
    prefixes = ['130', '131', '132', '133', '134', '135', '136', '137', '138', '139',
                '150', '151', '152', '153', '155', '156', '157', '158', '159',
                '180', '181', '182', '183', '184', '185', '186', '187', '188', '189']
    prefix = random.choice(prefixes)
    suffix = ''.join([str(random.randint(0, 9)) for _ in range(8)])
    return prefix + suffix


def generate_sku(category_id, product_id):
    """生成SKU编码"""
    category_code = f'{category_id:02d}'
    product_code = f'{product_id:04d}'
    return f'SKU-{category_code}-{product_code}'


def generate_order_no(date, seq):
    """生成订单号"""
    date_str = date.strftime('%Y%m%d')
    return f'ORD{date_str}{seq:04d}'


def chinese_pinyin(name):
    """简单模拟拼音邮箱"""
    # 简化处理：随机生成拼音风格的邮箱
    prefix = ''.join([c for c in name if '\u4e00' <= c <= '\u9fff'])[:3]
    return f'{prefix}{random.randint(100, 999)}@email.com'


# ============================================
# 数据生成函数
# ============================================


def generate_categories():
    """生成商品类别数据"""
    print("生成类别数据...")
    categories = []
    for idx, (name, parent_id, description, sort_order) in enumerate(CATEGORIES_DATA, start=1):
        categories.append({
            'id': idx,
            'name': name,
            'parent_id': parent_id,
            'description': description,
            'sort_order': sort_order,
        })

    # 创建类别ID映射
    category_map = {c['name']: c['id'] for c in categories}

    return pd.DataFrame(categories), category_map


def generate_users(count):
    """生成用户数据"""
    print(f"生成 {count} 个用户...")
    users = []
    vip_weights = [50, 30, 15, 5]  # VIP等级权重

    for i in range(1, count + 1):
        last_name = random.choice(['张', '李', '王', '刘', '陈', '杨', '赵', '黄', '周', '吴',
                                   '徐', '孙', '胡', '朱', '高', '林', '何', '郭', '马', '罗'])
        first_name = random.choice(['伟', '芳', '娜', '秀英', '敏', '静', '丽', '强', '磊', '军',
                                    '洋', '勇', '艳', '杰', '娟', '涛', '明', '超', '秀兰', '霞',
                                    '平', '刚', '桂英', '玉兰', '萍', '毅', '浩', '宇', '思', '梦'])
        username = f"{last_name}{first_name}"
        if i > 100:  # 添加数字避免重复
            username += str(random.randint(10, 99))

        registration_date = random_date(DATE_START, DATE_END)

        users.append({
            'id': i,
            'username': username,
            'email': f'user{i}@email.com',
            'phone': generate_phone(),
            'gender': random.choice(['男', '女', None]),
            'birth_date': random_date(datetime(1970, 1, 1), datetime(2005, 12, 31)),
            'registration_date': registration_date,
            'vip_level': random.choices([0, 1, 2, 3], weights=vip_weights)[0],
            'total_spent': round(random.uniform(0, 50000), 2),
            'is_active': random.random() > 0.05,  # 95% 活跃
        })

    return pd.DataFrame(users)


def generate_addresses(users_df):
    """生成收货地址数据"""
    print(f"生成 {len(users_df)} 个地址...")
    addresses = []
    provinces = list(PROVINCE_CITIES.keys())

    for idx, user in users_df.iterrows():
        province = random.choice(provinces)
        cities = PROVINCE_CITIES[province]
        city = random.choice(cities)

        # 如果是直辖市，district从城市列表选
        if province in ['北京市', '上海市', '天津市', '重庆市']:
            district = random.choice([c for c in cities if c.endswith('区') or c.endswith('县')])
            city = province
        else:
            districts = ['朝阳区', '海淀区', '浦东新区', '天河区', '福田区', '西湖区', '鼓楼区', '江汉区', '雁塔区']
            district = random.choice(districts)

        addresses.append({
            'id': idx + 1,
            'user_id': user['id'],
            'province': province,
            'city': city,
            'district': district,
            'detail_address': f'{random.choice(["建设路", "人民路", "解放路", "中山路", "和平路", "文化路"])}{random.randint(1, 999)}号',
            'is_default': True,
        })

    return pd.DataFrame(addresses)


def generate_products(count, categories_df):
    """生成商品数据"""
    print(f"生成 {count} 个商品...")
    products = []

    # 获取二级分类ID
    leaf_categories = categories_df[categories_df['parent_id'].notna()]

    for i in range(1, count + 1):
        category = leaf_categories.sample(1).iloc[0]
        category_id = int(category['id'])
        category_name = category['name']

        # 选择品牌
        brands = BRANDS.get(category_id, ['品牌A', '品牌B', '品牌C', '品牌D'])
        brand = random.choice(brands)

        # 生成商品名称
        templates = PRODUCT_TEMPLATES.get(category_id, ['{brand} {category} 商品{model}'])
        template = random.choice(templates)

        model = random.choice(['Pro', 'Max', 'Ultra', 'Plus', 'Premium', 'Elite',
                               'X1', 'X2', 'X3', 'S1', 'S2', 'LITE', '标准版'])

        # 如果需要type参数
        if '{type}' in template:
            product_type = random.choice(PRODUCT_TYPES.get(category_id, ['通用']))
            name = template.format(brand=brand, type=product_type, model=model)
        else:
            name = template.format(brand=brand, category=category_name, model=model)

        # 价格范围根据类别
        if category_id in [10, 11, 13]:  # 手机、电脑、相机
            price = random.uniform(500, 20000)
        elif category_id in [12, 14]:  # 配件、智能设备
            price = random.uniform(50, 5000)
        elif category_id in [20, 21, 22]:  # 服装鞋包
            price = random.uniform(50, 2000)
        elif category_id in [30, 31, 32]:  # 家居
            price = random.uniform(100, 10000)
        elif category_id in [40, 41, 42, 43]:  # 图书音像
            price = random.uniform(10, 500)
        elif category_id in [50, 51, 52, 53]:  # 食品
            price = random.uniform(5, 500)
        elif category_id in [60, 61, 62, 63]:  # 美妆
            price = random.uniform(20, 3000)
        else:
            price = random.uniform(10, 5000)

        price = round(price, 2)
        original_price = round(price * random.uniform(1.0, 1.5), 2)

        # 评分偏向高分
        rating = round(random.uniform(3.5, 5.0), 2)

        products.append({
            'id': i,
            'name': name,
            'category_id': category_id,
            'sku': generate_sku(category_id, i),
            'price': price,
            'original_price': original_price if random.random() > 0.3 else None,
            'stock': random.randint(0, 1000),
            'sales_count': random.randint(0, 5000),
            'rating': rating,
            'review_count': random.randint(0, 1000),
            'brand': brand,
            'description': f'{brand}正品{category_name}，品质保证，售后无忧。',
            'is_on_sale': random.random() > 0.1,  # 90% 在售
            'created_at': random_date(DATE_START, DATE_END),
        })

    return pd.DataFrame(products)


def generate_orders(count, users_df, addresses_df, products_df):
    """生成订单数据"""
    print(f"生成 {count} 个订单...")
    orders = []
    order_items = []

    statuses = ['pending', 'paid', 'shipped', 'completed', 'cancelled']
    status_weights = [5, 10, 15, 60, 10]  # 权重
    payment_methods = ['支付宝', '微信支付', '银行卡', 'Apple Pay', '云闪付']

    for i in range(1, count + 1):
        user = users_df.sample(1).iloc[0]
        user_id = int(user['id'])

        # 获取用户地址
        user_addresses = addresses_df[addresses_df['user_id'] == user_id]
        if len(user_addresses) == 0:
            address_id = addresses_df.sample(1).iloc[0]['id']
        else:
            address_id = user_addresses.sample(1).iloc[0]['id']

        # 订单日期
        order_date = random_datetime(DATE_START, DATE_END)

        # 选择商品
        num_items = random.randint(1, 5)
        selected_products = products_df.sample(num_items)

        total_amount = 0
        for _, product in selected_products.iterrows():
            quantity = random.randint(1, 3)
            price = float(product['price'])
            subtotal = price * quantity
            total_amount += subtotal

            order_items.append({
                'id': len(order_items) + 1,
                'order_id': i,
                'product_id': int(product['id']),
                'product_name': product['name'],
                'sku': product['sku'],
                'price': price,
                'quantity': quantity,
                'subtotal': round(subtotal, 2),
            })

        # 折扣和运费
        discount_amount = round(total_amount * random.uniform(0, 0.1), 2) if total_amount > 100 else 0
        shipping_fee = 0 if total_amount >= 99 else round(random.uniform(5, 20), 2)
        final_amount = round(total_amount - discount_amount + shipping_fee, 2)

        # 订单状态
        status = random.choices(statuses, weights=status_weights)[0]

        # 根据状态设置时间戳
        payment_time = None
        shipping_time = None
        completed_time = None

        if status in ['paid', 'shipped', 'completed']:
            payment_time = order_date + timedelta(hours=random.randint(1, 24))
        if status in ['shipped', 'completed']:
            shipping_time = payment_time + timedelta(days=random.randint(1, 3))
        if status == 'completed':
            completed_time = shipping_time + timedelta(days=random.randint(1, 7))

        orders.append({
            'id': i,
            'order_no': generate_order_no(order_date, i % 10000),
            'user_id': user_id,
            'address_id': int(address_id),
            'total_amount': round(total_amount, 2),
            'discount_amount': discount_amount,
            'shipping_fee': shipping_fee,
            'final_amount': final_amount,
            'status': status,
            'payment_method': random.choice(payment_methods) if status != 'pending' else None,
            'payment_time': payment_time,
            'shipping_time': shipping_time,
            'completed_time': completed_time,
            'created_at': order_date,
            'remark': random.choice(['', '请尽快发货', '周末配送', '当面点清', '小心轻放']),
        })

    return pd.DataFrame(orders), pd.DataFrame(order_items)


def generate_reviews(orders_df, products_df, users_df):
    """生成评价数据"""
    print("生成评价数据...")

    # 只对已完成订单生成评价
    completed_orders = orders_df[orders_df['status'] == 'completed']
    review_orders = completed_orders.sample(int(len(completed_orders) * REVIEW_RATIO))

    reviews = []

    for idx, order in review_orders.iterrows():
        # 每个订单随机评价1-2个商品
        # 这里简化处理，假设每个订单评价1个随机商品
        order_id = int(order['id'])

        # 获取订单商品（需要从order_items获取）
        # 这里简化处理，随机选择一个商品
        product_id = random.randint(1, min(1000, len(products_df)))

        product = products_df[products_df['id'] == product_id]
        if len(product) == 0:
            continue
        product_name = product.iloc[0]['name']

        user_id = int(order['user_id'])

        # 评分偏向高分
        rating_weights = [2, 5, 10, 30, 53]  # 1-5星的权重
        rating = random.choices([1, 2, 3, 4, 5], weights=rating_weights)[0]

        # 评价内容
        templates = REVIEW_TEMPLATES.get(rating, REVIEW_TEMPLATES[5])
        content = random.choice(templates).format(product=product_name)

        # 评价时间（订单完成后1-7天）
        if pd.notna(order['completed_time']):
            review_date = order['completed_time'] + timedelta(days=random.randint(1, 7))
        else:
            review_date = order['created_at'] + timedelta(days=random.randint(3, 14))

        reviews.append({
            'id': len(reviews) + 1,
            'order_id': order_id,
            'product_id': product_id,
            'user_id': user_id,
            'rating': rating,
            'content': content,
            'is_anonymous': random.random() > 0.7,
            'helpful_count': random.randint(0, 50),
            'created_at': review_date,
        })

    return pd.DataFrame(reviews)


# ============================================
# 主函数
# ============================================


def main():
    """主函数：生成所有数据并写入Excel"""
    print("=" * 60)
    print("电商测试数据库 Excel 文件生成")
    print("=" * 60)

    # 1. 生成类别
    categories_df, category_map = generate_categories()
    print(f"  - 类别: {len(categories_df)} 条")

    # 2. 生成用户
    users_df = generate_users(USER_COUNT)
    print(f"  - 用户: {len(users_df)} 条")

    # 3. 生成地址
    addresses_df = generate_addresses(users_df)
    print(f"  - 地址: {len(addresses_df)} 条")

    # 4. 生成商品
    products_df = generate_products(PRODUCT_COUNT, categories_df)
    print(f"  - 商品: {len(products_df)} 条")

    # 5. 生成订单和订单明细
    orders_df, order_items_df = generate_orders(ORDER_COUNT, users_df, addresses_df, products_df)
    print(f"  - 订单: {len(orders_df)} 条")
    print(f"  - 订单明细: {len(order_items_df)} 条")

    # 6. 生成评价
    reviews_df = generate_reviews(orders_df, products_df, users_df)
    print(f"  - 评价: {len(reviews_df)} 条")

    # 7. 写入Excel文件
    print(f"\n写入 Excel 文件: {OUTPUT_FILE}")

    with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
        categories_df.to_excel(writer, sheet_name='categories', index=False)
        users_df.to_excel(writer, sheet_name='users', index=False)
        addresses_df.to_excel(writer, sheet_name='addresses', index=False)
        products_df.to_excel(writer, sheet_name='products', index=False)
        orders_df.to_excel(writer, sheet_name='orders', index=False)
        order_items_df.to_excel(writer, sheet_name='order_items', index=False)
        reviews_df.to_excel(writer, sheet_name='reviews', index=False)

    print("\n" + "=" * 60)
    print("生成完成！")
    print("=" * 60)
    print(f"\n文件: {OUTPUT_FILE}")
    print(f"大小: {os.path.getsize(OUTPUT_FILE) / 1024 / 1024:.2f} MB")

    # 数据统计
    print("\n数据统计:")
    print(f"  users:        {len(users_df)} 行")
    print(f"  addresses:    {len(addresses_df)} 行")
    print(f"  categories:   {len(categories_df)} 行")
    print(f"  products:     {len(products_df)} 行")
    print(f"  orders:       {len(orders_df)} 行")
    print(f"  order_items:  {len(order_items_df)} 行")
    print(f"  reviews:      {len(reviews_df)} 行")

    # 订单状态分布
    print("\n订单状态分布:")
    status_counts = orders_df['status'].value_counts()
    for status, count in status_counts.items():
        print(f"  {status}: {count}")

    # 评分分布
    print("\n评分分布:")
    rating_counts = reviews_df['rating'].value_counts().sort_index()
    for rating, count in rating_counts.items():
        print(f"  {rating}星: {count}")


if __name__ == '__main__':
    main()
