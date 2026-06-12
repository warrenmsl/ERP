from __future__ import annotations

from typing import Any

OcrToken = tuple[str, float, tuple[float, float, float, float]]


def ocr_tokens(image: Any) -> list[OcrToken]:
    try:
        from ocrmac import ocrmac

        recognizer = ocrmac.OCR(image, language_preference=["zh-Hans", "en-US"])
        return recognizer.recognize()
    except Exception:
        pass

    try:
        import pytesseract

        text = pytesseract.image_to_string(image, lang="chi_sim+eng")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return []
        return [
            (line, 1.0, (0.0, index / max(len(lines), 1), 1.0, 1.0 / max(len(lines), 1)))
            for index, line in enumerate(lines)
        ]
    except Exception as exc:
        raise ValueError("截图 OCR 失败，请安装 ocrmac（macOS）或 tesseract，或改粘贴表格文本") from exc


def ocr_text_from_tokens(tokens: list[OcrToken]) -> str:
    parts: list[str] = []
    for text, _confidence, _bbox in tokens:
        cleaned = str(text or "").strip()
        if cleaned and cleaned not in parts:
            parts.append(cleaned)
    return " ".join(parts)
