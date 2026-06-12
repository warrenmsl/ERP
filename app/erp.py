from __future__ import annotations

import csv
import math
import re
from decimal import Decimal, ROUND_HALF_UP
from io import StringIO
from typing import Any

PINYIN_FALLBACK = {
    "测": "ce",
    "试": "shi",
    "新": "xin",
    "品": "pin",
    "金": "jin",
    "楷": "kai",
    "尚": "shang",
    "家": "jia",
    "居": "ju",
    "女": "nv",
    "装": "zhuang",
    "配": "pei",
    "件": "jian",
    "红": "hong",
    "蓝": "lan",
    "黑": "hei",
    "白": "bai",
    "灰": "hui",
    "绿": "lv",
    "黄": "huang",
    "紫": "zi",
    "粉": "fen",
    "棕": "zong",
    "米": "mi",
    "色": "se",
    "浅": "qian",
    "深": "shen",
    "大": "da",
    "中": "zhong",
    "小": "xiao",
    "码": "ma",
    "号": "hao",
    "款": "kuan",
    "长": "chang",
    "短": "duan",
    "圆": "yuan",
    "方": "fang",
    "包": "bao",
    "鞋": "xie",
    "衣": "yi",
    "裤": "ku",
    "裙": "qun",
    "套": "tao",
    "杯": "bei",
    "垫": "dian",
    "架": "jia",
    "桌": "zhuo",
    "椅": "yi",
    "灯": "deng",
    "里": "li",
    "沙": "sha",
    "发": "fa",
    "赫": "he",
    "本": "ben",
    "藤": "teng",
    "异": "yi",
    "咖": "ka",
}

STYLE_PINYIN_STRIP_SUFFIXES = (
    "沙发垫",
    "沙发巾",
    "椅垫",
    "靠垫",
    "坐垫",
)

INPUT_HEADER_ALIASES = {
    "product_name": {"产品名", "产品名称", "商品名", "商品名称", "名称", "name"},
    "color": {"颜色", "色号", "color", "colour"},
    "size": {"尺寸", "尺码", "码数", "规格", "产品尺寸", "size"},
    "price": {"价格", "售价", "单价", "基本售价", "成本价", "price"},
    "weight": {"重量", "重量(kg)", "克重", "单品重量", "单品重量(kg)", "单品重量kg", "weight", "g"},
    "supplier": {"供应商", "供应商名", "供应商名称", "supplier"},
    "width_span": {"门幅", "面料门幅", "幅宽"},
}

SKIP_LINE_PATTERNS = (
    re.compile(r"^导入说明"),
    re.compile(r"^标红为必填"),
)

FIELD_LABELS = {
    "product_name": "产品名称",
    "color": "颜色",
    "size": "尺寸",
    "price": "价格",
    "weight": "重量",
    "supplier": "供应商",
    "width_span": "门幅",
}


def full_pinyin_code(text: str) -> str:
    return "".join(_pinyin_parts(text)).lower()


def product_name_for_style_pinyin(text: str) -> str:
    name = str(text or "").strip()
    for suffix in STYLE_PINYIN_STRIP_SUFFIXES:
        if name.endswith(suffix):
            name = name[: -len(suffix)].strip()
            break
    return name


def style_pinyin_code(text: str) -> str:
    name = product_name_for_style_pinyin(text).replace("（", "(").replace("）", ")")
    parts: list[str] = []
    for match in re.finditer(r"\([^)]*\)|[^()]+", name):
        segment = match.group()
        if segment.startswith("(") and segment.endswith(")"):
            parts.append(f"({_pinyin_segment(segment[1:-1])})")
        else:
            parts.append(_pinyin_segment(segment))
    return "".join(parts)


def abbreviation_code(text: str) -> str:
    return "".join(part[0] for part in _pinyin_parts(text) if part).upper()


def color_code_for_sku(color: str) -> str:
    text = str(color or "").strip()
    if not text:
        return "ys"
    if text.endswith("色") and len(text) > 1:
        parts = _pinyin_parts(text[:-1])
        if parts and parts[0]:
            return f"{parts[0].lower()}s"
    abbr = abbreviation_code(text)
    if abbr:
        return abbr.lower()
    return full_pinyin_code(text) or "ys"


def product_abbreviation_code(text: str) -> str:
    name = product_name_for_style_pinyin(text).replace("（", "(").replace("）", ")")
    letters: list[str] = []
    for match in re.finditer(r"\([^)]*\)|[^()]+", name):
        segment = match.group()
        if segment.startswith("(") and segment.endswith(")"):
            segment = segment[1:-1]
        for part in _pinyin_parts(segment):
            if part:
                letters.append(part[0].upper())
    return "".join(letters)


def normalize_size_for_code(size: str) -> str:
    cleaned = re.sub(r"\s+", "", str(size).strip())
    cleaned = cleaned.replace("*", "-")
    cleaned = re.sub(r"(?i)cm$", "", cleaned)
    return cleaned


def sku_code(product_name: str, color: str, size: str) -> str:
    product_part = product_abbreviation_code(product_name).lower() or "prd"
    color_part = color_code_for_sku(color)
    size_part = normalize_size_for_code(size) or "00"
    return f"{product_part}{color_part}{size_part}"


