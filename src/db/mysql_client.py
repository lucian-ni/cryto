"""
MySQL数据库连接和操作模块
使用连接池管理数据库连接
"""
import os

import pymysql
from dbutils.pooled_db import PooledDB

from config.settings import (
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DB_CHARSET,
    DB_POOL_MIN_CACHED, DB_POOL_MAX_CACHED, DB_POOL_MAX_SHARED, DB_POOL_MAX_CONNECTIONS,
    DB_CONNECT_TIMEOUT
)
from src.lib_resource import (
    COLOR_GREEN, COLOR_RED, COLOR_RESET, TAG_DB,
    MSG_DB_CONNECT, MSG_DB_CONNECT_OK, MSG_DB_INIT_TABLE, MSG_DB_INIT_TABLE_OK, MSG_DB_ERROR
)


class MySQLClient:
    """MySQL数据库客户端，使用连接池管理连接"""

    _pool = None

    @classmethod
    def _get_pool(cls):
        """获取数据库连接池（单例模式）"""
        if cls._pool is None:
            print(f"{TAG_DB} {MSG_DB_CONNECT.format(host=DB_HOST, port=DB_PORT, db=DB_NAME)}")
            cls._pool = PooledDB(
                creator=pymysql,
                mincached=DB_POOL_MIN_CACHED,
                maxcached=DB_POOL_MAX_CACHED,
                maxshared=DB_POOL_MAX_SHARED,
                maxconnections=DB_POOL_MAX_CONNECTIONS,
                blocking=True,
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                charset=DB_CHARSET,
                autocommit=True,
                connect_timeout=DB_CONNECT_TIMEOUT
            )
            print(f"{TAG_DB} {COLOR_GREEN}{MSG_DB_CONNECT_OK}{COLOR_RESET}")
        return cls._pool

    @classmethod
    def get_connection(cls):
        """从连接池获取一个数据库连接"""
        return cls._get_pool().connection()

    @classmethod
    def init_tables(cls):
        """初始化数据表，执行 sql/init.sql 建表脚本"""
        print(f"{TAG_DB} {MSG_DB_INIT_TABLE}")
        # 定位 sql/init.sql 文件路径
        sql_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'sql', 'init.sql')
        sql_file_path = os.path.abspath(sql_file_path)
        print(f"{TAG_DB} 读取建表脚本：{sql_file_path}")

        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        conn = cls.get_connection()
        try:
            cursor = conn.cursor()
            # 按分号分隔执行多条SQL（过滤空语句和纯注释行）
            statements = sql_content.split(';')
            for stmt in statements:
                stmt = stmt.strip()
                # 跳过空语句和纯注释行
                if stmt and not all(
                    line.strip().startswith('--') or line.strip() == ''
                    for line in stmt.split('\n')
                ):
                    print(f"{TAG_DB} 执行SQL：{stmt[:60]}...")
                    cursor.execute(stmt)
            cursor.close()
            print(f"{TAG_DB} {COLOR_GREEN}{MSG_DB_INIT_TABLE_OK}{COLOR_RESET}")
        except Exception as e:
            print(f"{TAG_DB} {COLOR_RED}{MSG_DB_ERROR.format(error=str(e))}{COLOR_RESET}")
            raise
        finally:
            conn.close()

    @classmethod
    def execute_query(cls, sql, params=None):
        """
        执行查询SQL，返回字典列表
        :param sql: SQL语句
        :param params: 参数元组
        :return: 查询结果（字典列表）
        """
        conn = cls.get_connection()
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(sql, params)
            result = cursor.fetchall()
            cursor.close()
            return result
        except Exception as e:
            print(f"{TAG_DB} {COLOR_RED}{MSG_DB_ERROR.format(error=str(e))}{COLOR_RESET}")
            raise
        finally:
            conn.close()

    @classmethod
    def execute_many(cls, sql, params_list):
        """
        批量执行SQL（INSERT/UPDATE），返回影响行数
        :param sql: SQL语句
        :param params_list: 参数元组列表
        :return: 影响行数
        """
        conn = cls.get_connection()
        try:
            cursor = conn.cursor()
            affected = cursor.executemany(sql, params_list)
            conn.commit()
            cursor.close()
            return affected
        except Exception as e:
            conn.rollback()
            print(f"{TAG_DB} {COLOR_RED}{MSG_DB_ERROR.format(error=str(e))}{COLOR_RESET}")
            raise
        finally:
            conn.close()

    @classmethod
    def execute_update(cls, sql, params=None):
        """
        执行单条INSERT/UPDATE/DELETE，返回影响行数
        :param sql: SQL语句
        :param params: 参数元组
        :return: 影响行数
        """
        conn = cls.get_connection()
        try:
            cursor = conn.cursor()
            affected = cursor.execute(sql, params)
            conn.commit()
            cursor.close()
            return affected
        except Exception as e:
            conn.rollback()
            print(f"{TAG_DB} {COLOR_RED}{MSG_DB_ERROR.format(error=str(e))}{COLOR_RESET}")
            raise
        finally:
            conn.close()
