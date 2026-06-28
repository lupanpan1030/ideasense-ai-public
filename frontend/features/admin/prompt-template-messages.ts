export const PROMPT_MESSAGES = {
  en: {
    actions: {
      publish: "Publish override",
      publishing: "Publishing...",
      revert: "Revert to default",
      reverting: "Reverting...",
      viewDefault: "View default template",
    },
    badges: {
      global: "Global default",
      org: "Org override",
      templates: "templates",
    },
    browse: {
      description:
        "Filter by purpose, stage, or source. Search by key/content and sort by recency.",
      empty: "No prompt templates match the current filters.",
      loading: "Loading templates...",
      purpose: "Purpose",
      search: "Search",
      searchPlaceholder: "Search by key or content...",
      sort: "Sort",
      sortOldest: "Oldest updated",
      sortRecent: "Recently updated",
      source: "Source",
      stage: "Stage",
      title: "Browse templates",
    },
    errors: {
      accessDenied: "You do not have access to manage prompt templates.",
      default: "Unable to update prompt templates.",
      network: "Prompt templates are unavailable. Try again shortly.",
      sessionExpired: "Your session expired. Please sign in again.",
      unavailable: "Prompt templates are unavailable. Try again shortly.",
    },
    meta: {
      purpose: "Purpose",
      stage: "Stage",
      stages: "Stages",
      variant: "Variant",
    },
    page: {
      eyebrow: "Admin",
      subtitle:
        "Publish organization-specific overrides while keeping the default templates available as a fallback.",
      title: "Prompt templates",
    },
    purposes: {
      all: {
        label: "All",
        description: "All prompt templates across the product.",
      },
      chat: {
        label: "Chat",
        description: "Live chat and follow-up prompts.",
      },
      report: {
        label: "Report",
        description: "Report generation and narrative prompts.",
      },
      summary: {
        label: "Summary",
        description: "Stage summary and digest prompts.",
      },
      score: {
        label: "Scoring",
        description: "DVF scoring and evaluation prompts.",
      },
      extract: {
        label: "Extraction",
        description: "Structured extraction prompts.",
      },
      evaluate: {
        label: "Evaluation",
        description: "Question rewrite and evaluation prompts.",
      },
    },
    sources: {
      all: "All sources",
      org: "Org override",
      global: "Global default",
    },
    stages: {
      all: "All stages",
      problem: "Problem",
      market: "Market",
      tech: "Tech",
      report: "Report",
    },
    textareaLabel: "Override content",
  },
  zh: {
    actions: {
      publish: "发布覆盖版本",
      publishing: "发布中...",
      revert: "恢复默认模板",
      reverting: "恢复中...",
      viewDefault: "查看默认模板",
    },
    badges: {
      global: "全局默认",
      org: "组织覆盖",
      templates: "个模板",
    },
    browse: {
      description: "按用途、阶段或来源筛选。可按键名/内容搜索并按更新时间排序。",
      empty: "当前筛选条件下没有匹配的 Prompt 模板。",
      loading: "正在加载模板...",
      purpose: "用途",
      search: "搜索",
      searchPlaceholder: "按键名或内容搜索...",
      sort: "排序",
      sortOldest: "最早更新",
      sortRecent: "最近更新",
      source: "来源",
      stage: "阶段",
      title: "浏览模板",
    },
    errors: {
      accessDenied: "你没有管理 Prompt 模板的权限。",
      default: "无法更新 Prompt 模板。",
      network: "Prompt 模板服务暂时不可用，请稍后再试。",
      sessionExpired: "登录状态已过期，请重新登录。",
      unavailable: "Prompt 模板服务暂时不可用，请稍后再试。",
    },
    meta: {
      purpose: "用途",
      stage: "阶段",
      stages: "阶段",
      variant: "变体",
    },
    page: {
      eyebrow: "管理",
      subtitle: "发布组织级覆盖模板，同时保留默认模板作为回退。",
      title: "Prompt 模板",
    },
    purposes: {
      all: {
        label: "全部",
        description: "产品中的全部 Prompt 模板。",
      },
      chat: {
        label: "对话",
        description: "实时对话和追问 Prompt。",
      },
      report: {
        label: "报告",
        description: "报告生成和叙述 Prompt。",
      },
      summary: {
        label: "总结",
        description: "阶段总结和摘要 Prompt。",
      },
      score: {
        label: "评分",
        description: "DVF 评分和评估 Prompt。",
      },
      extract: {
        label: "抽取",
        description: "结构化抽取 Prompt。",
      },
      evaluate: {
        label: "评估",
        description: "问题改写和评估 Prompt。",
      },
    },
    sources: {
      all: "全部来源",
      org: "组织覆盖",
      global: "全局默认",
    },
    stages: {
      all: "全部阶段",
      problem: "问题",
      market: "市场",
      tech: "技术",
      report: "报告",
    },
    textareaLabel: "覆盖模板内容",
  },
} as const;

export type PromptMessages = (typeof PROMPT_MESSAGES)[keyof typeof PROMPT_MESSAGES];
