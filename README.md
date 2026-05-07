# CUA-Lark — 纯视觉飞书 Computer-Use Agent 测试框架

让 VLM 像真人测试者一样操作飞书桌面端：**截图 → 理解 → 决策 → 执行 → 再截图**。不依赖 DOM、Accessibility Tree 或硬编码坐标，仅通过纯视觉理解 UI。

## 为什么需要它？

飞书桌面端使用自研渲染引擎，传统 XPath/选择器定位完全失效；UI 频繁迭代导致测试脚本维护成本爆炸；接口级测试无法验证真实 UI 渲染结果。

CUA-Lark 通过 VLM 驱动 GUI 自动化，**将"写定位脚本"变为"写自然语言指令"**，用例编写从 30 分钟缩短到 1 分钟，且 UI 变更时无需维护。

## 快速开始

```bash
# 安装
pip install pyautogui pillow openai pyyaml gradio

# 配置（复制模板并填入 API Key）
cp configs/config.example.yaml configs/config.yaml

# 启动 Web 控制台
python -m cua_lark.web
# 访问 http://127.0.0.1:7860，输入自然语言指令即可运行

# 或 CLI 运行
python scripts/run_test.py --stage im_basic_send --max-steps 12
```

## 核心亮点

| 亮点 | 说明 |
|------|------|
| 🎯 **多目标 Batch 执行** | VLM 单轮推理识别多个不依赖的目标，输出 JSON 子操作数组一次执行。发送一条消息从"定位→输入→发送"3 步压缩为 1 步 |
| 🧠 **三层 VLM 角色分离** | 执行决策（thinking=enabled, 2048t）→ 规则选择（512t）→ 坐标校验（thinking=disabled），按认知复杂度分配推理资源 |
| 🎯 **Goal Contract** | Rule Selector 生成包含 Goal/CompletionEvidence/NonCompletionEvidence/MustNot 的目标合约，确保 VLM 准确判断任务何时完成 |
| 🔍 **强制 Grounding** | 每步必须输出 `target + bbox + point + confidence + evidence` 五元组，杜绝 VLM 幻觉坐标 |
| 🛡️ **安全守卫** | Grounding Check 二次坐标校验 + 动作策略限制 + Docs 浏览器安全边界 + 子操作间中止检查 |
| 📊 **进程质量评估** | 15+ 种问题模式自动检测（@但没点@按钮、编辑点错区域等），blocking warnings 翻转 PASSED→FAILED |
| 📝 **完整证据链** | 每步增量写盘 record.json（含完整 VLM prompt/输出/截图/耗时），支持完整回溯 |
| 🖥️ **双入口** | CLI 批量运行 + Gradio Web 控制台（含 Toast 通知 + 彩色结果横幅 + 任务中止） |

## 架构

```
入口层（CLI / Gradio Web）
  │
  ▼
CaseRunner 主循环（每步迭代）:
  截图 → Rule Selector(VLM #1) 选规则+Goal Contract
  → 构建 Prompt → VLM #2 推理 → 解析 Action+坐标转换
  → Grounding Check(VLM #3) → GUI 执行 → 截图 → 增量写盘
  │
  ├── Screen（窗口捕获/激活）
  ├── VLM（OpenAI-compatible，三角色差异化参数）
  ├── GUI（pyautogui 鼠标/键盘）
  ├── Rule Modules（20 个 .md 规则文件，按需加载）
  └── Reporting（record.json/steps.md/flow.md/summary.json）
```

**VLM 决策流程**（System Prompt 注入的伪代码控制流）：

```
observe(screenshot) → judge_goal(Goal Contract) → if satisfied: finished
  → else: intent → grounding(target+bbox+point+confidence+evidence) → action → expected
```

## 支持的飞书产品

| Product | 执行环境 | 用例数 | 典型 stage |
|---------|---------|--------|-----------|
| IM | 飞书桌面端 | 25 个 | basic_send, message_ops, conversation_ops, attachment_share |
| Docs | 浏览器 | 9 个 | docs_create, docs_edit, docs_structure, docs_share |
| Calendar | 飞书桌面端 | 演示用例 | - |
| Mail | 飞书桌面端 | 演示用例 | - |

## 项目结构

