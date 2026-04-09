from __future__ import annotations

from typing import Any

from app.services.data_service import list_products, record_search


ATTRIBUTE_FIELDS = ("category", "brand", "color", "style", "material", "pattern")


def _extract_preferences(query: str, products: list[dict[str, Any]]) -> dict[str, str]:
    preferences: dict[str, str] = {}
    for field in ATTRIBUTE_FIELDS:
        values = []
        for product in products:
            value = product.get(field)
            if value and value not in values:
                values.append(value)
        for value in values:
            if value in query:
                preferences[field] = value
                break
    return preferences


def _character_overlap(query: str, content: str) -> float:
    query_chars = {char for char in query if not char.isspace()}
    if not query_chars:
        return 0.0
    content_chars = set(content)
    return len(query_chars & content_chars) / len(query_chars)


def _normalize_score(score: float) -> float:
    return round(min(max(score, 0.05), 0.99), 4)


def _format_item(product: dict[str, Any], score: float, reasons: list[str]) -> dict[str, Any]:
    """
    格式化推荐商品数据为统一的响应格式
    
    将原始商品数据和推荐评分转换为标准的推荐结果格式，
    包含商品基本信息、评分、相似度、属性特征和推荐理由。
    
    Args:
        product: 商品字典数据，包含商品的所有属性信息
            - product_id: 商品唯一标识
            - name: 商品名称
            - image_url: 商品图片 URL
            - price: 商品价格
            - brand: 商品品牌
            - category: 商品类别
            - color: 商品颜色
            - style: 商品风格
            - material: 商品材质
            - pattern: 商品图案
            - description: 商品描述
        score: 推荐评分，范围通常为 0-1 之间的浮点数
        reasons: 推荐理由列表，每个元素为一条推荐原因字符串
    
    Returns:
        dict[str, Any]: 格式化后的推荐商品字典，包含以下字段：
            - product_id: 商品 ID
            - name: 商品名称
            - image_url: 商品图片链接
            - price: 商品价格
            - brand: 商品品牌
            - category: 商品分类
            - score: 推荐评分（保留 4 位小数）
            - similarity: 相似度百分比（整数形式）
            - attributes: 商品属性字典（颜色、风格、材质、图案）
            - reason: 推荐理由（最多 3 条，用逗号连接）
            - description: 商品描述信息
    """
    # 构建商品属性信息字典
    attributes = {
        "color": product["color"],
        "style": product["style"],
        "material": product["material"],
        "pattern": product["pattern"],
    }
    
    # 生成推荐理由，最多取前 3 条，若无理由则使用默认说明
    reason_text = "，".join(reasons[:3]) if reasons else "与查询条件整体接近，适合作为候选推荐商品。"
    
    return {
        "product_id": product["product_id"],
        "name": product["name"],
        "image_url": product["image_url"],
        "price": product["price"],
        "brand": product["brand"],
        "category": product["category"],
        "score": round(score, 4),
        "similarity": int(score * 100),
        "attributes": attributes,
        "reason": reason_text,
        "description": product["description"],
    }


def recommend_by_text(query: str, top_k: int = 8) -> dict[str, Any]:
    """
    根据文本查询进行商品推荐
    
    该函数分析查询文本的语义和偏好特征，与商品库中的商品进行多维度匹配评分，
    包括字符重叠度、名称匹配、描述匹配以及属性偏好匹配，返回最相关的 Top-K 
    个商品推荐结果。
    
    Args:
        query: 用户输入的文本查询字符串，用于提取搜索意图和商品偏好特征
        top_k: 返回推荐结果的数量，默认为 8，即返回评分最高的 8 个商品
        
    Returns:
        包含推荐结果的字典，包括以下字段:
            - query: 原始查询文本
            - query_type: 查询类型，固定为"text"表示文本检索
            - recommendation_reason: 推荐理由说明，描述系统的推荐逻辑和识别到的查询重点
            - items: 推荐商品列表，每个商品包含产品信息、匹配分数和推荐理由
            
    推荐评分规则:
        - 基础分：0.12 + 0.18 * 字符重叠度
        - 名称匹配：查询词在商品名称中时 +0.25
        - 描述匹配：查询词在商品描述中时 +0.12
        - 属性偏好匹配：根据提取的偏好特征 (类目/品牌/颜色/风格/材质/图案) 给予不同权重加分
    """
    # 获取所有商品数据
    products = list_products()
    
    # 从查询文本中提取用户的商品属性偏好
    preferences = _extract_preferences(query, products)
    scored_items: list[dict[str, Any]] = []

    # 遍历所有商品，计算每个商品与查询的匹配度评分
    for product in products:
        # 拼接商品的所有文本字段用于字符重叠度计算
        content = " ".join(
            [
                product["name"],
                product["brand"],
                product["category"],
                product["color"],
                product["style"],
                product["material"],
                product["pattern"],
                product["description"],
            ]
        )
        # 计算基础评分：基于字符重叠度的相似度
        score = 0.12 + 0.18 * _character_overlap(query, content)
        reasons: list[str] = []

        # 名称精确匹配：查询词完整出现在商品名称中时给予较高权重加分
        if query and query in product["name"]:
            score += 0.25
            reasons.append("商品名称与查询词高度接近")

        # 描述文本匹配：查询词出现在商品描述中时给予中等权重加分
        if query and query in product["description"]:
            score += 0.12
            reasons.append("描述文本与查询需求匹配")

        # 属性偏好匹配：检查商品是否符合从查询中提取的属性偏好
        for field in ATTRIBUTE_FIELDS:
            expected = preferences.get(field)
            if expected and product[field] == expected:
                field_label = {
                    "category": "同类目",
                    "brand": "同品牌",
                    "color": "颜色相近",
                    "style": "风格一致",
                    "material": "材质一致",
                    "pattern": "图案相近",
                }[field]
                reasons.append(field_label)
                # 不同属性赋予不同权重：类目最高 (0.18)，颜色/风格次之 (0.14)，材质 (0.1)，品牌/图案 (0.08)
                score += {
                    "category": 0.18,
                    "brand": 0.08,
                    "color": 0.14,
                    "style": 0.14,
                    "material": 0.1,
                    "pattern": 0.08,
                }[field]

        # 对评分进行归一化处理，确保分数在合理范围内
        score = _normalize_score(score)
        # 将商品及其评分和推荐理由格式化后加入评分列表
        scored_items.append(_format_item(product, score, reasons))

    # 按评分降序排序，选取前 top_k 个商品作为最终推荐结果
    scored_items.sort(key=lambda item: item["score"], reverse=True)
    selected = scored_items[:top_k]
    # 记录本次文本检索日志，用于后续分析和优化
    record_search("text", query, [item["product_id"] for item in selected])

    # 构建推荐理由说明
    summary = "系统根据文本语义、类目和属性匹配度完成第一版推荐排序。"
    # 如果识别到明确的属性偏好，在推荐理由中说明
    if preferences:
        parts = [f"{key}:{value}" for key, value in preferences.items()]
        summary = f"系统识别到查询重点为 {' / '.join(parts)}，优先推荐共享这些特征的商品。"

    return {
        "query": query,
        "query_type": "text",
        "recommendation_reason": summary,
        "items": selected,
    }


