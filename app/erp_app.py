from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.erp import (
    build_erp_rows,
    erp_missing_price_warning,
    erp_pinyin_warning as get_erp_pinyin_warning,
)
from app.erp_db import ErpDatabase
from app.erp_export import build_distribution_xlsx, build_new_product_xlsx
from app.erp_ingest import ingest_upload, normalize_raw_text_for_erp
from app.erp_upload import DISTRIBUTION_FILENAME, NEW_PRODUCT_FILENAME

DATABASE_PATH = os.getenv("DATABASE_PATH", "data/erp.sqlite3")
DB = ErpDatabase(DATABASE_PATH)

app = FastAPI(title="ERP 资料录入")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


def _attachment_disposition(filename: str, *, ascii_fallback: str) -> str:
    try:
        filename.encode("latin-1")
    except UnicodeEncodeError:
        encoded = quote(filename)
        return f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded}'
    return f'attachment; filename="{filename}"'


def _erp_upload_result_from_request(request: Request) -> dict[str, str] | None:
    batch_id = request.query_params.get("upload_batch_id")
    if not batch_id:
        return None
    return {
        "batch_id": batch_id,
        "upload_status": request.query_params.get("upload_status", ""),
        "upload_message": request.query_params.get("upload_message", ""),
    }


async def _read_erp_upload(request: Request) -> dict[str, str]:
    form = await request.form()
    pasted_text = str(form.get("raw_text", ""))
    raw_text = pasted_text
    source_file_name = str(form.get("source_file_name", ""))
    source_type = str(form.get("source_type", "table_text"))
    width_span = str(form.get("width_span", ""))
    default_product_name = str(form.get("default_product_name", "")).strip() or "待命名产品"
    upload = form.get("upload_file")
    upload_error = ""
    if upload is not None and getattr(upload, "filename", ""):
        content = await upload.read()
        try:
            extracted, detected_type, filename = ingest_upload(upload.filename, content)
            if extracted.strip():
                raw_text = extracted
                source_type = detected_type
                if not source_file_name.strip():
                    source_file_name = filename
            elif pasted_text.strip():
                raw_text = pasted_text
                source_type = "table_text"
                upload_error = "截图/Excel 未解析出内容，已改用下方粘贴文本"
            else:
                raise ValueError("截图/Excel 未解析出内容，请在下方粘贴识别文本，或换更清晰文件")
        except ValueError as exc:
            if pasted_text.strip():
                raw_text = pasted_text
                source_type = "table_text"
                upload_error = f"文件解析失败，已改用粘贴文本：{exc}"
            else:
                raise
    normalized, hints = normalize_raw_text_for_erp(raw_text)
    if normalized.strip():
        raw_text = normalized
    if hints.get("width_span") and not width_span.strip():
        width_span = hints["width_span"]
    if hints.get("product_name") and default_product_name == "待命名产品":
        default_product_name = hints["product_name"]
    return {
        "raw_text": raw_text,
        "source_file_name": source_file_name,
        "source_type": source_type,
        "width_span": width_span,
        "default_product_name": default_product_name,
        "upload_notice": upload_error,
    }


async def _build_erp_from_upload(request: Request) -> dict:
    payload = await _read_erp_upload(request)
    if not payload["raw_text"].strip():
        raise ValueError("请粘贴表格文本，或上传 Excel / 截图")
    built = build_erp_rows(
        payload["default_product_name"],
        payload["raw_text"],
        payload["width_span"],
    )
    if not built["rows"]:
        raise ValueError("没有解析到可录入的规格行，请检查表格或截图内容")
    return built


