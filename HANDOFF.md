# Handoff — oprag 项目交接文档

生成时间：2026-07-16

## 项目概述

键帽售前智能客服系统。基于 LangGraph + LlamaIndex，支持多轮对话、轴体识别、订单查询、人工转接。

仓库：https://github.com/ziyumiao/miao-rag

## 当前进度

| 阶段 | 状态 | 关键文件 |
|------|------|----------|
| P0   | ✅ 完成 | `src/oprag/agent/graph.py` — LangGraph 空壳 |
| P0.5 | ✅ 完成 | `src/oprag/api/middleware.py` — 认证/限流/CORS |
| P1   | ✅ 完成 | `data/products.md`, `data/faq.md`, `data/keyboard_db.json` |
| P2   | ✅ 完成 | `src/oprag/tools/chat_cleaner.py` — 规则引擎 + LLM兜底 |
| P3   | ⬜ 待开始 | LlamaIndex 混合索引 + 知识图谱 |
| P4   | ⬜ 待开始 | 核心 Agent（意图识别 → 检索 → 生成答案） |
| P5   | ⬜ 待开始 | 高级能力（纠错/拍照/联网/订单/情感） |
| P6   | ⬜ 待开始 | 人工转接 |

## 测试状态

```
tests/test_security.py  — 17 tests passed (P0.5)
tests/test_cleaner.py   — 13 tests passed (P2)
```

## 关键技术决策（已沉淀到 DESIGN.md）

1. **LLM 选型**：文本用 DeepSeek V4 Flash，图片识别用通义千问 VL Max
2. **检索**：LlamaIndex 混合检索（BM25 + 向量）+ ChromaDB
3. **会话持久化**：PostgreSQL（LangGraph AsyncPostgresSaver）
4. **限流**：全局+session 用内存，buyer_nick 日限额用 PG，不引入 Redis
5. **Metadata 结构**：`compatible_switches` 用结构级分类 `standard_mx` / `low_profile_mx`
6. **兼容性判断**：三层递进（型号库 → 联网搜索 → 拍照引导）
7. **Prompt 安全**：RCTRF 五层结构 + 分隔符 + 强制 JSON 输出
8. **售后分层**：使用咨询 Agent 回答，退换货/物流转人工
9. **意图识别**：合并到一次 RCTRF LLM 调用，同时输出 intent + retrieval_needed + entities + direct_answer
10. **生成答案**：一次 LLM 调用同时输出 answer + confidence + evaluation，省去判断解决节点

## P2 清洗流水线详情

- `tools/chat_cleaner.py`：
  - 7 组规则句式（兼容性/轴体/价格/材质/使用咨询 等）
  - 11 组品牌中英文映射（海盗船→Corsair 等）
  - 客服回复中自动提取轴体信息 → 事实三元组
  - `clean_all_records()` 批量处理
  - `export_to_jsonl()` 输出格式
  - `build_llm_extraction_prompt()` 兜底 prompt
  - 统计 `rule_misses` 供后续 LLM 批处理

## 下一步：P3 索引构建

P3 需要把 P1 的知识文档 + P2 清洗出的 QA 对全部构建成可检索的索引：

1. LlamaIndex 文档加载器 → 按商品实体分块
2. ChromaDB 向量索引 + BM25 关键词索引 → HybridFusionRetriever
3. 知识图谱：LLM 从文档抽取实体/关系 → networkx 图存储
4. 实现 `/knowledge/build` API

执行 P3 前需先准备好：
- P1 的 `data/products.md` 和 `data/faq.md`（已有模板，需替换为真实商品）
- P2 的清洗结果（目前无真实聊天记录，可用 mock 数据跑通流程）
- `.env` 中的 Embedding API Key（`text-embedding-3-small`）

## 待 P3 编码前要确认的

- 真实商品数据是否已准备好？（`products.md` 目前是 4 条模板）
- Embedding API Key 是否已配置？
- 键盘型号库是否需要扩充？（目前 30 条）
- jieba 自定义词典 `data/dict.txt` 是否已创建？

## P4 预留优化

以下优化已记录在 PLAN.md P4 任务清单中，实现时注意：

- 意图识别合并到一次 RCTRF 调用（避免 2 次 LLM 调用）
- 生成答案一次调用同时输出 answer + evaluation（避免判断解决节点）
- 流式 SSE 推送（首字延迟 < 1.5s）
- 检索必要性判断：闲聊/FAQ 直接回答，不走检索
- P4 完成后评估是否需要输出检测节点

## 敏感信息提醒

- `.env` 未被 git 追踪
- GitHub Token 已从所有文件中清除
- API Key 配置在 `settings.py` 中通过环境变量读取
- 日志中 `buyer_nick` 必须脱敏（只截取前两位）
