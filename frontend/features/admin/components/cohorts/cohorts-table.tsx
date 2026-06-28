"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiClient } from "@/lib/api/client";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";
import {
  buildCohortsQuery,
  DEFAULT_COHORTS_LIMIT,
  resolveCohortIntlLocale,
  type AdminCohortsMessages,
  type CohortCreatePayload,
  type CohortStatusFilter,
  type CohortsResponse,
  type CohortSummary,
} from "@/features/admin/admin-cohorts-view-model";
import { CreateCohortModal } from "./cohort-modals";
import { CohortsTableSurface } from "./cohorts-table-surface";

const getCohortsErrorMessage = (
  error: unknown,
  messages: AdminCohortsMessages
): string => {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return messages.errors.expiredSession;
    }
    if (error.status === 403) {
      return messages.errors.noAccess;
    }
    if (error.status >= 500) {
      return messages.errors.unavailable;
    }
  }
  return messages.errors.loadFailed;
};

const getCohortActionErrorMessage = (
  error: unknown,
  messages: AdminCohortsMessages
): string => {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return messages.errors.expiredSession;
    }
    if (error.status === 403) {
      return messages.errors.noAccess;
    }
    if (error.status === 409) {
      return messages.errors.updateConflict;
    }
    if (error.status >= 500) {
      return messages.errors.updateUnavailable;
    }
  }
  return messages.errors.updateFailed;
};

const fetchCohorts = async (
  page: number,
  statusFilter: CohortStatusFilter,
  query: string
): Promise<CohortsResponse> => {
  const queryString = buildCohortsQuery(page, statusFilter, query);
  const url = queryString ? `/admin-api/cohorts?${queryString}` : "/admin-api/cohorts";
  return apiClient.fetchJson<CohortsResponse>(url);
};

const createCohort = async (
  payload: CohortCreatePayload
): Promise<CohortSummary> =>
  apiClient.postJson<CohortSummary>("/admin-api/cohorts", payload);

const updateCohort = async (
  cohortId: string,
  payload: { is_archived: boolean }
): Promise<CohortSummary> =>
  apiClient.postJson<CohortSummary>(`/admin-api/cohorts/${cohortId}`, payload, {
    method: "PATCH",
  });