def _erp_page_context(request: Request, **extra) -> dict:
    return {
        "request": request,
        "erp_error": request.query_params.get("erp_error"),
        "erp_warning": None,
        "erp_pinyin_warning": None,
        "erp_preview": None,
        "erp_input": {},
        "notify_error": request.query_params.get("notify_error"),
        "erp_upload_result": _erp_upload_result_from_request(request),
        **extra,
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def erp_home(request: Request):
    return templates.TemplateResponse(
        request,
        "erp_page.html",
        _erp_page_context(request),
    )


@app.get("/modules/erp")
def erp_module_redirect():
    return RedirectResponse("/", status_code=303)


@app.post("/modules/erp/preview")
async def preview_erp_import(request: Request):
    erp_preview = None
    erp_error = None
    erp_warning = None
    erp_pinyin_warning = None
    erp_input: dict[str, str] = {}
    try:
        payload = await _read_erp_upload(request)
        erp_input = payload
        if not payload["raw_text"].strip():
            raise ValueError("请粘贴表格文本，或上传 Excel / 截图")
        built = build_erp_rows(
            payload["default_product_name"],
            payload["raw_text"],
            payload["width_span"],
        )
        if not built["rows"]:
            raise ValueError("没有解析到可录入的规格行，请检查表格或截图内容")
        erp_warning = erp_missing_price_warning(built)
        erp_pinyin_warning = get_erp_pinyin_warning(built)
        erp_preview = {"input": payload, "built": built}
    except ValueError as exc:
        erp_error = str(exc)
    return templates.TemplateResponse(
        request,
        "erp_page.html",
        _erp_page_context(
            request,
            erp_error=erp_error,
            erp_warning=erp_warning,
            erp_pinyin_warning=erp_pinyin_warning,
            erp_preview=erp_preview,
            erp_input=erp_input,
        ),
    )


@app.post("/modules/erp/auto-upload")
async def auto_upload_erp_route(request: Request):
    try:
        form = await request.form()
        only = str(form.get("only", "distribution") or "distribution").strip()
        if only not in {"distribution", "new_product"}:
            raise ValueError("未知上传类型")
        send_notify = str(form.get("send_notify", "")).strip().lower() in {"1", "true", "on", "yes"}
        payload = await _read_erp_upload(request)
        built = build_erp_rows(
            payload["default_product_name"],
            payload["raw_text"],
            payload["width_span"],
        )
        if not built["rows"]:
            raise ValueError("没有解析到可录入的规格行，请检查表格或截图内容")
        result = DB.confirm_erp_auto_upload(built, payload, only=only, send_notify=send_notify)
        redirect = (
            f"/?upload_batch_id={result['batch_id']}"
            f"&upload_status={quote(result['upload_status'])}"
            f"&upload_message={quote(result['message'])}"
        )
        if result.get("notify_error"):
            redirect = f"{redirect}&notify_error={quote(result['notify_error'])}"
        return RedirectResponse(redirect, status_code=303)
    except ValueError as exc:
        return RedirectResponse(f"/?erp_error={quote(str(exc))}", status_code=303)


@app.post("/modules/erp/retry-upload/{batch_id}")
async def retry_erp_upload_route(batch_id: int):
    try:
        result = DB.retry_erp_upload(batch_id)
        return RedirectResponse(
            (
                f"/?upload_batch_id={result['batch_id']}"
                f"&upload_status={quote(result['upload_status'])}"
                f"&upload_message={quote(result['message'])}"
            ),
            status_code=303,
        )
    except ValueError as exc:
        return RedirectResponse(f"/?erp_error={quote(str(exc))}", status_code=303)


@app.get("/modules/erp/download/{batch_id}/{file_kind}")
def download_erp_bundle_file(batch_id: int, file_kind: str):
    batch = DB.fetch_erp_batch(batch_id)
    if not batch or not batch["export_dir"]:
        return RedirectResponse("/?erp_error=导出文件不存在", status_code=303)
    export_dir = batch["export_dir"]
    if file_kind == "distribution":
        path = f"{export_dir}/{DISTRIBUTION_FILENAME}"
        filename = DISTRIBUTION_FILENAME
        ascii_fallback = "distribution.xlsx"
    elif file_kind == "new-product":
        path = f"{export_dir}/{NEW_PRODUCT_FILENAME}"
        filename = NEW_PRODUCT_FILENAME
        ascii_fallback = "new_product.xlsx"
    else:
        return RedirectResponse("/?erp_error=未知文件类型", status_code=303)
    try:
        content = open(path, "rb").read()
    except OSError:
        return RedirectResponse("/?erp_error=导出文件不存在", status_code=303)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": _attachment_disposition(filename, ascii_fallback=ascii_fallback)},
    )


@app.post("/modules/erp/export-distribution")
async def export_erp_distribution(request: Request):
    try:
        built = await _build_erp_from_upload(request)
        content = build_distribution_xlsx(built)
    except ValueError as exc:
        return RedirectResponse(f"/?erp_error={quote(str(exc))}", status_code=303)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": _attachment_disposition("分销上架模版.xlsx", ascii_fallback="distribution.xlsx")},
    )


@app.post("/modules/erp/export-new-product")
async def export_erp_new_product(request: Request):
    try:
        built = await _build_erp_from_upload(request)
        content = build_new_product_xlsx(built)
    except ValueError as exc:
        return RedirectResponse(f"/?erp_error={quote(str(exc))}", status_code=303)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": _attachment_disposition("新品录入.xlsx", ascii_fallback="new_product.xlsx")},
    )


def run() -> None:
    port = int(os.getenv("PORT", "8001"))
    host = os.getenv("HOST", "127.0.0.1")
    uvicorn.run("app.erp_app:app", host=host, port=port, reload=False)