def recommend_by_image(image_profile: dict[str, Any], top_k: int = 8) -> dict[str, Any]:
    """
    根据上传图片的特征进行商品推荐
    
    该函数分析上传图片的主色调和推断品类，与商品库中的商品进行匹配评分，
    返回最相关的 Top-K 个商品推荐结果。
    
    Args:
        image_profile: 图片特征字典，包含以下字段:
            - dominant_color: 图片主色调
            - inferred_category: 从图片名称推断的品类
            - saved_url: 图片保存后的 URL
            - original_name: 图片原始名称
            - note: 图片相关备注信息
        top_k: 返回推荐结果的数量，默认为 8
        
    Returns:
        包含推荐结果的字典，包括:
            - query: 查询标识 (图片原始名称或默认"图片检索")
            - query_type: 查询类型，固定为"image"
            - image_profile: 图片特征信息字典
            - recommendation_reason: 推荐理由说明
            - items: 推荐商品列表，每个商品包含产品信息、匹配分数和推荐理由
    """
    products = list_products()
    dominant_color = image_profile.get("dominant_color", "")
    inferred_category = image_profile.get("inferred_category", "")
    scored_items: list[dict[str, Any]] = []

    # 遍历所有商品，计算与图片特征的匹配度评分
    for product in products:
        score = 0.15
        reasons: list[str] = []

        # 主色调匹配：权重最高 (0.34)，颜色一致时大幅提升分数
        if dominant_color and product["color"] == dominant_color:
            score += 0.34
            reasons.append(f"主色调接近，均为{dominant_color}")

        # 推断品类匹配：根据图片名称线索推断的品类进行匹配 (0.24)
        if inferred_category and product["category"] == inferred_category:
            score += 0.24
            reasons.append(f"图片名称线索推断为{inferred_category}")

        # 默认品类补偿：当无法推断品类时，优先选择连衣裙这一常见视觉品类 (0.08)
        if not inferred_category and product["category"] == "连衣裙":
            score += 0.08
            reasons.append("第一版默认优先返回视觉品类")

        # 风格加分：特定流行风格获得额外加分 (0.05)
        if product["style"] in ("复古", "甜美", "通勤"):
            score += 0.05

        # 图案加分：纯色款式获得额外加分 (0.04)
        if product["pattern"] == "纯色":
            score += 0.04

        score = _normalize_score(score)
        scored_items.append(_format_item(product, score, reasons))

    # 按匹配分数降序排序，选取前 top_k 个商品
    scored_items.sort(key=lambda item: item["score"], reverse=True)
    selected = scored_items[:top_k]
    
    # 记录本次图片检索日志
    query_text = f"图片检索:{dominant_color or '未知颜色'}"
    record_search("image", query_text, [item["product_id"] for item in selected])

    # 构建推荐理由说明
    recommendation_reason = "系统已保存上传图片，并根据主色调和基础类目线索完成第一版图片推荐。"
    if dominant_color:
        recommendation_reason = f"系统识别到上传图片主色调偏向{dominant_color}，因此优先返回颜色和品类接近的商品。"

    return {
        "query": image_profile.get("original_name", "图片检索"),
        "query_type": "image",
        "image_profile": {
            "dominant_color": dominant_color,
            "inferred_category": inferred_category,
            "saved_url": image_profile.get("saved_url", ""),
            "note": image_profile.get("note", ""),
        },
        "recommendation_reason": recommendation_reason,
        "items": selected,
    }
