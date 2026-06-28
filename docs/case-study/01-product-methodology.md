# Product And Methodology

## 一句话结论
IdeaSense AI 的产品核心不是“聊天”，而是一个可控的创业评估工作流。它借用 AI 对话作为入口，但真正的产品方法是用结构化访谈、缺失项识别、Stage Gate 确认和 DVF 评分，把一个早期软件想法推进到可讨论、可验证、可复盘的评估报告。

## 背景
这篇文档主要面向招聘方和 portfolio reviewer，同时兼顾潜在用户和未来合作者。它要说明的不是“我接了一个 LLM API”，而是我如何把一个模糊的创业评估任务拆成产品流程、数据合同、AI 输出边界和用户确认机制。

早期软件创业者和学生团队通常不是缺想法，而是缺一套能持续追问、结构化记录、区分事实与假设的评估流程。直接问通用 AI 或 ChatGPT 容易出现几个问题：

- 讨论会发散，关键问题没有闭环。
- 模型倾向于顺着用户说，很少强硬指出“这里缺信息”。
- 缺失事实容易被补成听起来合理的判断。
- 用户很难复盘“这个结论来自哪一段回答、哪一个阶段、哪一类证据”。
- 最终建议看起来完整，但不一定暴露 unknown、assumption 和 evidence gap。

IdeaSense AI 把流程固定为：

```txt
Problem / Desirability -> Market / Viability -> Tech / Feasibility -> Report
```

也就是说，IdeaSense 不是让 AI 自由发挥成一个“老好人”顾问，而是把 AI 放进一个咨询式评估框架里：先追问问题、用户、市场、商业和技术约束，再把缺失项和风险明确暴露出来。

## 设计目标
- 让用户先明确 #1 problem 和 P0 user，再进入商业和技术判断。
- 用 DVF 作为隐性访谈结构，同时作为最终报告的评分框架。
- 允许 unknown、unsure、not applicable 这类回答，并把它们保存为不确定性，而不是把用户卡死在一道题上。
- 每个阶段必须生成摘要并由用户确认，不能让 AI 静默推进或自动替用户确认事实。
- 把用户输入、AI 推断、外部支持、未知项和 evidence gap 分层展示。
- 对选中的可外部验证 claim 附加 verification status，但不把它包装成全量事实审计或反欺诈系统。
- 面向创业课程、孵化器、学生团队和独立开发者，支持 mentor/admin 后续查看。

## 当前实现
当前仓库已打通以下产品能力：

- 注册、登录、邮箱验证、邀请加入。
- 项目创建和项目列表。
- 分阶段访谈式聊天。
- 上下文抽取和 live context 面板。
- Stage Gate 确认。
- DVF 评分与报告查看。
- 证据分层：confirmed inputs、founder assumptions、AI inferences、unknowns、evidence gaps、verification summary。
- 问题级 verification：对部分可外部检查的 claim 展示 supported、contradicted、uncertain、not applicable、provider unavailable 等状态。
- Sample Workspace / Sample Report 公共演示链路。
- 组织、cohort、mentor/admin 管理能力。

核心事实源：

- `README.md`: 当前 MVP 状态。
- `docs/spec/PUBLIC_SPEC.md`: public-safe 流程、边界和 API 合同摘要。
- 私有 `docs/spec/MASTER_SPEC.md`: 完整三阶段问题脚本、字段映射和生产合同。
- `docs/INTEGRATED_PRODUCT_TECH_SPEC.md`: 产品定义、用户、方法论和公开页面理解。
- `resources/question_bank.example.yaml`: public-safe 问题银行结构示例。生产问题银行内容保留在私有仓库。

## 关键决策
- Problem first: 用户先定义问题，再定义用户，不先跳到 solution pitch。
- Stage Gate: 阶段结束必须有摘要确认，用户可以修正 AI 总结。
- Unknown handling: 用户答不上来不是失败路径。早期项目天然有大量未验证内容，系统应保存不确定性并继续推进。
- DVF as review frame: 报告使用 Desirability / Viability / Feasibility，而不是泛化的“商业建议”。DVF 既约束访谈问题，也约束最终评分。
- Evidence layering: 用户确认代表“这个输入进入评估流程”，不等于外部事实已经被证明；外部搜索和验证结果只能作为 evidence layer。
- Missingness as product signal: 缺失项本身就是评估结果的一部分。系统要告诉用户项目目前缺什么，而不是为了生成一份漂亮报告而补齐事实。
- Report as artifact: 报告是可导出、可打印、可复盘的结果，不是聊天窗口里的一段长回复。

## 风险与权衡
- 流程太严格会让用户觉得像表单，所以前端需要保留自然语言访谈体验。
- 流程太自由会回到普通 chatbot，所以后端必须有阶段、字段、状态和确认边界。
- AI 可以帮助草拟，但不能替用户确认事实。
- 外部验证可以提高可信度，但不能被写成“系统已经证明所有用户说法都是真的或假的”。
- 报告需要给出判断，但必须暴露证据不足、未知项、assumption 和后续验证计划。

这个边界尤其重要：IdeaSense 可以指出 supported、contradicted、uncertain 或 not applicable，但不应该声称自己一定“知道哪些是真的、哪些是假的”。更准确的说法是，系统把判断拆成可追踪的证据层，并在证据不足时降低信心或要求后续验证。

## 验证方式
- 使用 sample workspace 检查用户是否能理解阶段推进。
- 使用 sample report 检查报告是否能体现 DVF、阶段摘要、风险和验证计划。
- 使用后端阶段测试和前端 chat/report 测试确保核心流程没有断裂。
- 变更阶段字段、问题脚本或报告结构时，先更新私有 `docs/spec/MASTER_SPEC.md`，并同步 public-safe 摘要到 `docs/spec/PUBLIC_SPEC.md`。
- 核对 public spec、私有 Master Spec 和当前代码中的 context card、verification status、Stage Gate 和 report contract 定义，避免文档把当前实现说得过强。

## 可公开摘要
IdeaSense AI is a guided startup assessment workflow, not a generic chatbot. It uses consulting-style structured interviews, DVF scoring, and stage-gate confirmation to turn a raw software idea into an evidence-aware report. The system preserves uncertainty, separates founder assumptions from confirmed workflow inputs, and attaches external verification signals only where claims can reasonably be checked.
