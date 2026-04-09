# Project1

第一版可运行项目，先把整条链路跑通。

当前版本已经包含：

- `frontend/`：第一版首页、推荐结果页、统计分析页
- `backend/`：FastAPI 后端、演示商品数据、文本推荐接口、图片推荐接口
- 图片检索的第一版占位层：先完成图片保存、主色调分析和基础类目猜测

后续在这个基础上逐步替换：

- 模拟 JSON 数据 -> MySQL
- 图片占位逻辑 -> YOLO
- 规则推荐 -> Neo4j + Milvus + 融合排序

## 目录说明

```text
project1/
├─ frontend/

├─ backend/
│  ├─ app/
│  ├─ data/
│  ├─ static/
│  ├─ uploads/
│  └─ requirements.txt
└─ README.md
```

## 启动方法

### 1. 启动后端

```powershell
cd d:\PROJECT\RecommandSystem\project1\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

uvicorn app.main:app --reload
```

启动后打开：

- `http://127.0.0.1:8000/api/health`
- `http://127.0.0.1:8000/docs`

### 2. 启动前端静态服务

另开一个 PowerShell：

```powershell
cd d:\PROJECT\RecommandSystem\project1\frontend
npm run dev
```

然后浏览器打开：

- `http://127.0.0.1:8000`

## 当前接口

- `GET /api/health`
- `POST /api/recommend/by-text`
- `POST /api/recommend/by-image`
- `GET /api/products/{product_id}`
- `GET /api/graph/product/{product_id}`
- `GET /api/analytics/summary`

## 推荐测试建议

- `白色复古连衣裙`
- `蓝色通勤衬衫`
- `复古波点裙`
- 上传一张浅色商品图进行图片检索

## 下一步怎么做

按这个顺序继续：

1. 把 `products.json` 迁移到 MySQL
2. 给商品建立品牌、类目、属性三张关系表
3. 用脚本把结构化数据同步到 Neo4j
4. 把 `image_service.py` 里的占位替换成真实 YOLO 检测
5. 给商品生成视觉向量和文本向量
6. 接入 Milvus 做候选召回
7. 在 `recommend_service.py` 里改成融合排序

## 当前版本说明

这一版的目标是“能跑、能演示、能继续扩展”。

现在先做的事是：

- 启动起来
- 确认前后端流程已经打通
- 然后再往数据库和 YOLO 上推进