export function CohortsTable() {
  const locale = useAppLocale();
  const appMessages = useAppMessages();
  const messages = appMessages.adminCohorts;
  const timelineMessages = appMessages.adminShared.timeline;
  const intlLocale = resolveCohortIntlLocale(locale);
  const router = useRouter();
  const [cohorts, setCohorts] = useState<CohortSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<CohortStatusFilter>("active");
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [pendingArchive, setPendingArchive] = useState<Record<string, boolean>>({});
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [nameInput, setNameInput] = useState("");
  const [descriptionInput, setDescriptionInput] = useState("");
  const [startAtInput, setStartAtInput] = useState("");
  const [endAtInput, setEndAtInput] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setDebouncedQuery(query.trim());
    }, 300);
    return () => window.clearTimeout(handle);
  }, [query]);

  useEffect(() => {
    setPage(1);
  }, [query, statusFilter]);

  useEffect(() => {
    let isActive = true;
    setIsLoading(true);
    setLoadError(null);
    fetchCohorts(page, statusFilter, debouncedQuery)
      .then((response) => {
        if (!isActive) {
          return;
        }
        setCohorts(response.cohorts ?? []);
        setTotal(response.total ?? 0);
      })
      .catch((error) => {
        if (!isActive) {
          return;
        }
        setLoadError(getCohortsErrorMessage(error, messages));
      })
      .finally(() => {
        if (!isActive) {
          return;
        }
        setIsLoading(false);
      });
    return () => {
      isActive = false;
    };
  }, [page, statusFilter, debouncedQuery, messages]);

  useEffect(() => {
    if (!toastMessage) {
      return;
    }
    const timeout = window.setTimeout(() => setToastMessage(null), 2400);
    return () => window.clearTimeout(timeout);
  }, [toastMessage]);

  useEffect(() => {
    if (total === 0) {
      return;
    }
    const nextTotalPages = Math.max(
      1,
      Math.ceil(total / DEFAULT_COHORTS_LIMIT)
    );
    if (page > nextTotalPages) {
      setPage(nextTotalPages);
    }
  }, [total, page]);

  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(total / DEFAULT_COHORTS_LIMIT)),
    [total]
  );
  const canGoBack = page > 1;
  const canGoForward = page < totalPages;
  const pageStart =
    total === 0 ? 0 : (page - 1) * DEFAULT_COHORTS_LIMIT + 1;
  const pageEnd = Math.min(page * DEFAULT_COHORTS_LIMIT, total);

  const handleRowClick = (cohortId: string) => {
    router.push(buildLocalePath(locale, `/admin/cohorts/${cohortId}`));
  };

  const handleArchiveToggle = async (cohort: CohortSummary) => {
    if (pendingArchive[cohort.id]) {
      return;
    }
    setActionError(null);
    setPendingArchive((prev) => ({ ...prev, [cohort.id]: true }));
    try {
      await updateCohort(cohort.id, { is_archived: !cohort.is_archived });
      setToastMessage(
        cohort.is_archived ? messages.toasts.unarchived : messages.toasts.archived
      );
      const response = await fetchCohorts(page, statusFilter, debouncedQuery);
      setCohorts(response.cohorts ?? []);
      setTotal(response.total ?? 0);
    } catch (error) {
      setActionError(getCohortActionErrorMessage(error, messages));
    } finally {
      setPendingArchive((prev) => {
        const next = { ...prev };
        delete next[cohort.id];
        return next;
      });
    }
  };

  const resetCreateForm = () => {
    setNameInput("");
    setDescriptionInput("");
    setStartAtInput("");
    setEndAtInput("");
    setFormError(null);
    setSubmitError(null);
  };

  const handleOpenCreate = () => {
    resetCreateForm();
    setIsCreateOpen(true);
  };

  const handleCreateSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);
    setSubmitError(null);

    const trimmedName = nameInput.trim();
    if (!trimmedName) {
      setFormError(messages.errors.nameRequired);
      return;
    }

    setIsSubmitting(true);
    try {
      await createCohort({
        name: trimmedName,
        description: descriptionInput.trim() || null,
        start_at: startAtInput || null,
        end_at: endAtInput || null,
      });
      setIsCreateOpen(false);
      resetCreateForm();
      setToastMessage(messages.toasts.created);
      setPage(1);
      const response = await fetchCohorts(1, statusFilter, debouncedQuery);
      setCohorts(response.cohorts ?? []);
      setTotal(response.total ?? 0);
    } catch (error) {
      setSubmitError(getCohortActionErrorMessage(error, messages));
    } finally {
      setIsSubmitting(false);
    }
  };

  const statusFilterOptions = useMemo(
    () => [
      { value: "active", label: messages.filters.statusOptions.active },
      { value: "archived", label: messages.filters.statusOptions.archived },
      { value: "all", label: messages.filters.statusOptions.all },
    ] satisfies Array<{ value: CohortStatusFilter; label: string }>,
    [messages]
  );

  return (
    <>
      <CohortsTableSurface
        actionError={actionError}
        canGoBack={canGoBack}
        canGoForward={canGoForward}
        cohorts={cohorts}
        intlLocale={intlLocale}
        isLoading={isLoading}
        loadError={loadError}
        locale={locale}
        messages={messages}
        onArchiveToggle={handleArchiveToggle}
        onCreateOpen={handleOpenCreate}
        onNextPage={() => setPage(page + 1)}
        onPreviousPage={() => setPage(Math.max(page - 1, 1))}
        onQueryChange={setQuery}
        onRowClick={handleRowClick}
        onStatusFilterChange={setStatusFilter}
        page={page}
        pageEnd={pageEnd}
        pageStart={pageStart}
        pendingArchive={pendingArchive}
        query={query}
        statusFilter={statusFilter}
        statusFilterOptions={statusFilterOptions}
        timelineMessages={timelineMessages}
        toastMessage={toastMessage}
        total={total}
        totalPages={totalPages}
      />
      <CreateCohortModal
        descriptionInput={descriptionInput}
        endAtInput={endAtInput}
        formError={formError}
        isOpen={isCreateOpen}
        isSubmitting={isSubmitting}
        messages={messages}
        nameInput={nameInput}
        onClose={() => setIsCreateOpen(false)}
        onDescriptionChange={setDescriptionInput}
        onEndAtChange={setEndAtInput}
        onNameChange={setNameInput}
        onStartAtChange={setStartAtInput}
        onSubmit={handleCreateSubmit}
        startAtInput={startAtInput}
        submitError={submitError}
      />
    </>
  );
}
