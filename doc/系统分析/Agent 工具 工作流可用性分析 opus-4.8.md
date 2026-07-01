# Agent / 工具 / 工作流 三大功能可用性分析

> 分析日期：2026-06-28
> 范围：前端 `frontend/src/**` 交互层 + 对应后端 API 能力边界
> 结论：基于源码逐行核实

---

## 总体病根

三个功能「都差点意思」的共同原因是同一个——**前端只做了「列表 + 基础表单壳子」，把真正决定可用性的那层交互全省略了**：

| 功能 | 看起来有 | 实际缺的关键交互 |
|---|---|---|
| Agent 添加 | 完整表单 | ❌ 工具绑定、❌ provider/model 下拉、❌ 错误提示、❌ 试聊 |
| 工具注册 | 列表+tab | ❌ 注册表单（按钮是死的）、❌ 测试（按钮是死的） |
| 工作流编辑 | 画布拖拽 | ❌ 节点配置面板、❌ 条件编辑器、❌ 选 agent/tool、❌ 验证 |

**后端 API 的能力基本都在，但前端没把这些能力暴露成可操作的 UI。** 三块都停在「demo 能看，但工作流跑不通」的状态。

---

## 一、Agent 添加（`AgentEditPage.tsx`）

表单形态完整，但有几处会导致「填了存不进去 / 存了没用」。

### 🔴 致命：没法给 Agent 绑定工具
整个创建/编辑表单里**完全没有「工具绑定」这一项**。而 Agent 的灵魂就是用工具。结果：建出来的 Agent 只能纯聊天，画布上拖进去也调不了任何工具。这是「差点意思」最核心的来源。
（注：即便绑定了，后端 ReAct 循环也未实现 —— 见《项目分析报告.md》缺陷 #1）

### 🔴 provider / model 是自由文本框，不是下拉
```tsx
<Input label="提供商" value={form.llm_provider} ... />   // 手敲
<Input label="模型"   value={form.model_name} ... />   // 手敲
```
但后端 schema 卡死：`llm_provider` 必须匹配 `^(openai|deepseek|qwen|zhipu)$`（`schemas/agent.py:12`）。敲错一个字母（`OpenAI`、`gpt4`）就被 422 拒绝，而前端只弹一句无信息的「保存失败」（`catch {}` 把错误吃掉了）。**用户不知道错在哪。**

### 🟠 前后端默认值不一致
| 字段 | 前端默认 | 后端默认 | 后果 |
|---|---|---|---|
| `model_name` | `gpt-4` | `gpt-4o-mini` | `gpt-4` 不在定价表里，成本算 0 |
| `enable_memory` | `false` | `true` | 行为不符预期 |
| `memory_policy` | `recent` | `private` | 语义对不上 |

### 🟠 没有「测试 Agent」入口
后端有 `AgentTestRequest` 与测试端点，但编辑页没有「试聊」按钮，建完要去别处验证。

---

## 二、工具注册（`ToolListPage.tsx`）

**完全不能用**——不是体验差，是按钮全是死的。

### 🔴「+ 注册工具」按钮没有任何 onClick
```tsx
<Button>+ 注册工具</Button>   // 无 onClick，点了无反应
```
**前端没有工具注册的表单/弹窗。** 无法从 UI 注册任何工具——自定义工具的源码、`tool_schema`、MCP 配置都没有录入口。后端 `POST /tools` 是好的，前端没接。

### 🔴「测试」按钮同样是死的
```tsx
<Button variant="ghost" size="sm">测试</Button>   // 无 onClick
```
后端 `/tools/{id}/test` 写好了，前端没接。

### 结论
工具页目前只能**看列表 + 删除**。「工具注册」功能在 UI 层等于不存在。可用工具仅限后端 `ensure_builtin_tools()` 预置的 calculator / datetime。

---

## 三、工作流编辑（`WorkflowEditorPage.tsx`）

画布能拖、能连线，但**拖进去的节点没法配置**，导致工作流基本跑不通。

### 🔴 致命：没有节点配置面板
拖一个节点进画布后，**没有任何地方能配置它**：
- Agent 节点：`agent_id` 在 `onDrop` 时被**硬塞成 `agents[0].id`**（第 146 行），想换别的 Agent？没有 UI。
- Tool 节点：`tool_id` 永远是 `null`（第 153 行 `tool_id: null`，且无处可改）。**工具节点 100% 会在运行时报「工具节点未配置 tool_id」。**
- 节点 label 拖进去后改不了。

成熟编排器都是「点选节点 → 右侧属性面板」。这里完全缺失，是「差点意思」的最大元凶。

### 🔴 条件边靠 label 前缀 hack
```tsx
condition_expr: e.label.startsWith('if ') ? e.label : null
```
没有条件编辑器。要手动把边 label 写成 `if xxx` 才能被识别成条件——而画布上根本没有改边 label 的 UI。

### 🟠 节点类型只暴露 3 种，后端支持 8 种
左侧面板只有 `agent / tool / condition`，后端支持 `start / end / fork / join / human`。且 `nodeTypes` 只注册了 3 种，start/end 被强行当成 `agent` 类型渲染（第 47 行）。fork/join/human 拖不进来，并行和人工节点用不了。

### 🟠「验证」按钮没接
```tsx
<Button variant="secondary">验证</Button>   // 死按钮
```
后端有 workflow 校验端点，前端没调。

### 🟠 其他
- 没有删除节点的 UI（只能靠键盘 Delete，且无确认）
- 连线无合法性校验（可把 end 连回 start）
- 用 `alert()` 报错，体验粗糙

---

## 修复建议优先级（影响大 → 小）

1. **工作流编辑器加节点配置面板**（点选节点 → 右侧 Drawer：选 agent_id / tool_id、改 label、写 condition）——不补则整个工作流空转。
2. **工具注册弹窗**（接 `+ 注册工具` 与 `测试` 两个死按钮，覆盖 custom 源码 + MCP 配置录入）。
3. **Agent 表单**：provider/model 改下拉、加工具绑定多选、`catch` 里把后端 `detail` 弹出来、对齐前后端默认值、加「试聊」入口。
4. **工作流编辑器补全**：边 label/condition 编辑、节点删除确认、连线合法性校验、暴露 fork/join/human 节点、接「验证」按钮、`alert` 换 Toast。

---

## 证据索引

| 问题 | 文件:行 |
|---|---|
| Agent 表单无工具绑定 | `frontend/src/pages/AgentEditPage.tsx`（全文无 tool 字段） |
| provider/model 自由文本 | `AgentEditPage.tsx:94-95` |
| 后端 provider 正则约束 | `backend/app/schemas/agent.py:12` |
| catch 吞错误 | `AgentEditPage.tsx:50` |
| 注册工具按钮无 onClick | `frontend/src/pages/ToolListPage.tsx:62` |
| 测试按钮无 onClick | `ToolListPage.tsx:44` |
| Agent 节点硬塞 agents[0] | `frontend/src/pages/WorkflowEditorPage.tsx:146` |
| Tool 节点 tool_id 恒为 null | `WorkflowEditorPage.tsx:153` |
| 条件边 label hack | `WorkflowEditorPage.tsx:84` |
| start/end 当 agent 渲染 | `WorkflowEditorPage.tsx:47` |
| 验证按钮无 onClick | `WorkflowEditorPage.tsx:195` |
