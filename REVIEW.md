# Code Review 结论

**分支**：master（HEAD: 890320d）  
**评分**：7 / 10  
**测试**：30 passed ✅  

---

## 严重问题（P3 前必须修复）

| # | 文件:行号 | 问题 | 风险 |
|---|-----------|------|------|
| 4 | `agent/graph.py:71-73` | PG 连接失败 `except Exception: pass` 静默降级到 MemorySaver | 生产会话重启丢失，运维无感知 |
| 5 | `api/__init__.py:39` | `create_agent(use_pg=False)` 硬编码 | PG 持久化形同虚设，无法跨实例 |
| 9 | `config.py:16,21,26` | LLM/Vision/Embedding API Key 默认值 `"sk-"` | `.env` 缺失时不报错，带无效 key 启动 |

---

## 安全组件未接线

| # | 文件 | 问题 |
|---|------|------|
| 14 | `tools/input_filter.py` | `filter_input` 已实现但从未在 `/qa/chat` 链路中调用 |
| 15 | `tools/prompt_template.py` | RCTRF 五层分隔符不完整，缺 Role/Context/Rules/Task/Format 子层分隔 |

---

## 建议项

### 架构

- `pyproject.toml:5` `requires-python=">=3.11"` 与 DESIGN.md 要求 3.12.13 不一致，建议收紧到 `>=3.12`
- `loader/`、`retriever/`、`graph/` 三个空目录缺 `__init__.py` 占位
- `tools/__init__.py` 注释写「P5 实现」但 chat_cleaner 已在 P2 实现，过时

### LangGraph

- `nodes.py:15` 意图识别节点每次递增 `ask_count`，语义错误，应由追问节点递增
- `graph.py:18-19` `_route_after_retrieve` 是常量路由，不需要 conditional_edges
- `_route_after_intent` 缺少「直接可回答 / 需检索 / 信息不足」三分路由的 TODO 标注

### 安全

- `middleware.py:29` API Key 比较用 `!=` 而非 `secrets.compare_digest`（timing attack 风险，低优先级）
- `config.py:34` PG 连接串默认值含 `user:pass@localhost` 建议留空
- `middleware.py:55` 限流 session_id 取自 `X-Session-Id` header，但 `/qa/chat` 用 body `session_id`，前端不带 header 则全部落到 `default` 桶
- `middleware.py` 只实现了 session 维度限流，global QPS 和 buyer_nick 日限额未实现
- `middleware.py:55` 内存计数器在多 worker 下失效，建议文档说明部署约束
- 缺少 `debug: bool` 配置项，生产应关闭 `/docs` 暴露

### 代码质量

- `chat_cleaner.py:164-169` 在函数内动态定义 `class Msg`，建议提到模块级
- `chat_cleaner.py:131-138` `AGENT_COMPAT_POSITIVE`/`AGENT_COMPAT_NEGATIVE` 定义了但从未使用（死代码）
- `chat_cleaner.py:131` `AGENT_SWITCH_PATTERN` 正则过宽，`是|用` 会匹配噪声
- `api/__init__.py:34` 用闭包变量 `_agent` 而非 `app.state.agent`，两套真相来源
- `config.py:54` `settings = Settings()` 模块级单例，测试环境无 `.env` 时走默认值不报错

### 测试

- `test_cleaner.py:32` 断言过宽 `"兼容" in qa.question or "K70" in qa.question`，or 让断言几乎不会失败
- `test_security.py:136-146` 限流测试有 flaky 风险，依赖时序，建议 mock `time.monotonic`
- `agent/nodes.py` 四个空壳节点零测试，路由分支无覆盖
- 缺 `conftest.py`，`build_test_app` 重复构造
- 缺 `pyproject.toml` 的 `[tool.pytest.ini_options]`、ruff、mypy 配置

### 文档漂移

- DESIGN.md 5 节状态定义有 `user_id`，`state.py` 没有，只有 `buyer_nick`
- PLAN.md 说 `data/dict.txt` 已创建，实际缺失
- HANDOFF.md 仓库地址 `miao-rag` 与项目名 `oprag` 不一致

### 性能

- `chat_cleaner.py:184` 规则匹配 `O(n²)`，建议预构建 customer_idx → agent_reply 索引
- `middleware.py` 限流用 list comprehension 清理窗口，高并发下 GC 压力大，建议用 `deque.popleft`
- `api/__init__.py:88` `ainvoke` 阻塞全量返回，P4 流式 SSE 需改 `astream` + `StreamingResponse`

---

## 各维度评分

| 维度 | 分数 | 评价 |
|------|------|------|
| 架构设计 | 8 | 分层清晰，状态图解耦好，空目录占位缺失 |
| LangGraph 用法 | 6 | 基础正确，PG 降级静默 + ask_count 语义错误 + 硬编码 use_pg |
| 安全设计 | 6 | 思路完整，但组件未接线 + 限流维度不全 + 多 worker 失效 |
| 代码质量 | 7 | 类型注解现代，有死代码 + 命名混乱 + 正则过宽 |
| 测试质量 | 7 | TDD 节奏好，有 flaky 风险 + 断言过宽 + 路由零测试 |
| 可维护性 | 7 | 文档驱动加分，单文件膨胀 + 缺 ruff/mypy |
| 配置管理 | 7 | pydantic-settings 用对，API key 默认 sk- + 缺非空校验 |
| 性能 | 8 | 当前规模无问题，限流数据结构有优化空间，P4 流式需重构 |

---

## 综合评价

P0–P2 阶段质量相当不错的 TDD 项目。文档-领域-计划-交接四件套完整，测试全绿，占位与正式实现边界清晰。主要风险集中在静默降级链路、安全组件未接线、限流维度不全三处。建议 P3 第一个 PR 修复 3 个严重问题 + 接线 input_filter 后再扩功能。