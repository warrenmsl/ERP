from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

JUSHUITAN_LOGIN_URL = "https://www.erp321.com/"
JUSHUITAN_HOME_URL = "https://www.erp321.com/"
JUSHUITAN_DASHBOARD_URL = "https://www.erp321.com/epaas"
JUSHUITAN_DISTRIBUTION_START_URL = "https://www.erp321.com/epaas"
JUSHUITAN_SCM_DASHBOARD_URL = "https://sc.scm121.com/dashboard"
JUSHUITAN_SCM_GOODS_URL = "https://sc.scm121.com/manage/goods/goodsmanage/index"
JUSHUITAN_DISTRIBUTION_FLOW = (
    "ERP分销版",
    "商品",
    "商品管理",
    "导入 Excel 表格新增",
    "导入Excel表格新增",
)
JUSHUITAN_DISTRIBUTION_ENTRY_KEYWORDS = (
    "ERP分销版",
    "ERP 分销版",
    "分销版",
)
JUSHUITAN_DISTRIBUTION_IMPORT_KEYWORDS = (
    "导入Excel表格新增",
    "导入 Excel 表格新增",
    "导入Excel",
)
JUSHUITAN_DISTRIBUTION_IMPORT_DIALOG_HINTS = (
    "导入excel表格新增",
    "导入 excel 表格新增",
    "标准模板导入",
    "上传文件",
    "将Excel文件拖拽至框内上传",
)
JUSHUITAN_DISTRIBUTION_UPLOAD_KEYWORDS = (
    "上传文件",
    "确认导入",
    "开始导入",
    "确定导入",
)
JUSHUITAN_DISTRIBUTION_SYNC_TITLE = "以下商品将同步至基础资料，请确认"
JUSHUITAN_DISTRIBUTION_SYNC_CONFIRM_HINTS = (
    JUSHUITAN_DISTRIBUTION_SYNC_TITLE,
    "以下商品将同步至基础资料",
    "同步至基础资料",
    "将新增至基础资料",
)
JUSHUITAN_DISTRIBUTION_SYNC_READY_HINTS = (
    JUSHUITAN_DISTRIBUTION_SYNC_TITLE,
    "将新增至基础资料",
    "商品编码[",
    "以下商品将同步至基础资料",
)
JUSHUITAN_DISTRIBUTION_SYNC_CONFIRM_BUTTON = "确定"
JUSHUITAN_DISTRIBUTION_SYNC_CONFIRM_LABEL_RE = re.compile(r"确\s*定")
JUSHUITAN_NEW_PRODUCT_START_URL = "https://www.erp321.com/epaas"
JUSHUITAN_NEW_PRODUCT_MENU_KEYWORDS = (
    "商品及库存管理(普通商品资料)",
    "商品及库存管理（普通商品资料）",
    "商品及库存管理",
    "普通商品资料",
)
JUSHUITAN_NEW_PRODUCT_IMPORT_MENU = (
    "从Excel导入商品",
    "从 Excel 导入商品",
)
JUSHUITAN_NEW_PRODUCT_UPDATE_MODE = "全部更新"
JUSHUITAN_NEW_PRODUCT_KEYWORDS = JUSHUITAN_NEW_PRODUCT_MENU_KEYWORDS
JUSHUITAN_NEW_PRODUCT_PAGE_HINTS = (
    "款式编码",
    "商品编码",
    "普通商品资料",
    "商品及库存管理",
)
JUSHUITAN_NEW_PRODUCT_IMPORT_DIALOG_HINTS = (
    "从Excel导入商品",
    "从 Excel 导入商品",
    "点击或拖拽Excel文件到这里上传",
    "下载模板",
)
JUSHUITAN_NEW_PRODUCT_IMPORT_EXCLUDE = (
    "Excel导入款信息",
    "Excel导入款式信息",
)
JUSHUITAN_NEW_PRODUCT_UPLOAD_KEYWORDS = (
    "确认导入",
    "开始导入",
    "确定导入",
    "导入",
)
IMPORT_ENTRY_KEYWORDS = ("批量导入", "Excel导入", "导入商品", "文件导入", "导入")
SUBMIT_KEYWORDS = ("确认导入", "开始导入", "确定导入", "导入", "上传", "确认", "确定", "提交")
SUCCESS_KEYWORDS = ("导入成功", "上传成功", "操作成功", "成功")
RPA_CLICK_PAUSE_MS = 200
RPA_STEP_PAUSE_MS = 400
RPA_POPUP_PAUSE_MS = 150
RPA_ACTION_TIMEOUT_MS = 3000
RPA_SUCCESS_WAIT_MS = 10000
RPA_DISTRIBUTION_SYNC_WAIT_MS = 180000
RPA_DISTRIBUTION_SYNC_POLL_MS = 80
RPA_MODAL_CONFIRM_TIMEOUT_MS = 3000
RPA_CONFIRM_FAIL_PAUSE_MS = 120000
POPUP_CLOSE_SELECTORS = (
    ".ant-modal-close",
    ".ant-modal-close-x",
    ".ant-drawer-close",
    "[aria-label='Close']",
    "[class*='modal'] [class*='close']",
)
POPUP_DISMISS_TEXTS = (
    "不再提醒",
    "知道了",
    "我知道了",
    "关闭",
    "取消",
    "暂不",
    "暂不处理",
    "稍后再说",
    "下次再说",
    "跳过",
)
POPUP_TITLE_HINTS = (
    "订购到期或即将到期",
    "店铺过期/异常提醒",
    "店铺过期",
    "订购到期",
    "异常提醒",
    "提醒",
    "公告",
)
STORE_EXPIRY_REMINDER_HINTS = POPUP_TITLE_HINTS
RPA_SCM_DASHBOARD_POPUP_WAIT_MS = 250
STORE_EXPIRY_REMINDER_PRIORITY_HINTS = (
    "订购到期或即将到期",
    "店铺过期/异常提醒",
    "店铺过期",
)
STORE_EXPIRY_MODAL_TITLE_HINTS = STORE_EXPIRY_REMINDER_PRIORITY_HINTS
RPA_STORE_EXPIRY_DISMISS_MAX_ROUNDS = 12
RPA_BLOCKING_REMINDERS_MAX_ROUNDS = 8


@dataclass
class TemplateConfig:
    path: str = ""
    start_url: str = ""
    file_input: str = "input[type=file]"
    submit: str = "button[type=submit]"
    success_contains: str = "成功"
    menu_keywords: tuple[str, ...] = ()
    flow_clicks: tuple[str, ...] = ()
    wait_url_contains: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TemplateConfig:
        keywords = data.get("menu_keywords") or []
        flow_clicks = data.get("flow_clicks") or []
        return cls(
            path=str(data.get("path", "")),
            start_url=str(data.get("start_url", "")),
            file_input=str(data.get("file_input", "input[type=file]")),
            submit=str(data.get("submit", "button[type=submit]")),
            success_contains=str(data.get("success_contains", "成功")),
            menu_keywords=tuple(str(item) for item in keywords),
            flow_clicks=tuple(str(item) for item in flow_clicks),
            wait_url_contains=str(data.get("wait_url_contains", "")),
        )


