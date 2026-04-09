from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from app.utils.image_utils import infer_dominant_color, save_bytes_to_file


CATEGORY_HINTS = {
    "dress": "连衣裙",
    "shirt": "衬衫",
    "skirt": "半身裙",
    "coat": "风衣",
    "suit": "西装外套",
    "knit": "针织衫",
    "pants": "牛仔裤",
    "连衣裙": "连衣裙",
    "衬衫": "衬衫",
    "半身裙": "半身裙",
    "风衣": "风衣",
    "外套": "西装外套",
}


def analyze_upload(file: UploadFile, upload_dir: Path) -> dict[str, Any]:
    raw_bytes = file.file.read()
    suffix = Path(file.filename or "").suffix or ".jpg"
    saved_name = f"{uuid.uuid4().hex}{suffix}"
    saved_path = save_bytes_to_file(raw_bytes, upload_dir / saved_name)

    lowered = (file.filename or "").lower()
    inferred_category = ""
    for keyword, category in CATEGORY_HINTS.items():
        if keyword.lower() in lowered:
            inferred_category = category
            break

    dominant_color = infer_dominant_color(raw_bytes)
    readable_name = re.sub(r"[^0-9A-Za-z\u4e00-\u9fa5._-]", "", file.filename or "upload.jpg")

    return {
        "saved_path": saved_path,
        "saved_url": f"/uploads/{saved_name}",
        "original_name": readable_name,
        "dominant_color": dominant_color,
        "inferred_category": inferred_category,
        "note": "第一版中这里是 YOLO 占位层，当前先完成图片保存、主色调提取和类目猜测，后续可直接替换成真实 YOLO 检测结果。",
    }
