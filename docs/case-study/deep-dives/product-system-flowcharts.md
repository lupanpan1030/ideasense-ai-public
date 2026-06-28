# Deep Dive: Product And System Flowcharts

## 一句话结论
这份文档保存 IdeaSense AI 的产品主链路和工程执行链路。图表使用 Mermaid 编写，适合在 GitHub、Markdown 编辑器或文档站中直接渲染。

## Mermaid 写法速记
- `flowchart TD`: 从上到下排版。
- `A[普通步骤]`: 矩形步骤节点。
- `B{判断条件}`: 菱形判断节点。
- `A --> B`: 普通箭头。
- `A -- 条件 --> B`: 带条件说明的箭头。
- `sequenceDiagram`: 时序图，用于展示前端、后端、数据库、worker 和 LLM 的调用顺序。

## 产品主链路
这张图用于解释用户视角的核心流程：项目创建、分阶段访谈、上下文抽取、Stage Gate 确认、DVF 评分和最终报告。

```mermaid
flowchart TD
    A[注册 / 登录] --> B{邮箱已验证?}
    B -- 否 --> B1[仅允许完成 Problem 阶段]
    B1 --> B2[完成邮箱验证]
    B -- 是 --> C[创建 Project]
    B2 --> C

    C --> D[Problem / Desirability 访谈]
    D --> E[answer_gate 判断回答是否足够]
    E -- 不足 --> F[继续追问缺失项]
    F --> D
    E -- 通过 --> G[抽取上下文并更新 Live Context]
    G --> H{Problem Stage Gate}
    H -- 用户修改摘要 --> D
    H -- 用户确认 --> I[锁定 Problem 阶段]

    I --> J[Market / Viability 访谈]
    J --> K[抽取市场、用户、商业可行性信息]
    K --> L{Market Stage Gate}
    L -- 用户修改摘要 --> J
    L -- 用户确认 --> M[锁定 Market 阶段]

    M --> N{Tech 路线}
    N -- 技术型 / 需要深挖 --> O[Tech Pro / Feasibility 访谈]
    N -- 非技术型 / 轻量检查 --> P[Tech Lite / Feasibility 访谈]
    O --> Q[抽取技术风险、实现路径、资源约束]
    P --> Q

    Q --> R{Tech Stage Gate}
    R -- 用户修改摘要 --> N
    R -- 用户确认 --> S[进入 Report 阶段]

    S --> T[显示 Preparing report / 报告页骨架]
    T --> U[后台生成报告 report_generation_v0]
    U --> V{报告状态}
    V -- queued / running / finalizing --> T
    V -- failed / stale --> W[显示错误、重试或状态修正]
    W --> U
    V -- ready --> X[DVF 评分 + Evidence-grounded Report]

    X --> Y[用户查看 / 确认 / 导出]
    X --> Z[Mentor / Admin 后续查看与复盘]
```

## 工程执行链路
这张图用于解释系统视角的状态机和后台任务边界：哪些步骤在 API 可见路径中完成，哪些步骤进入 `background_jobs` 由 worker 处理。

```mermaid
flowchart TD
    A[Frontend: Project Workspace] --> B[POST /api/v1/chat/stream]
    B --> C[Backend API: chat.py]

    C --> D[读取 project runtime]
    D --> E{current_stage + stage_status}

    E -- problem / market / tech + in_progress --> F[answer_gate]
    F --> G{回答是否足够?}
    G -- 不足 --> H[返回追问问题 SSE]
    H --> A

    G -- 足够 --> I[返回下一题 / stage-ready 提示 SSE]
    I --> J[写入 background_jobs]
    J --> K[extract_answer_v0]
    K --> L[Worker 抽取结构化上下文]
    L --> M[写入 project_states / live context]

    I --> N{阶段是否 ready?}
    N -- 否 --> A
    N -- 是 --> O[stage_status = awaiting_confirm]
    O --> P[Frontend 显示 Stage Gate 摘要]

    P --> Q{用户确认?}
    Q -- 修改 --> A
    Q -- 确认 --> R[POST /api/v1/assessments/:stage/confirm]

    R --> S[Backend: stage_runtime 推进状态]
    S --> T[锁定当前 stage]
    T --> U{是否 Tech 已确认?}

    U -- 否 --> V[进入下一阶段]
    V --> A

    U -- 是 --> W[进入 report 阶段]
    W --> X[Frontend 跳转 Report Skeleton]
    X --> Y[enqueue report_generation_v0]

    T --> Z[enqueue stage_finalize_v0]
    Z --> Z1[Worker 生成 DVF stage score]
    Z1 --> Z2[生成 context card / validation plan]
    Z2 --> Z3[可选 verify_question_claims_v0]

    Y --> AA[Worker 生成最终报告]
    AA --> AB{report_job_status}
    AB -- queued / running / finalizing --> X
    AB -- failed / stale --> AC[显示错误 / retry]
    AC --> Y
    AB -- ready --> AD[project_reports: final report]
    AD --> AE[Frontend 显示 DVF Report]
```

## 工程时序图
这张图用于解释前端、API、数据库、worker 和 LLM provider 的调用顺序。它更适合工程评审、架构讲解和后续排查等待链路。

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant API as Backend API
    participant DB as PostgreSQL
    participant W as Worker
    participant LLM as LLM Provider

    U->>FE: 输入阶段回答
    FE->>API: POST /api/v1/chat/stream
    API->>DB: 读取 project runtime / current_stage
    API->>LLM: answer_gate 判断回答质量
    LLM-->>API: pass / needs_more

    alt 回答不足
        API-->>FE: SSE 返回追问
        FE-->>U: 显示下一条问题
    else 回答通过
        API-->>FE: SSE 返回下一题或 stage-ready
        API->>DB: enqueue extract_answer_v0
        W->>DB: claim background job
        W->>LLM: 抽取结构化上下文
        LLM-->>W: extracted context
        W->>DB: 写入 project_states / live context
    end

    alt 阶段达到确认条件
        FE-->>U: 显示 Stage Gate 摘要
        U->>FE: confirm stage
        FE->>API: POST /api/v1/assessments/:stage/confirm
        API->>DB: 锁定 stage / 推进 current_stage
        API->>DB: enqueue stage_finalize_v0

        W->>DB: claim stage_finalize_v0
        W->>LLM: 生成 stage scoring / context card / validation plan
        W->>DB: 写入 stage artifacts
    end

    alt Tech 阶段确认后
        API-->>FE: report stage ready
        FE-->>U: 显示 Preparing report
        API->>DB: enqueue report_generation_v0

        W->>DB: claim report_generation_v0
        W->>LLM: 生成 DVF final report
        LLM-->>W: report content
        W->>DB: 写入 project_reports

        FE->>API: poll report status
        API->>DB: 查询 report_job_status
        API-->>FE: ready
        FE-->>U: 显示最终报告
    end
```

## 使用边界
- 产品说明优先使用“产品主链路”。
- 架构说明优先使用“工程执行链路”。
- 工程评审、排查慢请求、说明同步/异步边界时优先使用“工程时序图”。
- 图表中的报告 ready 不等于按钮被点击成功；它应对应当前 context version 下的 final `project_reports` artifact。
