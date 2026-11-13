# SmartCart 本地免费模型评测汇总

评测日期：2026-11-12（Asia/Shanghai）

## 评测环境

- 聊天模型：`mindbridge-qwen2.5-7b-ft:latest`，Q4_K_M，7.6B，本地 llama.cpp，16K 运行窗口。
- 向量模型：`embeddinggemma:latest`，768 维，本地 Ollama。
- SmartCart 持久配置未改写；评测进程使用临时环境变量覆盖模型端点。
- 正式配置仍为 `qwen3.8-max`、`qwen-plus`、`text-embedding-v4`（1024 维）。
- 本报告是本地模型诊断，不代表正式 API 模型的生产效果。

## 结果

| 项目 | 结果 | 结论 |
|---|---:|---|
| 后端完整测试集 | 2150 通过，6 失败，45 跳过，共 2201 条 | 5 条失败为 Windows 缺少创建符号链接权限；1 条为跨平台同款重复率断言真实失败 |
| Harness 安全契约 | 843/848 通过 | 同一组 5 条符号链接权限失败；整体仍按未通过记录 |
| 前端测试 | 249/249 通过，19/19 文件通过 | 通过 |
| 前端生产构建 | 625 模块转换，构建成功 | 通过 |
| Agent 本地模型冒烟 | 0/12 通过 | 12 条均约 45 秒超时，本地 7B 模型不能完成当前完整工具提示与上下文 |
| 长期偏好提炼 | 1/12 通过（8.3%） | 多数无法形成项目要求的结构化事实；另有 1 条偏好极性错误 |
| 关键词检索 | NDCG@5 0.8936；Recall@5 0.9219；Precision 0.4125；P95 136.99 ms | 72 条离线诊断 |
| BM25 检索 | NDCG@5 0.8549；Recall@5 0.9271；Precision 0.4156；P95 80.24 ms | Recall +0.52 个百分点，Precision +0.31 个百分点，NDCG -3.87 个百分点，P95 -41.43% |
| 检索硬约束 | 预算/配送违规 0；材质约束无覆盖样本 | 已覆盖部分未发现违规，不能声称材质门禁通过 |

## 真实失败复核

`tests/test_eval_product_runner.py::test_formal_runner_scores_cross_platform_duplicates_by_canonical_entity`
单独复测仍失败：实际 `canonical_duplicate_rate=0.0`，测试期望 `0.5`。该失败不依赖聊天模型或 Embedding 配置，需要后续判断是评测器口径过时，还是检索提前去重导致指标观测缺失；本轮只诊断，不修改业务代码。

## 当前不能证明的简历指标

- “复杂任务 RT 降低 65%”：缺少单 Agent 同模型同数据基线；本地模型冒烟全部超时。
- “10+ 轮 Token 降低 30%”：模型请求没有成功结算 usage，不能计算真实 Token 降幅。
- “任务完成率 71% 提升到 89%”：当前没有对应旧版本基线，本地冒烟为 0/12。
- “长期记忆命中率 72%”：本轮测的是偏好提炼正确性，不是召回命中率；提炼仅 1/12。
- “向量召回提升 22%”：本轮未重建正式向量主链；离线 BM25 的 NDCG 反而下降 3.87 个百分点。
- “badcase 排查 30 分钟缩短到 5 分钟”：需要人员操作计时或历史工单日志。
- “AG-UI 重复提交率 0%”：需要真实用户行为日志；单元测试通过不能替代线上重复提交率。

## 证据

- `full-tests.xml`、`full-tests.log`：后端完整测试集。
- `canonical-duplicate-recheck.xml`、`canonical-duplicate-recheck.log`：真实失败单条复测。
- `harness-contracts/report.html`：Harness 安全契约。
- `harness-smoke/report.html`：本地聊天模型冒烟。
- `memory/extraction.json`：长期偏好提炼结果。
- `retrieval/keyword/report.json`：关键词检索报告。
- `retrieval/bm25/report.json`：BM25 检索报告。
- `retrieval/comparison.json`：关键词与 BM25 对照。
- `frontend-tests.log`、`frontend-build.log`：前端测试与构建。