@dataclass
class ErpRpaConfig:
    mode: str = "jushuitan"
    base_url: str = JUSHUITAN_HOME_URL
    login_url: str = JUSHUITAN_LOGIN_URL
    storage_state: str = "config/erp_storage.json"
    headful: bool = True
    login_wait_ms: int = 300000
    distribution: TemplateConfig = field(default_factory=TemplateConfig)
    new_product: TemplateConfig = field(default_factory=TemplateConfig)
    ready: bool = False
    load_error: str | None = None

    @classmethod
    def load(cls, path: Path | None = None) -> ErpRpaConfig:
        config_path = path or Path("config/erp_rpa.local.json")
        if config_path.exists():
            try:
                data = json.loads(config_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                return cls(ready=False, load_error=f"配置文件 JSON 无效：{exc}")
        else:
            data = cls._default_jushuitan_data()

        mode = str(data.get("mode", "jushuitan")).strip().lower()
        base_url = str(data.get("base_url", JUSHUITAN_HOME_URL)).strip() or JUSHUITAN_HOME_URL
        login_url = str(data.get("login_url", JUSHUITAN_LOGIN_URL)).strip() or JUSHUITAN_LOGIN_URL
        storage_state = str(data.get("storage_state", "config/erp_storage.json")).strip()
        headful = bool(data.get("headful", True))
        login_wait_ms = int(data.get("login_wait_ms", 300000))

        distribution = TemplateConfig.from_dict(data.get("distribution", {}))
        new_product = TemplateConfig.from_dict(data.get("new_product", {}))
        if mode == "jushuitan":
            if not distribution.start_url:
                distribution.start_url = JUSHUITAN_DISTRIBUTION_START_URL
            if not distribution.flow_clicks:
                distribution.flow_clicks = JUSHUITAN_DISTRIBUTION_FLOW
            if not distribution.wait_url_contains:
                distribution.wait_url_contains = "scm121.com"
            if not new_product.start_url:
                new_product.start_url = JUSHUITAN_NEW_PRODUCT_START_URL
            if not new_product.menu_keywords:
                new_product.menu_keywords = JUSHUITAN_NEW_PRODUCT_MENU_KEYWORDS

        has_storage = Path(storage_state).exists()
        if mode == "jushuitan":
            ready = True
            load_error = None if has_storage or headful else "请先运行：python -m app.erp_rpa login"
        elif not base_url:
            ready = False
            load_error = "配置缺少 base_url"
        elif not has_storage:
            ready = False
            load_error = f"未找到登录态文件 {storage_state}，请先运行：python -m app.erp_rpa login"
        else:
            ready = True
            load_error = None

        return cls(
            mode=mode,
            base_url=base_url,
            login_url=login_url,
            storage_state=storage_state,
            headful=headful,
            login_wait_ms=login_wait_ms,
            distribution=distribution,
            new_product=new_product,
            ready=ready,
            load_error=load_error,
        )

    @staticmethod
    def _default_jushuitan_data() -> dict[str, Any]:
        return {
            "mode": "jushuitan",
            "base_url": JUSHUITAN_HOME_URL,
            "login_url": JUSHUITAN_LOGIN_URL,
            "storage_state": "config/erp_storage.json",
            "headful": True,
            "login_wait_ms": 300000,
            "distribution": {
                "start_url": JUSHUITAN_DISTRIBUTION_START_URL,
                "flow_clicks": list(JUSHUITAN_DISTRIBUTION_FLOW),
                "wait_url_contains": "scm121.com",
            },
            "new_product": {
                "start_url": JUSHUITAN_NEW_PRODUCT_START_URL,
                "menu_keywords": list(JUSHUITAN_NEW_PRODUCT_MENU_KEYWORDS),
            },
        }


def run_batch_upload(
    config: ErpRpaConfig,
    files: dict[str, Path],
    screenshot_dir: Path | None = None,
    only: str | None = None,
    *,
    stop_before_confirm: bool = False,
    stop_after_import_dialog: bool = False,
) -> list[str]:
    from playwright.sync_api import sync_playwright

    storage_path = Path(config.storage_state)
    use_headful = config.headful or not storage_path.exists()
    details: list[str] = []

    with sync_playwright() as playwright:
        browser = _launch_browser(playwright, headless=not use_headful)
        if storage_path.exists():
            context = browser.new_context(storage_state=str(storage_path))
        else:
            context = browser.new_context()
        page = context.new_page()
        upload_failed = False
        try:
            if config.mode == "jushuitan":
                _ensure_jushuitan_session(page, context, config, storage_path, use_headful)
                if only in (None, "distribution"):
                    details.append(
                        _jushuitan_upload_distribution(
                            page,
                            files["distribution"],
                            config.distribution,
                            debug_dir=screenshot_dir,
                            headful=use_headful,
                            stop_before_confirm=stop_before_confirm,
                            stop_after_import_dialog=stop_after_import_dialog,
                        )
                    )
                if only in (None, "new_product"):
                    if only != "new_product":
                        _ensure_jushuitan_session(page, context, config, storage_path, use_headful=False)
                    details.append(
                        _jushuitan_upload_new_product(
                            page,
                            files["new_product"],
                            config.new_product,
                            debug_dir=screenshot_dir,
                            headful=use_headful,
                            stop_before_confirm=only == "new_product" and stop_before_confirm,
                            stop_after_import_dialog=only == "new_product" and stop_after_import_dialog,
                        )
                    )
            else:
                details.append(
                    _upload_file(page, config.base_url, config.distribution, files["distribution"], "分销上架")
                )
                details.append(
                    _upload_file(page, config.base_url, config.new_product, files["new_product"], "新品录入")
                )
        except Exception:
            upload_failed = True
            if screenshot_dir is not None:
                screenshot_dir.mkdir(parents=True, exist_ok=True)
                try:
                    page.screenshot(path=str(screenshot_dir / "error.png"), full_page=True)
                except Exception:
                    pass
                for candidate in context.pages:
                    if _url_contains(candidate.url, "scm121.com"):
                        try:
                            candidate.screenshot(
                                path=str(screenshot_dir / "error_scm121.png"),
                                full_page=True,
                            )
                        except Exception:
                            pass
                    url = str(candidate.url or "")
                    if _url_contains(url, "erp321.com") and not _url_contains(url, "scm121.com"):
                        try:
                            candidate.screenshot(
                                path=str(screenshot_dir / "error_epaas.png"),
                                full_page=True,
                            )
                        except Exception:
                            pass
            raise
        finally:
            if storage_path.parent.exists() or config.mode == "jushuitan":
                storage_path.parent.mkdir(parents=True, exist_ok=True)
                context.storage_state(path=str(storage_path))
            if use_headful and (upload_failed or stop_before_confirm or stop_after_import_dialog):
                _pause_before_browser_close(context)
            context.close()
            browser.close()
    return details


def _ensure_jushuitan_session(
    page: Any,
    context: Any,
    config: ErpRpaConfig,
    storage_path: Path,
    use_headful: bool,
) -> None:
    page.goto(config.base_url or JUSHUITAN_HOME_URL, wait_until="domcontentloaded", timeout=60000)
    if _looks_logged_in(page):
        _dismiss_blocking_reminders(page)
        return
    page.goto(config.login_url or JUSHUITAN_LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
    if use_headful:
        print("已在浏览器打开聚水潭登录页，请人工登录。登录成功后脚本会自动继续…")
    _wait_for_jushuitan_login(page, config.login_wait_ms)
    _dismiss_blocking_reminders(page)
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    context.storage_state(path=str(storage_path))


def _looks_logged_in(page: Any) -> bool:
    url = str(page.url or "").lower()
    if "login" in url:
        return False
    if page.locator("input[type=password]").count() > 0:
        return False
    for keyword in ("商品", "订单", "库存", "首页", "工作台"):
        if page.get_by_text(keyword, exact=False).count() > 0:
            return True
    return "erp321.com" in url and "login" not in url


def _wait_for_jushuitan_login(page: Any, timeout_ms: int) -> None:
    page.wait_for_function(
        """() => {
            const href = location.href.toLowerCase();
            if (href.includes('login')) return false;
            if (document.querySelector('input[type=password]')) return false;
            const text = document.body ? document.body.innerText : '';
            return ['商品', '订单', '库存', '首页', '工作台'].some((item) => text.includes(item));
        }""",
        timeout=timeout_ms,
    )


def _launch_browser(playwright: Any, headless: bool) -> Any:
    try:
        return playwright.chromium.launch(headless=headless, channel="chrome")
    except Exception:
        return playwright.chromium.launch(headless=headless)


def _jushuitan_upload_distribution(
    page: Any,
    file_path: Path,
    template: TemplateConfig,
    *,
    debug_dir: Path | None = None,
    headful: bool = True,
    stop_before_confirm: bool = False,
    stop_after_import_dialog: bool = False,
) -> str:
    if not file_path.exists():
        raise FileNotFoundError(f"分销上架 文件不存在：{file_path}")

    work_page = _run_distribution_stable_phase(page, template)
    if stop_after_import_dialog:
        return "分销上架 稳定阶段完成：「导入 Excel 表格新增」弹窗已打开"
    work_page = _run_distribution_import_file_phase(work_page, file_path, template)
    if stop_before_confirm:
        return (
            f"分销上架：{file_path.name} 已提交导入，"
            "等待「同步至基础资料」弹窗（请继续调确定步骤）"
        )

    work_page = _run_distribution_confirm_phase(
        work_page,
        debug_dir=debug_dir,
        headful=headful,
    )
    return f"分销上架 上传成功：{file_path.name}"


def _run_distribution_stable_phase(page: Any, template: TemplateConfig) -> Any:
    """
    分销上架稳定阶段（已验收，勿随意改动）：
    epaas → scm121 商品管理 → 点击「导入 Excel 表格新增」→ 弹窗打开。
    """
    page.goto(template.start_url or JUSHUITAN_DASHBOARD_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(RPA_CLICK_PAUSE_MS)
    _dismiss_blocking_reminders(page)

    work_page = _open_jushuitan_scm_page(page)
    work_page = _navigate_to_goods_manage(work_page)
    work_page = _wait_for_goods_manage_ready(work_page)
    _dismiss_blocking_reminders(work_page)

    if not _click_first_visible_text(work_page, JUSHUITAN_DISTRIBUTION_IMPORT_KEYWORDS):
        raise RuntimeError("分销上架：未找到「导入 Excel 表格新增」")

    work_page = _resolve_live_scm_page(work_page)
    work_page.wait_for_timeout(RPA_CLICK_PAUSE_MS)
    return _wait_for_distribution_import_dialog_ready(work_page)


def _run_distribution_import_file_phase(
    work_page: Any,
    file_path: Path,
    template: TemplateConfig,
) -> Any:
    """
    分销上架上传阶段：在导入弹窗内选文件并点「上传文件」提交。
    """
    work_page = _resolve_live_scm_page(work_page)
    _set_file_on_page(work_page, file_path, template.file_input)
    work_page.wait_for_timeout(RPA_CLICK_PAUSE_MS)

    if not _click_distribution_import_submit(work_page):
        raise RuntimeError("分销上架：未找到「上传文件」或导入确认按钮")

    work_page.wait_for_timeout(RPA_STEP_PAUSE_MS)
    return _resolve_live_scm_page(work_page)


def _click_distribution_import_submit(page: Any) -> bool:
    if _click_first_visible_text(page, JUSHUITAN_DISTRIBUTION_UPLOAD_KEYWORDS, prefer_last=True):
        return True
    return _click_submit(page)


def _run_distribution_confirm_phase(
    work_page: Any,
    *,
    debug_dir: Path | None = None,
    headful: bool = True,
) -> Any:
    """
    分销上架确认阶段（待调优）：
    「同步至基础资料」弹窗 → 点「确 定」→ 等待导入成功。
    """
    work_page = _resolve_live_scm_page(work_page)
    if not _confirm_distribution_basic_data_sync(work_page):
        work_page = _resolve_live_scm_page(work_page)
        _dump_distribution_confirm_debug(work_page, debug_dir, headful=headful)
        raise RuntimeError("分销上架：未找到「同步至基础资料」确认弹窗或「确定」按钮")

    work_page = _resolve_live_scm_page(work_page)
    _wait_for_success(work_page)
    return work_page


def _confirm_distribution_basic_data_sync(page: Any) -> bool:
    attempts = max(1, RPA_DISTRIBUTION_SYNC_WAIT_MS // RPA_DISTRIBUTION_SYNC_POLL_MS)
    live_page = page
    for _ in range(attempts):
        live_page = _resolve_live_scm_page(live_page)
        try:
            for scope in _page_scopes(live_page):
                try:
                    if not _distribution_sync_modal_ready(scope):
                        continue
                    if _click_distribution_sync_confirm_ant_modal(live_page, scope):
                        return True
                    if _click_distribution_sync_confirm_nk(live_page, scope):
                        return True
                    if _click_distribution_sync_confirm_js(scope):
                        live_page.wait_for_timeout(30)
                        return True
                    if _click_distribution_sync_confirm_by_text(live_page, scope):
                        return True
                    if _click_distribution_sync_confirm_fallback(live_page, scope):
                        return True
                except Exception as exc:
                    if _is_playwright_detach_error(exc):
                        continue
                    raise
        except Exception as exc:
            if _is_playwright_detach_error(exc):
                live_page.wait_for_timeout(RPA_DISTRIBUTION_SYNC_POLL_MS)
                continue
            raise
        live_page.wait_for_timeout(RPA_DISTRIBUTION_SYNC_POLL_MS)
    return False


def _distribution_sync_modal_ready(scope: Any) -> bool:
    for hint in JUSHUITAN_DISTRIBUTION_SYNC_READY_HINTS:
        marker = scope.get_by_text(hint, exact=False)
        count = min(_safe_locator_count(marker), 4)
        for index in range(count):
            try:
                if marker.nth(index).is_visible():
                    return True
            except Exception:
                continue
    return False


def _is_distribution_confirm_label(text: str) -> bool:
    return re.sub(r"\s+", "", text.strip()) == JUSHUITAN_DISTRIBUTION_SYNC_CONFIRM_BUTTON


def _click_distribution_sync_confirm_ant_modal(page: Any, scope: Any) -> bool:
    modal_roots = (
        ".ant-modal-confirm",
        ".ant-modal-wrap",
        ".ant-modal",
        "[role='dialog']",
    )
    for root_selector in modal_roots:
        for hint in JUSHUITAN_DISTRIBUTION_SYNC_CONFIRM_HINTS:
            modal = scope.locator(root_selector).filter(has_text=hint)
            if _safe_locator_count(modal) == 0:
                continue
            container = modal.first
            confirm_in_bar = container.locator(
                "div.ant-modal-confirm-btns button.ant-btn-primary"
            )
            count = _safe_locator_count(confirm_in_bar)
            for index in reversed(range(min(count, 3))):
                if _try_click_distribution_confirm_button(page, confirm_in_bar.nth(index)):
                    return True

            labeled = container.locator("button.ant-btn-primary").filter(
                has_text=JUSHUITAN_DISTRIBUTION_SYNC_CONFIRM_LABEL_RE
            )
            count = _safe_locator_count(labeled)
            for index in reversed(range(min(count, 3))):
                if _try_click_distribution_confirm_button(page, labeled.nth(index)):
                    return True
    return False


def _try_click_distribution_confirm_button(page: Any, target: Any) -> bool:
    try:
        text = target.inner_text(timeout=500)
    except Exception:
        text = ""
    if text and not _is_distribution_confirm_label(text):
        return False
    return _try_click_target(
        page,
        target,
        timeout_ms=RPA_MODAL_CONFIRM_TIMEOUT_MS,
        pause_ms=50,
        prefer_force=True,
    )


def _click_distribution_sync_confirm_nk(page: Any, scope: Any) -> bool:
    marker = scope.locator("div[_nk]").filter(has_text=JUSHUITAN_DISTRIBUTION_SYNC_TITLE)
    count = _safe_locator_count(marker)
    if count == 0:
        marker = scope.locator("div[_nk]").filter(has_text="以下商品将同步至基础资料")
        count = _safe_locator_count(marker)
    for index in range(min(count, 4)):
        target = marker.nth(index)
        try:
            if not target.is_visible():
                continue
        except Exception:
            continue
        if _click_ant_primary_confirm_near_marker(page, target):
            return True
        if _click_confirm_from_marker(page, target):
            return True
    return False


def _click_ant_primary_confirm_near_marker(page: Any, marker: Any) -> bool:
    confirm = marker.locator(
        "xpath=ancestor::*[position()<=24]//button[contains(@class,'ant-btn-primary')]"
    )
    count = _safe_locator_count(confirm)
    if count == 0:
        return False
    for index in reversed(range(min(count, 3))):
        if _try_click_target(
            page,
            confirm.nth(index),
            timeout_ms=RPA_MODAL_CONFIRM_TIMEOUT_MS,
            pause_ms=30,
            prefer_force=True,
        ):
            return True
    return False


def _click_distribution_sync_confirm_js(scope: Any) -> bool:
    script = """
    (keywords) => {
      const isVisible = (node) => {
        if (!node || node.nodeType !== 1) return false;
        const style = window.getComputedStyle(node);
        if (style.display === 'none' || style.visibility === 'hidden') return false;
        const rect = node.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
      };
      const labelOf = (node) => (node.innerText || node.textContent || '').trim();
      const normalizeLabel = (text) => (text || '').replace(/\\s+/g, '').trim();
      const isConfirmLabel = (node) => normalizeLabel(labelOf(node)) === '确定';
      const canClick = (node) => {
        if (!node || !isVisible(node)) return false;
        if (node.disabled) return false;
        if (node.classList && node.classList.contains('ant-btn-disabled')) return false;
        if (node.getAttribute('aria-disabled') === 'true') return false;
        return isConfirmLabel(node);
      };
      const clickConfirmInTree = (root) => {
        const confirmBarButtons = root.querySelectorAll(
          'div.ant-modal-confirm-btns button.ant-btn-primary'
        );
        for (let index = confirmBarButtons.length - 1; index >= 0; index -= 1) {
          const node = confirmBarButtons[index];
          if (!canClick(node)) continue;
          node.click();
          return true;
        }
        const primaries = root.querySelectorAll('button.ant-btn-primary, .ant-btn-primary');
        for (let index = primaries.length - 1; index >= 0; index -= 1) {
          const node = primaries[index];
          if (!canClick(node)) continue;
          node.click();
          return true;
        }
        const nodes = root.querySelectorAll(
          'button, [role="button"], .ant-btn, a.ant-btn, div.ant-btn, span.ant-btn, div[_nk], div, span, a'
        );
        for (let index = nodes.length - 1; index >= 0; index -= 1) {
          const node = nodes[index];
          if (!canClick(node)) continue;
          node.click();
          return true;
        }
        return false;
      };
      const climbAndClick = (start) => {
        let current = start;
        for (let depth = 0; depth < 24 && current; depth += 1) {
          if (clickConfirmInTree(current)) return true;
          current = current.parentElement;
        }
        return false;
      };
      const nodes = document.querySelectorAll('div[_nk], body *');
      for (const node of nodes) {
        const text = labelOf(node);
        if (!keywords.some((item) => text.includes(item))) continue;
        if (!isVisible(node)) continue;
        if (climbAndClick(node)) return true;
      }
      return false;
    }
    """
    try:
        return bool(scope.evaluate(script, list(JUSHUITAN_DISTRIBUTION_SYNC_CONFIRM_HINTS)))
    except Exception:
        return False


def _click_distribution_sync_confirm_by_text(page: Any, scope: Any) -> bool:
    for hint in JUSHUITAN_DISTRIBUTION_SYNC_CONFIRM_HINTS:
        marker = scope.get_by_text(hint, exact=False)
        count = min(_safe_locator_count(marker), 4)
        for index in range(count):
            target = marker.nth(index)
            try:
                if not target.is_visible():
                    continue
            except Exception:
                continue
            if _click_confirm_from_marker(page, target):
                return True
    return False


def _click_confirm_from_marker(page: Any, marker: Any) -> bool:
    script = """
    (node) => {
      const isVisible = (el) => {
        if (!el || el.nodeType !== 1) return false;
        const style = window.getComputedStyle(el);
        if (style.display === 'none' || style.visibility === 'hidden') return false;
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
      };
      const labelOf = (el) => (el.innerText || el.textContent || '').trim();
      const normalizeLabel = (text) => (text || '').replace(/\\s+/g, '').trim();
      const isConfirmLabel = (el) => normalizeLabel(labelOf(el)) === '确定';
      const canClick = (el) => {
        if (!el || !isVisible(el)) return false;
        if (el.disabled) return false;
        if (el.classList && el.classList.contains('ant-btn-disabled')) return false;
        if (el.getAttribute('aria-disabled') === 'true') return false;
        return isConfirmLabel(el);
      };
      const selector =
        'button, [role="button"], .ant-btn, a.ant-btn, div.ant-btn, span.ant-btn, div[_nk], div, span, a';
      let current = node;
      for (let depth = 0; depth < 24 && current; depth += 1) {
        const confirmBarButtons = current.querySelectorAll(
          'div.ant-modal-confirm-btns button.ant-btn-primary'
        );
        for (let index = confirmBarButtons.length - 1; index >= 0; index -= 1) {
          if (canClick(confirmBarButtons[index])) {
            confirmBarButtons[index].click();
            return true;
          }
        }
        const primaries = current.querySelectorAll('button.ant-btn-primary, .ant-btn-primary');
        for (let index = primaries.length - 1; index >= 0; index -= 1) {
          if (canClick(primaries[index])) {
            primaries[index].click();
            return true;
          }
        }
        const buttons = current.querySelectorAll(selector);
        for (let index = buttons.length - 1; index >= 0; index -= 1) {
          if (canClick(buttons[index])) {
            buttons[index].click();
            return true;
          }
        }
        current = current.parentElement;
      }
      return false;
    }
    """
    try:
        clicked = marker.evaluate(script)
        if clicked:
            page.wait_for_timeout(30)
        return bool(clicked)
    except Exception:
        return False


def _click_distribution_sync_confirm_fallback(page: Any, scope: Any) -> bool:
    confirm_bar = scope.locator("div.ant-modal-confirm-btns button.ant-btn-primary")
    count = _safe_locator_count(confirm_bar)
    for index in reversed(range(min(count, 4))):
        if _try_click_distribution_confirm_button(page, confirm_bar.nth(index)):
            return True

    confirms = scope.get_by_role(
        "button",
        name=JUSHUITAN_DISTRIBUTION_SYNC_CONFIRM_LABEL_RE,
    )
    count = _safe_locator_count(confirms)
    for index in reversed(range(min(count, 6))):
        if _try_click_distribution_confirm_button(page, confirms.nth(index)):
            return True
    return False


def _dump_distribution_confirm_debug(
    work_page: Any,
    debug_dir: Path | None,
    *,
    headful: bool,
) -> None:
    work_page = _resolve_live_scm_page(work_page)
    if debug_dir is None:
        if headful:
            work_page.wait_for_timeout(RPA_CONFIRM_FAIL_PAUSE_MS)
        return

    debug_dir.mkdir(parents=True, exist_ok=True)
    try:
        work_page.screenshot(path=str(debug_dir / "confirm_fail.png"), full_page=True)
    except Exception:
        pass

    snippet_script = """
    () => {
      const hints = ['同步至基础资料', '将新增至基础资料', '商品编码['];
      const chunks = [];
      const buttons = document.querySelectorAll(
        'button, .ant-btn, [role="button"], a.ant-btn, div.ant-btn, span.ant-btn'
      );
      const normalizeLabel = (text) => (text || '').replace(/\\s+/g, '').trim();
      for (const button of buttons) {
        const label = normalizeLabel((button.innerText || button.textContent || '').trim());
        if (label !== '确定') continue;
        chunks.push('<!-- 确定按钮 -->\\n' + button.outerHTML);
      }
      for (const node of document.querySelectorAll('body *')) {
        const text = (node.innerText || node.textContent || '');
        if (!hints.some((item) => text.includes(item))) continue;
        if (text.length > 12000) continue;
        chunks.push('<!-- 同步弹窗区域 -->\\n' + node.outerHTML.slice(0, 12000));
        break;
      }
      return chunks.join('\\n\\n');
    }
    """
    try:
        snippet = work_page.evaluate(snippet_script)
        (debug_dir / "confirm_modal_snippet.html").write_text(snippet or "", encoding="utf-8")
    except Exception:
        pass

    if headful:
        work_page.wait_for_timeout(RPA_CONFIRM_FAIL_PAUSE_MS)


def _open_jushuitan_scm_page(page: Any) -> Any:
    work_page = _click_and_get_work_page(page, JUSHUITAN_DISTRIBUTION_ENTRY_KEYWORDS, prefer_last=True)
    if work_page is not None and _url_contains(work_page.url, "scm121.com"):
        _dismiss_blocking_reminders(work_page)
        return work_page

    for candidate in reversed(page.context.pages):
        if _url_contains(candidate.url, "scm121.com"):
            _dismiss_blocking_reminders(candidate)
            return candidate

    if work_page is None:
        work_page = _click_and_get_work_page(page, JUSHUITAN_DISTRIBUTION_ENTRY_KEYWORDS, prefer_last=True)
    if work_page is None:
        raise RuntimeError("分销上架：未找到「ERP分销版」入口")

    work_page.wait_for_url("**scm121.com**", timeout=60000)
    _dismiss_blocking_reminders(work_page)
    return work_page


def _dismiss_scm_dashboard_popups(page: Any) -> int:
    return _dismiss_blocking_reminders(page)


def _store_expiry_modal_scope(page: Any) -> Any | None:
    modal_selector = ".ant-modal-wrap, .ant-modal, [role='dialog']"
    for scope in _page_scopes(page):
        for hint in STORE_EXPIRY_MODAL_TITLE_HINTS:
            modal = scope.locator(modal_selector).filter(has_text=hint)
            if _safe_locator_count(modal) == 0:
                continue
            container = modal.first
            try:
                if container.is_visible():
                    return container
            except Exception:
                return container
    return None


def _store_expiry_modal_visible(page: Any) -> bool:
    return _store_expiry_modal_scope(page) is not None


def _click_store_expiry_modal_close(page: Any, container: Any) -> bool:
    for selector in POPUP_CLOSE_SELECTORS:
        close_btn = container.locator(selector).first
        if _safe_locator_count(close_btn) > 0 and _try_click_target(
            page, close_btn, prefer_force=True
        ):
            return True
    return False


def _click_store_expiry_no_remind_links(page: Any, container: Any) -> int:
    clicked = 0
    targets = container.get_by_text("不再提醒", exact=True)
    count = _safe_locator_count(targets)
    for index in range(count):
        if _try_click_target(page, targets.nth(index), prefer_force=True):
            clicked += 1
    return clicked


def _save_store_expiry_dismiss_failure_screenshot(page: Any, debug_dir: Path | None) -> None:
    target_dir = debug_dir if debug_dir is not None else Path("logs")
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        shot_path = target_dir / "store_expiry_popup_failure.png"
        live_page = _resolve_live_scm_page(page)
        live_page.screenshot(path=str(shot_path), full_page=True)
    except Exception:
        pass


def _dismiss_blocking_reminders(page: Any, debug_dir: Path | None = None) -> int:
    page.wait_for_timeout(RPA_SCM_DASHBOARD_POPUP_WAIT_MS)
    total = 0
    for _ in range(RPA_BLOCKING_REMINDERS_MAX_ROUNDS):
        had_store_expiry = _store_expiry_modal_visible(page)
        store_closed = _dismiss_store_expiry_reminder(page) if had_store_expiry else 0
        total += store_closed
        popups_closed = _dismiss_popups(page, max_rounds=3)
        total += popups_closed
        if not had_store_expiry and popups_closed == 0:
            break
        if had_store_expiry and store_closed == 0 and popups_closed == 0:
            break
        page.wait_for_timeout(RPA_POPUP_PAUSE_MS)
    if _store_expiry_modal_visible(page):
        _save_store_expiry_dismiss_failure_screenshot(page, debug_dir)
        print(
            "店铺过期弹窗未能自动关闭，请手动点右上角 X 或「不再提醒」",
            flush=True,
        )
    return total


def _dismiss_store_expiry_reminder(page: Any) -> int:
    closed_count = 0
    for _ in range(RPA_STORE_EXPIRY_DISMISS_MAX_ROUNDS):
        if not _store_expiry_modal_visible(page):
            return closed_count
        container = _store_expiry_modal_scope(page)
        if container is None:
            return closed_count

        progress = False
        if _click_store_expiry_modal_close(page, container):
            closed_count += 1
            progress = True
        else:
            no_remind_clicked = _click_store_expiry_no_remind_links(page, container)
            if no_remind_clicked > 0:
                closed_count += no_remind_clicked
                progress = True
            else:
                try:
                    page.keyboard.press("Escape")
                    closed_count += 1
                    progress = True
                except Exception:
                    pass

        page.wait_for_timeout(200)
        if not _store_expiry_modal_visible(page):
            return closed_count
        if not progress:
            break
    return closed_count


def _navigate_to_goods_manage(page: Any) -> Any:
    if _url_contains(page.url, "goodsmanage"):
        return page

    page.goto(JUSHUITAN_SCM_GOODS_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(RPA_CLICK_PAUSE_MS)

    if not _url_contains(page.url, "goodsmanage"):
        if _click_sidebar_text(page, "商品"):
            page.wait_for_timeout(RPA_CLICK_PAUSE_MS)
            if _click_first_visible_text(page, ("商品管理",), prefer_last=False):
                try:
                    page.wait_for_url("**goodsmanage**", timeout=30000)
                    return page
                except Exception:
                    pass

    if not _url_contains(page.url, "goodsmanage"):
        raise RuntimeError("分销上架：未能进入「商品管理」页面")
    return page


def _wait_for_goods_manage_ready(page: Any, timeout_ms: int = 45000) -> Any:
    attempts = max(1, timeout_ms // 200)
    live_page = page
    for _ in range(attempts):
        live_page = _resolve_live_scm_page(live_page)
        if _goods_manage_import_ready(live_page):
            return live_page
        try:
            live_page.wait_for_timeout(200)
        except Exception:
            pass
    return live_page


def _goods_manage_import_ready(page: Any) -> bool:
    for scope in _page_scopes(page):
        for text in JUSHUITAN_DISTRIBUTION_IMPORT_KEYWORDS:
            marker = scope.get_by_text(text, exact=False)
            count = min(_safe_locator_count(marker), 4)
            for index in range(count):
                try:
                    if marker.nth(index).is_visible():
                        return True
                except Exception:
                    continue
    return False


def _wait_for_distribution_import_dialog_ready(page: Any, timeout_ms: int = 30000) -> Any:
    attempts = max(1, timeout_ms // 200)
    live_page = page
    for _ in range(attempts):
        live_page = _resolve_live_scm_page(live_page)
        if _distribution_import_dialog_ready(live_page):
            return live_page
        try:
            live_page.wait_for_timeout(200)
        except Exception:
            pass
    raise RuntimeError("分销上架：「导入 Excel 表格新增」弹窗未打开")


def _distribution_import_dialog_ready(page: Any) -> bool:
    for scope in _page_scopes(page):
        for hint in JUSHUITAN_DISTRIBUTION_IMPORT_DIALOG_HINTS:
            marker = scope.get_by_text(hint, exact=False)
            count = min(_safe_locator_count(marker), 4)
            for index in range(count):
                try:
                    if marker.nth(index).is_visible():
                        return True
                except Exception:
                    continue
    return False


def _click_sidebar_text(page: Any, text: str) -> bool:
    scopes = _page_scopes(page)
    for scope in scopes:
        locator = scope.get_by_text(text, exact=True)
        count = min(locator.count(), 12)
        for index in range(count):
            target = locator.nth(index)
            try:
                box = target.bounding_box()
                if box is not None and box["x"] > 160:
                    continue
            except Exception:
                pass
            if _try_click_target(page, target):
                return True
    return _click_first_visible_text(page, (text,), prefer_last=False)


def _is_playwright_detach_error(exc: BaseException) -> bool:
    message = str(exc).lower()
    return (
        "detached" in message
        or "target closed" in message
        or "has been closed" in message
    )


def _safe_locator_count(locator: Any) -> int:
    try:
        return locator.count()
    except Exception as exc:
        if _is_playwright_detach_error(exc):
            return 0
        raise


def _resolve_live_scm_page(page: Any) -> Any:
    try:
        context = page.context
    except Exception:
        return page

    for candidate in reversed(context.pages):
        try:
            if candidate.is_closed() is True:
                continue
        except Exception:
            continue
        if _url_contains(candidate.url, "scm121.com"):
            return candidate

    try:
        if page.is_closed() is not True and _url_contains(page.url, "scm121.com"):
            return page
    except Exception:
        pass
    return page


def _pause_before_browser_close(context: Any) -> None:
    for candidate in reversed(context.pages):
        try:
            if candidate.is_closed() is True:
                continue
            candidate.bring_to_front()
            candidate.wait_for_timeout(RPA_CONFIRM_FAIL_PAUSE_MS)
            return
        except Exception:
            continue


def _page_scopes(page: Any) -> list[Any]:
    scopes: list[Any] = []
    try:
        if page.is_closed() is True:
            return scopes
    except Exception:
        pass

    scopes.append(page)
    try:
        frames = page.frames
    except Exception:
        return scopes

    for frame in frames:
        if frame == page.main_frame:
            continue
        try:
            if frame.is_detached() is True:
                continue
        except Exception:
            continue
        scopes.append(frame)
    return scopes


def _dismiss_popups(page: Any, max_rounds: int = 2) -> int:
    closed_count = 0
    for _ in range(max_rounds):
        closed_this_round = False
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(RPA_POPUP_PAUSE_MS)
        except Exception:
            pass

        for scope in _page_scopes(page):
            if _close_hinted_modals(scope, page):
                closed_this_round = True
                closed_count += 1
                page.wait_for_timeout(RPA_POPUP_PAUSE_MS)
                continue

            for selector in POPUP_CLOSE_SELECTORS:
                locator = scope.locator(selector)
                for index in range(min(_safe_locator_count(locator), 6)):
                    target = locator.nth(index)
                    if _try_click_target(page, target):
                        closed_this_round = True
                        closed_count += 1
                        page.wait_for_timeout(RPA_POPUP_PAUSE_MS)
                        break
                if closed_this_round:
                    break

            if closed_this_round:
                continue

            for text in POPUP_DISMISS_TEXTS:
                buttons = scope.get_by_role("button", name=text)
                for index in range(min(_safe_locator_count(buttons), 4)):
                    target = buttons.nth(index)
                    if _try_click_target(page, target):
                        closed_this_round = True
                        closed_count += 1
                        page.wait_for_timeout(RPA_POPUP_PAUSE_MS)
                        break
                if closed_this_round:
                    break

        if not closed_this_round:
            break
        page.wait_for_timeout(RPA_POPUP_PAUSE_MS)
    return closed_count


def _close_hinted_modals(scope: Any, page: Any) -> bool:
    for hint in POPUP_TITLE_HINTS:
        modal = scope.locator(".ant-modal, .ant-modal-wrap, [role='dialog']").filter(has_text=hint)
        for index in range(min(_safe_locator_count(modal), 3)):
            container = modal.nth(index)
            for selector in POPUP_CLOSE_SELECTORS:
                close_btn = container.locator(selector).first
                if _safe_locator_count(close_btn) > 0 and _try_click_target(page, close_btn):
                    return True
    return False


def _url_contains(url: str, needle: str) -> bool:
    return needle.lower() in str(url or "").lower()


def _click_and_get_work_page(page: Any, texts: tuple[str, ...], prefer_last: bool = False) -> Any | None:
    context = page.context
    pages_before = set(context.pages)
    if not _click_first_visible_text(page, texts, prefer_last=prefer_last):
        return None
    page.wait_for_timeout(RPA_STEP_PAUSE_MS)
    for candidate in reversed(context.pages):
        if candidate not in pages_before:
            return candidate
    if any(text in str(page.url) for text in ("scm121.com", "goodsmanage")):
        return page
    for candidate in context.pages:
        url = str(candidate.url or "")
        if "scm121.com" in url or "goodsmanage" in url:
            return candidate
    return page


def _set_file_on_page(page: Any, file_path: Path, file_input_selector: str) -> None:
    attempts = max(1, 30000 // 200)
    live_page = _resolve_live_scm_page(page)
    for _ in range(attempts):
        live_page = _resolve_live_scm_page(live_page)
        for scope in _page_scopes(live_page):
            locator = scope.locator(file_input_selector)
            if _safe_locator_count(locator) == 0:
                continue
            try:
                locator.first.set_input_files(str(file_path.resolve()))
                return
            except Exception as exc:
                if _is_playwright_detach_error(exc):
                    break
                raise
        try:
            live_page.wait_for_timeout(200)
        except Exception:
            pass
    live_page = _resolve_live_scm_page(live_page)
    locator = live_page.locator(file_input_selector).first
    locator.wait_for(state="attached", timeout=30000)
    locator.set_input_files(str(file_path.resolve()))


def _jushuitan_upload_new_product(
    page: Any,
    file_path: Path,
    template: TemplateConfig,
    *,
    debug_dir: Path | None = None,
    headful: bool = True,
    stop_before_confirm: bool = False,
    stop_after_import_dialog: bool = False,
) -> str:
    if not file_path.exists():
        raise FileNotFoundError(f"新品录入 文件不存在：{file_path}")

    work_page = _run_new_product_stable_phase(page, template)
    if stop_after_import_dialog:
        return "新品录入 稳定阶段完成：「从Excel导入商品」弹窗已打开"

    work_page = _run_new_product_import_file_phase(work_page, file_path, template)
    if stop_before_confirm:
        return f"新品录入：{file_path.name} 已上传，等待确认导入"

    work_page = _run_new_product_confirm_phase(
        work_page,
        debug_dir=debug_dir,
        headful=headful,
    )
    return f"新品录入 上传成功：{file_path.name}"


def _run_new_product_stable_phase(page: Any, template: TemplateConfig) -> Any:
    """
    新品录入稳定阶段：epaas → 商品 → 普通商品资料 → 从Excel导入商品 → 选全部更新。
    """
    page.goto(template.start_url or JUSHUITAN_DASHBOARD_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(RPA_CLICK_PAUSE_MS)
    _dismiss_blocking_reminders(page)

    if not _click_sidebar_text(page, "商品"):
        raise RuntimeError("新品录入：未找到左侧「商品」菜单")

    page.wait_for_timeout(RPA_STEP_PAUSE_MS)

    if not _click_first_visible_text(page, JUSHUITAN_NEW_PRODUCT_MENU_KEYWORDS):
        raise RuntimeError("新品录入：未找到「商品及库存管理(普通商品资料)」")

    work_page = _wait_for_new_product_page_ready(page)
    _dismiss_blocking_reminders(work_page)

    if not _open_new_product_import_dialog(work_page):
        raise RuntimeError("新品录入：未找到「从Excel导入商品」")

    work_page = _wait_for_new_product_import_modal_ready(work_page)
    work_page.wait_for_timeout(RPA_CLICK_PAUSE_MS)

    if not _select_new_product_update_mode(work_page, JUSHUITAN_NEW_PRODUCT_UPDATE_MODE):
        raise RuntimeError(f"新品录入：未找到「{JUSHUITAN_NEW_PRODUCT_UPDATE_MODE}」选项")

    return _resolve_live_epaas_page(work_page)


def _run_new_product_import_file_phase(
    work_page: Any,
    file_path: Path,
    template: TemplateConfig,
) -> Any:
    """
    新品录入上传阶段：在导入弹窗内选文件（全部更新已在稳定阶段选中）。
    """
    work_page = _resolve_live_epaas_page(work_page)
    _set_file_on_epaas_page(work_page, file_path, template.file_input)
    work_page.wait_for_timeout(RPA_CLICK_PAUSE_MS)
    return _resolve_live_epaas_page(work_page)


def _run_new_product_confirm_phase(
    work_page: Any,
    *,
    debug_dir: Path | None = None,
    headful: bool = True,
) -> Any:
    """
    新品录入确认阶段：点确认导入 → 等待导入成功。
    """
    work_page = _resolve_live_epaas_page(work_page)
    if not _click_new_product_import_submit(work_page):
        work_page = _resolve_live_epaas_page(work_page)
        _dump_new_product_debug(work_page, debug_dir, headful=headful)
        raise RuntimeError("新品录入：未找到「确认导入」或导入确认按钮")

    work_page = _resolve_live_epaas_page(work_page)
    _wait_for_success(work_page)
    return work_page


def _resolve_live_epaas_page(page: Any) -> Any:
    try:
        context = page.context
    except Exception:
        return page

    for candidate in reversed(context.pages):
        try:
            if candidate.is_closed() is True:
                continue
        except Exception:
            continue
        url = str(candidate.url or "")
        if _url_contains(url, "erp321.com") and not _url_contains(url, "scm121.com"):
            return candidate

    try:
        if page.is_closed() is not True:
            url = str(page.url or "")
            if _url_contains(url, "erp321.com"):
                return page
    except Exception:
        pass
    return page


def _new_product_page_ready(page: Any) -> bool:
    for scope in _page_scopes(page):
        for hint in JUSHUITAN_NEW_PRODUCT_PAGE_HINTS:
            marker = scope.get_by_text(hint, exact=False)
            count = min(_safe_locator_count(marker), 4)
            for index in range(count):
                try:
                    if marker.nth(index).is_visible():
                        return True
                except Exception:
                    continue
    return False


def _wait_for_new_product_page_ready(page: Any, timeout_ms: int = 30000) -> Any:
    attempts = max(1, timeout_ms // 200)
    live_page = page
    for _ in range(attempts):
        live_page = _resolve_live_epaas_page(live_page)
        if _new_product_page_ready(live_page):
            return live_page
        try:
            live_page.wait_for_timeout(200)
        except Exception:
            pass
    raise RuntimeError("新品录入：普通商品资料页未就绪")


def _new_product_import_dialog_ready(page: Any) -> bool:
    for scope in _page_scopes(page):
        for hint in JUSHUITAN_NEW_PRODUCT_IMPORT_DIALOG_HINTS:
            marker = scope.get_by_text(hint, exact=False)
            count = min(_safe_locator_count(marker), 4)
            for index in range(count):
                try:
                    if marker.nth(index).is_visible():
                        return True
                except Exception:
                    continue
    return False


def _wait_for_new_product_import_modal_ready(page: Any, timeout_ms: int = 30000) -> Any:
    attempts = max(1, timeout_ms // 200)
    live_page = page
    for _ in range(attempts):
        live_page = _resolve_live_epaas_page(live_page)
        if _new_product_import_dialog_ready(live_page):
            return live_page
        try:
            live_page.wait_for_timeout(200)
        except Exception:
            pass
    raise RuntimeError("新品录入：「从Excel导入商品」弹窗未打开")


def _new_product_import_modal_scope(page: Any) -> Any | None:
    live_page = _resolve_live_epaas_page(page)
    for scope in _page_scopes(live_page):
        modal = scope.locator(".ant-modal, .ant-modal-wrap, [role='dialog']").filter(
            has_text="从Excel导入商品"
        )
        count = min(_safe_locator_count(modal), 3)
        for index in range(count):
            container = modal.nth(index)
            try:
                if container.is_visible():
                    return container
            except Exception:
                continue
    return None


def _open_new_product_import_dialog(page: Any) -> bool:
    live_page = _resolve_live_epaas_page(page)
    for text in JUSHUITAN_NEW_PRODUCT_IMPORT_MENU:
        if _click_first_visible_text(live_page, (text,)):
            return True
    if not _click_first_visible_text(live_page, ("导入",), prefer_last=False):
        return False
    live_page.wait_for_timeout(RPA_STEP_PAUSE_MS)
    for text in JUSHUITAN_NEW_PRODUCT_IMPORT_MENU:
        if _click_first_visible_text(live_page, (text,), prefer_last=False):
            return True
    return False


def _select_new_product_update_mode(page: Any, mode_text: str) -> bool:
    live_page = _resolve_live_epaas_page(page)
    modal = _new_product_import_modal_scope(live_page)
    scopes: list[Any] = []
    if modal is not None:
        scopes.append(modal)
    scopes.extend(_page_scopes(live_page))

    for scope in scopes:
        radio = scope.get_by_role("radio", name=mode_text)
        count = min(_safe_locator_count(radio), 4)
        for index in range(count):
            if _try_click_target(live_page, radio.nth(index)):
                return True
        label = scope.locator("label").filter(has_text=mode_text)
        count = min(_safe_locator_count(label), 4)
        for index in range(count):
            if _try_click_target(live_page, label.nth(index)):
                return True
    return _click_first_visible_text(live_page, (mode_text,), prefer_last=False)


def _set_file_on_epaas_page(page: Any, file_path: Path, file_input_selector: str) -> None:
    attempts = max(1, 30000 // 200)
    live_page = _resolve_live_epaas_page(page)
    for _ in range(attempts):
        live_page = _resolve_live_epaas_page(live_page)
        modal = _new_product_import_modal_scope(live_page)
        search_scopes: list[Any] = []
        if modal is not None:
            search_scopes.append(modal)
        search_scopes.extend(_page_scopes(live_page))
        for scope in search_scopes:
            locator = scope.locator(file_input_selector)
            if _safe_locator_count(locator) == 0:
                continue
            try:
                locator.first.set_input_files(str(file_path.resolve()))
                return
            except Exception as exc:
                if _is_playwright_detach_error(exc):
                    break
                raise
        try:
            live_page.wait_for_timeout(200)
        except Exception:
            pass
    live_page = _resolve_live_epaas_page(live_page)
    locator = live_page.locator(file_input_selector).first
    locator.wait_for(state="attached", timeout=30000)
    locator.set_input_files(str(file_path.resolve()))


def _click_new_product_import_submit(page: Any) -> bool:
    live_page = _resolve_live_epaas_page(page)
    modal = _new_product_import_modal_scope(live_page)
    scopes: list[Any] = []
    if modal is not None:
        scopes.append(modal)
    scopes.extend(_page_scopes(live_page))

    for scope in scopes:
        for text in JUSHUITAN_NEW_PRODUCT_UPLOAD_KEYWORDS:
            button = scope.get_by_role("button", name=text)
            count = min(_safe_locator_count(button), 4)
            for index in reversed(range(count)):
                if _try_click_target(live_page, button.nth(index)):
                    return True
            locator = scope.get_by_text(text, exact=False)
            count = min(_safe_locator_count(locator), 4)
            for index in reversed(range(count)):
                if _try_click_target(live_page, locator.nth(index)):
                    return True
    return False


def _dump_new_product_debug(page: Any, debug_dir: Path | None, *, headful: bool = True) -> None:
    if debug_dir is None:
        return
    debug_dir.mkdir(parents=True, exist_ok=True)
    live_page = _resolve_live_epaas_page(page)
    try:
        live_page.screenshot(path=str(debug_dir / "new_product_confirm_fail.png"), full_page=True)
    except Exception:
        pass


def _jushuitan_discover_and_upload(
    page: Any,
    file_path: Path,
    menu_keywords: tuple[str, ...],
    label: str,
) -> str:
    if not file_path.exists():
        raise FileNotFoundError(f"{label} 文件不存在：{file_path}")

    page.goto(JUSHUITAN_HOME_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(RPA_STEP_PAUSE_MS)
    _click_first_visible_text(page, menu_keywords)
    page.wait_for_timeout(RPA_STEP_PAUSE_MS)
    _click_first_visible_text(page, IMPORT_ENTRY_KEYWORDS)

    _set_file_on_page(page, file_path, "input[type=file]")

    if not _click_submit(page):
        raise RuntimeError(f"{label}：未找到导入/上传按钮")

    _wait_for_success(page)
    return f"{label} 上传成功：{file_path.name}"


def _click_first_visible_text(page: Any, texts: tuple[str, ...], prefer_last: bool = False) -> bool:
    scopes = _page_scopes(page)
    for scope in scopes:
        for text in texts:
            for exact in (True, False):
                locator = scope.get_by_text(text, exact=exact)
                count = min(_safe_locator_count(locator), 8)
                indexes = range(count)
                if prefer_last:
                    indexes = reversed(list(indexes))
                for index in indexes:
                    target = locator.nth(index)
                    if _try_click_target(page, target):
                        return True
            tile = scope.locator("a, button, div, span, li").filter(has_text=text)
            count = min(_safe_locator_count(tile), 8)
            indexes = range(count)
            if prefer_last:
                indexes = reversed(list(indexes))
            for index in indexes:
                target = tile.nth(index)
                if _try_click_target(page, target):
                    return True
    return False


def _try_click_target(
    page: Any,
    target: Any,
    *,
    timeout_ms: int | None = None,
    pause_ms: int | None = None,
    prefer_force: bool = False,
) -> bool:
    click_timeout = RPA_ACTION_TIMEOUT_MS if timeout_ms is None else timeout_ms
    click_pause = RPA_CLICK_PAUSE_MS if pause_ms is None else pause_ms
    force_order = (True, False) if prefer_force else (False, True)
    for force in force_order:
        try:
            if not force and not target.is_visible():
                continue
            target.click(timeout=click_timeout, force=force)
            if click_pause > 0:
                page.wait_for_timeout(click_pause)
            return True
        except Exception:
            continue
    return False


def _click_submit(page: Any) -> bool:
    live_page = _resolve_live_scm_page(page)
    for scope in _page_scopes(live_page):
        for text in SUBMIT_KEYWORDS:
            button = scope.get_by_role("button", name=text)
            if _safe_locator_count(button) > 0:
                try:
                    button.first.click(timeout=RPA_ACTION_TIMEOUT_MS)
                    return True
                except Exception as exc:
                    if _is_playwright_detach_error(exc):
                        continue
            locator = scope.get_by_text(text, exact=False)
            if _safe_locator_count(locator) > 0:
                try:
                    locator.first.click(timeout=RPA_ACTION_TIMEOUT_MS)
                    return True
                except Exception as exc:
                    if _is_playwright_detach_error(exc):
                        continue
    return False


def _wait_for_success(page: Any) -> None:
    scopes = _page_scopes(page)
    for text in SUCCESS_KEYWORDS:
        for scope in scopes:
            try:
                scope.get_by_text(text, exact=False).first.wait_for(timeout=RPA_SUCCESS_WAIT_MS)
                return
            except Exception:
                continue
    page.wait_for_timeout(RPA_STEP_PAUSE_MS)


def _upload_file(
    page: Any,
    base_url: str,
    template: TemplateConfig,
    file_path: Path,
    label: str,
) -> str:
    if not file_path.exists():
        raise FileNotFoundError(f"{label} 文件不存在：{file_path}")
    target_url = urljoin(base_url.rstrip("/") + "/", template.path.lstrip("/"))
    page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
    page.locator(template.file_input).first.set_input_files(str(file_path.resolve()))
    page.locator(template.submit).first.click(timeout=30000)
    page.get_by_text(template.success_contains).first.wait_for(timeout=60000)
    return f"{label} 上传成功：{file_path.name}"


def save_login_state(config_path: Path | None, storage_path: Path, login_url: str, wait_ms: int) -> None:
    from playwright.sync_api import sync_playwright

    storage_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = _launch_browser(playwright, headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(login_url, wait_until="domcontentloaded")
        print("已在浏览器打开聚水潭 ERP 登录页，请人工登录。登录成功后脚本会自动保存会话。")
        _wait_for_jushuitan_login(page, wait_ms)
        _dismiss_blocking_reminders(page)
        context.storage_state(path=str(storage_path))
        context.close()
        browser.close()
    print(f"登录态已保存到 {storage_path}")


def _prepare_scm_goods_page_for_confirm(page: Any) -> Any:
    page.goto(JUSHUITAN_DASHBOARD_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(RPA_CLICK_PAUSE_MS)
    _dismiss_blocking_reminders(page)
    work_page = _open_jushuitan_scm_page(page)
    work_page = _navigate_to_goods_manage(work_page)
    return _wait_for_goods_manage_ready(work_page)


def upload_bundle_cli(
    batch_id: int,
    config_path: Path,
    only: str | None = None,
    *,
    stop_before_confirm: bool = False,
    stop_after_import_dialog: bool = False,
) -> int:
    from app.erp_upload import DISTRIBUTION_FILENAME, NEW_PRODUCT_FILENAME, bundle_file_paths

    export_dir = Path("data/erp_exports") / str(batch_id)
    if not export_dir.exists():
        print(f"导出目录不存在：{export_dir}", file=sys.stderr)
        return 1
    config = ErpRpaConfig.load(config_path)
    if not config.ready:
        print(config.load_error or "RPA 未就绪", file=sys.stderr)
        return 1
    files = bundle_file_paths(export_dir)
    try:
        details = run_batch_upload(
            config,
            files,
            screenshot_dir=export_dir,
            only=only,
            stop_before_confirm=stop_before_confirm,
            stop_after_import_dialog=stop_after_import_dialog,
        )
    except Exception as exc:
        print(f"上传失败：{exc}", file=sys.stderr)
        return 1
    for line in details:
        print(line)
    return 0


def confirm_distribution_cli(batch_id: int | None, config_path: Path) -> int:
    from playwright.sync_api import sync_playwright

    config = ErpRpaConfig.load(config_path)
    if not config.ready:
        print(config.load_error or "RPA 未就绪", file=sys.stderr)
        return 1

    screenshot_dir = Path("data/erp_exports") / str(batch_id) if batch_id is not None else None
    storage_path = Path(config.storage_state)
    use_headful = config.headful or not storage_path.exists()

    with sync_playwright() as playwright:
        browser = _launch_browser(playwright, headless=not use_headful)
        if storage_path.exists():
            context = browser.new_context(storage_state=str(storage_path))
        else:
            context = browser.new_context()
        page = context.new_page()
        upload_failed = False
        try:
            _ensure_jushuitan_session(page, context, config, storage_path, use_headful)
            if batch_id is not None:
                export_dir = Path("data/erp_exports") / str(batch_id)
                if not export_dir.exists():
                    print(f"导出目录不存在：{export_dir}", file=sys.stderr)
                    return 1
                from app.erp_upload import bundle_file_paths

                file_path = bundle_file_paths(export_dir)["distribution"]
                work_page = _run_distribution_stable_phase(page, config.distribution)
                work_page = _run_distribution_import_file_phase(
                    work_page,
                    file_path,
                    config.distribution,
                )
            else:
                work_page = _prepare_scm_goods_page_for_confirm(page)
                print("已打开商品管理页，等待「同步至基础资料」弹窗…")
            _run_distribution_confirm_phase(
                work_page,
                debug_dir=screenshot_dir,
                headful=use_headful,
            )
            print("分销上架：同步确认完成")
            return 0
        except Exception as exc:
            upload_failed = True
            if screenshot_dir is not None:
                screenshot_dir.mkdir(parents=True, exist_ok=True)
                for candidate in context.pages:
                    if _url_contains(candidate.url, "scm121.com"):
                        try:
                            candidate.screenshot(
                                path=str(screenshot_dir / "confirm_fail.png"),
                                full_page=True,
                            )
                        except Exception:
                            pass
            print(f"确认失败：{exc}", file=sys.stderr)
            return 1
        finally:
            if storage_path.parent.exists():
                storage_path.parent.mkdir(parents=True, exist_ok=True)
                context.storage_state(path=str(storage_path))
            if upload_failed and use_headful:
                _pause_before_browser_close(context)
            context.close()
            browser.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="聚水潭 ERP Playwright RPA 工具")
    subparsers = parser.add_subparsers(dest="command")

    login_parser = subparsers.add_parser("login", help="打开聚水潭登录页，人工登录后保存会话")
    login_parser.add_argument("--config", default="config/erp_rpa.local.json", help="RPA 配置文件路径")

    upload_parser = subparsers.add_parser("upload", help="打开聚水潭并自动定位导入页上传指定批次")
    upload_parser.add_argument("batch_id", type=int, help="ERP 导出批次 ID")
    upload_parser.add_argument("--config", default="config/erp_rpa.local.json", help="RPA 配置文件路径")
    upload_parser.add_argument(
        "--only",
        choices=("distribution", "new_product"),
        help="仅上传分销上架或新品录入（默认两者都传）",
    )
    upload_parser.add_argument(
        "--stop-after-import-dialog",
        action="store_true",
        help="仅 --only 时有效：分销=导入弹窗打开；新品=从Excel导入弹窗+全部更新",
    )
    upload_parser.add_argument(
        "--stop-before-confirm",
        action="store_true",
        help="仅 --only 时有效：分销=停同步确认前；新品=停确认导入前",
    )

    confirm_parser = subparsers.add_parser(
        "confirm",
        help="仅调试「同步至基础资料」确定步骤",
    )
    confirm_parser.add_argument(
        "--batch-id",
        type=int,
        help="先跑稳定阶段+上传文件，再点确定；不传则只等当前页弹窗",
    )
    confirm_parser.add_argument("--config", default="config/erp_rpa.local.json", help="RPA 配置文件路径")

    args = parser.parse_args(argv)
    if args.command == "login":
        config = ErpRpaConfig.load(Path(args.config))
        storage_path = Path(config.storage_state)
        save_login_state(
            Path(args.config) if Path(args.config).exists() else None,
            storage_path,
            config.login_url,
            config.login_wait_ms,
        )
        return 0
    if args.command == "upload":
        return upload_bundle_cli(
            args.batch_id,
            Path(args.config),
            only=args.only,
            stop_before_confirm=args.stop_before_confirm,
            stop_after_import_dialog=args.stop_after_import_dialog,
        )
    if args.command == "confirm":
        return confirm_distribution_cli(getattr(args, "batch_id", None), Path(args.config))

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
