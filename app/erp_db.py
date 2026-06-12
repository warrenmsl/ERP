from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.erp import build_erp_rows
from app.erp_upload import (
    export_erp_bundle,
    run_erp_playwright_upload,
    validate_built_for_upload,
)
from app.notify import erp_notify_auto_enabled, send_erp_ready_notice

STANDALONE_ERP_PRODUCT_SKU = "__erp_standalone__"


def _erp_missing_hint(built: dict[str, Any]) -> str:
    batch_missing = built.get("batch_missing") or []
    row_missing: list[str] = []
    for row in built.get("rows", []):
        for field in row.get("missing_fields", []):
            if field not in row_missing:
                row_missing.append(field)
    parts: list[str] = []
    if batch_missing:
        parts.append(f"批次待补：{'、'.join(batch_missing)}")
    if row_missing:
        parts.append(f"行内待补：{'、'.join(row_missing)}")
    return f"；{'；'.join(parts)}" if parts else ""


SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'draft',
    owner_module TEXT NOT NULL DEFAULT 'erp',
    next_assignee TEXT NOT NULL DEFAULT 'ERP 资料录入',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workflow_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    from_status TEXT NOT NULL,
    to_status TEXT NOT NULL,
    action TEXT NOT NULL,
    message TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    channel TEXT NOT NULL,
    recipient TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'sent',
    created_at TEXT NOT NULL,
    FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS erp_import_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'table_text',
    source_file_name TEXT NOT NULL DEFAULT '',
    raw_text TEXT NOT NULL DEFAULT '',
    product_name TEXT NOT NULL,
    product_full_code TEXT NOT NULL,
    product_abbr TEXT NOT NULL,
    upload_status TEXT NOT NULL DEFAULT 'draft',
    erp_upload_code TEXT NOT NULL DEFAULT '',
    width_span TEXT NOT NULL DEFAULT '',
    export_dir TEXT NOT NULL DEFAULT '',
    upload_error TEXT NOT NULL DEFAULT '',
    uploaded_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS erp_sku_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    product_full_code TEXT NOT NULL,
    product_abbr TEXT NOT NULL,
    color TEXT NOT NULL,
    size TEXT NOT NULL,
    variant_code TEXT NOT NULL,
    price REAL NOT NULL,
    weight REAL NOT NULL,
    supplier_name TEXT NOT NULL DEFAULT '',
    missing_fields TEXT NOT NULL DEFAULT '',
    cost_price REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY(batch_id) REFERENCES erp_import_batches(id),
    FOREIGN KEY(product_id) REFERENCES products(id)
);
"""


class ErpDatabase:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.init()

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def init(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    def create_product(self, data: dict[str, Any]) -> int:
        now = utc_now()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO products
                    (sku, name, category, description, owner_module, next_assignee, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["sku"].strip(),
                    data["name"].strip(),
                    data.get("category", "").strip(),
                    data.get("description", "").strip(),
                    data.get("owner_module", "erp"),
                    data.get("next_assignee", "ERP 资料录入"),
                    now,
                    now,
                ),
            )
            product_id = int(cursor.lastrowid)
            self._add_event(connection, product_id, "", "draft", "create_product", "创建商品记录")
            return product_id

    def fetch_product(self, product_id: int) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM products WHERE id = ?",
                (product_id,),
            ).fetchone()

    def create_erp_import(
        self,
        product_id: int,
        raw_text: str,
        source_type: str = "table_text",
        source_file_name: str = "",
        width_span: str = "",
        default_product_name: str = "",
    ) -> int:
        with self.connect() as connection:
            product = connection.execute(
                "SELECT * FROM products WHERE id = ?",
                (product_id,),
            ).fetchone()
            if not product:
                raise ValueError("商品不存在")
            name_for_build = str(product["name"] or "")
            if product["sku"] == STANDALONE_ERP_PRODUCT_SKU and default_product_name.strip():
                name_for_build = default_product_name.strip()
            built = build_erp_rows(name_for_build, raw_text, width_span)
            if not built["rows"]:
                raise ValueError("没有解析到可录入的规格行，请检查表格或截图文本")
            now = utc_now()
            cursor = connection.execute(
                """
                INSERT INTO erp_import_batches
                    (product_id, source_type, source_file_name, raw_text, product_name,
                     product_full_code, product_abbr, upload_status, width_span, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product_id,
                    source_type,
                    source_file_name.strip(),
                    raw_text.strip(),
                    built["product_name"],
                    built["product_full_code"],
                    built["product_abbr"],
                    "draft",
                    built.get("width_span", ""),
                    now,
                    now,
                ),
            )
            batch_id = int(cursor.lastrowid)
            for row in built["rows"]:
                connection.execute(
                    """
                    INSERT INTO erp_sku_rows
                        (batch_id, product_id, product_name, product_full_code, product_abbr,
                         color, size, variant_code, price, cost_price, weight, supplier_name, missing_fields, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        batch_id,
                        product_id,
                        row["erp_goods_name"],
                        row["style_code"],
                        row["product_abbr"],
                        row["erp_color"],
                        row["erp_spec"],
                        row["sku_code"],
                        row["price"],
                        row.get("cost_price", 0.0),
                        row["weight"],
                        row["supplier"],
                        ",".join(row.get("missing_fields", [])),
                        now,
                    ),
                )
            missing_hint = _erp_missing_hint(built)
            self._add_event(
                connection,
                product_id,
                product["status"],
                product["status"],
                "prepare_erp_import",
                f"已生成 ERP 导入表：{built['product_full_code']}，{len(built['rows'])} 条规格明细{missing_hint}",
            )
            return batch_id

    def fetch_erp_batch(self, batch_id: int) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM erp_import_batches WHERE id = ?",
                (batch_id,),
            ).fetchone()

    def fetch_erp_rows(self, batch_id: int) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM erp_sku_rows WHERE batch_id = ? ORDER BY id",
                (batch_id,),
            ).fetchall()

    def confirm_erp_auto_upload(
        self,
        built: dict[str, Any],
        payload: dict[str, str],
        only: str | None = "distribution",
        send_notify: bool | None = None,
    ) -> dict[str, Any]:
        if only == "new_product":
            success_prefix = "新品录入自动上传成功"
        else:
            success_prefix = "分销上架自动上传成功"
        if send_notify is None:
            send_notify = erp_notify_auto_enabled()
        return self._confirm_erp_upload_impl(
            self._standalone_product_id(),
            built,
            payload,
            only=only,
            success_message_prefix=success_prefix,
            send_notify=send_notify,
        )

    def _standalone_product_id(self) -> int:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT id FROM products WHERE sku = ?",
                (STANDALONE_ERP_PRODUCT_SKU,),
            ).fetchone()
            if row:
                return int(row["id"])
        return self.create_product(
            {
                "sku": STANDALONE_ERP_PRODUCT_SKU,
                "name": "ERP自动上传记录",
                "description": "系统占位，用于无待办商品时的聚水潭自动上传批次",
            }
        )

    def _confirm_erp_upload_impl(
        self,
        product_id: int,
        built: dict[str, Any],
        payload: dict[str, str],
        *,
        only: str | None,
        success_message_prefix: str = "ERP 录入成功",
        send_notify: bool = False,
    ) -> dict[str, Any]:
        blocking = validate_built_for_upload(built)
        if blocking:
            raise ValueError("；".join(blocking))

        batch_id = self.create_erp_import(
            product_id,
            payload.get("raw_text", ""),
            payload.get("source_type", "table_text"),
            payload.get("source_file_name", ""),
            payload.get("width_span", ""),
            default_product_name=payload.get("default_product_name", ""),
        )
        export_dir = export_erp_bundle(built, batch_id)
        self._set_batch_upload_state(batch_id, "ready", export_dir=str(export_dir))
        self._set_batch_upload_state(batch_id, "uploading", export_dir=str(export_dir))

        upload_result = run_erp_playwright_upload(export_dir, batch_id, only=only)
        if upload_result.rpa_skipped:
            self._set_batch_upload_state(
                batch_id,
                "ready",
                export_dir=str(export_dir),
                upload_error=upload_result.error or "",
            )
            return {
                "batch_id": batch_id,
                "upload_status": "ready",
                "export_dir": str(export_dir),
                "upload_error": upload_result.error,
                "message": upload_result.error or "已导出 xlsx，待配置 RPA 或手工导入",
            }

        if not upload_result.ok:
            self._set_batch_upload_state(
                batch_id,
                "failed",
                export_dir=str(export_dir),
                upload_error=upload_result.error or "上传失败",
            )
            return {
                "batch_id": batch_id,
                "upload_status": "failed",
                "export_dir": str(export_dir),
                "upload_error": upload_result.error,
                "message": upload_result.error or "ERP 自动上传失败",
            }

        upload_code = f"ERP-BATCH-{batch_id:05d}"
        self._set_batch_upload_state(
            batch_id,
            "uploaded",
            export_dir=str(export_dir),
            upload_error="",
            erp_upload_code=upload_code,
        )
        notify_error: str | None = None
        message = f"{success_message_prefix}，批次 {upload_code}（{len(built.get('rows', []))} 条规格）"
        if send_notify:
            notify_error = self.notify_erp_batch_ready(product_id, batch_id)
            if notify_error:
                message = f"{message}；钉钉提醒发送失败：{notify_error}"
            else:
                message = f"{message}；已发送钉钉提醒"
        return {
            "batch_id": batch_id,
            "upload_status": "uploaded",
            "export_dir": str(export_dir),
            "upload_error": "",
            "message": message,
            "details": upload_result.details or [],
            "notify_error": notify_error,
        }

    def retry_erp_upload(self, batch_id: int) -> dict[str, Any]:
        batch = self.fetch_erp_batch(batch_id)
        if not batch:
            raise ValueError("ERP 导入批次不存在")
        export_dir = Path(str(batch["export_dir"] or ""))
        if not export_dir.exists():
            raise ValueError("导出文件不存在，请重新解析并确认录入")
        self._set_batch_upload_state(batch_id, "uploading", upload_error="")
        upload_result = run_erp_playwright_upload(export_dir, batch_id)
        if upload_result.rpa_skipped or not upload_result.ok:
            self._set_batch_upload_state(
                batch_id,
                "failed",
                upload_error=upload_result.error or "上传失败",
            )
            return {
                "batch_id": batch_id,
                "upload_status": "failed",
                "export_dir": str(export_dir),
                "upload_error": upload_result.error,
                "message": upload_result.error or "重试上传失败",
            }
        upload_code = f"ERP-BATCH-{batch_id:05d}"
        self._set_batch_upload_state(
            batch_id,
            "uploaded",
            upload_error="",
            erp_upload_code=upload_code,
        )
        return {
            "batch_id": batch_id,
            "upload_status": "uploaded",
            "export_dir": str(export_dir),
            "upload_error": "",
            "message": f"重试上传成功，批次 {upload_code}",
            "details": upload_result.details or [],
        }

    def _set_batch_upload_state(
        self,
        batch_id: int,
        upload_status: str,
        export_dir: str = "",
        upload_error: str = "",
        erp_upload_code: str = "",
    ) -> None:
        with self.connect() as connection:
            updates = {
                "upload_status": upload_status,
                "updated_at": utc_now(),
            }
            if export_dir:
                updates["export_dir"] = export_dir
            if upload_error or upload_status in {"failed", "uploaded", "ready"}:
                updates["upload_error"] = upload_error
            if erp_upload_code:
                updates["erp_upload_code"] = erp_upload_code
            if upload_status == "uploaded":
                updates["uploaded_at"] = utc_now()
            assignments = ", ".join(f"{key} = ?" for key in updates)
            connection.execute(
                f"UPDATE erp_import_batches SET {assignments} WHERE id = ?",
                (*updates.values(), batch_id),
            )

    def notify_erp_batch_ready(self, product_id: int, batch_id: int) -> str | None:
        batch = self.fetch_erp_batch(batch_id)
        if not batch:
            return "ERP 批次不存在"
        product = self.fetch_product(product_id)
        product_name = str(batch["product_name"] or (product["name"] if product else "") or "待命名产品")
        with self.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM erp_sku_rows WHERE batch_id = ?",
                (batch_id,),
            ).fetchone()
            row_count = int(row["total"]) if row else 0
        link_product_id = 0 if product and product["sku"] == STANDALONE_ERP_PRODUCT_SKU else product_id
        result = send_erp_ready_notice(
            product_name=product_name,
            erp_code=str(batch["product_full_code"] or ""),
            row_count=row_count,
            product_id=link_product_id,
            batch_id=batch_id,
            upload_code=str(batch["erp_upload_code"] or ""),
        )
        content = result.content
        if result.error:
            content = f"{content}\n[发送失败: {result.error}]"
        with self.connect() as connection:
            self._add_notification(
                connection,
                product_id,
                result.channel,
                result.recipient,
                content,
                status=result.status,
            )
        return result.error if not result.ok else None

    def _add_event(
        self,
        connection: sqlite3.Connection,
        product_id: int,
        from_status: str,
        to_status: str,
        action: str,
        message: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO workflow_events
                (product_id, from_status, to_status, action, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (product_id, from_status, to_status, action, message, utc_now()),
        )

    def _add_notification(
        self,
        connection: sqlite3.Connection,
        product_id: int,
        channel: str,
        recipient: str,
        content: str,
        status: str = "sent",
    ) -> None:
        connection.execute(
            """
            INSERT INTO notifications
                (product_id, channel, recipient, content, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (product_id, channel, recipient, content, status, utc_now()),
        )


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
