from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass
class NotifyResult:
    ok: bool
    channel: str
    recipient: str
    content: str
    error: str | None = None

    @property
    def status(self) -> str:
        return "sent" if self.ok else "failed"


def notify_mode() -> str:
    return os.environ.get("NOTIFY_MODE", "mock").strip().lower()


def erp_notify_auto_enabled() -> bool:
    return os.environ.get("NOTIFY_ERP_AUTO", "1").strip().lower() not in {"0", "false", "no", "off"}


def build_erp_ready_content(
    product_name: str,
    erp_code: str,
    row_count: int,
    *,
    product_id: int = 0,
    batch_id: int = 0,
    upload_code: str = "",
    detail_url: str = "",
) -> str:
    base_url = os.environ.get("NOTIFY_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    if not detail_url:
        if product_id > 0:
            detail_url = f"{base_url}/products/{product_id}"
        elif batch_id > 0:
            detail_url = f"{base_url}/modules/erp?upload_batch_id={batch_id}"
        else:
            detail_url = f"{base_url}/modules/erp"
    batch_line = upload_code or (f"ERP-BATCH-{batch_id:05d}" if batch_id > 0 else "")
    lines = [
        "【ERP资料已录入】",
        f"商品：{product_name}",
        f"款式编码：{erp_code}",
        f"规格数量：{row_count} 条",
    ]
    if batch_line:
        lines.append(f"批次：{batch_line}")
    lines.extend(
        [
            f"详情：{detail_url}",
            "提醒：资料已录入聚水潭，请美工/运营安排主图详情排版。",
        ]
    )
    return "\n".join(lines)


def build_design_request_content(
    product_name: str,
    design_brief: str,
    product_id: int,
    detail_url: str,
) -> str:
    summary = str(design_brief or "").strip() or "请根据商品资料制作主图和详情页素材"
    return (
        "【上架协同】新商品待排版\n"
        f"商品：{product_name}\n"
        f"需求：{summary}\n"
        f"详情：{detail_url}"
    )


def send_design_request(
    *,
    product_name: str,
    design_brief: str,
    product_id: int,
) -> NotifyResult:
    base_url = os.environ.get("NOTIFY_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    detail_url = f"{base_url}/products/{product_id}"
    content = build_design_request_content(product_name, design_brief, product_id, detail_url)
    return send_group_text(content, recipient="美工排版群")


def send_erp_ready_notice(
    *,
    product_name: str,
    erp_code: str,
    row_count: int,
    product_id: int = 0,
    batch_id: int = 0,
    upload_code: str = "",
) -> NotifyResult:
    content = build_erp_ready_content(
        product_name,
        erp_code,
        row_count,
        product_id=product_id,
        batch_id=batch_id,
        upload_code=upload_code,
    )
    return send_group_text(content, recipient="ERP协同群")


def send_group_text(content: str, *, recipient: str) -> NotifyResult:
    mode = notify_mode()
    if mode == "dingtalk":
        return _send_dingtalk_group(content, recipient=recipient)
    return _send_mock_group(content, recipient=recipient)


def _send_mock_group(content: str, *, recipient: str) -> NotifyResult:
    return NotifyResult(
        ok=True,
        channel="mock_wechat_group",
        recipient=recipient,
        content=f"模拟群通知：\n{content}",
    )


def _send_dingtalk_group(content: str, *, recipient: str) -> NotifyResult:
    webhook_url = os.environ.get("DINGTALK_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return NotifyResult(
            ok=False,
            channel="dingtalk_group",
            recipient=recipient,
            content=content,
            error="未配置 DINGTALK_WEBHOOK_URL",
        )
    signed_url = _dingtalk_signed_url(webhook_url, os.environ.get("DINGTALK_SECRET", "").strip())
    payload = json.dumps(
        {"msgtype": "text", "text": {"content": content}},
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        signed_url,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return NotifyResult(
            ok=False,
            channel="dingtalk_group",
            recipient=recipient,
            content=content,
            error=f"HTTP {exc.code}: {detail}",
        )
    except urllib.error.URLError as exc:
        return NotifyResult(
            ok=False,
            channel="dingtalk_group",
            recipient=recipient,
            content=content,
            error=str(exc.reason or exc),
        )

    try:
        result = json.loads(body)
    except json.JSONDecodeError:
        return NotifyResult(
            ok=False,
            channel="dingtalk_group",
            recipient=recipient,
            content=content,
            error=f"钉钉返回非 JSON：{body}",
        )
    if result.get("errcode") == 0:
        return NotifyResult(
            ok=True,
            channel="dingtalk_group",
            recipient=recipient,
            content=content,
        )
    return NotifyResult(
        ok=False,
        channel="dingtalk_group",
        recipient=recipient,
        content=content,
        error=result.get("errmsg") or body,
    )


def _dingtalk_signed_url(webhook_url: str, secret: str) -> str:
    if not secret:
        return webhook_url
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    digest = hmac.new(secret.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(digest))
    separator = "&" if "?" in webhook_url else "?"
    return f"{webhook_url}{separator}timestamp={timestamp}&sign={sign}"
