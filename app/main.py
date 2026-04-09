from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.services.data_service import build_analytics_summary, build_product_graph, get_product
from app.services.image_service import analyze_upload
from app.services.recommend_service import recommend_by_image, recommend_by_text


BACKEND_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = BACKEND_DIR / "uploads"
STATIC_DIR = BACKEND_DIR / "static"

app = FastAPI(
    title="Project1 Recommend System",
    description="本科毕设第一版系统，先跑通前后端与推荐流程，后续再替换为 MySQL/Neo4j/Milvus/YOLO 真正实现。",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,     # 允许跨域
    allow_origins=[
        "http://localhost:8080",        
        "http://127.0.0.1:8080",
        "https://recommendserver-920l.onrender.com",
    ], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class TextRecommendRequest(BaseModel):
    query: str = Field(..., min_length=1, description="文本查询词")
    top_k: int = Field(default=8, ge=1, le=20)


def api_response(data, message: str = "success", code: int = 0):
    return {"code": code, "message": message, "data": data}


@app.get("/api/health")
async def health():
    return api_response({"status": "ok", "service": "project1-backend"})


@app.post("/api/recommend/by-text")
async def recommend_text(payload: TextRecommendRequest):
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query 不能为空")
    return api_response(recommend_by_text(query=query, top_k=payload.top_k))


@app.post("/api/recommend/by-image")
async def recommend_image(file: UploadFile = File(...), top_k: int = Form(default=8)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="请上传图片文件")
    try:
        image_profile = analyze_upload(file=file, upload_dir=UPLOAD_DIR)
    except Exception as e:  
        raise HTTPException(status_code=400, detail=f"图片处理失败: {e}") from e
    return api_response(recommend_by_image(image_profile=image_profile, top_k=top_k))


@app.get("/api/products/{product_id}")
async def product_detail(product_id: int):
    product = get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return api_response(product)


@app.get("/api/graph/product/{product_id}")
async def product_graph(product_id: int):
    graph = build_product_graph(product_id)
    if not graph:
        raise HTTPException(status_code=404, detail="商品不存在")
    return api_response(graph)


@app.get("/api/analytics/summary")
async def analytics_summary():
    return api_response(build_analytics_summary())
