"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  createPromptTemplate,
  fetchPromptTemplates,
  getPromptTemplatesErrorMessage,
  revertPromptTemplate,
  type PromptTemplate,
} from "@/features/admin/prompt-templates";
import { PROMPT_MESSAGES } from "@/features/admin/prompt-template-messages";
import {
  groupTemplates,
  parseStageList,
  type PromptGroup,
  type PurposeKey,
  type SourceKey,
  type StageKey,
} from "@/features/admin/prompt-template-view-model";
import { useAppLocale } from "@/lib/i18n/provider";
import { PromptTemplatesSurface } from "./prompt-templates-surface";

export function PromptTemplatesClient() {
  const locale = useAppLocale();
  const messageLocale = locale === "zh" ? "zh" : "en";
  const messages = PROMPT_MESSAGES[messageLocale];
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [purposeFilter, setPurposeFilter] = useState<PurposeKey>("all");
  const [stageFilter, setStageFilter] = useState<StageKey>("all");
  const [sourceFilter, setSourceFilter] = useState<SourceKey>("all");
  const [query, setQuery] = useState("");
  const [sortOrder, setSortOrder] = useState<"recent" | "oldest">("recent");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [revertingKey, setRevertingKey] = useState<string | null>(null);

  const groups = useMemo(() => groupTemplates(templates), [templates]);

  const purposeCounts = useMemo(() => {
    const counts: Record<PurposeKey, number> = {
      all: 0,
      chat: 0,
      report: 0,
      summary: 0,
      score: 0,
      extract: 0,
      evaluate: 0,
    };
    groups.forEach((group) => {
      const active = group.org ?? group.global;
      if (!active) {
        return;
      }
      const purpose = (active.purpose || "chat") as PurposeKey;
      counts.all += 1;
      if (counts[purpose] !== undefined) {
        counts[purpose] += 1;
      }
    });
    return counts;
  }, [groups]);

  const stageCounts = useMemo(() => {
    const counts: Record<StageKey, number> = {
      all: 0,
      problem: 0,
      market: 0,
      tech: 0,
      report: 0,
    };
    groups.forEach((group) => {
      const active = group.org ?? group.global;
      if (!active) {
        return;
      }
      counts.all += 1;
      const stages = parseStageList(active.stage);
      stages.forEach((stage) => {
        counts[stage] += 1;
      });
    });
    return counts;
  }, [groups]);

  const sourceCounts = useMemo(() => {
    const counts: Record<SourceKey, number> = {
      all: 0,
      org: 0,
      global: 0,
    };
    groups.forEach((group) => {
      const hasOrg = Boolean(group.org);
      counts.all += 1;
      if (hasOrg) {
        counts.org += 1;
      } else {
        counts.global += 1;
      }
    });
    return counts;
  }, [groups]);

  const filteredGroups = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const base = groups.filter((group) => {
      const active = group.org ?? group.global;
      if (!active) {
        return false;
      }
      const purpose = (active.purpose || "chat") as PurposeKey;
      if (purposeFilter !== "all" && purpose !== purposeFilter) {
        return false;
      }
      const stages = parseStageList(active.stage);
      if (stageFilter !== "all" && !stages.includes(stageFilter)) {
        return false;
      }
      if (sourceFilter === "org" && !group.org) {
        return false;
      }
      if (sourceFilter === "global" && group.org) {
        return false;
      }
      if (!normalizedQuery) {
        return true;
      }
      const haystack = `${group.key} ${active.content}`.toLowerCase();
      return haystack.includes(normalizedQuery);
    });
    const sorted = [...base];
    sorted.sort((a, b) => {
      const aTemplate = a.org ?? a.global;
      const bTemplate = b.org ?? b.global;
      const aDate = aTemplate?.updatedAt || aTemplate?.createdAt || "";
      const bDate = bTemplate?.updatedAt || bTemplate?.createdAt || "";
      const aTime = aDate ? Date.parse(aDate) : 0;
      const bTime = bDate ? Date.parse(bDate) : 0;
      if (sortOrder === "recent") {
        return bTime - aTime;
      }
      return aTime - bTime;
    });
    return sorted;
  }, [groups, purposeFilter, query, sortOrder, sourceFilter, stageFilter]);

  const groupedByPurpose = useMemo(() => {
    const map = new Map<PurposeKey, PromptGroup[]>();
    filteredGroups.forEach((group) => {
      const active = group.org ?? group.global;
      const purpose = (active?.purpose || "chat") as PurposeKey;
      const existing = map.get(purpose) ?? [];
      existing.push(group);
      map.set(purpose, existing);
    });
    return Array.from(map.entries()).sort((a, b) =>
      messages.purposes[a[0]].label.localeCompare(messages.purposes[b[0]].label)
    );
  }, [filteredGroups, messages]);

  const loadTemplates = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const data = await fetchPromptTemplates();
      setTemplates(data);
    } catch (error) {
      setLoadError(getPromptTemplatesErrorMessage(error, messages.errors));
    } finally {
      setIsLoading(false);
    }
  }, [messages.errors]);

  useEffect(() => {
    void loadTemplates();
  }, [loadTemplates]);

  useEffect(() => {
    setDrafts((prev) => {
      const next = { ...prev };
      groups.forEach((group) => {
        if (next[group.key] !== undefined) {
          return;
        }
        const active = group.org ?? group.global;
        if (active) {
          next[group.key] = active.content;
        }
      });
      return next;
    });
  }, [groups]);

  const handleDraftChange = (key: string, value: string) => {
    setDrafts((prev) => ({ ...prev, [key]: value }));
  };

  const handlePublish = async (group: PromptGroup) => {
    const base = group.org ?? group.global;
    if (!base) {
      return;
    }
    setActionError(null);
    setSavingKey(group.key);
    try {
      await createPromptTemplate(group.key, {
        content: drafts[group.key] ?? base.content,
        purpose: base.purpose,
        stage: base.stage,
        variant: base.variant,
      });
      await loadTemplates();
    } catch (error) {
      setActionError(getPromptTemplatesErrorMessage(error, messages.errors));
    } finally {
      setSavingKey(null);
    }
  };

  const handleRevert = async (group: PromptGroup) => {
    setActionError(null);
    setRevertingKey(group.key);
    try {
      const response = await revertPromptTemplate(group.key);
      if (response.effectiveTemplate) {
        setDrafts((prev) => ({
          ...prev,
          [group.key]: response.effectiveTemplate?.content ?? "",
        }));
      }
      await loadTemplates();
    } catch (error) {
      setActionError(getPromptTemplatesErrorMessage(error, messages.errors));
    } finally {
      setRevertingKey(null);
    }
  };

  return (
    <PromptTemplatesSurface
      actionError={actionError}
      drafts={drafts}
      groupedByPurpose={groupedByPurpose}
      isLoading={isLoading}
      loadError={loadError}
      messages={messages}
      onDraftChange={handleDraftChange}
      onPublish={handlePublish}
      onPurposeFilterChange={setPurposeFilter}
      onQueryChange={setQuery}
      onRevert={handleRevert}
      onSortOrderChange={setSortOrder}
      onSourceFilterChange={setSourceFilter}
      onStageFilterChange={setStageFilter}
      purposeCounts={purposeCounts}
      purposeFilter={purposeFilter}
      query={query}
      revertingKey={revertingKey}
      savingKey={savingKey}
      sortOrder={sortOrder}
      sourceCounts={sourceCounts}
      sourceFilter={sourceFilter}
      stageCounts={stageCounts}
      stageFilter={stageFilter}
    />
  );
}
