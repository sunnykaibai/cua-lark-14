# CUA-Lark — 纯视觉飞书 Computer-Use Agent 测试框架

CUA-Lark 是一个**纯视觉**的飞书/Lark GUI 自动化测试框架。它通过 **VLM（视觉语言模型）** 观察屏幕截图、理解自然语言任务指令，自主执行 GUI 操作并完成端到端测试。Agent 像真人测试者一样：看屏幕 → 决定下一步操作 → 执行动作 → 再看屏幕 → 直到任务完成。

## 目录

- [核心设计理念](#核心设计理念)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [运行方式](#运行方式)
  - [CLI 命令行](#cli-命令行)
  - [Web 前端（Gradio）](#web-前端gradio)
- [架构详解](#架构详解)
  - [执行链路](#执行链路)
  - [产品路由 (Product)](#产品路由-product)
  - [规则选择器 (Rule Selector)](#规则选择器-rule-selector)
  - [动作策略 (Action Policy)](#动作策略-action-policy)
- [用例编写](#用例编写)
- [配置参考](#配置参考)
- [场景与规则系统](#场景与规则系统)
- [测试结果](#测试结果)
- [优化与消融 (Ablation)](#优化与消融-ablation)
- [与旧工程的对应关系](#与旧工程的对应关系)

## 核心设计理念

- **纯视觉 (Pure Vision)**：Agent 仅通过截图理解 UI 状态，不依赖 DOM、Accessibility Tree、API 或硬编码坐标
- **VLM 自主决策**：每一步操作由 VLM 基于当前截图和历史自主选择，不使用语义 guard 或脚本化兜底
- **用户视角**：测试指令是自然语言用户需求（如"给孙浩翔发消息"），不是内部操作步骤
- **关注点分离**：`instruction`/`expected`/`verification` 严格分离 — VLM 执行时只看 instruction，expected 留给最终验证
- **归一化动作路径**：所有 GUI 操作统一经过 `Action` 对象 → 坐标转换 → 执行 → 截图 → 记录

## 快速开始

### 环境要求

- macOS（GUI 自动化依赖 AppleScript + pyautogui）
- Python 3.11+
- 飞书/Lark 桌面客户端已安装并登录
- VLM API Key（支持 OpenAI 兼容接口）

### 安装

```bash
cd /Users/sunny/Downloads/final
pip install pyautogui pillow openai pyyaml gradio
```

### 配置 VLM

编辑 `configs/config.yaml`，填入 VLM 的 API Key 和模型信息：

```yaml
vlm:
  default_backend: "seed-2.0"
  seed_2_0:
    api_key: "your-api-key"
    base_url: "https://ark.cn-beijing.volces.com/api/v3"
    model: "your-model-id"
```

### 运行第一个测试

```bash
# Web 前端 — 最简单的方式
python -m cua_lark.web

# CLI 方式 — 运行 IM 基础发送用例
python scripts/run_test.py \
  --round demo-send \
  --cases tests/test_cases/phase2-im.yaml \
  --stage im_basic_send \
  --max-steps 12
```

## 项目结构

```text
00-new_construction/                  # 当前主工作区 (NEW_ROOT)
├── scripts/run_test.py              # 唯一 CLI 测试入口
├── configs/config.yaml              # VLM / 截图 / 执行参数配置
├── AGENTS.md                        # AI Agent 开发规则
│
├── cua_lark/                        # 核心代码包
│   ├── cli.py                       # CLI 参数解析、依赖装配、轮次创建
│   │
│   ├── domain/                      # 领域模型
│   │   ├── models.py                # TestCase / Action / StepResult / CaseResult / Status / ActionKind
│   │   ├── action_parser.py         # VLM 文本输出 → Action 对象解析 + 0-1000 坐标映射
│   │   └── coordinates.py           # 截图坐标 → 真实屏幕坐标、窗口边界检测
│   │
│   ├── adapters/                    # 外部适配器
│   │   ├── screen.py                # 截图、窗口捕获、视觉变化检测、截图画布标注
│   │   ├── vlm.py                   # OpenAI 兼容 VLM 客户端 (chat/completions)
│   │   └── gui.py                   # pyautogui 执行器 + 空跑(DryRun)执行器
│   │
│   ├── testing/                     # 测试核心
│   │   ├── runner.py                # CaseRunner: 主循环、VLM 调用、动作执行、最终验证
│   │   ├── cases.py                 # YAML 用例加载、stage 过滤、产品推断
│   │   ├── prompt.py                # 执行/设置/验证 prompt 构建、产品协议注入
│   │   ├── action_policy.py         # 按产品限制允许的动作类型
│   │   ├── rule_selector.py         # VLM 驱动的规则模块选择器
│   │   ├── rules.py                 # 规则模块加载、渲染、哈希
│   │   ├── process_quality.py       # 执行过程质量检查
│   │   ├── grounding_check.py       # 点击坐标安全校验
│   │   ├── observation.py           # 视觉变化解读
│   │   ├── lark_cli_verify.py       # 飞书 CLI 辅助验证
│   │   ├── run_context.py           # 测试轮次目录创建
│   │   └── setup.py                 # 前置 setup 步骤 prompt 构建
│   │
│   ├── scenarios/                   # 场景 Prompt 模板
│   │   ├── system.md                # 通用系统 Prompt
│   │   ├── general.md               # 通用桌面 GUI 场景规则
│   │   ├── im.md                    # IM 场景专用规则
│   │   ├── docs.md                  # Docs 场景专用规则
│   │   └── rule_selector.md         # Rule Selector 的 prompt 模板
│   │
│   ├── rules/                       # 操作规则模块 (VLM 运行时加载)
│   │   ├── index.md                 # 规则索引 (供 Rule Selector 使用)
│   │   ├── feishu_shell.md          # 飞书桌面外壳/窗口管理
│   │   ├── live_object.md           # 区分真实 UI vs 截图/卡片里的对象
│   │   ├── im_chat.md               # 聊天气泡操作
│   │   ├── composer.md              # 文本输入框状态
│   │   ├── mention_picker.md        # @提及选择器
│   │   ├── message_operations.md    # 消息级操作 (回复/标记/表情)
│   │   ├── conversation_ops.md      # 会话级操作
│   │   ├── emoji_picker.md          # 表情选择器
│   │   ├── attachment_share.md      # 附件/分享
│   │   ├── rich_text.md             # 富文本输入
│   │   ├── search_find.md           # 搜索/查找
│   │   ├── screenshot_overlay.md    # 截图覆盖层
│   │   ├── docs_shell.md            # Docs 外壳/浏览器
│   │   ├── docs_body_edit.md        # Docs 正文编辑
│   │   ├── docs_structure.md        # Docs 结构 (标题/列表/表格/分割线)
│   │   ├── docs_search_navigation.md # Docs 搜索/导航
│   │   ├── docs_format_link.md      # Docs 格式化/链接
│   │   ├── docs_exact_span.md       # Docs 精确文本定位
│   │   ├── docs_share_permission.md # Docs 分享/权限
│   │   └── docs_local_material.md   # Docs 本地素材导入
│   │
│   ├── reporting/                   # 报告生成
│   │   └── writer.py                # summary.json / README.md / record.json / steps.md / flow.md
│   │
│   ├── web/                         # Gradio Web 前端
│   │   ├── __init__.py
│   │   ├── __main__.py              # 启动入口: python -m cua_lark.web
│   │   └── app.py                   # UI 布局、事件处理、结果展示
│   │
│   └── runtime/
│       └── config.py                # 工作区路径解析、配置加载
│
├── tests/test_cases/                # YAML 测试用例
│   ├── phase2-im.yaml               # Phase 2 IM 用例
│   ├── phase2-docs.yaml             # Phase 2 Docs 用例
│   ├── im_e2e.yaml                  # IM 端到端用例
│   ├── docs-demo-e2e.yaml           # Docs 端到端演示
│   ├── cal-mail-demo-e2e.yaml       # 日历/邮箱演示
│   └── ...                          # 更多用例
│
├── results/                         # 测试结果归档 (按轮次)
├── ablation/                        # 优化消融记录
└── work_dairy/                      # 工作记录/设计文档
```

## 运行方式

### CLI 命令行

```bash
python scripts/run_test.py [选项]
```

#### 全部 CLI 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--cases PATH` | YAML 用例文件路径 | `tests/test_cases/phase2-im.yaml` |
| `--case ID` | 运行指定 case id（可多次指定） | - |
| `--stage ID` | 运行指定 test_stage（可多次指定） | - |
| `--round NAME` | 本轮测试名称 | `round` |
| `--suite NAME` | 报告中的套件名 | `cua-lark` |
| `--max-steps N` | 每个 case 最大执行步数 | `12` |
| `--capture {app,full}` | 截图来源（app=应用窗口，full=全屏） | `app` |
| `--backend NAME` | VLM 后端覆盖 | - |
| `--scenario PATH` | 场景 prompt 文件（遗留，推荐 --system-prompt） | - |
| `--system-prompt PATH` | 系统 prompt 文件 | `scenarios/system.md` |
| `--grounding-check` | 对高风险点击坐标做二次校验 | `False` |
| `--grounding-check-mode {high-risk,all}` | 坐标检查范围 | `high-risk` |
| `--rules MODULES` | 逗号分隔的起始规则模块（`auto`=自动选） | - |
| `--rule-selection {static,vlm}` | 规则选择模式（静态固定 vs VLM 动态选） | `vlm` |
| `--no-default-rules` | 禁用默认起始规则 | `False` |
| `--bare-user-prompt` | 执行 prompt 只含任务/历史，不含规则 | `False` |
| `--enable-docs-batch` | 允许 Docs 用例使用 batch 动作 | `False` |
| `--skip-setup` | 跳过 setup_instruction 前置步骤 | `False` |
| `--no-activate-feishu-host` | 不自动激活飞书客户端 | `False` |
| `--hybrid-locator` | 用 Accessibility 候选点精炼点击坐标 | `False` |
| `--prefer-browser-docs` | Docs 用例优先截取浏览器窗口 | `False` |
| `--dry-run` | 空跑模式（不操作 GUI） | `False` |
| `--dry-run-response TEXT` | 空跑模式下 VLM 的伪响应 | - |
| `--static-screen PATH` | 空跑模式使用的静态截图 | - |
| `--config PATH` | 自定义配置文件路径 | `configs/config.yaml` |

#### 运行示例

```bash
# IM 基础发送（最常用）
python scripts/run_test.py \
  --round 0507-demo-im \
  --cases tests/test_cases/phase2-im.yaml \
  --stage im_basic_send \
  --max-steps 12

# Docs 用例
python scripts/run_test.py \
  --round 0507-demo-docs \
  --cases tests/test_cases/phase2-docs.yaml \
  --stage docs_create \
  --max-steps 14 \
  --grounding-check \
  --prefer-browser-docs

# 全屏截图模式
python scripts/run_test.py \
  --round 0507-full-screen \
  --stage im_basic_send \
  --capture full

# 空跑（不操作 GUI，用静态截图）
python scripts/run_test.py \
  --round 0507-dry-run \
  --case IM-P2-001 \
  --dry-run \
  --static-screen /path/to/screenshot.png \
  --dry-run-response "Action: finished(content='done')"

# 固定规则（不启用 VLM 动态规则选择）
python scripts/run_test.py \
  --round 0507-static-rules \
  --stage im_basic_send \
  --rule-selection static \
  --rules im_chat,composer,feishu_shell

# 运行特定 case id
python scripts/run_test.py \
  --round 0507-specific \
  --cases tests/test_cases/phase2-im.yaml \
  --case IM-P2-001 \
  --case IM-P2-005

# 日历/邮箱用例
python scripts/run_test.py \
  --round 0507-calendar \
  --cases tests/test_cases/cal-mail-demo-e2e.yaml \
  --max-steps 14
```

### Web 前端（Gradio）

启动 Web 控制台，通过浏览器界面交互式运行测试：

```bash
python -m cua_lark.web
```

访问 `http://127.0.0.1:7860`

#### Web 前端功能

| Tab | 功能 |
|-----|------|
| ✏️ **指令输入** | 输入自然语言指令和预期结果，选择产品（IM/Docs/Calendar/Mail），一键运行 |
| 📋 **用例选择** | 从已有 YAML 用例文件中按 stage 筛选并批量运行 |
| ⚙️ **配置** | 查看当前 config.yaml 配置和场景规则 |
| 📊 **结果浏览** | 浏览历史测试结果、查看步骤和截图 |

#### 任务完成通知

测试完成后，Web 前端会通过两种方式提示用户：

1. **Toast 弹窗** — 页面顶部弹出，显示通过/失败状态
   - ✅ 绿色：全部通过
   - ⚠️ 黄色：部分通过或全部失败
2. **彩色横幅** — 结果区顶部 HTML 横幅，永久可见
   - 绿色渐变：测试通过
   - 红色渐变：测试失败
   - 橙色渐变：测试阻塞

## 架构详解

### 执行链路

```
用户指令 (YAML / Web UI)
    │
    ▼
┌──────────────────────────────────────────────────────┐
│  CaseRunner.run(case)                                │
│                                                      │
│  1. _activate_feishu_host_for_case(case)             │  ← 根据 product 激活环境
│  2. 执行 setup_instruction（如有）                    │
│  3. 进入主循环 (for step in range(max_steps)):       │
│     ┌─────────────────────────────────────────┐      │
│     │ a. 截图 → NN-before.png                 │      │
│     │ b. Rule Selector 选择规则模块           │      │  ← VLM 动态选规则
│     │ c. 构建执行 Prompt                      │      │
│     │ d. VLM 推理 → 返回 Action                │      │
│     │ e. 解析 Action / 坐标转换                │      │
│     │ f. Grounding Check（可选）               │      │  ← 坐标安全检查
│     │ g. GUI 执行动作                          │      │
│     │ h. 截图 → NN-after.png                  │      │
│     │ i. 记录视觉变化                          │      │
│     │ j. 写 record.json / steps.md            │      │
│     └─────────────────────────────────────────┘      │
│  4. Final Verify（可选）                             │
│  5. 进程质量评估                                     │
│                                                      │
│  输出: CaseResult(screenshot, steps, status, ...)    │
└──────────────────────────────────────────────────────┘
```

每一步的详细记录（VLM prompt/输出/截图/规则选择/grounding check）都写入 `record.json` 和 `steps.md`，支持完整回溯。

### 产品路由 (Product)

`product` 字段是测试用例的**场景路由开关**，它告诉系统当前任务属于飞书的哪个产品模块：

| product | 描述 | 执行环境 | 典型动作 |
|---------|------|---------|----------|
| `IM` | 即时通讯 | 飞书桌面客户端 | 发送消息/表情/文件、回复、@提及 |
| `Docs` | 飞书云文档 | 浏览器（feishu.cn） | 创建文档、编辑正文、插入结构、分享 |
| `Calendar` | 日历 | 飞书桌面客户端 | 查看日程、创建日程 |
| `Mail` | 邮箱 | 飞书桌面客户端 | 查看/发送邮件 |

**product 的影响范围**：

1. **环境激活** — `Docs` 在浏览器中运行，不激活飞书桌面端；`IM`/`Calendar`/`Mail` 激活飞书客户端
2. **系统 Prompt** — 加载对应的场景 Prompt（`scenarios/im.md`、`scenarios/docs.md`）
3. **导航协议** — 对于非 IM/Docs 的产品，生成导航到目标模块的指令
4. **动作策略** — 不同产品限制不同的可用动作集合（如 Docs 不能拖拽）
5. **安全守卫** — Docs 用例拦截对浏览器标签页/macOS 菜单栏/Dock 的点击
6. **规则模块** — Docs 自动包含 `docs_shell` 和 `live_object` 模块

### 规则选择器 (Rule Selector)

Rule Selector 是一个**VLM 驱动的规则模块选择器**，在执行第一步调用。它根据当前截图、任务指令和历史，从规则索引中选出 2-5 个最相关的操作规则模块。

**为什么需要 Rule Selector？** 共有 20 个规则模块，全部注入会超出 VLM 上下文窗口。Rule Selector 确保只加载当前任务需要的规则。

**工作流程**：

```
截 图 + 指令 + 规则索引
    │
    ▼
VLM (Rule Selection Prompt)
    │
    ▼
输出: RuleNeeds: ["im_chat", "composer", "feishu_shell"]
      Goal: 在孙浩翔聊天窗口中出现指定消息
      CompletionEvidence: ["孙浩翔聊天窗口中最新消息..."]
      NonCompletionEvidence: ["输入框中仍有未发送的内容"]
      MustNot: ["不要重复发送已有消息"]
    │
    ▼
加载对应 .md 规则模块 → 注入执行 Prompt
```

规则索引详见 [cua_lark/rules/index.md](file:///Users/sunny/Downloads/final/cua_lark/rules/index.md)。

### 动作策略 (Action Policy)

`action_policy.py` 根据 `product` 字段自动推断允许的动作类型：

| Product | 允许的动作 |
|---------|-----------|
| `docs` | click, type_text, hotkey, wait, scroll, batch（可选 drag/right_click） |
| `im` | click, type_text, hotkey, wait, scroll, drag, right_click |
| `calendar/mail/base/vc` | 所有动作（无限制） |
| 未知 | click, type_text, hotkey, wait, scroll |

YAML 用例中的 `allowed_actions` 字段会与推断结果合并，提供更细粒度的控制。

## 用例编写

### YAML 格式

```yaml
test_stages:
  - id: im_basic_send
    order: 1
    name: 基础发送
    description: 短信/链接/多行/表情发送验证
    cases: [IM-P2-001, IM-P2-002, IM-P2-003]

test_cases:
  - id: IM-P2-001
    phase: phase-2
    test_stage: im_basic_send
    product: IM
    name: 发送普通文本给孙浩翔
    instruction: 给孙浩翔发送消息"CUA-Lark Phase2 测试"
    expected: 与孙浩翔的聊天记录中出现指定消息
    allowed_actions: [click, type_text, hotkey, wait, scroll]
    verification:
      method: final_visual_semantic
      assertion: 孙浩翔聊天窗口中出现指定消息
    setup_instruction: 确保飞书已打开并显示消息列表
    setup_expected: 显示飞书消息列表界面
    setup_max_steps: 6
```

### 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | ✅ | 用例唯一标识，建议用有意义前缀 |
| `name` | ✅ | 用例名称，用于报告显示 |
| `instruction` | ✅ | 自然语言用户指令，**不写UI方位提示** |
| `expected` | ✅ | 预期结果自然语言描述 |
| `product` | - | 产品类型 (IM/Docs/Calendar/Mail)，不填则自动推断 |
| `test_stage` | - | 所属测试阶段 id |
| `phase` | - | 测试阶段标识 |
| `allowed_actions` | - | 显式允许的动作列表 |
| `verification.method` | - | 验证方法 (final_visual_semantic) |
| `verification.assertion` | - | 验证断言文本 |
| `setup_instruction` | - | 前置环境准备指令 |
| `setup_expected` | - | 前置环境预期状态 |
| `setup_max_steps` | - | 前置步骤最大步数 (默认 6) |
| `input_materials` | - | 输入素材列表 (label/content) |

### instruction 编写原则

1. 用真实用户的自然语言描述目标，不写操作步骤
2. 不写方位提示（如"右上角"、"左侧列表"、"点击 X 按钮"）
3. 不写验证用语（如"确认"、"验证"、"判定通过"）
4. 不要用拍照/screenshot 里的文字做目标（VLM 需要操作真实 UI，不是图片里的 UI）

## 配置参考

配置文件位于 `configs/config.yaml`：

```yaml
# VLM 配置
vlm:
  default_backend: "seed-2.0"      # 默认 VLM 后端
  seed_2_0:                         # Seed 2.0 模型配置
    api_key: "your-key"
    base_url: "https://..."
    model: "your-model-id"
    temperature: 1.0
    top_p: 0.95
    max_tokens: 2048
    thinking:
      type: "enabled"
    reasoning_effort: "medium"
  call_profiles:                    # 不同调用场景的 VLM 参数覆盖
    rule_selection:
      thinking: {type: "enabled"}
      max_tokens: 512
    grounding_check:
      thinking: {type: "disabled"}
      max_tokens: 512

# 操作执行配置
executor:
  operation_delay: 0.8             # 操作后等待 (秒)
  mouse_move_duration: 0.2         # 鼠标移动耗时 (秒)
  type_interval: 0.05              # 字符输入间隔 (秒)
  screen_edge_padding: 4           # 屏幕边缘安全像素
  dock_activation_margin: 18       # macOS Dock 安全距离

# 截图配置
screenshot:
  save_to_disk: true
  format: "png"
  prefer_app_window: true           # 优先截取应用窗口
  app_names: ["飞书", "Feishu", "Lark"]
  browser_app_names: ["Safari", "Google Chrome", "Arc"]
  browser_title_keywords: ["feishu.cn", "larksuite.com", "飞书云文档"]
  recovery_attempts: 2             # 窗口找回重试次数
```

## 场景与规则系统

### 场景 (Scenarios)

场景文件定义产品级的操作约定和背景知识，位于 `cua_lark/scenarios/`：

- **system.md** — 通用系统 Prompt，定义动作格式、坐标系统、基本规则
- **general.md** — 通用桌面 GUI 操作规则
- **im.md** — IM 场景专用规则
- **docs.md** — Docs 场景专用规则

场景文件按 `product` 字段自动加载（如 `product: "IM"` → 加载 `im.md`）。

### 规则模块 (Rules)

规则模块是更细粒度的操作规范，位于 `cua_lark/rules/`，共 20 个：

| 分类 | 模块 | 说明 |
|------|------|------|
| 通用 | `feishu_shell` | 飞书桌面窗口管理 |
| 通用 | `live_object` | 区分真实 UI 对象 vs 截图内对象 |
| 通用 | `search_find` | 搜索/查找通用流程 |
| 通用 | `screenshot_overlay` | 截图工具条/覆盖层处理 |
| IM | `im_chat` | 聊天气泡、消息定位 |
| IM | `composer` | 输入框状态、发送 |
| IM | `mention_picker` | @ 提及 UI |
| IM | `message_operations` | 回复、标记、表情反应 |
| IM | `conversation_ops` | 会话列表操作 |
| IM | `emoji_picker` | 表情选择器 |
| IM | `attachment_share` | 附件上传、分享弹窗 |
| IM | `rich_text` | 富文本消息 |
| Docs | `docs_shell` | Docs 外壳、浏览器切换 |
| Docs | `docs_body_edit` | 正文编辑、文本插入 |
| Docs | `docs_structure` | 标题、列表、表格、分割线 |
| Docs | `docs_search_navigation` | 文档内搜索、目录导航 |
| Docs | `docs_format_link` | 格式化、链接创建 |
| Docs | `docs_exact_span` | 精确文本区间定位 |
| Docs | `docs_share_permission` | 分享弹窗、权限 |
| Docs | `docs_local_material` | 本地 Markdown/文本导入 |

## 测试结果

每次运行自动创建独立结果目录：

```text
results/<round-name>-<YYYYMMDD-HHMMSS>/
├── README.md          # 总览：通过率、Case Matrix、失败详情
├── summary.json       # 机器可读汇总
└── cases/
    └── <case-id>__<case-name>/
        ├── record.json        # 完整执行记录（每一步的 prompt/输出/截图/规则/grounding check）
        ├── steps.md           # 人类可读步骤时间线
        ├── flow.md            # 执行流摘要
        ├── 01-before.png      # 每步操作前截图
        ├── 01-after.png       # 每步操作后截图
        ├── 01-grounding.png   # 标注截图（grounding check）
        ├── 02-before.png
        └── final.png          # 最终状态截图
```

### 关键文件说明

| 文件 | 用途 |
|------|------|
| `summary.json` | 汇总统计：总数/通过/失败/成功率/耗时/grounding check 统计 |
| `README.md` | 人类 review 入口：Case Matrix 表格 + 每个 case 的状态 |
| `record.json` | 完整机器记录，包含每步的 VLM prompt、原始输出、规则选择、grounding check |
| `steps.md` | 每步的 Markdown 时间线，包含动作/目标/思路/截图路径 |
| `flow.md` | 执行流程摘要 |

用于优化对比的轮次必须以 `MMDD-HHMM` 开头（如 `0507-1510-fix-grounding`），和 `ablation/` 中的记录保持同一时间线。

## 优化与消融 (Ablation)

每个重要优化都应和 baseline 做指标对照。消融记录位于 `ablation/` 目录：

```text
ablation/
├── README.md
└── MM-DD/
    └── MMDD-HHMM-<优化名称>.md
```

每条消融记录应包含：
- 优化变量描述
- 对比命令
- 对比轮次路径
- 通过率/耗时等关键指标
- 是否保留该优化的结论

优化相关的测试轮次也应以 `MMDD-HHMM` 开头，方便自然排序和按时间线 review。

## 与旧工程的对应关系

`cua-lark-14` 已作为历史版本封存，不再接收新功能。

| 旧位置 | 新位置 | 变化 |
|--------|--------|------|
| `scripts/run_test.py` + `scripts/run_phase2_stepwise.py` | `scripts/run_test.py` | 入口合并 |
| `src/runner/*` | `testing/runner.py`, `reporting/writer.py` | 运行和报告拆开 |
| `src/core/action_schema.py` | `domain/action_parser.py`, `domain/models.py` | 动作模型与解析更短 |
| `src/perception/vlm_client.py` | `adapters/vlm.py` | 只保留 OpenAI 兼容调用 |
| `src/executor/actions.py` | `adapters/gui.py` | 执行器只接收标准 Action |
| `outputs/phase-*`, `logs/runs` | `results/<round-time>` | 结果按轮次归档 |

## 后续扩展指南

- **新场景**：在 `cua_lark/scenarios/` 下新增 `.md` 文件，运行时传 `--system-prompt` 或通过 product 自动匹配
- **新规则模块**：在 `cua_lark/rules/` 下新增 `.md`，并在 `index.md` 中注册
- **新用例**：在 `tests/test_cases/` 下新增 YAML 文件，遵循现有格式
- **新执行器**：实现 `Gui.execute(Action)` 协议
- **新 VLM 模型**：实现 `VisionModel.complete(image, prompt, system_prompt)` 协议
