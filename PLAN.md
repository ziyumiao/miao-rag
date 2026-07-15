# 工作计划（oprag）

## 阶段总览

| 阶段 | 名称 | 目标 | 预计耗时 | 产出物 |
|------|------|------|----------|--------|
| P0 | 基础设施 | 可启动的空 Agent | 0.5 天 | 项目骨架、配置、LangGraph 空壳 |
| P0.5 | 安全加固 | 认证、防注入、限流、防泄露 | 0.5 天 | 中间件 + 认证模块 |
| P1 | 知识冷启动 | 手工录入首批知识 | 1 天 | 商品目录 + 键盘型号库 |
| P2 | 清洗流水线 | 聊天记录 → 结构化知识 | 2 天 | 规则引擎 + LLM 提取脚本 |
| P3 | 索引构建 | 知识入库可检索 | 0.5 天 | ChromaDB 索引 + 知识图谱 |
| P4 | 核心 Agent | 完成基础售前问答 | 3 天 | 意图识别 → 检索 → 生成答案 |
| P5 | 高级能力 | 纠错/拍照/联网/订单/情感 | 3 天 | 完整工具集 Agent |
| P6 | 人工转接 | 兜底闭环 | 1 天 | 转人工工单 + 对话摘要 |

---

## P0 — 基础设施

**目标**：LangGraph 空壳可启动，能接收请求、返回固定回复。

### 任务清单

- [ ] 初始化项目目录结构
- [ ] 配置 pyproject.toml（依赖：langgraph、llama-index、chromadb、fastapi 等）
- [ ] 创建 .env 配置管理
- [ ] 搭建 FastAPI + uvicorn 服务骨架
- [ ] 创建 LangGraph StateGraph 空流程（START → 占位节点 → END）
- [ ] 实现 `/qa/chat` 接口，返回固定回复 "系统初始化中"
- [ ] 实现 `/health` 健康检查
- [ ] 验证：`curl /health` 返回 200

---

## P0.5 — 安全加固

**目标**：API 认证、防注入、限流、防泄露。

### 任务清单

- [ ] 实现 API Key 认证中间件
  - H5 页面携带 `X-API-Key` header
  - 后端 `verify_api_key` 中间件校验
  - 无效 Key 返回 401
- [ ] 实现 buyer_nick 服务端校验
  - 新会话首次建立时，后端调千牛 API 确认 buyer_nick 对应当前会话
  - 校验通过后绑定到 `session_id`，后续消息不再重复调用千牛
  - 校验失败返回 403
- [ ] 实现 Prompt 注入防护
  - RCTRF prompt 模板（`tools/prompt_template.py`）
  - 输入清洗：正则过滤常见注入模式（`input_filter.py`）
  - P4 评估是否需要输出检测
- [ ] 实现速率限制中间件
  - 全局 QPS 限制：内存计数器，默认 10 QPS
  - 按 session 限流：内存计数器，默认 2 QPS
  - 按 buyer_nick 日限额：PG 原子计数 `INSERT ON CONFLICT UPDATE`，默认 200 次/天
  - 超限返回 429 + 友好提示
- [ ] 实现敏感信息保护
  - 日志脱敏：`buyer_nick` 只截取前两位
  - 输出清洗：移除 `sk-`/`ghp_` 等 Token 格式子串
  - 不记录 LLM 请求/响应完整内容到持久化日志
- [ ] 实现 CORS 配置
  - 仅允许千牛域名（`*.taobao.com`、`*.tmall.com`）
- [ ] 验证：未带 Token 请求返回 401 / 超频返回 429

---

## P1 — 知识冷启动

**目标**：手工整理首批知识，让检索索引有内容可查。

### 任务清单

- [ ] 编写 `data/products.md`：手工录入当前所有在售键帽商品
  - 每条包含：名称、材质、高度、适配轴体结构、不兼容说明、价格、SKU
  - 参考 `DESIGN.md` 6.1 节的分块格式
- [ ] 编写 `data/faq.md`：高频 FAQ（安装方法、清洗维护、退换货政策等）
- [ ] 编写 `data/keyboard_db.json`：键盘型号库
  - 从历史记忆 / 常见品牌入手，手工录入 30-50 条高频型号
  - 字段：brand、model、type、switch_structure、switch_height
- [ ] 编写 `data/compatibility.md`：兼容性总则文档
  - 标准 MX 轴、矮轴、静电容、ALPS 的结构说明
  - 哪些能用、哪些不能用、为什么
- [ ] 验证：文档可被 LlamaIndex 加载解析

---

## P2 — 清洗流水线

**目标**：编写聊天记录清洗脚本，后续有数据即可跑。

### 任务清单

- [ ] 实现规则引擎 `tools/chat_cleaner.py`
  - 6 组正则匹配（兼容性/轴体/价格/型号/材质/高度/安装）
  - 客服回复提取（正面/负面/追问分类）
- [ ] 实现 LLM 兜底提取
  - Prompt：从一段对话中提取 QA 对 + 事实三元组
  - 批量处理脚本
- [ ] 实现图片处理
  - Vision LLM 识别轴体 → 结构化标注
  - OCR 提取表格（如果有）
- [ ] 输出格式定义：`qa_pairs.jsonl` + `facts.jsonl`
- [ ] 质检流程：随机抽样 5% + 强模型复审低置信度结果
- [ ] 验证：用 3-5 条模拟对话跑通全流程

