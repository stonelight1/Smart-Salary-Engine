"""数据库迁移：为 salary_run 表增加软删除、作废、归档字段

运行方式：
    cd backend && uv run python -m app.db.migrate_add_task_controls
"""

from app.db.database import engine, SessionLocal
from sqlalchemy import text


def upgrade():
    """执行迁移"""
    with engine.connect() as conn:
        # 检查字段是否已存在
        existing = [row[0] for row in conn.execute(text("PRAGMA table_info(salary_run)")).fetchall()]

        if "delete_flag" not in existing:
            conn.execute(text("ALTER TABLE salary_run ADD COLUMN delete_flag INTEGER NOT NULL DEFAULT 0"))
            conn.execute(text("ALTER TABLE salary_run ADD COLUMN deleted_by VARCHAR(64)"))
            conn.execute(text("ALTER TABLE salary_run ADD COLUMN deleted_at DATETIME"))

        if "void_reason" not in existing:
            conn.execute(text("ALTER TABLE salary_run ADD COLUMN void_reason TEXT"))
            conn.execute(text("ALTER TABLE salary_run ADD COLUMN voided_by VARCHAR(64)"))
            conn.execute(text("ALTER TABLE salary_run ADD COLUMN voided_at DATETIME"))

        if "archive_flag" not in existing:
            conn.execute(text("ALTER TABLE salary_run ADD COLUMN archive_flag INTEGER NOT NULL DEFAULT 0"))
            conn.execute(text("ALTER TABLE salary_run ADD COLUMN archived_by VARCHAR(64)"))
            conn.execute(text("ALTER TABLE salary_run ADD COLUMN archived_at DATETIME"))

        conn.commit()
        print("迁移完成：已添加软删除、作废、归档字段")


def downgrade():
    """回滚（SQLite 不支持 DROP COLUMN，仅打印提示）"""
    print("SQLite 不支持回滚 ALTER TABLE ADD COLUMN，如需回滚请重建数据库")


if __name__ == "__main__":
    upgrade()
