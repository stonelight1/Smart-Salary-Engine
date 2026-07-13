"""
迁移 V5 — 员工异动待确认 + 任职历史

新建表:
- employee_change_candidate (异动待确认)
- employee_assignment_history (任职历史)
"""

import sqlite3

DB = "/Users/ydd/Desktop/AI项目/salary-system/data/sse.db"

conn = sqlite3.connect(DB)
c = conn.cursor()
print("Migrating to V5...")

# 1. employee_assignment_history
c.execute("""
    CREATE TABLE IF NOT EXISTS employee_assignment_history (
        id VARCHAR(64) PRIMARY KEY,
        employee_master_id VARCHAR(64) NOT NULL,
        department VARCHAR(255),
        position VARCHAR(255),
        effective_start_date DATE NOT NULL,
        effective_end_date DATE,
        change_type VARCHAR(32) NOT NULL,
        change_reason VARCHAR(255),
        source_batch_id VARCHAR(64),
        created_by VARCHAR(64),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")
c.execute("CREATE INDEX IF NOT EXISTS idx_assign_emp ON employee_assignment_history(employee_master_id)")
print("  + employee_assignment_history table")

# 2. employee_change_candidate
c.execute("""
    CREATE TABLE IF NOT EXISTS employee_change_candidate (
        id VARCHAR(64) PRIMARY KEY,
        salary_month VARCHAR(7) NOT NULL,
        employee_master_id VARCHAR(64),
        candidate_type VARCHAR(32) NOT NULL,
        employee_no VARCHAR(64),
        employee_name VARCHAR(255) NOT NULL,
        department VARCHAR(255),
        position VARCHAR(255),
        hire_date DATE,
        old_data_json TEXT,
        new_data_json TEXT,
        detection_reason VARCHAR(255),
        source_batch_id VARCHAR(64),
        status VARCHAR(16) DEFAULT 'PENDING' CHECK(status IN ('PENDING','CONFIRMED','IGNORED','REJECTED')),
        handled_by VARCHAR(64),
        handled_at DATETIME,
        handle_remark VARCHAR(255),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")
c.execute("CREATE INDEX IF NOT EXISTS idx_cand_month ON employee_change_candidate(salary_month)")
c.execute("CREATE INDEX IF NOT EXISTS idx_cand_status ON employee_change_candidate(status)")
print("  + employee_change_candidate table")

# 3. employee_master add source_type and first_seen_month if missing
def add_col(table, col, typ, default=None):
    c.execute(f"PRAGMA table_info({table})")
    existing = {r[1] for r in c.fetchall()}
    if col not in existing:
        d = f" DEFAULT {default}" if default else ""
        c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}{d}")
        print(f"  + {table}.{col}")

add_col("employee_master", "source_type", "VARCHAR(32)", "'MANUAL'")
add_col("employee_master", "first_seen_month", "VARCHAR(7)")
add_col("employee_master", "last_seen_month", "VARCHAR(7)")

conn.commit()
conn.close()
print("V5 migration complete")