---

## P3 — 索引构建

**目标**：文档 + QA 对 → 可检索的知识库。

### 任务清单

- [ ] 实现 LlamaIndex 文档加载器
  - 加载 `data/` 下所有 .md/.pdf/.docx
  - 按商品实体分块（以 `---` 或 `##` 为分隔符）
- [ ] 实现 metadata 标注
  - 从文档中提取 compatible_switches、incompatible_switches、material 等
  - 默认所有产品 compatible_switches=["standard_mx"]
- [ ] 创建混合索引
  - ChromaDB 向量索引
  - BM25 关键词索引（LlamaIndex BM25Retriever）
  - HybridFusionRetriever（RRF 融合）
- [ ] 搭建知识图谱
  - LLM 从文档抽取实体/关系
  - networkx 图存储
  - 实现基础图查询（实体邻居、兼容性路径）
- [ ] 实现 `/knowledge/build` API
- [ ] 验证：`curl /knowledge/build` → 返回文档数、块数、实体数、关系数

---

## P4 — 核心 Agent

**目标**：完成基础售前问答链路。

### 任务清单

- [ ] 实现并行意图识别节点
  - 情感分析（正面/负面/中性）
  - 业务意图提取（compatibility_check / product_inquiry / after_sales）
  - 实体提取（键盘型号 / 轴体 / 键帽规格）
  - 使用 RCTRF prompt 模板（`tools/prompt_template.py`）
- [ ] 实现情感回应逻辑
  - 感谢赞美、安抚抱怨、中性推进
- [ ] 实现兼容性判断逻辑
  - 三层递进：型号库 → 联网搜索 → 拍照引导
  - 三路结果：compatible / incompatible / unknown
- [ ] 实现检索节点
  - 混合检索 + metadata 过滤
  - 知识图谱查询
- [ ] 实现追问节点
  - 追问次数计数（超过 3 次触发转人工）
  - 追问话术生成
- [ ] 实现生成答案节点
  - RCTRF prompt 模板 + 结构化 JSON 输出
  - 上下文拼接 + LLM 生成
  - 产品推荐生成
- [ ] Prompt 效果评估
  - 用 20 个测试用例验证 RCTRF 防注入效果
  - 评估是否需要增加输出检测节点（扫描生成答案中的敏感信息泄露）
- [ ] 串接完整 LangGraph 流程
- [ ] 验证：5 个标准场景端到端跑通（参考 DESIGN.md 第 9 节）

---

## P5 — 高级能力

**目标**：补齐智能售前所需的全部工具。

### 任务清单

- [ ] 拼写纠错工具
  - LLM 规范化 + ngram 模糊匹配兜底
- [ ] 拍照识别工具
  - 多模态 LLM 识别轴体结构/高度/颜色
  - 结果结构化输出
- [ ] 联网搜索工具
  - LLM 联网搜索键盘型号规格
  - 强制结构化 JSON 输出，标注来源和置信度
- [ ] 订单查询工具
  - 淘宝 API `taobao.trades.sold.get` 集成
  - 按 buyer_nick 查询历史订单
- [ ] 多业务意图并行处理
  - 一轮对话中多个业务问题逐一回应

---

## P6 — 人工转接

**目标**：兜底闭环，无法处理时无缝转人工。

### 任务清单

- [ ] 转人工触发条件
  - 追问超过 3 次
  - 检索置信度低于阈值
  - 客户明确要求转人工
  - 检测到投诉/辱骂等风险场景
- [ ] 对话摘要生成
  - 提取完整对话中的关键信息
  - 包含：客户问题、已获取的信息、当前卡点
- [ ] 转接通知
  - 生成工单
  - 通知人工客服（IM 推送 or 数据库标记）
- [ ] 转接响应
  - 告知客户"已为您转接人工客服，请稍候"

---

## 依赖关系

```
P0 ──→ P0.5 ──→ P1 ──→ P3 ──→ P4 ──→ P5 ──→ P6
  │                              │
  └────────→ P2 ────────────────┘
```

P0.5 依赖 P0（需要 API 框架才能加中间件）。P1 和 P2 可以并行（独立工作），但都依赖 P0.5（API 层安全加固完成）。P3 合并 P1+P2 的产出后构建索引。

## 当前状态

- [x] 设计文档完成（DESIGN.md）
- [x] 领域模型完成（CONTEXT.md）
- [x] P0 基础设施 ✅
  - LangGraph 空壳 Agent（StateGraph: 意图识别 → 检索 → 生成答案 → 转人工）
  - FastAPI `/health` `/qa/chat` `/qa/reset` `/knowledge/stats`
  - 配置管理（DeepSeek V4 Flash + 通义千问 VL Max + PG + ChromaDB）
- [ ] P0.5 安全加固（当前优先）
- [x] P1 知识冷启动 ✅
  - `data/products.md` — 4 个键帽商品模板（风格描述代替颜色）
  - `data/faq.md` — 10 条 FAQ（安装/清洗/退换/松动/透光/矮轴/磁轴/赠品等）
  - `data/keyboard_db.json` — 30 个高频键盘型号映射库
  - `data/dict.txt` — jieba 自定义词典（键帽行业术语，P3 使用）
- [ ] P2 清洗流水线
