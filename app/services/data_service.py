from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_DIR / "data"
PRODUCTS_PATH = DATA_DIR / "products.json"
SEARCH_LOGS_PATH = DATA_DIR / "search_logs.json"


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def list_products() -> list[dict[str, Any]]:
    return _read_json(PRODUCTS_PATH, [])


def get_product(product_id: int) -> dict[str, Any] | None:
    for product in list_products():
        if product["product_id"] == product_id:
            return product
    return None


def list_search_logs() -> list[dict[str, Any]]:
    return _read_json(SEARCH_LOGS_PATH, [])


def record_search(query_type: str, query: str, matched_ids: list[int]) -> None:
    logs = list_search_logs()
    logs.append(
        {
            "query_type": query_type,
            "query": query,
            "matched_ids": matched_ids,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    _write_json(SEARCH_LOGS_PATH, logs)


def build_product_graph(product_id: int) -> dict[str, Any] | None:
    """
    构建商品知识图谱，包含商品、品牌、类目、属性及相似商品的关系网络
    
    该函数通过给定的商品 ID，构建一个以该商品为核心的关系图谱。图谱包含以下节点类型：
    - 商品节点：核心商品及其相似商品
    - 品牌节点：商品所属品牌
    - 类目节点：商品所属类目
    - 属性节点：商品的颜色、风格、材质、图案等属性
    
    图谱中的连接关系包括：
    - 商品与品牌的所属关系
    - 商品与类目的所属关系
    - 商品与属性的关联关系
    - 商品与相似商品的相似度关系
    
    Args:
        product_id (int): 商品 ID，用于获取目标商品信息
        
    Returns:
        dict[str, Any] | None: 返回图谱数据字典，包含 nodes 和 links 两个键
            - nodes: 节点列表，每个节点包含 id、name、category 及可能的额外信息
            - links: 连接关系列表，每个连接包含 source、target 和 label
            如果商品不存在则返回 None
            
    Raises:
        无显式异常抛出，但依赖 get_product 和 list_products 函数的正常执行
    """
    # 获取目标商品信息
    product = get_product(product_id)
    if not product:
        return None

    # 获取所有商品列表用于计算相似商品
    products = list_products()
    nodes: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []

    def add_node(node_id: str, name: str, category: str, extra: dict[str, Any] | None = None) -> None:
        """
        向图谱中添加节点，避免重复添加
        
        Args:
            node_id (str): 节点唯一标识符
            name (str): 节点名称
            category (str): 节点类别（如"商品"、"品牌"、"类目"、"属性"、"相似商品"）
            extra (dict[str, Any] | None, optional): 额外信息字典，默认为 None
        """
        if any(node["id"] == node_id for node in nodes):
            return
        payload = {"id": node_id, "name": name, "category": category}
        if extra:
            payload.update(extra)
        nodes.append(payload)

    # 添加核心商品节点及其直接关联的品牌和类目节点
    add_node(f"product-{product['product_id']}", product["name"], "商品")
    add_node(f"brand-{product['brand']}", product["brand"], "品牌")
    add_node(f"category-{product['category']}", product["category"], "类目")
    
    # 建立商品与品牌、类目的连接关系
    links.append(
        {
            "source": f"product-{product['product_id']}",
            "target": f"brand-{product['brand']}",
            "label": "所属品牌",
        }
    )
    links.append(
        {
            "source": f"product-{product['product_id']}",
            "target": f"category-{product['category']}",
            "label": "所属类目",
        }
    )

    # 添加商品属性节点（颜色、风格、材质、图案）并建立连接
    for key in ("color", "style", "material", "pattern"):
        node_id = f"{key}-{product[key]}"
        add_node(node_id, product[key], "属性")
        links.append(
            {
                "source": f"product-{product['product_id']}",
                "target": node_id,
                "label": key,
            }
        )

    # 计算相似商品：基于共享属性数量（至少共享 2 项属性）
    similar_products: list[dict[str, Any]] = []
    for candidate in products:
        if candidate["product_id"] == product["product_id"]:
            continue
        shared = 0
        for key in ("category", "color", "style", "material", "pattern"):
            if candidate[key] == product[key]:
                shared += 1
        if shared >= 2:
            similar_products.append(candidate | {"shared_count": shared})

    # 按共享属性数量降序排序，选取最相似的 3 个商品添加到图谱中
    similar_products.sort(key=lambda item: item["shared_count"], reverse=True)
    for candidate in similar_products[:3]:
        add_node(f"product-{candidate['product_id']}", candidate["name"], "相似商品")
        links.append(
            {
                "source": f"product-{product['product_id']}",
                "target": f"product-{candidate['product_id']}",
                "label": f"共享{candidate['shared_count']}项属性",
            }
        )

    return {"nodes": nodes, "links": links}


def build_analytics_summary() -> dict[str, Any]:
    """
    构建数据分析摘要信息
    
    从产品数据和搜索日志中统计各项指标，包括产品总数、品牌分布、类目分布、搜索热度等关键业务指标，用于前端数据可视化展示。
    
    Returns:
        dict[str, Any]: 包含以下字段的分析摘要字典:
            - total_products (int): 产品总数
            - total_brands (int): 品牌总数
            - total_categories (int): 类目总数
            - total_searches (int): 搜索记录总数
            - text_searches (int): 文本搜索次数
            - image_searches (int): 图片搜索次数
            - average_price (float): 平均价格，保留两位小数
            - category_distribution (list[dict]): 类目分布列表，每项包含 name 和 value
            - brand_distribution (list[dict]): 品牌分布列表，每项包含 name 和 value
            - style_distribution (list[dict]): 风格分布列表，每项包含 name 和 value
            - hot_queries (list[dict]): 热门查询 TOP6，每项包含 name 和 value
            - recent_logs (list[dict]): 最近 8 条搜索日志（倒序排列）
    """
    # 获取所有产品数据和搜索日志
    products = list_products()
    logs = list_search_logs()

    # 统计各维度的分布情况：类目、品牌、风格、查询类型
    category_counter = Counter(product["category"] for product in products)
    brand_counter = Counter(product["brand"] for product in products)
    style_counter = Counter(product["style"] for product in products)
    query_type_counter = Counter(log["query_type"] for log in logs)
    
    # 统计热门文本查询（排除空查询），取出现频率最高的 6 个
    hot_queries = Counter(
        log["query"] for log in logs if log["query_type"] == "text" and log["query"]
    ).most_common(6)

    # 构建并返回完整的分析摘要数据
    return {
        "total_products": len(products),
        "total_brands": len(brand_counter),
        "total_categories": len(category_counter),
        "total_searches": len(logs),
        "text_searches": query_type_counter.get("text", 0),
        "image_searches": query_type_counter.get("image", 0),
        "average_price": round(
            sum(product["price"] for product in products) / max(len(products), 1), 2
        ),
        "category_distribution": [
            {"name": key, "value": value} for key, value in category_counter.most_common()
        ],
        "brand_distribution": [
            {"name": key, "value": value} for key, value in brand_counter.most_common()
        ],
        "style_distribution": [
            {"name": key, "value": value} for key, value in style_counter.most_common()
        ],
        "hot_queries": [{"name": key, "value": value} for key, value in hot_queries],
        "recent_logs": logs[-8:][::-1],
    }
