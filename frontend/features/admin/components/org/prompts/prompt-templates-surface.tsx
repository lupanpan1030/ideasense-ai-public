import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { PromptMessages } from "@/features/admin/prompt-template-messages";
import {
  formatStageLabel,
  PURPOSE_KEYS,
  SOURCE_KEYS,
  STAGE_KEYS,
  type PromptGroup,
  type PurposeKey,
  type SourceKey,
  type StageKey,
} from "@/features/admin/prompt-template-view-model";

type PromptTemplatesSurfaceProps = {
  actionError: string | null;
  drafts: Record<string, string>;
  groupedByPurpose: Array<[PurposeKey, PromptGroup[]]>;
  isLoading: boolean;
  loadError: string | null;
  messages: PromptMessages;
  onDraftChange: (key: string, value: string) => void;
  onPublish: (group: PromptGroup) => void;
  onPurposeFilterChange: (value: PurposeKey) => void;
  onQueryChange: (value: string) => void;
  onRevert: (group: PromptGroup) => void;
  onSortOrderChange: (value: "recent" | "oldest") => void;
  onSourceFilterChange: (value: SourceKey) => void;
  onStageFilterChange: (value: StageKey) => void;
  purposeCounts: Record<PurposeKey, number>;
  purposeFilter: PurposeKey;
  query: string;
  revertingKey: string | null;
  savingKey: string | null;
  sortOrder: "recent" | "oldest";
  sourceCounts: Record<SourceKey, number>;
  sourceFilter: SourceKey;
  stageCounts: Record<StageKey, number>;
  stageFilter: StageKey;
};

