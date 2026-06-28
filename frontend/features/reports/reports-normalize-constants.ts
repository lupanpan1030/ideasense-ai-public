export const REPORT_STAGE_SUMMARIES = [
  {
    stage: "problem",
    label: "Stage 1",
    title: "Problem framing",
    placeholder: "Awaiting Stage 1 summary.",
  },
  {
    stage: "market",
    label: "Stage 2",
    title: "Market & business model",
    placeholder: "Awaiting Stage 2 summary.",
  },
  {
    stage: "tech",
    label: "Stage 3",
    title: "Feasibility & architecture",
    placeholder: "Awaiting Stage 3 summary.",
  },
] as const;

export const LEAN_CANVAS_FIELDS = [
  { key: "problem", label: "problem" },
  { key: "customer_segments", label: "customerSegments" },
  { key: "unique_value_proposition", label: "uniqueValueProposition" },
  { key: "solution", label: "solution" },
  { key: "channels", label: "channels" },
  { key: "revenue_streams", label: "revenueStreams" },
  { key: "cost_structure", label: "costStructure" },
  { key: "key_metrics", label: "keyMetrics" },
  { key: "unfair_advantage", label: "unfairAdvantage" },
] as const;

export const STAGE_ORDER: Record<string, number> = {
  problem: 0,
  market: 1,
  tech: 2,
  report: 3,
};
