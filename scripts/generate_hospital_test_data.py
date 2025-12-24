#!/usr/bin/env python3
"""
生成医院健康管理系统测试数据
包含多个相关联的工作表，用于测试完整的数据上传和查询流程
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

# 设置随机种子保证可重复性
np.random.seed(42)
random.seed(42)

# ==================== 基础数据定义 ====================

# 中文姓名生成
SURNAMES = ['张', '王', '李', '赵', '刘', '陈', '杨', '黄', '周', '吴', '徐', '孙', '马', '朱', '胡', '郭', '何', '林', '高', '罗']
MALE_NAMES = ['伟', '强', '磊', '军', '杰', '勇', '涛', '明', '超', '刚', '平', '辉', '鹏', '斌', '华', '亮', '建', '峰', '浩', '宇']
FEMALE_NAMES = ['芳', '娟', '敏', '静', '丽', '艳', '娜', '秀英', '玲', '燕', '红', '慧', '婷', '雪', '萍', '梅', '霞', '倩', '琴', '蕾']

# 科室信息
DEPARTMENTS = [
    {'id': 1, 'name': '内科', 'category': '临床科室', 'floor': 2, 'head_doctor_id': 1},
    {'id': 2, 'name': '外科', 'category': '临床科室', 'floor': 3, 'head_doctor_id': 5},
    {'id': 3, 'name': '儿科', 'category': '临床科室', 'floor': 4, 'head_doctor_id': 9},
    {'id': 4, 'name': '妇产科', 'category': '临床科室', 'floor': 5, 'head_doctor_id': 12},
    {'id': 5, 'name': '骨科', 'category': '临床科室', 'floor': 3, 'head_doctor_id': 15},
    {'id': 6, 'name': '神经内科', 'category': '临床科室', 'floor': 6, 'head_doctor_id': 18},
    {'id': 7, 'name': '心血管科', 'category': '临床科室', 'floor': 7, 'head_doctor_id': 20},
    {'id': 8, 'name': '皮肤科', 'category': '临床科室', 'floor': 2, 'head_doctor_id': 22},
    {'id': 9, 'name': '眼科', 'category': '临床科室', 'floor': 4, 'head_doctor_id': 24},
    {'id': 10, 'name': '急诊科', 'category': '临床科室', 'floor': 1, 'head_doctor_id': 26},
    {'id': 11, 'name': '放射科', 'category': '医技科室', 'floor': 1, 'head_doctor_id': 28},
    {'id': 12, 'name': '检验科', 'category': '医技科室', 'floor': 1, 'head_doctor_id': 29},
]

# 医生职称
TITLES = ['主任医师', '副主任医师', '主治医师', '住院医师']
TITLE_WEIGHTS = [0.15, 0.25, 0.35, 0.25]

# 诊断病症（按科室分类）
DIAGNOSES = {
    1: ['感冒', '支气管炎', '肺炎', '高血压', '糖尿病', '胃炎', '肝炎'],  # 内科
    2: ['阑尾炎', '疝气', '胆结石', '甲状腺结节', '痔疮'],  # 外科
    3: ['小儿感冒', '小儿腹泻', '小儿肺炎', '手足口病', '水痘'],  # 儿科
    4: ['产检', '妊娠期高血压', '先兆流产', '月经不调', '盆腔炎'],  # 妇产科
    5: ['骨折', '腰椎间盘突出', '颈椎病', '关节炎', '骨质疏松'],  # 骨科
    6: ['头痛', '眩晕', '失眠', '癫痫', '帕金森病'],  # 神经内科
    7: ['冠心病', '心律不齐', '心肌梗死', '心力衰竭', '高血脂'],  # 心血管科
    8: ['湿疹', '荨麻疹', '银屑病', '痤疮', '皮炎'],  # 皮肤科
    9: ['近视', '白内障', '青光眼', '结膜炎', '干眼症'],  # 眼科
    10: ['急性腹痛', '外伤', '急性胸痛', '中暑', '食物中毒'],  # 急诊科
    11: ['CT检查', 'X光检查', 'MRI检查', 'B超检查'],  # 放射科
    12: ['血常规', '尿常规', '肝功能', '肾功能', '血糖检测'],  # 检验科
}

# 药品信息
MEDICATIONS = [
    {'id': 1, 'name': '阿莫西林胶囊', 'category': '抗生素', 'unit': '盒', 'price': 15.00, 'stock': 500, 'manufacturer': '华北制药'},
    {'id': 2, 'name': '布洛芬缓释胶囊', 'category': '解热镇痛', 'unit': '盒', 'price': 18.50, 'stock': 350, 'manufacturer': '扬子江药业'},
    {'id': 3, 'name': '奥美拉唑肠溶胶囊', 'category': '消化系统', 'unit': '盒', 'price': 28.00, 'stock': 280, 'manufacturer': '阿斯利康'},
    {'id': 4, 'name': '硝苯地平缓释片', 'category': '心血管', 'unit': '盒', 'price': 35.00, 'stock': 200, 'manufacturer': '拜耳'},
    {'id': 5, 'name': '二甲双胍片', 'category': '降糖药', 'unit': '盒', 'price': 12.00, 'stock': 400, 'manufacturer': '中美施贵宝'},
    {'id': 6, 'name': '氯雷他定片', 'category': '抗过敏', 'unit': '盒', 'price': 22.00, 'stock': 300, 'manufacturer': '先声药业'},
    {'id': 7, 'name': '阿托伐他汀钙片', 'category': '心血管', 'unit': '盒', 'price': 45.00, 'stock': 180, 'manufacturer': '辉瑞'},
    {'id': 8, 'name': '头孢克肟分散片', 'category': '抗生素', 'unit': '盒', 'price': 32.00, 'stock': 250, 'manufacturer': '石药集团'},
    {'id': 9, 'name': '复方甘草片', 'category': '呼吸系统', 'unit': '盒', 'price': 8.00, 'stock': 600, 'manufacturer': '云南白药'},
    {'id': 10, 'name': '蒙脱石散', 'category': '消化系统', 'unit': '盒', 'price': 25.00, 'stock': 320, 'manufacturer': '博福-益普生'},
    {'id': 11, 'name': '葡萄糖注射液', 'category': '输液', 'unit': '瓶', 'price': 5.50, 'stock': 1000, 'manufacturer': '科伦药业'},
    {'id': 12, 'name': '生理盐水', 'category': '输液', 'unit': '瓶', 'price': 3.00, 'stock': 1200, 'manufacturer': '华润双鹤'},
    {'id': 13, 'name': '左氧氟沙星片', 'category': '抗生素', 'unit': '盒', 'price': 38.00, 'stock': 220, 'manufacturer': '第一三共'},
    {'id': 14, 'name': '氨氯地平片', 'category': '心血管', 'unit': '盒', 'price': 42.00, 'stock': 190, 'manufacturer': '辉瑞'},
    {'id': 15, 'name': '泮托拉唑钠肠溶胶囊', 'category': '消化系统', 'unit': '盒', 'price': 55.00, 'stock': 150, 'manufacturer': '武田制药'},
    {'id': 16, 'name': '维生素C片', 'category': '维生素', 'unit': '瓶', 'price': 6.00, 'stock': 800, 'manufacturer': '华北制药'},
    {'id': 17, 'name': '钙尔奇D', 'category': '维生素', 'unit': '瓶', 'price': 68.00, 'stock': 160, 'manufacturer': '惠氏'},
    {'id': 18, 'name': '感冒灵颗粒', 'category': '呼吸系统', 'unit': '盒', 'price': 12.50, 'stock': 450, 'manufacturer': '999'},
    {'id': 19, 'name': '板蓝根颗粒', 'category': '中成药', 'unit': '盒', 'price': 15.00, 'stock': 380, 'manufacturer': '白云山'},
    {'id': 20, 'name': '连花清瘟胶囊', 'category': '中成药', 'unit': '盒', 'price': 28.00, 'stock': 420, 'manufacturer': '以岭药业'},
]

# 城市和地区
CITIES = ['北京市', '上海市', '广州市', '深圳市', '杭州市', '南京市', '成都市', '武汉市', '西安市', '重庆市']
DISTRICTS = {
    '北京市': ['朝阳区', '海淀区', '东城区', '西城区', '丰台区', '通州区'],
    '上海市': ['浦东新区', '徐汇区', '静安区', '黄浦区', '杨浦区', '长宁区'],
    '广州市': ['天河区', '越秀区', '海珠区', '白云区', '番禺区', '黄埔区'],
    '深圳市': ['福田区', '南山区', '罗湖区', '宝安区', '龙岗区', '龙华区'],
    '杭州市': ['西湖区', '上城区', '拱墅区', '滨江区', '余杭区', '萧山区'],
    '南京市': ['玄武区', '秦淮区', '鼓楼区', '建邺区', '栖霞区', '江宁区'],
    '成都市': ['武侯区', '锦江区', '青羊区', '金牛区', '成华区', '高新区'],
    '武汉市': ['武昌区', '洪山区', '江岸区', '江汉区', '汉阳区', '青山区'],
    '西安市': ['雁塔区', '碑林区', '新城区', '未央区', '莲湖区', '长安区'],
    '重庆市': ['渝中区', '江北区', '南岸区', '沙坪坝区', '九龙坡区', '渝北区'],
}

# 医保类型
INSURANCE_TYPES = ['城镇职工医保', '城镇居民医保', '新农合', '商业保险', '自费']
INSURANCE_WEIGHTS = [0.35, 0.25, 0.15, 0.10, 0.15]

# 血型
BLOOD_TYPES = ['A型', 'B型', 'O型', 'AB型']
BLOOD_WEIGHTS = [0.28, 0.24, 0.36, 0.12]

# 就诊类型
VISIT_TYPES = ['门诊', '急诊', '住院', '复诊', '体检']
VISIT_WEIGHTS = [0.45, 0.10, 0.15, 0.25, 0.05]


def generate_name(gender):
    """生成中文姓名"""
    surname = random.choice(SURNAMES)
    if gender == '男':
        name = random.choice(MALE_NAMES)
    else:
        name = random.choice(FEMALE_NAMES)
    return surname + name


def generate_phone():
    """生成手机号"""
    prefixes = ['130', '131', '132', '133', '134', '135', '136', '137', '138', '139',
                '150', '151', '152', '153', '155', '156', '157', '158', '159',
                '170', '171', '172', '173', '175', '176', '177', '178',
                '180', '181', '182', '183', '184', '185', '186', '187', '188', '189']
    return random.choice(prefixes) + ''.join([str(random.randint(0, 9)) for _ in range(8)])


def generate_id_card(birth_date, gender):
    """生成身份证号（模拟）"""
    # 区域码（随机选择）
    area_codes = ['110101', '310101', '440103', '440305', '330102', '320102', '510104', '420102', '610102', '500103']
    area = random.choice(area_codes)
    
    # 出生日期
    birth_str = birth_date.strftime('%Y%m%d')
    
    # 顺序码（奇数为男，偶数为女）
    if gender == '男':
        seq = str(random.randint(0, 49) * 2 + 1).zfill(3)
    else:
        seq = str(random.randint(0, 49) * 2).zfill(3)
    
    # 校验码（简化处理）
    check = random.choice('0123456789X')
    
    return area + birth_str + seq + check


def generate_address():
    """生成地址"""
    city = random.choice(CITIES)
    district = random.choice(DISTRICTS[city])
    street_num = random.randint(1, 200)
    building = random.randint(1, 30)
    unit = random.randint(1, 6)
    room = random.randint(101, 2505)
    return f"{city}{district}某某路{street_num}号{building}栋{unit}单元{room}室"


# ==================== 数据生成函数 ====================

def generate_patients(n=200):
    """生成患者数据"""
    patients = []
    for i in range(1, n + 1):
        gender = random.choice(['男', '女'])
        # 年龄分布：儿童15%，青年30%，中年35%，老年20%
        age_group = np.random.choice(['child', 'young', 'middle', 'old'], p=[0.15, 0.30, 0.35, 0.20])
        if age_group == 'child':
            age = random.randint(1, 17)
        elif age_group == 'young':
            age = random.randint(18, 35)
        elif age_group == 'middle':
            age = random.randint(36, 55)
        else:
            age = random.randint(56, 85)
        
        birth_date = datetime.now() - timedelta(days=age * 365 + random.randint(0, 364))
        
        patients.append({
            '患者ID': f'P{str(i).zfill(5)}',
            '姓名': generate_name(gender),
            '性别': gender,
            '年龄': age,
            '出生日期': birth_date.strftime('%Y-%m-%d'),
            '身份证号': generate_id_card(birth_date, gender),
            '联系电话': generate_phone(),
            '血型': np.random.choice(BLOOD_TYPES, p=BLOOD_WEIGHTS),
            '医保类型': np.random.choice(INSURANCE_TYPES, p=INSURANCE_WEIGHTS),
            '联系地址': generate_address(),
            '紧急联系人': generate_name(random.choice(['男', '女'])),
            '紧急联系电话': generate_phone(),
            '过敏史': random.choice(['无', '青霉素', '磺胺类', '海鲜', '花粉', '无', '无', '无']),
            '建档日期': (datetime.now() - timedelta(days=random.randint(30, 1000))).strftime('%Y-%m-%d'),
        })
    return pd.DataFrame(patients)


def generate_doctors(n=30):
    """生成医生数据"""
    doctors = []
    dept_idx = 0
    for i in range(1, n + 1):
        gender = random.choice(['男', '女'])
        age = random.randint(28, 60)
        # 职称与年龄相关
        if age < 32:
            title = '住院医师'
        elif age < 38:
            title = np.random.choice(['住院医师', '主治医师'], p=[0.3, 0.7])
        elif age < 48:
            title = np.random.choice(['主治医师', '副主任医师'], p=[0.4, 0.6])
        else:
            title = np.random.choice(['副主任医师', '主任医师'], p=[0.4, 0.6])
        
        # 轮流分配到各科室
        dept_id = (i % 12) + 1 if i > 12 else i
        dept_name = DEPARTMENTS[dept_id - 1]['name']
        
        # 工作年限
        work_years = age - 25 - random.randint(0, 3)
        if work_years < 1:
            work_years = 1
        
        doctors.append({
            '医生ID': f'D{str(i).zfill(4)}',
            '姓名': generate_name(gender),
            '性别': gender,
            '年龄': age,
            '职称': title,
            '科室ID': dept_id,
            '科室名称': dept_name,
            '工作年限': work_years,
            '联系电话': generate_phone(),
            '邮箱': f'doctor{i}@hospital.com',
            '擅长领域': random.choice(DIAGNOSES.get(dept_id, ['常见病'])) + '、' + random.choice(DIAGNOSES.get(dept_id, ['多发病'])),
            '门诊费用': random.choice([20, 30, 50, 80, 100]) if title in ['住院医师', '主治医师'] else random.choice([100, 150, 200, 300]),
            '出诊时间': random.choice(['周一至周五', '周一三五', '周二四六', '周一至周六']),
            '是否专家': '是' if title in ['主任医师', '副主任医师'] else '否',
        })
    return pd.DataFrame(doctors)


def generate_departments():
    """生成科室数据"""
    depts = []
    for dept in DEPARTMENTS:
        depts.append({
            '科室ID': dept['id'],
            '科室名称': dept['name'],
            '科室类别': dept['category'],
            '所在楼层': dept['floor'],
            '科室主任ID': f"D{str(dept['head_doctor_id']).zfill(4)}",
            '床位数': random.randint(20, 80) if dept['category'] == '临床科室' else 0,
            '已占床位': random.randint(10, 60) if dept['category'] == '临床科室' else 0,
            '联系电话': f"010-8888{str(dept['id']).zfill(4)}",
            '科室简介': f"{dept['name']}是我院重点科室，拥有先进的医疗设备和专业的医疗团队。",
        })
    return pd.DataFrame(depts)


def generate_appointments(patients_df, doctors_df, n=500):
    """生成挂号记录"""
    appointments = []
    patient_ids = patients_df['患者ID'].tolist()
    doctor_ids = doctors_df['医生ID'].tolist()
    
    # 生成过去一年的挂号记录
    start_date = datetime.now() - timedelta(days=365)
    
    for i in range(1, n + 1):
        patient_id = random.choice(patient_ids)
        doctor_row = doctors_df.sample(1).iloc[0]
        doctor_id = doctor_row['医生ID']
        dept_id = doctor_row['科室ID']
        dept_name = doctor_row['科室名称']
        
        # 挂号日期
        appt_date = start_date + timedelta(days=random.randint(0, 365))
        
        # 挂号时间段
        time_slot = random.choice(['08:00-09:00', '09:00-10:00', '10:00-11:00', '11:00-12:00',
                                   '14:00-15:00', '15:00-16:00', '16:00-17:00'])
        
        # 就诊类型
        visit_type = np.random.choice(VISIT_TYPES, p=VISIT_WEIGHTS)
        
        # 挂号状态（大部分已完成）
        if appt_date.date() < datetime.now().date():
            status = np.random.choice(['已完成', '已取消', '爽约'], p=[0.85, 0.10, 0.05])
        else:
            status = np.random.choice(['待就诊', '已取消'], p=[0.9, 0.1])
        
        appointments.append({
            '挂号ID': f'A{str(i).zfill(6)}',
            '患者ID': patient_id,
            '医生ID': doctor_id,
            '科室ID': dept_id,
            '科室名称': dept_name,
            '挂号日期': appt_date.strftime('%Y-%m-%d'),
            '预约时段': time_slot,
            '就诊类型': visit_type,
            '挂号费用': doctor_row['门诊费用'],
            '挂号状态': status,
            '挂号渠道': random.choice(['窗口挂号', '自助机', 'APP预约', '微信预约', '电话预约']),
            '创建时间': (appt_date - timedelta(days=random.randint(0, 7))).strftime('%Y-%m-%d %H:%M:%S'),
        })
    return pd.DataFrame(appointments)


def generate_medical_records(appointments_df, n=400):
    """生成诊疗记录"""
    records = []
    # 只为已完成的挂号生成诊疗记录
    completed_appts = appointments_df[appointments_df['挂号状态'] == '已完成'].head(n)
    
    for idx, appt in completed_appts.iterrows():
        dept_id = appt['科室ID']
        diagnosis = random.choice(DIAGNOSES.get(dept_id, ['待诊断']))
        
        # 病情严重程度
        severity = np.random.choice(['轻度', '中度', '重度'], p=[0.55, 0.35, 0.10])
        
        records.append({
            '诊疗记录ID': f'MR{str(len(records) + 1).zfill(6)}',
            '挂号ID': appt['挂号ID'],
            '患者ID': appt['患者ID'],
            '医生ID': appt['医生ID'],
            '就诊日期': appt['挂号日期'],
            '主诉': f"患者因{diagnosis}相关症状就诊",
            '诊断结果': diagnosis,
            '病情程度': severity,
            '治疗方案': random.choice(['药物治疗', '物理治疗', '手术治疗', '综合治疗', '观察随访']),
            '医嘱': f"建议{random.choice(['休息', '清淡饮食', '多喝水', '适当运动', '定期复查'])}",
            '复诊建议': random.choice(['1周后复诊', '2周后复诊', '1个月后复诊', '如有不适随时就诊', '无需复诊']),
            '是否住院': '是' if severity == '重度' and random.random() > 0.5 else '否',
            '备注': '',
        })
    return pd.DataFrame(records)


def generate_prescriptions(medical_records_df, n=350):
    """生成处方记录"""
    prescriptions = []
    med_records = medical_records_df.head(n)
    
    for idx, record in med_records.iterrows():
        # 每个诊疗记录生成1-4种药品
        med_count = random.randint(1, 4)
        selected_meds = random.sample(MEDICATIONS, med_count)
        
        for med in selected_meds:
            quantity = random.randint(1, 5)
            prescriptions.append({
                '处方ID': f'RX{str(len(prescriptions) + 1).zfill(6)}',
                '诊疗记录ID': record['诊疗记录ID'],
                '患者ID': record['患者ID'],
                '医生ID': record['医生ID'],
                '药品ID': med['id'],
                '药品名称': med['name'],
                '药品类别': med['category'],
                '数量': quantity,
                '单位': med['unit'],
                '单价': med['price'],
                '金额': round(med['price'] * quantity, 2),
                '用法用量': random.choice(['每日3次，每次1片', '每日2次，每次1片', '每日1次，每次2片', '需要时服用', '每日1次，睡前服用']),
                '开具日期': record['就诊日期'],
                '有效期': (datetime.strptime(record['就诊日期'], '%Y-%m-%d') + timedelta(days=random.choice([3, 7, 14, 30]))).strftime('%Y-%m-%d'),
            })
    return pd.DataFrame(prescriptions)


def generate_medications():
    """生成药品库存数据"""
    meds = []
    for med in MEDICATIONS:
        meds.append({
            '药品ID': med['id'],
            '药品名称': med['name'],
            '药品类别': med['category'],
            '规格': random.choice(['10mg*24片', '20mg*20片', '100ml', '0.5g*12粒', '250mg*20片']),
            '单位': med['unit'],
            '进货价': round(med['price'] * 0.6, 2),
            '零售价': med['price'],
            '库存数量': med['stock'],
            '库存预警': 50,
            '生产厂家': med['manufacturer'],
            '有效期': (datetime.now() + timedelta(days=random.randint(180, 720))).strftime('%Y-%m-%d'),
            '存储条件': random.choice(['常温', '阴凉', '冷藏']),
            '是否处方药': random.choice(['是', '否']),
            '最后入库日期': (datetime.now() - timedelta(days=random.randint(1, 60))).strftime('%Y-%m-%d'),
        })
    return pd.DataFrame(meds)


def generate_bills(appointments_df, prescriptions_df, n=400):
    """生成费用账单"""
    bills = []
    completed_appts = appointments_df[appointments_df['挂号状态'] == '已完成'].head(n)
    
    for idx, appt in completed_appts.iterrows():
        # 挂号费
        registration_fee = appt['挂号费用']
        
        # 检查费（随机）
        exam_fee = random.choice([0, 50, 100, 150, 200, 350, 500]) if random.random() > 0.3 else 0
        
        # 药费（从处方计算）
        patient_prescriptions = prescriptions_df[
            (prescriptions_df['患者ID'] == appt['患者ID']) & 
            (prescriptions_df['开具日期'] == appt['挂号日期'])
        ]
        medicine_fee = patient_prescriptions['金额'].sum() if not patient_prescriptions.empty else 0
        
        # 治疗费
        treatment_fee = random.choice([0, 50, 100, 200, 300, 500]) if random.random() > 0.4 else 0
        
        # 总费用
        total_fee = registration_fee + exam_fee + medicine_fee + treatment_fee
        
        # 医保报销比例
        insurance_ratio = random.choice([0.0, 0.5, 0.6, 0.7, 0.8, 0.85])
        reimbursement = round(total_fee * insurance_ratio, 2)
        self_pay = round(total_fee - reimbursement, 2)
        
        bills.append({
            '账单ID': f'B{str(len(bills) + 1).zfill(6)}',
            '患者ID': appt['患者ID'],
            '挂号ID': appt['挂号ID'],
            '账单日期': appt['挂号日期'],
            '挂号费': registration_fee,
            '检查费': exam_fee,
            '药品费': round(medicine_fee, 2),
            '治疗费': treatment_fee,
            '总金额': round(total_fee, 2),
            '医保报销': reimbursement,
            '自费金额': self_pay,
            '支付方式': random.choice(['微信支付', '支付宝', '银行卡', '现金', '医保卡']),
            '支付状态': np.random.choice(['已支付', '待支付', '已退款'], p=[0.90, 0.07, 0.03]),
            '支付时间': appt['挂号日期'] + ' ' + random.choice(['09:30:00', '10:45:00', '14:20:00', '15:55:00', '16:30:00']),
        })
    return pd.DataFrame(bills)


def main():
    """主函数：生成所有数据并保存为Excel"""
    print("[Hospital] Starting to generate hospital management test data...")
    
    # 生成各表数据
    print("  [1/8] Generating patient data...")
    patients_df = generate_patients(200)
    
    print("  [2/8] Generating doctor data...")
    doctors_df = generate_doctors(30)
    
    print("  [3/8] Generating department data...")
    departments_df = generate_departments()
    
    print("  [4/8] Generating appointment data...")
    appointments_df = generate_appointments(patients_df, doctors_df, 500)
    
    print("  [5/8] Generating medical records...")
    medical_records_df = generate_medical_records(appointments_df, 400)
    
    print("  [6/8] Generating prescription data...")
    prescriptions_df = generate_prescriptions(medical_records_df, 350)
    
    print("  [7/8] Generating medication inventory...")
    medications_df = generate_medications()
    
    print("  [8/8] Generating billing data...")
    bills_df = generate_bills(appointments_df, prescriptions_df, 400)
    
    # 保存到Excel文件
    output_path = os.path.join(os.path.dirname(__file__), 'hospital_management_test_data.xlsx')
    
    print(f"\n[Save] Saving data to: {output_path}")
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        patients_df.to_excel(writer, sheet_name='患者信息', index=False)
        doctors_df.to_excel(writer, sheet_name='医生信息', index=False)
        departments_df.to_excel(writer, sheet_name='科室信息', index=False)
        appointments_df.to_excel(writer, sheet_name='挂号记录', index=False)
        medical_records_df.to_excel(writer, sheet_name='诊疗记录', index=False)
        prescriptions_df.to_excel(writer, sheet_name='处方记录', index=False)
        medications_df.to_excel(writer, sheet_name='药品库存', index=False)
        bills_df.to_excel(writer, sheet_name='费用账单', index=False)
    
    # 打印统计信息
    print("\n[Done] Data generation complete! Statistics:")
    print(f"   - Patients: {len(patients_df)} records")
    print(f"   - Doctors: {len(doctors_df)} records")
    print(f"   - Departments: {len(departments_df)} records")
    print(f"   - Appointments: {len(appointments_df)} records")
    print(f"   - Medical Records: {len(medical_records_df)} records")
    print(f"   - Prescriptions: {len(prescriptions_df)} records")
    print(f"   - Medications: {len(medications_df)} records")
    print(f"   - Bills: {len(bills_df)} records")
    
    print("\n[Test] Sample queries you can test:")
    print("   1. Query department visit statistics")
    print("   2. Analyze patient distribution by age group")
    print("   3. Calculate doctor workload and revenue")
    print("   4. View medication usage ranking")
    print("   5. Analyze monthly revenue trends")
    print("   6. Calculate insurance reimbursement ratios")
    print("   7. Query patient visit history and billing details")
    print("   8. Analyze disease distribution and seasonal trends")
    
    return output_path


if __name__ == '__main__':
    main()