export function PromptTemplatesSurface({
  actionError,
  drafts,
  groupedByPurpose,
  isLoading,
  loadError,
  messages,
  onDraftChange,
  onPublish,
  onPurposeFilterChange,
  onQueryChange,
  onRevert,
  onSortOrderChange,
  onSourceFilterChange,
  onStageFilterChange,
  purposeCounts,
  purposeFilter,
  query,
  revertingKey,
  savingKey,
  sortOrder,
  sourceCounts,
  sourceFilter,
  stageCounts,
  stageFilter,
}: PromptTemplatesSurfaceProps) {
  return (
    <div className="page">
      <div className="page-header">
        <div className="stack-sm">
          <p className="eyebrow">{messages.page.eyebrow}</p>
          <h1 className="page-title">{messages.page.title}</h1>
          <p className="page-subtitle">{messages.page.subtitle}</p>
        </div>
      </div>

      {loadError ? (
        <div className="alert" role="alert">
          <span>{loadError}</span>
        </div>
      ) : null}
      {actionError ? (
        <div className="alert" role="alert">
          <span>{actionError}</span>
        </div>
      ) : null}

      {isLoading ? (
        <div className="card">
          <div className="card__body">{messages.browse.loading}</div>
        </div>
      ) : (
        <div className="admin-org-stack">
          <Card>
            <CardHeader className="stack-sm">
              <CardTitle>{messages.browse.title}</CardTitle>
              <CardDescription>{messages.browse.description}</CardDescription>
            </CardHeader>
            <CardContent className="stack-sm">
              <div className="admin-prompts__toolbar">
                <div className="admin-prompts__filters">
                  <div className="admin-prompts__filter-group">
                    <p className="field__label" id="prompt-purpose-filter-label">
                      {messages.browse.purpose}
                    </p>
                    <div
                      className="admin-tabs admin-prompts__tabs"
                      role="group"
                      aria-labelledby="prompt-purpose-filter-label"
                    >
                      {PURPOSE_KEYS.map((key) => (
                        <button
                          key={key}
                          type="button"
                          aria-pressed={key === purposeFilter}
                          className={[
                            "admin-tab",
                            key === purposeFilter ? "admin-tab--active" : "",
                          ]
                            .filter(Boolean)
                            .join(" ")}
                          onClick={() => onPurposeFilterChange(key)}
                        >
                          {messages.purposes[key].label} ({purposeCounts[key] ?? 0})
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="admin-prompts__filter-group">
                    <p className="field__label" id="prompt-stage-filter-label">
                      {messages.browse.stage}
                    </p>
                    <div
                      className="admin-tabs admin-prompts__tabs"
                      role="group"
                      aria-labelledby="prompt-stage-filter-label"
                    >
                      {STAGE_KEYS.map((key) => (
                        <button
                          key={key}
                          type="button"
                          aria-pressed={key === stageFilter}
                          className={[
                            "admin-tab",
                            key === stageFilter ? "admin-tab--active" : "",
                          ]
                            .filter(Boolean)
                            .join(" ")}
                          onClick={() => onStageFilterChange(key)}
                        >
                          {messages.stages[key]} ({stageCounts[key] ?? 0})
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="admin-prompts__filter-group">
                    <p className="field__label" id="prompt-source-filter-label">
                      {messages.browse.source}
                    </p>
                    <div
                      className="admin-tabs admin-prompts__tabs"
                      role="group"
                      aria-labelledby="prompt-source-filter-label"
                    >
                      {SOURCE_KEYS.map((key) => (
                        <button
                          key={key}
                          type="button"
                          aria-pressed={key === sourceFilter}
                          className={[
                            "admin-tab",
                            key === sourceFilter ? "admin-tab--active" : "",
                          ]
                            .filter(Boolean)
                            .join(" ")}
                          onClick={() => onSourceFilterChange(key)}
                        >
                          {messages.sources[key]} ({sourceCounts[key] ?? 0})
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="admin-prompts__search-row">
                  <Input
                    id="prompt-search"
                    label={messages.browse.search}
                    className="admin-prompts__search"
                    inputClassName="admin-prompts__search-input"
                    value={query}
                    onChange={(event) => onQueryChange(event.target.value)}
                    placeholder={messages.browse.searchPlaceholder}
                  />
                  <div className="field admin-prompts__sort">
                    <label className="field__label" htmlFor="prompt-sort">
                      {messages.browse.sort}
                    </label>
                    <select
                      id="prompt-sort"
                      className="input"
                      value={sortOrder}
                      onChange={(event) =>
                        onSortOrderChange(
                          event.target.value === "oldest" ? "oldest" : "recent"
                        )
                      }
                    >
                      <option value="recent">{messages.browse.sortRecent}</option>
                      <option value="oldest">{messages.browse.sortOldest}</option>
                    </select>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {groupedByPurpose.length === 0 ? (
            <div className="admin-projects__empty" role="status">
              {messages.browse.empty}
            </div>
          ) : null}

          {groupedByPurpose.map(([purpose, purposeGroups]) => (
            <section key={purpose} className="admin-prompts__section">
              <div className="admin-prompts__section-header">
                <div className="stack-sm">
                  <h2 className="section-title">
                    {messages.purposes[purpose].label}
                  </h2>
                  <p className="text-muted">
                    {messages.purposes[purpose].description}
                  </p>
                </div>
                <Badge variant="secondary">
                  {purposeGroups.length} {messages.badges.templates}
                </Badge>
              </div>
              <div className="admin-prompts__grid">
                {purposeGroups.map((group) => {
                  const orgTemplate = group.org;
                  const defaultTemplate = group.global;
                  const activeTemplate = orgTemplate ?? defaultTemplate;
                  if (!activeTemplate) {
                    return null;
                  }
                  const isSaving = savingKey === group.key;
                  const isReverting = revertingKey === group.key;
                  const stageLabel = formatStageLabel(activeTemplate.stage, messages);
                  return (
                    <Card key={group.key}>
                      <CardHeader className="stack-sm">
                        <div className="stack-sm">
                          <CardTitle>{group.key}</CardTitle>
                          <CardDescription>
                            {messages.meta.purpose}: {activeTemplate.purpose}
                            {stageLabel ? ` · ${stageLabel}` : ""}
                            {activeTemplate.variant
                              ? ` · ${messages.meta.variant}: ${activeTemplate.variant}`
                              : ""}
                          </CardDescription>
                        </div>
                        <div className="cluster-tight">
                          <Badge variant={orgTemplate ? "default" : "secondary"}>
                            {orgTemplate
                              ? messages.badges.org
                              : messages.badges.global}
                          </Badge>
                          <Badge variant="outline">v{activeTemplate.version}</Badge>
                        </div>
                      </CardHeader>
                      <CardContent className="stack-sm">
                        <div className="stack-sm">
                          <label
                            className="field__label"
                            htmlFor={`prompt-${group.key}`}
                          >
                            {messages.textareaLabel}
                          </label>
                          <textarea
                            id={`prompt-${group.key}`}
                            className="textarea admin-org-settings__editor"
                            value={drafts[group.key] ?? ""}
                            onChange={(event) =>
                              onDraftChange(group.key, event.target.value)
                            }
                            rows={8}
                          />
                        </div>
                        <div className="cluster">
                          <Button
                            onClick={() => onPublish(group)}
                            disabled={isSaving}
                          >
                            {isSaving
                              ? messages.actions.publishing
                              : messages.actions.publish}
                          </Button>
                          {orgTemplate ? (
                            <Button
                              variant="ghost"
                              onClick={() => onRevert(group)}
                              disabled={isReverting}
                            >
                              {isReverting
                                ? messages.actions.reverting
                                : messages.actions.revert}
                            </Button>
                          ) : null}
                        </div>
                        {defaultTemplate ? (
                          <details className="admin-advanced">
                            <summary className="admin-advanced__summary">
                              <span className="admin-advanced__title">
                                {messages.actions.viewDefault}
                              </span>
                              <span className="admin-advanced__chip">
                                v{defaultTemplate.version}
                              </span>
                            </summary>
                            <div className="admin-advanced__card">
                              <pre className="admin-prompt-code">
                                {defaultTemplate.content}
                              </pre>
                            </div>
                          </details>
                        ) : null}
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
