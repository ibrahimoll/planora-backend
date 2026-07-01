from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


def ensure_report_requests_table(engine: Engine) -> None:
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS report_requests (
        report_request_id BIGSERIAL PRIMARY KEY,
        project_id BIGINT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
        requested_by_user_id BIGINT NULL REFERENCES users(user_id) ON DELETE SET NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        link_signature VARCHAR(128) NULL UNIQUE,
        admin_note TEXT NULL,
        rejection_reason TEXT NULL,
        report_export_id BIGINT NULL REFERENCES report_exports(report_export_id) ON DELETE SET NULL,
        resolved_by_admin_id BIGINT NULL REFERENCES users(user_id) ON DELETE SET NULL,
        requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        resolved_at TIMESTAMPTZ NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT chk_report_requests_status CHECK (status IN ('pending', 'ready', 'rejected'))
    )
    """

    index_sql = [
        "CREATE INDEX IF NOT EXISTS ix_report_requests_project_id ON report_requests(project_id)",
        "CREATE INDEX IF NOT EXISTS ix_report_requests_requested_by_user_id ON report_requests(requested_by_user_id)",
        "CREATE INDEX IF NOT EXISTS ix_report_requests_status ON report_requests(status)",
        "CREATE INDEX IF NOT EXISTS ix_report_requests_link_signature ON report_requests(link_signature)",
        "CREATE INDEX IF NOT EXISTS ix_report_requests_report_export_id ON report_requests(report_export_id)",
        "CREATE INDEX IF NOT EXISTS ix_report_requests_resolved_by_admin_id ON report_requests(resolved_by_admin_id)",
        "CREATE INDEX IF NOT EXISTS ix_report_requests_requested_at ON report_requests(requested_at)",
    ]

    with engine.begin() as connection:
        connection.execute(text(create_table_sql))
        for statement in index_sql:
            connection.execute(text(statement))