def variant_code(product_name: str, color: str, size: str) -> str:
    return sku_code(product_name, color, size)


def erp_color_value(product_name: str, color: str) -> str:
    product = str(product_name or "").strip()
    color_text = str(color or "").strip()
    if product and color_text:
        return f"{product}{color_text}"
    return product or color_text


def markup_selling_price(cost: float) -> int:
    return int(math.ceil(cost * 1.05))


def erp_goods_name(product_name: str, width_span: str) -> str:
    product = str(product_name or "").strip()
    span = str(width_span or "").strip()
    if product and span:
        suffix = span if span.startswith("门幅") else f"门幅{span}"
        return f"{product}{suffix}"
    return product


_UNICODE_PINYIN_PATTERN = re.compile(r"u[0-9a-f]{4}")


def pypinyin_available() -> bool:
    try:
        import pypinyin  # noqa: F401

        return True
    except ImportError:
        return False


def erp_pinyin_warning(built: dict[str, Any]) -> str | None:
    style_code = str(built.get("product_full_code") or built.get("style_code") or "")
    if not pypinyin_available():
        return (
            "拼音库 pypinyin 未安装，款式编码/商品编码可能异常。"
            "请在项目目录执行：pip install -r requirements.txt"
        )
    if style_code and _UNICODE_PINYIN_PATTERN.search(style_code):
        return "款式编码含有异常 unicode 片段，拼音库可能未正确加载，款式编码/商品编码可能异常。"
    return None


def erp_missing_price_warning(built: dict[str, Any]) -> str | None:
    rows = built.get("rows") or []
    if not rows:
        return None
    missing = sum(1 for row in rows if not row.get("price_present"))
    if missing == len(rows):
        return (
            f"已识别 {len(rows)} 条规格，但未读到成本价/重量。"
            "请换更清晰截图，或把报价表数字行粘贴到文本框。"
        )
    if missing > 0:
        return (
            f"已识别 {len(rows)} 条规格，其中 {missing} 条未读到成本价/重量"
            "（截图 OCR 未能识别部分报价数字）。可换更清晰图片，或把缺失行手动粘贴到文本框。"
        )
    return None


def parse_customer_table(raw_text: str, default_product_name: str, default_width_span: str = "") -> list[dict[str, Any]]:
    lines = [line.rstrip("\r\n") for line in raw_text.splitlines() if line.strip()]
    if not lines:
        return []

    rows = [_split_line(line) for line in lines if not _should_skip_line(line)]
    if not rows:
        return []

    header_map = _detect_header(rows[0])
    data_rows = rows[1:] if header_map else rows
    parsed: list[dict[str, Any]] = []

    for raw_row in data_rows:
        if header_map:
            row = _row_from_header(raw_row, header_map)
        else:
            row = _row_without_header(raw_row, default_product_name)
        if not row:
            continue
        row["product_name"] = row.get("product_name") or default_product_name
        if not row.get("width_span"):
            row["width_span"] = default_width_span
        parsed.append(row)
    return parsed


def build_erp_rows(product_name: str, raw_text: str, width_span: str = "") -> dict[str, Any]:
    parsed_rows = parse_customer_table(raw_text, product_name, width_span)
    canonical_name = _first_non_empty([row.get("product_name") for row in parsed_rows], product_name)
    batch_width_span = _first_non_empty([row.get("width_span") for row in parsed_rows], width_span)
    style_code = style_pinyin_code(canonical_name) if canonical_name else ""
    product_abbr = product_abbreviation_code(canonical_name) if canonical_name else ""

    mapped_rows: list[dict[str, Any]] = []
    for row in parsed_rows:
        mapped_rows.append(map_customer_row_to_erp(row, canonical_name, batch_width_span, style_code, product_abbr))

    batch_missing = collect_missing_fields(
        {
            "product_name": canonical_name,
            "width_span": batch_width_span,
        },
        batch_level=True,
    )

    return {
        "product_name": canonical_name,
        "width_span": batch_width_span,
        "product_full_code": style_code,
        "product_abbr": product_abbr,
        "batch_missing": batch_missing,
        "rows": mapped_rows,
    }


