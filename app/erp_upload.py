from __future__ import annotations

import asyncio
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.erp import erp_pinyin_warning
from app.erp_export import build_distribution_xlsx, build_new_product_xlsx

DISTRIBUTION_FILENAME = "分销上架模版.xlsx"
NEW_PRODUCT_FILENAME = "新品录入.xlsx"
_UNICODE_PINYIN_PATTERN = re.compile(r"u[0-9a-f]{4}")


@dataclass
class UploadResult:
    ok: bool
    export_dir: Path | None = None
    error: str | None = None
    rpa_skipped: bool = False
    details: list[str] | None = None


def validate_built_for_upload(built: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = built.get("rows") or []
    if not rows:
        errors.append("没有可录入的规格行")
        return errors

    pinyin_warning = erp_pinyin_warning(built)
    if pinyin_warning:
        errors.append(pinyin_warning)

    style_code = str(built.get("product_full_code") or "")
    if style_code and _UNICODE_PINYIN_PATTERN.search(style_code):
        errors.append(f"款式编码异常：{style_code}")

    if not any(row.get("price_present") for row in rows):
        errors.append("全部规格未读到成本价，无法录入 ERP")

    batch_missing = built.get("batch_missing") or []
    if "门幅" in batch_missing:
        errors.append("缺少门幅，商品名称无法完整写入")

    return errors


def export_erp_bundle(built: dict[str, Any], batch_id: int, base_dir: Path | None = None) -> Path:
    root = base_dir or Path("data/erp_exports")
    export_dir = root / str(batch_id)
    export_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / DISTRIBUTION_FILENAME).write_bytes(build_distribution_xlsx(built))
    (export_dir / NEW_PRODUCT_FILENAME).write_bytes(build_new_product_xlsx(built))
    return export_dir


def bundle_file_paths(export_dir: Path) -> dict[str, Path]:
    return {
        "distribution": export_dir / DISTRIBUTION_FILENAME,
        "new_product": export_dir / NEW_PRODUCT_FILENAME,
    }


def _run_erp_playwright_upload_sync(
    export_dir: Path,
    batch_id: int,
    only: str | None = None,
) -> UploadResult:
    try:
        from app.erp_rpa import ErpRpaConfig, run_batch_upload
    except ImportError:
        return UploadResult(
            ok=False,
            export_dir=export_dir,
            error="未安装 Playwright，请执行：pip install -r requirements-rpa.txt && playwright install chromium",
            rpa_skipped=True,
        )

    config = ErpRpaConfig.load()
    if not config.ready:
        return UploadResult(
            ok=False,
            export_dir=export_dir,
            error=config.load_error or "聚水潭 RPA 未就绪，请先执行：pip install -r requirements-rpa.txt && python -m app.erp_rpa login",
            rpa_skipped=True,
        )

    files = bundle_file_paths(export_dir)
    try:
        details = run_batch_upload(config, files, screenshot_dir=export_dir, only=only)
        return UploadResult(ok=True, export_dir=export_dir, details=details)
    except Exception as exc:
        return UploadResult(ok=False, export_dir=export_dir, error=str(exc))


def run_erp_playwright_upload(
    export_dir: Path,
    batch_id: int,
    only: str | None = None,
) -> UploadResult:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return _run_erp_playwright_upload_sync(export_dir, batch_id, only=only)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_run_erp_playwright_upload_sync, export_dir, batch_id, only)
        return future.result()
