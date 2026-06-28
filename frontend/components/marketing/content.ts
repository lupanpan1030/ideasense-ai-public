import {
  DEFAULT_APP_LOCALE,
  normalizeAppLocale,
  type AppLocale,
} from "@/lib/i18n/config";

type MarketingFaqItem = {
  id: string;
  question: string;
  answer: string;
};

type MarketingStep = {
  index: string;
  title: string;
  description: string;
};

type MarketingMember = {
  name: string;
  role: string;
  image: string;
  href?: string;
};

type MarketingLabelValue = {
  label: string;
  value: string;
};

type MarketingSection = {
  eyebrow: string;
  title: string;
  description: string;
};

type MarketingHomeContent = {
  pageLabels: {
    hero: string;
    features: string;
    process: string;
    insights: string;
    faq: string;
    team: string;
  };
  goToPageAriaPrefix: string;
  nav: {
    features: string;
    process: string;
    faq: string;
    team: string;
    login: string;
    register: string;
  };
  hero: {
    badge: string;
    meta: string;
    headline: string;
    subheadline: string;
    description: string;
    primaryCta: string;
    sampleCta: string;
    reportCta: string;
    audience: string;
    previousSlideAria: string;
    nextSlideAria: string;
    goToSlideAriaPrefix: string;
    backgroundAlt: string;
  };
  features: {
    eyebrow: string;
    title: string;
    description: string;
    cta: string;
    imageAlts: [string, string, string, string];
  };
  process: {
    eyebrow: string;
    title: string;
    description: string;
    steps: MarketingStep[];
    cards: MarketingStep[];
    cta: string;
  };
  insights: {
    eyebrow: string;
    title: string;
    description: string;
    cta: string;
    footnote: string;
    imageAlts: {
      primary: string;
      secondary: string;
    };
  };
  faq: {
    eyebrow: string;
    title: string;
    description: string;
    items: MarketingFaqItem[];
    cta: string;
  };
  team: {
    eyebrow: string;
    title: string;
    description: string;
    members: MarketingMember[];
    collaborationTitle: string;
    collaborationDescription: string;
    collaborationCta: string;
    collaborationFootnote: string;
    copyrightTemplate: string;
  };
  closing: {
    eyebrow: string;
    title: string;
    description: string;
    primaryCta: string;
    secondaryCta: string;
    footnote: string;
  };
};

type MethodologyContent = {
  eyebrow: string;
  title: string;
  description: string;
  heroPanel: {
    eyebrow: string;
    statement?: string;
    principleLabel: string;
    principleText: string;
  };
  heroHighlights: MarketingLabelValue[];
  why: MarketingSection & {
    points: Array<
      | string
      | {
          title: string;
          description: string;
        }
    >;
    pill: string;
  };
  framework: MarketingSection;
  frameworkVisual: {
    desirabilityRows: Array<{
      label: string;
      value: string;
    }>;
    viabilityLabel: string;
    feasibilityAxes: {
      left: string;
      right: string;
    };
  };
  stages: Array<{
    title: string;
    displayTitle?: string;
    weight: string;
    description: string;
    checks: string[];
  }>;
  review: MarketingSection & {
    gatesTitle: string;
    gates: string[];
  };
  sessionTitle: string;
  sessionSteps: Array<{
    title: string;
    description: string;
  }>;
  uncertainty: MarketingSection & {
    points: string[];
    chips: string[];
  };
  outputsSection: MarketingSection;
  outputsTitle: string;
  outputs: string[];
  artifact: {
    eyebrow: string;
    title: string;
    summaryRows: Array<{
      label: string;
      value: string;
    }>;
    scoreboardLabel: string;
    scoreboardRows: Array<{
      label: string;
      value: string;
    }>;
    modulesLabel: string;
    modules: string[];
    exportChips: string[];
    judgmentLabel: string;
    judgmentText: string;
  };
  closing: {
    eyebrow: string;
    title: string;
    description: string;
    primaryCta: string;
    secondaryCta: string;
  };
  actions: {
    start: string;
    sampleReport: string;
    backHome: string;
  };
};

export type MarketingContent = {
  home: MarketingHomeContent;
  methodology: MethodologyContent;
};

