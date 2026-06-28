import { DEFAULT_APP_LOCALE, type AppLocale } from "@/lib/i18n/config";

export type WorkflowStep = {
  key: string;
  index: string;
  label: string;
  meta: string;
  description: string;
};

const WORKFLOW_STEPS_BY_LOCALE: Record<AppLocale, WorkflowStep[]> = {
  en: [
    {
      key: "problem",
      index: "01",
      label: "Problem fit",
      meta: "Stage 1 - Desirability",
      description:
        "Define the #1 problem, the priority user, and why the pain is urgent. Capture frequency, severity, and current alternatives to validate the gap.",
    },
    {
      key: "market",
      index: "02",
      label: "Market viability",
      meta: "Stage 2 - Viability",
      description:
        "Test the business model, pricing logic, and market size assumptions. Surface go-to-market risks and the experiments that can de-risk them.",
    },
    {
      key: "tech",
      index: "03",
      label: "Tech feasibility",
      meta: "Stage 3 - Feasibility",
      description:
        "Define MVP scope, architecture choices, and delivery constraints. Identify technical risks, compliance needs, and realistic mitigation steps.",
    },
    {
      key: "report",
      index: "04",
      label: "Report synthesis",
      meta: "Stage 4 - Report",
      description:
        "Consolidate findings into a clear report, rule-based DVF signals, and next-step recommendations. Highlight what to build, validate, and prioritize.",
    },
  ],
  zh: [
    {
      key: "problem",
      index: "01",
      label: "问题契合度",
      meta: "阶段 1 - 需求吸引力",
      description:
        "明确最关键的问题、优先用户，以及为什么这个痛点足够紧迫。记录出现频率、严重程度和当前替代方案，验证问题缺口是否真实存在。",
    },
    {
      key: "market",
      index: "02",
      label: "市场可行性",
      meta: "阶段 2 - 商业可行性",
      description:
        "检验商业模式、定价逻辑和市场规模假设，找出获客与进入市场的主要风险，并列出能够降低风险的实验。",
    },
    {
      key: "tech",
      index: "03",
      label: "技术可行性",
      meta: "阶段 3 - 技术可行性",
      description:
        "定义 MVP 范围、架构选择和交付限制，识别关键技术风险、合规要求以及现实可行的缓解方案。",
    },
    {
      key: "report",
      index: "04",
      label: "报告综合",
      meta: "阶段 4 - 报告",
      description:
        "将结论整理成清晰报告、规则化的 DVF 信号和下一步建议，明确接下来要构建、验证和优先处理的事项。",
    },
  ],
};

export const resolveWorkflowSteps = (locale: AppLocale): WorkflowStep[] =>
  WORKFLOW_STEPS_BY_LOCALE[locale] ?? WORKFLOW_STEPS_BY_LOCALE[DEFAULT_APP_LOCALE];

export const workflowSteps = resolveWorkflowSteps(DEFAULT_APP_LOCALE);
