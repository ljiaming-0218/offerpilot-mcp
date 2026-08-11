from backend.database import verify_database, iter_table_names


connected = verify_database()
print("当前配置数据库连接状态：", connected)

if connected:
    table_names = list(iter_table_names())
    print("当前数据库表：", table_names)