const marketingContentEn: MarketingContent = {
  home: {
    pageLabels: {
      hero: "Home",
      features: "Features",
      process: "Process",
      insights: "Insights",
      faq: "FAQ",
      team: "Team",
    },
    goToPageAriaPrefix: "Go to",
    nav: {
      features: "Perspective",
      process: "DVF Engine",
      faq: "FAQ",
      team: "About",
      login: "Login",
      register: "Register",
    },
    hero: {
      badge: "IdeaSense AI",
      meta: "Structured AI review for startup ideas before you build.",
      headline: "Validate before you build.",
      subheadline:
        "IdeaSense helps early-stage founders and solo builders pressure-test software ideas before they commit to build.",
      description:
        "Run a staged validation workflow with structured review, DVF scoring, and decision-ready reports.",
      primaryCta: "Start Free",
      sampleCta: "Explore Sample Workspace",
      reportCta: "View Sample Report",
      audience:
        "Built for early-stage software founders and solo builders.",
      previousSlideAria: "Previous slide",
      nextSlideAria: "Next slide",
      goToSlideAriaPrefix: "Go to slide",
      backgroundAlt:
        "Dogfooding product demo showing IdeaSense AI reviewing IdeaSense AI through a staged interview, context gate, and DVF report.",
    },
    features: {
      eyebrow: "Perspective",
      title: "Most bad bets feel persuasive right before they get built.",
      description:
        "IdeaSense is designed to challenge the pitch, surface missing evidence, and slow down the rush to execution.",
      cta: "See the DVF Engine",
      imageAlts: [
        "Feature preview 1",
        "Feature preview 2",
        "Feature preview 3",
        "Feature preview 4",
      ],
    },
    process: {
      eyebrow: "DVF Engine",
      title: "Three signals. One clearer decision.",
      description:
        "Desirability, viability, and feasibility are reviewed separately so the result feels defensible, not improvised.",
      steps: [
        {
          index: "01",
          title: "Desirability",
          description:
            "Is the problem urgent and specific enough to matter?",
        },
        {
          index: "02",
          title: "Viability",
          description:
            "Does the market, model, and positioning support the idea?",
        },
        {
          index: "03",
          title: "Feasibility",
          description:
            "Can an MVP be built responsibly within real constraints?",
        },
        {
          index: "04",
          title: "Decision",
          description:
            "Turn the evidence into a report, risk view, and next-step recommendation.",
        },
      ],
      cards: [
        {
          index: "01",
          title: "Desirability",
          description:
            "Is the problem urgent and specific enough to matter?",
        },
        {
          index: "02",
          title: "Viability",
          description:
            "Does the market, model, and positioning support the idea?",
        },
        {
          index: "03",
          title: "Feasibility",
          description:
            "Can an MVP be built responsibly within real constraints?",
        },
        {
          index: "04",
          title: "Decision",
          description:
            "Turn the evidence into a report, risk view, and next-step recommendation.",
        },
      ],
      cta: "Start Free",
    },
    insights: {
      eyebrow: "Decision-Ready Report",
      title: "A report your team can actually use.",
      description:
        "Instead of another generic plan, get a concise decision artifact: score, risks, assumptions, and what to validate next.",
      cta: "See Sample Report",
      footnote: "Reports can be printed and exported for follow-up discussion.",
      imageAlts: {
        primary:
          "IdeaSense AI dogfooding report showing the decision overview and DVF score.",
        secondary:
          "Close-up of the IdeaSense AI dogfooding report with the decision band and score.",
      },
    },
    faq: {
      eyebrow: "FAQ",
      title: "Questions, answered.",
      description:
        "The short version of how IdeaSense thinks, scores, and protects the work.",
      items: [
        {
          id: "chatgpt",
          question: "How is this different from asking ChatGPT?",
          answer:
            "ChatGPT is good at open-ended brainstorming. IdeaSense runs a staged review: anchor questions, summary confirmation, DVF scoring, and a report built from structured project state rather than a one-off chat response.",
        },
        {
          id: "dvf",
          question: "What is the DVF Score?",
          answer:
            "It stands for Desirability (35%), Viability (35%), and Feasibility (30%). It is a weighted reading of evidence, risk, and unresolved assumptions across those three dimensions, not a guarantee of success.",
        },
        {
          id: "architecture",
          question: "Can it really help with technical architecture?",
          answer:
            "It can help frame MVP scope, dependencies, delivery risk, and architecture tradeoffs. The report can include an architecture diagram when the underlying project information supports it, but it should be treated as a discussion artifact, not a final implementation blueprint.",
        },
        {
          id: "privacy",
          question: "Is my idea data private?",
          answer:
            "IdeaSense uses account, project, report, and verification data to operate the product. We do not position project content as something to sell onward, and the Privacy page explains the current boundaries, storage, and request path in more detail.",
        },
      ],
      cta: "Start Free",
    },
    team: {
      eyebrow: "About",
      title: "Built independently for founder reality.",
      description:
        "IdeaSense AI is an independent product built and operated by Ethan Lu for early-stage software founders and solo builders who need clearer decisions.",
      members: [
        {
          name: "Ethan Lu",
          role: "Independent builder",
          image: "/marketing/welcome/team/founder-portrait.jpg",
          href: "https://www.ethanchenlu.com",
        },
      ],
      collaborationTitle: "Independent product, open to feedback",
      collaborationDescription:
        "If you work with founders or early-stage teams, product feedback and thoughtful questions are welcome.",
      collaborationCta: "Request Collaboration",
      collaborationFootnote:
        "Open registration is live, and product feedback goes straight into ongoing iteration.",
      copyrightTemplate: "© {year} IdeaSense AI. Operated by Ethan Lu. All rights reserved.",
    },
    closing: {
      eyebrow: "Start with evidence",
      title: "Sharper evidence. Better bets.",
      description:
        "Use a structured founder review, DVF scoring, and a decision-ready report to decide whether to proceed, pause, or pivot.",
      primaryCta: "Start Free",
      secondaryCta: "Explore Sample Workspace",
      footnote:
        "Open registration is live. Scores support judgment; they do not guarantee outcomes.",
    },
  },
  methodology: {
    eyebrow: "Methodology",
    title: "From vague ideas to structured judgment.",
    description:
      "IdeaSense helps early-stage teams pressure-test a software idea through structured dialogue, staged review, DVF scoring, and a decision-ready report.",
    heroPanel: {
      eyebrow: "Method snapshot",
      statement: "Proceed, but expose the highest-impact unknown first.",
      principleLabel: "Core principle",
      principleText:
        "Unknown is allowed, but unchecked certainty should not silently become an official conclusion.",
    },
    heroHighlights: [
      {
        label: "Typical review",
        value: "30-60 minutes to reach a first structured evaluation",
      },
      {
        label: "Built for",
        value: "0-1 founders, student teams, and mentors",
      },
      {
        label: "Outcome",
        value: "DVF scoring, key risks, and a report you can export",
      },
    ],
    why: {
      eyebrow: "Why this exists",
      title: "A good idea is not the same as a defendable decision.",
      description:
        "Most early concepts feel stronger than they are. The real work is not polishing the pitch. It is separating facts, estimates, assumptions, and unknowns before a team commits time, money, and momentum.",
      pill: "Not for polishing the pitch. For structuring the judgment.",
      points: [
        "Facts that already exist",
        "Estimates that still need pressure",
        "Assumptions carrying the idea",
        "Unknowns that should stay unknown",
      ],
    },
    framework: {
      eyebrow: "The framework",
      title: "Three lenses. One clearer decision.",
      description:
        "IdeaSense uses a DVF framework to assess whether an idea is desirable, viable, and feasible in the real world.",
    },
    frameworkVisual: {
      desirabilityRows: [
        { label: "Pain", value: "84%" },
        { label: "Audience", value: "76%" },
        { label: "Urgency", value: "71%" },
        { label: "Signal", value: "63%" },
      ],
      viabilityLabel: "Viability",
      feasibilityAxes: {
        left: "Impact",
        right: "Uncertainty",
      },
    },
    stages: [
      {
        title: "Desirability",
        weight: "35% weight",
        description:
          "We test the problem, the target user, the context of use, the urgency of pain, current alternatives, and whether real demand signals exist.",
        checks: [
          "Problem clarity",
          "User and context",
          "Urgency and pain",
          "Alternatives",
          "Demand evidence",
        ],
      },
      {
        title: "Viability",
        weight: "35% weight",
        description:
          "We examine the value proposition, business logic, market dynamics, channel friction, competition, and the assumptions behind commercial success.",
        checks: [
          "Value proposition",
          "Business logic",
          "Market dynamics",
          "Channel friction",
          "Competition",
        ],
      },
      {
        title: "Feasibility",
        weight: "30% weight",
        description:
          "We assess MVP scope, technical approach, dependencies, data and compliance constraints, team capability, and delivery risk.",
        checks: [
          "MVP scope",
          "Technical approach",
          "Dependencies",
          "Data and compliance",
          "Delivery risk",
        ],
      },
    ],
    review: {
      eyebrow: "How it works",
      title: "Not open-ended chat. A staged review process.",
      description:
        "The conversation moves through structured stages. Each stage has anchors, a summary checkpoint, and a clear standard for what is ready to move forward.",
      gatesTitle: "Stage gate discipline",
      gates: [
        "Each stage has anchor questions that matter.",
        "Users can correct the summary before it becomes official.",
        "Progress does not require every answer, but critical anchors cannot all remain unresolved.",
      ],
    },
    sessionTitle: "Staged review flow",
    sessionSteps: [
      {
        title: "Capture what matters",
        description:
          "The system gathers the problem, user, scenario, proposed solution, and the assumptions currently carrying your confidence.",
      },
      {
        title: "Challenge weak logic",
        description:
          "It pushes on missing evidence, edge cases, hidden dependencies, and reasoning gaps across the DVF dimensions.",
      },
      {
        title: "Confirm before advancing",
        description:
          "Before a stage closes, the system summarizes the current view and gives the user a chance to correct or confirm what should count as official input.",
      },
    ],
    uncertainty: {
      eyebrow: "Uncertainty matters",
      title: "Unknown is allowed. Unchecked certainty is not.",
      description:
        "A strong evaluation system should not force fake confidence. IdeaSense is designed to preserve uncertainty where evidence is weak, instead of converting every guess into a conclusion.",
      points: [
        "Users can correct summaries before they become official.",
        "Important fields cannot all remain unresolved.",
        "Weak evidence is treated differently from confirmed evidence.",
      ],
      chips: ["Unknown", "Needs evidence", "Confirmed"],
    },
    outputsSection: {
      eyebrow: "What you get",
      title: "A report built for action, not just reflection.",
      description:
        "The final output is meant to support discussion, comparison, printing, export, and next-step planning.",
    },
    outputsTitle: "What you get",
    outputs: [
      "DVF scoreboard and overall decision band",
      "Lean Canvas summary",
      "Market evidence and verification summary",
      "Key risks and unresolved assumptions",
      "Overall summary with export and print options",
    ],
    artifact: {
      eyebrow: "Report overview",
      title: "Decision-ready artifact",
      summaryRows: [
        { label: "DVF score", value: "77 / 100" },
        { label: "Decision band", value: "Proceed with guardrails" },
        { label: "Priority risks", value: "3" },
      ],
      scoreboardLabel: "Scoreboard",
      scoreboardRows: [
        { label: "Desirability", value: "82" },
        { label: "Viability", value: "74" },
        { label: "Feasibility", value: "76" },
      ],
      modulesLabel: "Output modules",
      modules: [
        "Lean Canvas",
        "Verification summary",
        "Key risks",
        "Overall summary",
      ],
      exportChips: ["Print PDF", "Export Markdown", "Export JSON"],
      judgmentLabel: "Core judgment",
      judgmentText:
        "Proceed with guardrails: validate completion and report traceability first.",
    },
    closing: {
      eyebrow: "Final takeaway",
      title: "Better structure. Better judgment.",
      description:
        "If a decision matters, it deserves more than instinct. It deserves a process that can be questioned, defended, and revisited.",
      primaryCta: "Start Your First Validation",
      secondaryCta: "Explore Sample Workspace",
    },
    actions: {
      start: "Start Free",
      sampleReport: "View Sample Report",
      backHome: "Back to Home",
    },
  },
};