```
cua_lark/
├── cli.py                       # CLI 入口
├── domain/                      # Action/TestCase/StepResult 模型 + 动作解析 + 坐标映射
├── adapters/                    # Screen/VLM/GUI 适配器（Protocol 接口，可替换）
├── testing/                     # Runner/Prompt/RuleSelector/Quality/Grounding
├── rules/                       # 20 个领域规则模块（im_chat/docs_body_edit...）
├── scenarios/                   # 场景 Prompt（system/im/docs/general）
├── reporting/                   # writer.py：增量写 record.json/steps.md/flow.md
├── web/                         # Gradio Web 控制台
└── runtime/                     # 配置加载
scripts/run_test.py              # CLI 入口
tests/test_cases/                # YAML 用例
configs/config.example.yaml      # 配置模板
```

## 运行示例

```bash
# IM 消息发送
python scripts/run_test.py --stage im_basic_send --max-steps 12

# Docs 创建
python scripts/run_test.py --cases tests/test_cases/phase2-docs.yaml \
  --stage docs_create --max-steps 14 --grounding-check --prefer-browser-docs

# 全屏截图
python scripts/run_test.py --stage im_basic_send --capture full

# 固定规则模块
python scripts/run_test.py --stage im_basic_send \
  --rule-selection static --rules im_chat,composer,feishu_shell

# 空跑调试（不操作 GUI）
python scripts/run_test.py --case IM-P2-001 --dry-run \
  --static-screen screen.png --dry-run-response "Action: finished()"
```

## CLI 主要参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--stage ID` | 运行指定 test_stage | - |
| `--cases PATH` | YAML 用例文件 | `tests/test_cases/phase2-im.yaml` |
| `--max-steps N` | 每用例最大步数 | `12` |
| `--capture {app,full}` | 截图范围 | `app` |
| `--grounding-check` | 坐标二次校验 | 关闭 |
| `--rule-selection {static,vlm}` | 规则选择模式 | `vlm` |
| `--bare-user-prompt` | prompt 不含规则（仅任务+历史） | 关闭 |
| `--dry-run` | 空跑（不操作 GUI） | 关闭 |
| `--skip-setup` | 跳过前置步骤 | 关闭 |
| `--prefer-browser-docs` | Docs 优先截浏览器 | 关闭 |

完整参数见 `python scripts/run_test.py --help`。

## 用例编写

```yaml
test_cases:
  - id: IM-P2-001
    product: IM
    name: 发送普通文本
    instruction: 给孙浩翔发送消息"CUA-Lark 测试"
    expected: 与孙浩翔的聊天记录中出现指定消息
    allowed_actions: [click, type_text, hotkey, wait, scroll]
    verification:
      method: final_visual_semantic
      assertion: 孙浩翔聊天窗口中出现指定消息
```

**关键原则**：`instruction` 用自然语言描述用户目标，不写定位提示（"右上角"、"点击 X 按钮"），不写验证用语（"确认"、"验证"）。预期结果放在 `expected` 和 `verification.assertion` 中。

## 配置

复制 `configs/config.example.yaml` 为 `config.yaml`，填入 VLM API Key：

```yaml
vlm:
  default_backend: "seed-2.0"
  seed_2_0:
    api_key: "your-api-key"
    base_url: "https://ark.cn-beijing.volces.com/api/v3"
    model: "your-model-id"
  call_profiles:              # 按角色分配推理资源
    rule_selection: {max_tokens: 512}
    grounding_check: {thinking: {type: "disabled"}, max_tokens: 512}
```

支持任何 OpenAI 兼容接口的 VLM。

## 测试结果

每次运行在 `results/<round>-<timestamp>/` 下生成：

```
cases/<case-id>__<case-name>/
├── record.json       # 每步完整记录（prompt/输出/截图/grounding/耗时）
├── steps.md          # 人类可读步骤时间线
├── flow.md           # Mermaid 流程图
├── 01-before.png     # 每步操作前/后截图
└── final.png         # 最终状态
```

每步结束后增量写盘，崩溃不丢数据。

## 扩展

- **新 VLM**：实现 `VisionModel.complete(image, prompt, system_prompt)` 协议
- **新平台 GUI**：实现 `Gui.execute(Action)` 协议
- **新规则**：`cua_lark/rules/` 下新增 `.md`，在 `index.md` 注册
- **新场景**：`cua_lark/scenarios/` 下新增 `.md`，按 product 自动匹配
- **新产品**：Web UI product dropdown 加选项，配场景和规则即可
