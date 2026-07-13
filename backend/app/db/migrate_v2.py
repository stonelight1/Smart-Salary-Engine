"""
数据库迁移脚本 - 薪资核算系统 V2

在现有 salary_run 表上新增 run_version、reference_run_id 字段，
在 employee_record 表上新增薪资核算扩展字段，
创建 performance_import_record、leave_import_record 新表。
"""

import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "salary.db")


def migrate():
    db_path = os.environ.get("DATABASE_URL", DB_PATH)
    # sqlite:/// 前缀处理
    if db_path.startswith("sqlite:///"):
        db_path = db_path[len("sqlite:///"):]

    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        print("跳过迁移（首次启动时将自动建表）")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print(f"已连接数据库: {db_path}")

    # 1. salary_run 表新增字段
    _add_column(cursor, "salary_run", "reference_run_id", "VARCHAR(64)")
    _add_column(cursor, "salary_run", "run_version", "VARCHAR(16)", default="'DRAFT'")
    cursor.execute("UPDATE salary_run SET run_version = 'FINAL' WHERE run_version IS NULL")
    print("  salary_run: reference_run_id, run_version 字段检查完成")

    # 2. employee_record 表新增字段
    emp_columns = [
        ("employee_no", "VARCHAR(64)"),
        ("department", "VARCHAR(255)"),
        ("position", "VARCHAR(255)"),
        ("salary_standard", "DECIMAL(14,2)"),
        ("basic_salary", "DECIMAL(14,2)"),
        ("performance_salary_standard", "DECIMAL(14,2)"),
        ("performance_score", "DECIMAL(6,4)"),
        ("performance_score_source", "VARCHAR(16)"),
        ("performance_salary_actual", "DECIMAL(14,2)"),
        ("attendance_rule_type", "VARCHAR(16)"),
        ("attendance_rule_name", "VARCHAR(64)"),
        ("standard_attendance_days", "DECIMAL(6,2)"),
        ("leave_days", "DECIMAL(6,2)"),
        ("actual_attendance_days", "DECIMAL(6,2)"),
        ("attendance_deduction", "DECIMAL(14,2)"),
        ("gross_salary_before_attendance", "DECIMAL(14,2)"),
    ]
    for col_name, col_type in emp_columns:
        _add_column(cursor, "employee_record", col_name, col_type)
    print("  employee_record: 薪资核算扩展字段检查完成")

    # 3. 创建 performance_import_record 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS performance_import_record (
            id VARCHAR(64) PRIMARY KEY,
            salary_run_id VARCHAR(64) NOT NULL,
            employee_record_id VARCHAR(64),
            employee_name VARCHAR(255) NOT NULL,
            score DECIMAL(6,4) NOT NULL,
            parse_method VARCHAR(32) NOT NULL,
            batch_id VARCHAR(64) NOT NULL,
            status VARCHAR(16) DEFAULT 'MATCHED',
            created_by VARCHAR(64) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_perf_run ON performance_import_record(salary_run_id)")
    print("  performance_import_record 表已创建")

    # 4. 创建 leave_import_record 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leave_import_record (
            id VARCHAR(64) PRIMARY KEY,
            salary_run_id VARCHAR(64) NOT NULL,
            employee_record_id VARCHAR(64),
            employee_name VARCHAR(255) NOT NULL,
            employee_no VARCHAR(64),
            leave_date DATE,
            leave_start DATE,
            leave_end DATE,
            leave_days DECIMAL(6,2) NOT NULL,
            leave_type VARCHAR(64) DEFAULT '',
            approval_id VARCHAR(128),
            batch_id VARCHAR(64) NOT NULL,
            status VARCHAR(16) DEFAULT 'MATCHED',
            created_by VARCHAR(64) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_leave_run ON leave_import_record(salary_run_id)")
    print("  leave_import_record 表已创建")

    conn.commit()
    conn.close()
    print("迁移完成")


def _add_column(cursor, table, column, col_type, default=None):
    """安全添加列（如果不存在）"""
    cursor.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cursor.fetchall()}
    if column not in existing:
        default_clause = f" DEFAULT {default}" if default else ""
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}")
        print(f"  {table}: 添加列 {column} ({col_type})")


if __name__ == "__main__":
    migrate()