const marketingContentZh: MarketingContent = {
  home: {
    pageLabels: {
      hero: "首页",
      features: "功能",
      process: "流程",
      insights: "洞察",
      faq: "常见问题",
      team: "团队",
    },
    goToPageAriaPrefix: "前往",
    nav: {
      features: "视角",
      process: "DVF 引擎",
      faq: "常见问题",
      team: "关于",
      login: "登录",
      register: "注册",
    },
    hero: {
      badge: "IdeaSense AI",
      meta: "面向软件创业想法的结构化 AI 验证。",
      headline: "先验证，再构建。",
      subheadline: "IdeaSense 帮助早期创始人和独立构建者在真正投入构建前，先把软件想法验证清楚。",
      description:
        "通过分阶段评审、DVF 评分与决策就绪报告，把一次想法讨论推进成更清楚的 go / no-go 判断。",
      primaryCta: "免费开始",
      sampleCta: "查看示例工作区",
      reportCta: "查看示例报告",
      audience:
        "适合早期软件创业者和独立构建者。",
      previousSlideAria: "上一张",
      nextSlideAria: "下一张",
      goToSlideAriaPrefix: "前往第",
      backgroundAlt:
        "IdeaSense AI 用自身作为测试项目的产品演示，展示阶段访谈、上下文确认和 DVF 报告。",
    },
    features: {
      eyebrow: "视角",
      title: "很多糟糕的下注，在真正开始构建前看起来都很有说服力。",
      description:
        "IdeaSense 的作用不是附和，而是挑战表述、暴露证据缺口，并减慢盲目执行的冲动。",
      cta: "查看 DVF 引擎",
      imageAlts: ["功能预览 1", "功能预览 2", "功能预览 3", "功能预览 4"],
    },
    process: {
      eyebrow: "DVF 引擎",
      title: "三个信号。一个更清楚的决定。",
      description:
        "把需求度、商业可行性和技术可实现性拆开判断，让结论有依据，而不是靠感觉。",
      steps: [
        {
          index: "01",
          title: "需求度",
          description: "这个问题是否足够真实、足够具体，也足够值得被解决？",
        },
        {
          index: "02",
          title: "商业可行性",
          description: "市场、模式和定位，是否真的支撑这件事成立？",
        },
        {
          index: "03",
          title: "技术可实现性",
          description: "在真实约束下，这个 MVP 能否负责任地做出来？",
        },
        {
          index: "04",
          title: "决策",
          description:
            "把证据收束成报告、风险视图和下一步建议。",
        },
      ],
      cards: [
        {
          index: "01",
          title: "需求度",
          description: "这个问题是否足够真实、足够具体，也足够值得被解决？",
        },
        {
          index: "02",
          title: "商业可行性",
          description: "市场、模式和定位，是否真的支撑这件事成立？",
        },
        {
          index: "03",
          title: "技术可实现性",
          description: "在真实约束下，这个 MVP 能否负责任地做出来？",
        },
        {
          index: "04",
          title: "决策",
          description: "把证据收束成报告、风险视图和下一步建议。",
        },
      ],
      cta: "免费开始",
    },
    insights: {
      eyebrow: "决策就绪报告",
      title: "一份团队真的会拿来用的报告。",
      description:
        "不是再生成一份泛泛商业计划，而是给你一份更短、更能行动的决策材料：分数、风险、假设，以及下一步该验证什么。",
      cta: "查看示例报告",
      footnote: "报告支持打印与导出，便于后续讨论和复盘。",
      imageAlts: {
        primary: "IdeaSense AI dogfooding 报告，展示决策概览和 DVF 分数。",
        secondary: "IdeaSense AI dogfooding 报告局部，展示决策建议和评分。",
      },
    },
    faq: {
      eyebrow: "常见问题",
      title: "几个关键问题。",
      description:
        "关于 IdeaSense 如何判断、如何评分，以及如何处理数据的简版说明。",
      items: [
        {
          id: "chatgpt",
          question: "它和直接问 ChatGPT 有什么不同？",
          answer:
            "ChatGPT 更适合开放式讨论。IdeaSense 运行的是分阶段评审：关键锚点问题、阶段总结确认、DVF 评分，以及基于结构化项目状态生成的报告，而不是一次性的聊天回复。",
        },
        {
          id: "dvf",
          question: "什么是 DVF 分数？",
          answer:
            "它代表需求度（35%）、商业可行性（35%）和技术可实现性（30%）。它是对证据、风险和未决假设的加权判断，不是成功率保证，也不是随意生成的数字。",
        },
        {
          id: "architecture",
          question: "它真的能帮助技术架构设计吗？",
          answer:
            "可以帮助你梳理 MVP 范围、关键依赖、交付风险和架构取舍。在项目信息足够时，报告里也可能出现架构图，但它更适合作为讨论材料，而不是最终实现蓝图。",
        },
        {
          id: "privacy",
          question: "我的想法数据安全吗？",
          answer:
            "IdeaSense 会使用账号、项目、报告和验证相关数据来运行产品。我们不会把项目内容定位成对外转售资产；更完整的边界、存储方式和请求路径，请以 Privacy 页面为准。",
        },
      ],
      cta: "免费开始",
    },
    team: {
      eyebrow: "关于",
      title: "由独立开发者为真实创业决策而构建。",
      description:
        "IdeaSense AI 是由 Ethan Lu 独立设计与运营的产品，面向需要在投入构建前先做清晰判断的早期软件创业者与独立构建者。",
      members: [
        {
          name: "Ethan Lu",
          role: "独立开发者",
          image: "/marketing/welcome/team/founder-portrait.jpg",
          href: "https://www.ethanchenlu.com",
        },
      ],
      collaborationTitle: "独立产品，欢迎反馈",
      collaborationDescription:
        "如果你正在做早期项目，或与创业者团队合作，欢迎提出反馈和问题。",
      collaborationCta: "申请合作",
      collaborationFootnote:
        "已开放注册，产品反馈会直接进入持续迭代。",
      copyrightTemplate: "© {year} IdeaSense AI。由 Ethan Lu 独立运营。保留所有权利。",
    },
    closing: {
      eyebrow: "从证据开始",
      title: "证据更清楚，下注更稳。",
      description:
        "通过结构化创始人评审、DVF 评分和决策就绪报告，判断这件事该继续、暂停，还是转向。",
      primaryCta: "免费开始",
      secondaryCta: "查看示例工作区",
      footnote:
        "当前已开放注册。分数用于辅助判断，不代表结果保证。",
    },
  },
  methodology: {
    eyebrow: "方法论",
    title: "重要的决定，不该只靠热情推进。",
    description:
      "IdeaSense 用结构化追问、阶段评审与 DVF 框架，把一个仍然模糊的想法，推进成更清楚、也更经得起追问的判断。",
    heroPanel: {
      eyebrow: "当前判断",
      statement: "可以继续，但先验证最大的未知。",
      principleLabel: "判断原则",
      principleText:
        "未知可以被保留；未经验证的确定性，不该直接写进结论。",
    },
    heroHighlights: [
      {
        label: "首轮评估",
        value: "30-60 分钟，形成第一版结构化判断",
      },
      {
        label: "评审框架",
        value: "需求、商业、实现，分别判断",
      },
      {
        label: "最终交付",
        value: "DVF 评分、关键风险与决策报告",
      },
    ],
    why: {
      eyebrow: "为什么需要这套方法",
      title: "不是把想法讲得更动人，而是让决定更经得起追问。",
      description:
        "真正重要的，不是把故事包装完整，而是在投入时间、资金与执行力之前，先把事实、假设、判断与未知拆开。",
      pill: "先去噪，再下注。",
      points: [
        {
          title: "不把猜测当结论",
          description:
            "证据不够时，就保留未知，而不是提前制造确定性。",
        },
        {
          title: "不让问题跳步",
          description:
            "先看需求，再看商业，最后回到实现。顺序本身，就是方法的一部分。",
        },
        {
          title: "不让输出停在摘要",
          description:
            "最后留下的，不只是整理过的聊天，而是一份可以继续推动决策的材料。",
        },
      ],
    },
    framework: {
      eyebrow: "核心框架",
      title: "三个维度，帮你把一件事看完整。",
      description:
        "需求、商业、实现。顺序看起来简单，但足以让很多仓促推进的决定，停下来重新被审视。",
    },
    frameworkVisual: {
      desirabilityRows: [
        { label: "痛点强度", value: "84%" },
        { label: "用户清晰度", value: "76%" },
        { label: "紧迫程度", value: "71%" },
        { label: "需求信号", value: "63%" },
      ],
      viabilityLabel: "商业",
      feasibilityAxes: {
        left: "影响",
        right: "不确定性",
      },
    },
    stages: [
      {
        title: "需求度",
        displayTitle: "Desirability",
        weight: "35% 权重",
        description:
          "判断这个问题是否真实存在、是否足够明确，以及用户是否真的愿意为解决它付出注意力与迁移成本。",
        checks: [
          "问题成立",
          "用户场景",
          "痛点强度",
          "替代压力",
          "需求证据",
        ],
      },
      {
        title: "商业可行性",
        displayTitle: "Viability",
        weight: "35% 权重",
        description:
          "判断价值主张是否能成立，市场与渠道是否允许它成为一门能持续运转的业务。",
        checks: [
          "价值主张",
          "商业逻辑",
          "市场格局",
          "渠道阻力",
          "竞争态势",
        ],
      },
      {
        title: "技术可实现性",
        displayTitle: "Feasibility",
        weight: "30% 权重",
        description:
          "判断在真实资源、时间与合规约束下，这个 MVP 是否能以负责任的方式被交付出来。",
        checks: [
          "MVP 范围",
          "技术路径",
          "关键依赖",
          "数据合规",
          "交付风险",
        ],
      },
    ],
    review: {
      eyebrow: "如何运行",
      title: "不是自由聊天，而是一场分阶段评审。",
      description:
        "每一段都有明确目的：先厘清，再追问，再确认。只有真正站得住的信息，才会被带进正式结论。",
      gatesTitle: "推进原则",
      gates: [
        "每个阶段都有关键判断点。",
        "总结进入正式结果前，用户可以修正。",
        "不是所有问题都要立刻回答，但关键锚点不能长期悬空。",
      ],
    },
    sessionTitle: "评审流程",
    sessionSteps: [
      {
        title: "先把问题说准确",
        description:
          "系统先收拢问题、用户、场景、方案，以及当前支撑你信心的核心假设。",
      },
      {
        title: "再把逻辑压扎实",
        description:
          "它会围绕 DVF 三个维度追问证据缺口、边界条件、隐藏依赖与推理漏洞。",
      },
      {
        title: "确认之后，再进入下一段",
        description:
          "每个阶段结束前，系统都会先总结当前判断，再由用户确认哪些信息应进入正式结果。",
      },
    ],
    uncertainty: {
      eyebrow: "不确定性治理",
      title: "允许未知，但不纵容伪确定性。",
      description:
        "成熟的评估系统，不该逼人给出漂亮却空心的答案。证据不够时，就该把不确定性完整保留下来。",
      points: [
        "总结进入正式结果前可以修正。",
        "关键判断点不能全部停留在未决。",
        "薄弱证据不会被当成已确认事实。",
      ],
      chips: ["未知", "待验证", "已确认"],
    },
    outputsSection: {
      eyebrow: "最终输出",
      title: "不是摘要，而是下一步的依据。",
      description:
        "最后生成的，不是整理过的聊天，而是一份可以继续讨论、比较、打印与导出的决策材料。",
    },
    outputsTitle: "最终输出",
    outputs: [
      "DVF 总评分与整体判断",
      "关键风险与未决假设",
      "证据综述与验证摘要",
      "下一步最值得验证的动作",
    ],
    artifact: {
      eyebrow: "报告视图",
      title: "决策就绪报告",
      summaryRows: [
        { label: "整体评分", value: "77 / 100" },
        { label: "决策建议", value: "有护栏地推进" },
        { label: "高优先风险", value: "3" },
      ],
      scoreboardLabel: "维度评分",
      scoreboardRows: [
        { label: "需求度", value: "82" },
        { label: "商业可行性", value: "74" },
        { label: "技术可实现性", value: "76" },
      ],
      modulesLabel: "核心模块",
      modules: ["精益画布", "证据综述", "关键风险", "整体判断"],
      exportChips: ["打印 PDF", "导出 Markdown", "导出 JSON"],
      judgmentLabel: "当前判断",
      judgmentText: "可以有护栏地推进，但应先验证完成率和报告可追溯性。",
    },
    closing: {
      eyebrow: "最后一层判断",
      title: "先把判断做清楚，再让执行发生。",
      description:
        "真正重要的决定，不该只凭热情推进。它应该经得起追问，也经得起回看。",
      primaryCta: "开始第一次验证",
      secondaryCta: "查看示例工作区",
    },
    actions: {
      start: "开始第一次验证",
      sampleReport: "查看示例报告",
      backHome: "返回首页",
    },
  },
};

export const MARKETING_CONTENT: Record<AppLocale, MarketingContent> = {
  en: marketingContentEn,
  zh: marketingContentZh,
};

export const resolveMarketingContent = (locale: unknown): MarketingContent =>
  MARKETING_CONTENT[normalizeAppLocale(locale)] ??
  MARKETING_CONTENT[DEFAULT_APP_LOCALE];