def map_customer_row_to_erp(
    row: dict[str, Any],
    canonical_name: str,
    batch_width_span: str,
    style_code: str,
    product_abbr: str,
) -> dict[str, Any]:
    source_product_name = str(row.get("product_name") or canonical_name or "").strip()
    color_raw = str(row.get("color") or "").strip()
    size_raw = str(row.get("size") or "").strip()
    supplier = str(row.get("supplier") or "").strip()
    row_width_span = str(row.get("width_span") or batch_width_span or "").strip()
    cost_price = _round_cost_price(_optional_number(row.get("price")))
    weight = _optional_number(row.get("weight"))
    base_selling_price = markup_selling_price(cost_price) if cost_price is not None else None

    mapped = {
        "source_product_name": source_product_name,
        "color_raw": color_raw,
        "size_raw": size_raw,
        "supplier": supplier,
        "width_span": row_width_span,
        "cost_price": cost_price if cost_price is not None else 0.0,
        "base_selling_price": base_selling_price if base_selling_price is not None else 0,
        "price": float(base_selling_price) if base_selling_price is not None else 0.0,
        "weight": weight if weight is not None else 0.0,
        "price_present": cost_price is not None,
        "weight_present": weight is not None,
        "style_code": style_pinyin_code(source_product_name) or style_code,
        "sku_code": sku_code(source_product_name, color_raw, size_raw) if source_product_name and color_raw and size_raw else "",
        "erp_color": erp_color_value(source_product_name, color_raw),
        "erp_spec": size_raw,
        "erp_goods_name": erp_goods_name(source_product_name, row_width_span),
        "product_name": erp_goods_name(source_product_name, row_width_span),
        "product_full_code": style_pinyin_code(source_product_name) or style_code,
        "product_abbr": product_abbreviation_code(source_product_name) or product_abbr,
        "color": erp_color_value(source_product_name, color_raw),
        "size": size_raw,
        "variant_code": sku_code(source_product_name, color_raw, size_raw) if source_product_name and color_raw and size_raw else "",
    }
    mapped["missing_fields"] = collect_missing_fields(mapped)
    return mapped


def collect_missing_fields(row: dict[str, Any], batch_level: bool = False) -> list[str]:
    missing: list[str] = []
    if not str(row.get("product_name") or row.get("source_product_name") or "").strip():
        missing.append(FIELD_LABELS["product_name"])
    if not batch_level:
        if not str(row.get("color_raw") or row.get("color") or "").strip():
            missing.append(FIELD_LABELS["color"])
        if not str(row.get("size_raw") or row.get("size") or "").strip():
            missing.append(FIELD_LABELS["size"])
        if not row.get("price_present"):
            missing.append(FIELD_LABELS["price"])
        if not row.get("weight_present"):
            missing.append(FIELD_LABELS["weight"])
        if not str(row.get("supplier") or "").strip():
            missing.append(FIELD_LABELS["supplier"])
    if not str(row.get("width_span") or "").strip():
        missing.append(FIELD_LABELS["width_span"])
    return missing


def _should_skip_line(line: str) -> bool:
    return any(pattern.search(line.strip()) for pattern in SKIP_LINE_PATTERNS)


def _first_non_empty(values: list[Any], fallback: str = "") -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return str(fallback or "").strip()


def _pinyin_parts(text: str) -> list[str]:
    try:
        from pypinyin import lazy_pinyin

        parts = []
        for token in lazy_pinyin(text):
            cleaned = _clean_token(token)
            if cleaned:
                parts.append(cleaned)
        return parts
    except Exception:
        parts: list[str] = []
        for char in text:
            if char in PINYIN_FALLBACK:
                parts.append(PINYIN_FALLBACK[char])
            elif char.isascii() and char.isalnum():
                parts.append(char.lower())
        return parts


def _clean_token(token: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", token).lower()


def _pinyin_segment(text: str) -> str:
    return "".join(_pinyin_parts(text)).lower()


def _split_line(line: str) -> list[str]:
    if "\t" in line:
        return [cell.strip() for cell in line.split("\t")]
    if "," in line:
        return [cell.strip() for cell in next(csv.reader(StringIO(line)))]
    return re.split(r"\s+", line)


def _detect_header(row: list[str]) -> dict[str, int]:
    header_map: dict[str, int] = {}
    for index, cell in enumerate(row):
        normalized = cell.strip().lower()
        for field, aliases in INPUT_HEADER_ALIASES.items():
            if normalized in {alias.lower() for alias in aliases}:
                header_map[field] = index
                break
    return header_map if {"color", "size"}.issubset(header_map) or "product_name" in header_map else {}


def _row_from_header(row: list[str], header_map: dict[str, int]) -> dict[str, Any]:
    def value(field: str) -> str:
        index = header_map.get(field)
        return row[index].strip() if index is not None and index < len(row) else ""

    parsed = {
        "product_name": value("product_name"),
        "color": value("color"),
        "size": value("size"),
        "price": value("price"),
        "weight": value("weight"),
        "supplier": value("supplier"),
        "width_span": value("width_span"),
    }
    if not any(parsed.values()):
        return {}
    return parsed


def _row_without_header(row: list[str], default_product_name: str) -> dict[str, Any]:
    if len(row) >= 6:
        return {
            "product_name": row[0] or default_product_name,
            "color": row[1],
            "size": row[2],
            "price": row[3],
            "weight": row[4],
            "supplier": row[5],
        }
    if len(row) >= 5:
        return {
            "product_name": default_product_name,
            "color": row[0],
            "size": row[1],
            "price": row[2],
            "weight": row[3],
            "supplier": row[4],
        }
    if len(row) >= 4:
        return {
            "product_name": default_product_name,
            "color": row[0],
            "size": row[1],
            "price": row[2],
            "weight": row[3],
        }
    return {}


def _round_cost_price(value: float | None) -> float | None:
    if value is None:
        return None
    quantized = Decimal(str(float(value))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return float(quantized)


def _optional_number(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    match = re.search(r"\d+(?:\.\d+)?", text)
    return float(match.group()) if match else None
