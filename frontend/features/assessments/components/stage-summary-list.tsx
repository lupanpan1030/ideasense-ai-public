"use client";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { StageSummarySnapshot } from "../api";
import { formatUpdatedAt, renderMarkdown, STAGE_LABELS } from "./stage-gate-utils";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";
import { getLocaleDisplayName } from "@/lib/i18n/artifact-locale";
import {
  hasAiAssistedCopy,
  normalizeLegacyAiAssistedCopy,
} from "@/lib/ai-assisted";

type StageSummaryListProps = {
  summaries: StageSummarySnapshot[];
  title?: string;
  stages?: string[];
  emptyLabel?: string;
};

const STAGE_ORDER = new Map([
  ["problem", 1],
  ["market", 2],
  ["tech", 3],
]);

const normalizeStage = (value: string) => value.trim().toLowerCase();

const resolveStageOrder = (stage: string) =>
  STAGE_ORDER.get(stage) ?? Number.MAX_SAFE_INTEGER;

const interpolate = (
  template: string,
  values: Record<string, string | number>
): string =>
  Object.entries(values).reduce(
    (result, [key, value]) => result.replaceAll(`{${key}}`, String(value)),
    template
  );

export function StageSummaryList({
  summaries,
  title,
  stages,
  emptyLabel,
}: StageSummaryListProps) {
  const locale = useAppLocale();
  const appMessages = useAppMessages();
  const messages = appMessages.stageSummaries;
  const summaryMap = new Map(
    summaries.map((entry) => [normalizeStage(entry.stage), entry])
  );

  const requestedStages = stages?.length
    ? stages.map(normalizeStage)
    : Array.from(summaryMap.keys());

  const uniqueStages = Array.from(new Set(requestedStages)).sort((left, right) => {
    const orderDelta = resolveStageOrder(left) - resolveStageOrder(right);
    return orderDelta !== 0 ? orderDelta : left.localeCompare(right);
  });

  if (!uniqueStages.length) {
    return null;
  }

  return (
    <section className="space-y-3">
      {title ? (
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
          <span className="font-medium text-foreground">{title}</span>
        </div>
      ) : null}
      <div className="grid gap-4">
        {uniqueStages.map((stageKey) => {
          const summary = summaryMap.get(stageKey) ?? null;
          const markdown = (summary?.finalSummaryMarkdown || summary?.draftSummaryMarkdown || "").trim();
          const hasAiAssist = hasAiAssistedCopy(markdown);
          const cleanedMarkdown = normalizeLegacyAiAssistedCopy(markdown) || markdown;
          const updatedLabel = summary?.updatedAt
            ? formatUpdatedAt(summary.updatedAt, {
                locale,
                prefix: messages.updatedPrefix,
                unknownLabel: messages.updatedUnknown,
              })
            : null;
          const stageMeta =
            messages.stages[stageKey as keyof typeof messages.stages] ?? null;
          const stageLabel = stageMeta?.tabLabel ?? STAGE_LABELS[stageKey] ?? stageKey;
          const activeLocale = summary?.confirmed
            ? summary.finalOutputLocale ?? summary.draftOutputLocale
            : summary?.draftOutputLocale ?? summary?.finalOutputLocale ?? null;
          const activeLocaleLabel = getLocaleDisplayName(appMessages, activeLocale);
          const showLocaleNotice =
            activeLocale && activeLocale !== locale && activeLocaleLabel;
          const localeNote =
            showLocaleNotice
              ? interpolate(messages.localeNotice.mismatchDescription, {
                  locale: activeLocaleLabel,
                })
              : null;
          const badgeLabel = summary
            ? summary.confirmed
              ? messages.badges.confirmed
              : messages.badges.draft
            : messages.badges.missing;
          const badgeVariant = summary
            ? summary.confirmed
              ? "success"
              : "warning"
            : "outline";

          return (
            <Card key={stageKey} variant="soft">
              <CardHeader className="pb-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <CardTitle className="text-base">
                    {stageLabel}
                  </CardTitle>
                  <div className="flex flex-wrap items-center gap-2">
                    {showLocaleNotice ? (
                      <Badge variant="outline">
                        {messages.localeNotice.badgePrefix}: {activeLocaleLabel}
                      </Badge>
                    ) : null}
                    {hasAiAssist ? (
                      <Badge variant="info">{messages.aiAssistedBadge}</Badge>
                    ) : null}
                    <Badge variant={badgeVariant}>{badgeLabel}</Badge>
                  </div>
                </div>
                {updatedLabel ? (
                  <CardDescription>{updatedLabel}</CardDescription>
                ) : null}
                {localeNote ? (
                  <CardDescription>{localeNote}</CardDescription>
                ) : null}
              </CardHeader>
              <CardContent className="pt-0">
                {markdown ? (
                  <div
                    className="markdown-preview"
                    dangerouslySetInnerHTML={{ __html: renderMarkdown(cleanedMarkdown) }}
                  />
                ) : (
                  <p className="text-xs italic text-muted-foreground">
                    {emptyLabel ?? messages.unavailable}
                  </p>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </section>
  );
}
