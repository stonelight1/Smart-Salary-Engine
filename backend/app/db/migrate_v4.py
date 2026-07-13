"""
数据库迁移 — V4 员工档案+薪资档案+月度快照

新建表:
- employee_master (员工档案)
- salary_standard (薪资标准)
- employee_position_history (岗位/部门异动)
- monthly_salary_snapshot (月度工资快照)
- salary_item_detail (工资项目明细)
"""

import sqlite3

DB = "/Users/ydd/Desktop/AI项目/salary-system/data/sse.db"


def add_col(c, table, col, typ, default=None):
    c.execute(f"PRAGMA table_info({table})")
    existing = {r[1] for r in c.fetchall()}
    if col not in existing:
        d = f" DEFAULT {default}" if default else ""
        c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}{d}")
        print(f"  + {table}.{col}")


conn = sqlite3.connect(DB)
c = conn.cursor()
print("Migrating to V4...")

# ============================================================
#  1. employee_master — 员工档案（长期）
# ============================================================
c.execute("""
    CREATE TABLE IF NOT EXISTS employee_master (
        id VARCHAR(64) PRIMARY KEY,
        employee_no VARCHAR(64) UNIQUE,
        employee_name VARCHAR(255) NOT NULL,
        department VARCHAR(255),
        position VARCHAR(255),
        hire_date DATE,
        resign_date DATE,
        status VARCHAR(16) DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE','RESIGNED')),
        contact_info VARCHAR(255),
        remark TEXT,
        created_by VARCHAR(64),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")
print("  + employee_master table")

# ============================================================
#  2. salary_standard — 薪资标准（长期，有效期限）
# ============================================================
c.execute("""
    CREATE TABLE IF NOT EXISTS salary_standard (
        id VARCHAR(64) PRIMARY KEY,
        employee_master_id VARCHAR(64) NOT NULL REFERENCES employee_master(id),
        salary_standard DECIMAL(14,2) NOT NULL,
        basic_salary DECIMAL(14,2),
        performance_salary_standard DECIMAL(14,2),
        effective_date DATE NOT NULL,
        end_date DATE,
        change_reason VARCHAR(255),
        created_by VARCHAR(64),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")
c.execute("CREATE INDEX IF NOT EXISTS idx_salary_std_emp ON salary_standard(employee_master_id)")
print("  + salary_standard table")

# ============================================================
#  3. employee_position_history — 岗位/部门异动
# ============================================================
c.execute("""
    CREATE TABLE IF NOT EXISTS employee_position_history (
        id VARCHAR(64) PRIMARY KEY,
        employee_master_id VARCHAR(64) NOT NULL REFERENCES employee_master(id),
        department VARCHAR(255),
        position VARCHAR(255),
        effective_date DATE NOT NULL,
        change_type VARCHAR(32) NOT NULL CHECK(change_type IN ('HIRE','TRANSFER','PROMOTION','RESIGN')),
        prev_department VARCHAR(255),
        prev_position VARCHAR(255),
        change_reason VARCHAR(255),
        created_by VARCHAR(64),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")
c.execute("CREATE INDEX IF NOT EXISTS idx_pos_hist_emp ON employee_position_history(employee_master_id)")
print("  + employee_position_history table")

# ============================================================
#  4. monthly_salary_snapshot — 月度工资快照
# ============================================================
c.execute("""
    CREATE TABLE IF NOT EXISTS monthly_salary_snapshot (
        id VARCHAR(64) PRIMARY KEY,
        salary_run_id VARCHAR(64) NOT NULL REFERENCES salary_run(id),
        employee_master_id VARCHAR(64) NOT NULL,
        employee_no VARCHAR(64),
        employee_name VARCHAR(255) NOT NULL,
        department VARCHAR(255),
        position VARCHAR(255),

        salary_standard DECIMAL(14,2),
        basic_salary DECIMAL(14,2),
        performance_salary_standard DECIMAL(14,2),

        performance_score DECIMAL(6,4) DEFAULT 1.0,
        performance_score_source VARCHAR(16) DEFAULT 'DEFAULT',
        performance_salary_actual DECIMAL(14,2),

        attendance_rule_type VARCHAR(16),
        attendance_rule_name VARCHAR(64),
        standard_attendance_days DECIMAL(6,2),
        leave_days DECIMAL(6,2) DEFAULT 0,
        actual_attendance_days DECIMAL(6,2),
        attendance_deduction DECIMAL(14,2),
        gross_salary_before_attendance DECIMAL(14,2),
        gross_salary_after_attendance DECIMAL(14,2),

        net_salary DECIMAL(14,2),

        status VARCHAR(16) DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE','FINISHED','REMOVED')),

        created_by VARCHAR(64),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")
c.execute("CREATE INDEX IF NOT EXISTS idx_snapshot_run ON monthly_salary_snapshot(salary_run_id)")
c.execute("CREATE INDEX IF NOT EXISTS idx_snapshot_emp ON monthly_salary_snapshot(employee_master_id)")
print("  + monthly_salary_snapshot table")

# ============================================================
#  5. salary_item_detail — 工资项目明细（可扩展）
# ============================================================
c.execute("""
    CREATE TABLE IF NOT EXISTS salary_item_detail (
        id VARCHAR(64) PRIMARY KEY,
        snapshot_id VARCHAR(64) NOT NULL REFERENCES monthly_salary_snapshot(id),
        salary_run_id VARCHAR(64) NOT NULL,
        item_type VARCHAR(16) NOT NULL CHECK(item_type IN ('EARNING','DEDUCTION','COMPANY_COST')),
        item_code VARCHAR(64) NOT NULL,
        item_name VARCHAR(128) NOT NULL,
        amount DECIMAL(14,2) NOT NULL DEFAULT 0,
        source VARCHAR(32) DEFAULT 'SYSTEM',
        remark TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")
c.execute("CREATE INDEX IF NOT EXISTS idx_item_snap ON salary_item_detail(snapshot_id)")
c.execute("CREATE INDEX IF NOT EXISTS idx_item_run ON salary_item_detail(salary_run_id)")
print("  + salary_item_detail table")

# ============================================================
#  6. salary_run 状态更新
# ============================================================
add_col(c, "salary_run", "employee_count", "INTEGER", "0")
add_col(c, "salary_run", "new_hire_count", "INTEGER", "0")
add_col(c, "salary_run", "resign_count", "INTEGER", "0")
# 新状态映射: DRAFT / DATA_PENDING / CALCULATED / REVIEWING / FINALIZED

# ============================================================
#  7. employee_master 初始数据：从现有 EmployeeRecord 去重
# ============================================================
try:
    c.execute("""
        INSERT OR IGNORE INTO employee_master (id, employee_no, employee_name, department, position, status, created_by)
        SELECT DISTINCT
            'emp_' || substr(hex(randomblob(4)), 1, 8),
            employee_no,
            employee_name,
            department,
            position,
            'ACTIVE',
            'admin'
        FROM employee_record
        WHERE employee_name IS NOT NULL AND employee_name != ''
    """)
    inserted = c.rowcount
    if inserted > 0:
        print(f"  Migrated {inserted} employees to employee_master")
except Exception as e:
    print(f"  Note: employee migration: {str(e)[:100]}")

conn.commit()
conn.close()
print("V4 migration complete")
