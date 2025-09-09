import random
from datetime import datetime

import MySQLdb

# 配置数据库连接信息
db_config = {
    'host': 'localhost',
    'user': 'root',
    'passwd': 'agent@123',
    'db': 'iids_db',
    'port': 3306,  # 如果不是默认端口，需要指定
}

# 生成模拟数据
def generate_weighted_random_number():
    # 定义区间和对应的比重
    ranges = [(204.48, 204.49, 0.5), (204.49, 204.52, 0.1), (204.47, 204.48, 0.1), (204.48, 204.48, 0.3)]

    # 根据比重计算每个区间的累积权重
    cumulative_weights = []
    weight_sum = 0
    for _, _, weight in ranges:
        weight_sum += weight
        cumulative_weights.append(weight_sum)

    # 生成一个0到1之间的随机数，并根据累积权重选择对应的区间
    random_value = random.random()
    for i, cumulative_weight in enumerate(cumulative_weights):
        if random_value < cumulative_weight:
            # 在选定的区间内生成一个随机数
            start, end, _ = ranges[i]
            random_number = round(random.uniform(start, end), 2)
            return random_number

def batch_insert_data():
    try:
        # 建立数据库连接
        connection = MySQLdb.connect(**db_config)
        # 创建游标对象
        cursor = connection.cursor()
        # 插入数据的 SQL 语句
        insert_query = "INSERT INTO his_flatnessreport (bladeId, holeAngle, flatness, created_at) VALUES (%s,%s,%s,%s)"
        # 准备要插入的数据
        data_to_insert = list()
        for i in range(144):
            angle = i *2.5
            # flatness = generate_weighted_random_number()
            flatness = 204.48

            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 获取当前时间

            data_to_insert.append(("test_blade_8", angle, flatness, created_at))

        # 执行批量插入
        cursor.executemany(insert_query, data_to_insert)
        # 提交事务
        connection.commit()
        print("数据插入成功")
    except MySQLdb.Error as e:
        print("发生错误：", e)
    finally:
        # 关闭游标和连接
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            print("数据库连接已关闭")


if __name__ == "__main__":
    print("............")
    batch_insert_data()