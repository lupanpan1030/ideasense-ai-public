"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ApiError } from "@/lib/api/client";
import {
  createDraftQuestionBank,
  fetchActiveQuestionBankDetail,
  fetchDraftQuestionBank,
  getQuestionBankAdminErrorMessage,
  importDraftJson,
  importDraftYaml,
  publishDraftQuestionBank,
  reorderDraftQuestions,
  updateDraftQuestion,
  type QuestionBankDraft,
  type QuestionBankQuestion,
  type QuestionBankVersion,
  type QuestionUpdatePayload,
} from "@/features/admin/question-banks";
import {
  DEFAULT_BANK_KEY,
  QUESTION_BANK_MESSAGES,
  STAGE_ORDER,
  TAB_STORAGE_KEY,
} from "@/features/admin/question-bank-messages";
import {
  parseQuestionBankJson as parseJson,
  questionBankListToText as listToText,
  questionBankTextToList as textToList,
  safeQuestionBankJsonStringify as safeJsonStringify,
} from "@/features/admin/question-bank-view-model";
import { QuestionBankQuestionsPanel } from "@/features/admin/components/org/question-banks/question-bank-questions-panel";
import {
  QuestionBankImportPanel,
  QuestionBankModeBanner,
  QuestionBankOverviewPanel,
  QuestionBankReorderPanel,
  QuestionBankStatusAlerts,
  QuestionBankTabs,
  type ImportFormat,
  type ImportMode,
  type QuestionTabKey,
} from "@/features/admin/components/org/question-banks/question-bank-panels";
import { useAppLocale } from "@/lib/i18n/provider";

type LoadState = "idle" | "loading" | "ready" | "error";

export function QuestionBankManager() {
  const locale = useAppLocale();
  const messageLocale = locale === "zh" ? "zh" : "en";
  const messages = QUESTION_BANK_MESSAGES[messageLocale];
  const [bankKeyInput, setBankKeyInput] = useState(DEFAULT_BANK_KEY);
  const [bankKey, setBankKey] = useState(DEFAULT_BANK_KEY);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);
  const [activeVersion, setActiveVersion] = useState<QuestionBankVersion | null>(
    null
  );
  const [activeDetail, setActiveDetail] = useState<QuestionBankDraft | null>(
    null
  );
  const [draft, setDraft] = useState<QuestionBankDraft | null>(null);
  const [selectedQuestionId, setSelectedQuestionId] = useState<string | null>(null);
  const [isWorking, setIsWorking] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [activeTab, setActiveTab] = useState<QuestionTabKey>("questions");
  const [searchQuery, setSearchQuery] = useState("");
  const [stageFilter, setStageFilter] = useState("all");

  const [questionTitle, setQuestionTitle] = useState("");
  const [questionType, setQuestionType] = useState("");
  const [questionPrompt, setQuestionPrompt] = useState("");
  const [questionStandard, setQuestionStandard] = useState("");
  const [questionConsultant, setQuestionConsultant] = useState("");
  const [questionInstruction, setQuestionInstruction] = useState("");
  const [questionValidation, setQuestionValidation] = useState("");
  const [questionSchemaPaths, setQuestionSchemaPaths] = useState("");
  const [questionKeyPoints, setQuestionKeyPoints] = useState("");
  const [questionPromptMeta, setQuestionPromptMeta] = useState("{}");
  const [questionNotes, setQuestionNotes] = useState("");
  const [questionError, setQuestionError] = useState<string | null>(null);

  const [importFormat, setImportFormat] = useState<ImportFormat>("yaml");
  const [importMode, setImportMode] = useState<ImportMode>("replace");
  const [importBody, setImportBody] = useState("");

  const [reorderStage, setReorderStage] = useState("");
  const [reorderVariant, setReorderVariant] = useState("");
  const [reorderList, setReorderList] = useState("");
  const [reorderError, setReorderError] = useState<string | null>(null);

  const currentQuestions = useMemo(() => {
    if (isEditing && draft) {
      return draft.questions;
    }
    return activeDetail?.questions ?? [];
  }, [activeDetail, draft, isEditing]);

  const stageOptions = useMemo(() => {
    const stages = new Set(currentQuestions.map((question) => question.stage));
    return Array.from(stages).sort(
      (a, b) => STAGE_ORDER.indexOf(a) - STAGE_ORDER.indexOf(b)
    );
  }, [currentQuestions]);

  const filteredQuestions = useMemo(() => {
    const normalizedQuery = searchQuery.trim().toLowerCase();
    if (!normalizedQuery && stageFilter === "all") {
      return currentQuestions;
    }
    return currentQuestions.filter((question) => {
      if (stageFilter !== "all" && question.stage !== stageFilter) {
        return false;
      }
      if (!normalizedQuery) {
        return true;
      }
      const haystack = [
        question.questionId,
        question.title,
        question.prompt,
        question.standardQuestion,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(normalizedQuery);
    });
  }, [currentQuestions, searchQuery, stageFilter]);

  const groupedQuestions = useMemo(() => {
    if (!filteredQuestions.length) {
      return [];
    }
    const groups = new Map<string, QuestionBankQuestion[]>();
    filteredQuestions.forEach((question) => {
      const key = `${question.stage}::${question.variant}`;
      const existing = groups.get(key) ?? [];
      existing.push(question);
      groups.set(key, existing);
    });
    return Array.from(groups.entries())
      .map(([key, questions]) => {
        const [stage, variant] = key.split("::");
        return {
          stage,
          variant,
          questions: [...questions].sort(
            (a, b) => a.orderIndex - b.orderIndex
          ),
        };
      })
      .sort((a, b) => {
        const stageCompare =
          STAGE_ORDER.indexOf(a.stage) - STAGE_ORDER.indexOf(b.stage);
        if (stageCompare !== 0) {
          return stageCompare;
        }
        return a.variant.localeCompare(b.variant);
      });
  }, [filteredQuestions]);

  const reorderStages = useMemo(
    () => Array.from(new Set(currentQuestions.map((question) => question.stage))),
    [currentQuestions]
  );

  const reorderVariants = useMemo(
    () =>
      groupedQuestions
        .filter((group) => group.stage === reorderStage)
        .map((group) => group.variant),
    [groupedQuestions, reorderStage]
  );

  const selectedQuestion = useMemo(() => {
    if (!filteredQuestions.length || !selectedQuestionId) {
      return null;
    }
    return (
      filteredQuestions.find(
        (question) => question.questionId === selectedQuestionId
      ) ?? null
    );
  }, [filteredQuestions, selectedQuestionId]);

  const loadBank = useCallback(
    async (requestedKey: string) => {
      const normalizedKey = requestedKey.trim().toLowerCase();
      if (!normalizedKey) {
        setLoadError(messages.bank.required);
        setLoadState("error");
        return;
      }

      setLoadState("loading");
      setLoadError(null);
      setActionNotice(null);
      setActionError(null);
      setActiveVersion(null);
      setActiveDetail(null);
      setDraft(null);
      setSelectedQuestionId(null);
      setIsEditing(false);
      setActiveTab("questions");

      try {
        const active = await fetchActiveQuestionBankDetail(normalizedKey, true);
        setActiveDetail(active);
        setActiveVersion(active.version);
        if (active.questions.length) {
          setSelectedQuestionId(active.questions[0].questionId);
        }
      } catch (error) {
        setLoadError(
          getQuestionBankAdminErrorMessage(error, messages.errors.questionBank)
        );
        setLoadState("error");
        return;
      }

      setBankKey(normalizedKey);
      setLoadState("ready");
    },
    [messages]
  );

  useEffect(() => {
    loadBank(DEFAULT_BANK_KEY);
  }, [loadBank]);

  useEffect(() => {
    if (!filteredQuestions.length) {
      setSelectedQuestionId(null);
      return;
    }
    if (
      !selectedQuestionId ||
      !filteredQuestions.some(
        (question) => question.questionId === selectedQuestionId
      )
    ) {
      setSelectedQuestionId(filteredQuestions[0].questionId);
    }
  }, [filteredQuestions, selectedQuestionId]);

  useEffect(() => {
    if (stageFilter !== "all" && !stageOptions.includes(stageFilter)) {
      setStageFilter("all");
    }
  }, [stageFilter, stageOptions]);

  useEffect(() => {
    const saved = window.localStorage.getItem(TAB_STORAGE_KEY);
    if (
      saved === "overview" ||
      saved === "questions" ||
      saved === "import" ||
      saved === "reorder"
    ) {
      setActiveTab(saved);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(TAB_STORAGE_KEY, activeTab);
  }, [activeTab]);

  useEffect(() => {
    if (!selectedQuestion) {
      setQuestionTitle("");
      setQuestionType("");
      setQuestionPrompt("");
      setQuestionStandard("");
      setQuestionConsultant("");
      setQuestionInstruction("");
      setQuestionValidation("");
      setQuestionSchemaPaths("");
      setQuestionKeyPoints("");
      setQuestionPromptMeta("{}");
      setQuestionNotes("");
      setQuestionError(null);
      return;
    }
    setQuestionTitle(selectedQuestion.title ?? "");
    setQuestionType(selectedQuestion.typeRaw ?? "");
    setQuestionPrompt(selectedQuestion.prompt ?? "");
    setQuestionStandard(selectedQuestion.standardQuestion ?? "");
    setQuestionConsultant(selectedQuestion.consultantTactic ?? "");
    setQuestionInstruction(selectedQuestion.instruction ?? "");
    setQuestionValidation(selectedQuestion.validationRule ?? "");
    setQuestionSchemaPaths(listToText(selectedQuestion.schemaPaths));
    setQuestionKeyPoints(listToText(selectedQuestion.expectedKeyPoints));
    setQuestionPromptMeta(safeJsonStringify(selectedQuestion.promptMeta));
    setQuestionNotes(selectedQuestion.notes ?? "");
    setQuestionError(null);
  }, [selectedQuestion]);

  useEffect(() => {
    if (!groupedQuestions.length) {
      setReorderStage("");
      setReorderVariant("");
      setReorderList("");
      return;
    }
    const current =
      groupedQuestions.find(
        (group) =>
          group.stage === reorderStage && group.variant === reorderVariant
      ) ?? groupedQuestions[0];
    setReorderStage(current.stage);
    setReorderVariant(current.variant);
    setReorderList(listToText(current.questions.map((q) => q.questionId)));
  }, [groupedQuestions, reorderStage, reorderVariant]);

  const ensureDraft = useCallback(async () => {
    try {
      const draftData = await fetchDraftQuestionBank(bankKey, true);
      setDraft(draftData);
      return draftData;
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        await createDraftQuestionBank(bankKey);
        const draftData = await fetchDraftQuestionBank(bankKey, true);
        setDraft(draftData);
        return draftData;
      }
      throw error;
    }
  }, [bankKey]);

  const handleEnterEdit = async () => {
    if (isWorking || !activeDetail) {
      return;
    }
    if (
      !window.confirm(messages.confirmEnterEdit)
    ) {
      return;
    }
    setIsWorking(true);
    setActionError(null);
    setActionNotice(null);
    try {
      const draftData = await ensureDraft();
      setIsEditing(true);
      setActiveTab("questions");
      if (draftData.questions.length) {
        setSelectedQuestionId(draftData.questions[0].questionId);
      }
    } catch (error) {
      setActionError(
        getQuestionBankAdminErrorMessage(error, messages.errors.questionBank)
      );
    } finally {
      setIsWorking(false);
    }
  };

  const handleExitEdit = () => {
    setIsEditing(false);
  };

  const handleLoad = () => {
    loadBank(bankKeyInput);
  };

  const handlePublish = async () => {
    if (!draft || isWorking || !isEditing) {
      return;
    }
    setIsWorking(true);
    setActionError(null);
    setActionNotice(null);
    try {
      await publishDraftQuestionBank(bankKey, {});
      await loadBank(bankKey);
      setIsEditing(false);
      setActionNotice(messages.alerts.draftPublished);
    } catch (error) {
      setActionError(
        getQuestionBankAdminErrorMessage(error, messages.errors.questionBank)
      );
    } finally {
      setIsWorking(false);
    }
  };

  const handleQuestionSave = async () => {
    if (!selectedQuestion || isWorking || !isEditing) {
      return;
    }
    setIsWorking(true);
    setQuestionError(null);
    setActionNotice(null);
    try {
      const payload: QuestionUpdatePayload = {
        title: questionTitle.trim() || null,
        type_raw: questionType.trim() || null,
        prompt: questionPrompt.trim() || null,
        standard_question: questionStandard.trim() || null,
        consultant_tactic: questionConsultant.trim() || null,
        instruction: questionInstruction.trim() || null,
        validation_rule: questionValidation.trim() || null,
        schema_paths: textToList(questionSchemaPaths),
        expected_key_points: textToList(questionKeyPoints),
        prompt_meta: parseJson(
          questionPromptMeta,
          messages.editor.promptMetaObject
        ),
        notes: questionNotes.trim() || null,
      };
      const updated = await updateDraftQuestion(
        bankKey,
        selectedQuestion.questionId,
        payload
      );
      setDraft((prev) => {
        if (!prev) {
          return prev;
        }
        return {
          ...prev,
          questions: prev.questions.map((question) =>
            question.questionId === updated.questionId ? updated : question
          ),
        };
      });
      setActionNotice(messages.alerts.questionUpdated);
    } catch (error) {
      if (
        error instanceof Error &&
        error.message === messages.editor.promptMetaObject
      ) {
        setQuestionError(messages.editor.promptMetaObject);
      } else {
        setQuestionError(
          getQuestionBankAdminErrorMessage(error, messages.errors.questionBank)
        );
      }
    } finally {
      setIsWorking(false);
    }
  };

  const handleImport = async () => {
    if (!draft || isWorking || !isEditing) {
      return;
    }
    setIsWorking(true);
    setActionError(null);
    setActionNotice(null);
    try {
      const response =
        importFormat === "yaml"
          ? await importDraftYaml(bankKey, { yaml: importBody, mode: importMode })
          : await importDraftJson(bankKey, { json: importBody, mode: importMode });
      setDraft(response);
      setSelectedQuestionId(
        response.questions.length ? response.questions[0].questionId : null
      );
      setActionNotice(messages.alerts.importCompleted);
    } catch (error) {
      setActionError(
        getQuestionBankAdminErrorMessage(error, messages.errors.questionBank)
      );
    } finally {
      setIsWorking(false);
    }
  };

  const handleReorder = async () => {
    if (!draft || isWorking || !isEditing) {
      return;
    }
    setIsWorking(true);
    setReorderError(null);
    setActionNotice(null);
    try {
      const questionIds = textToList(reorderList);
      if (!questionIds.length) {
        throw new Error(messages.errors.reorderMissing);
      }
      const response = await reorderDraftQuestions(bankKey, {
        groups: [
          {
            stage: reorderStage,
            variant: reorderVariant,
            question_ids: questionIds,
          },
        ],
      });
      setDraft(response);
      setActionNotice(messages.alerts.orderUpdated);
    } catch (error) {
      if (
        error instanceof Error &&
        error.message === messages.errors.reorderMissing
      ) {
        setReorderError(messages.errors.reorderMissing);
      } else {
        setReorderError(
          getQuestionBankAdminErrorMessage(error, messages.errors.questionBank)
        );
      }
    } finally {
      setIsWorking(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <div className="stack-sm">
          <p className="eyebrow">{messages.page.eyebrow}</p>
          <h1 className="page-title">{messages.page.title}</h1>
          <p className="page-subtitle">
            {messages.page.subtitle}
          </p>
        </div>
      </div>

      <div className="question-bank-stack">
        <Card>
          <CardHeader>
            <CardTitle>{messages.bank.title}</CardTitle>
            <CardDescription>{messages.bank.description}</CardDescription>
          </CardHeader>
          <CardContent className="question-bank-select">
            <label
              className="field question-bank-key-field"
              htmlFor="question-bank-key"
            >
              <span className="field__label">{messages.bank.keyLabel}</span>
              <input
                id="question-bank-key"
                className="input"
                value={bankKeyInput}
                onChange={(event) => setBankKeyInput(event.target.value)}
                placeholder={DEFAULT_BANK_KEY}
              />
            </label>
            <Button onClick={handleLoad} disabled={loadState === "loading"}>
              {loadState === "loading"
                ? messages.bank.loading
                : messages.actions.loadBank}
            </Button>
            <Badge variant="outline">
              {messages.bank.current}: {bankKey}
            </Badge>
          </CardContent>
        </Card>

        <QuestionBankStatusAlerts
          actionError={actionError}
          actionNotice={actionNotice}
          loadError={loadError}
          messages={messages}
        />

        <QuestionBankModeBanner
          activeDetail={activeDetail}
          activeTab={activeTab}
          isEditing={isEditing}
          isWorking={isWorking}
          messages={messages}
          onEnterEdit={handleEnterEdit}
          onExitEdit={handleExitEdit}
          onPublish={handlePublish}
        />

        <QuestionBankTabs
          activeTab={activeTab}
          isEditing={isEditing}
          messages={messages}
          onTabChange={setActiveTab}
        />

        {activeTab === "overview" ? (
          <QuestionBankOverviewPanel
            activeDetail={activeDetail}
            activeVersion={activeVersion}
            draft={draft}
            isEditing={isEditing}
            isWorking={isWorking}
            messageLocale={messageLocale}
            messages={messages}
            onEnterEdit={handleEnterEdit}
            onExitEdit={handleExitEdit}
            onPublish={handlePublish}
          />
        ) : null}

        {activeTab === "questions" ? (
          <QuestionBankQuestionsPanel
            activeDetail={activeDetail}
            filteredQuestions={filteredQuestions}
            groupedQuestions={groupedQuestions}
            isEditing={isEditing}
            isWorking={isWorking}
            messages={messages}
            onQuestionSave={handleQuestionSave}
            questionConsultant={questionConsultant}
            questionError={questionError}
            questionInstruction={questionInstruction}
            questionKeyPoints={questionKeyPoints}
            questionNotes={questionNotes}
            questionPrompt={questionPrompt}
            questionPromptMeta={questionPromptMeta}
            questionSchemaPaths={questionSchemaPaths}
            questionStandard={questionStandard}
            questionTitle={questionTitle}
            questionType={questionType}
            questionValidation={questionValidation}
            searchQuery={searchQuery}
            selectedQuestion={selectedQuestion}
            selectedQuestionId={selectedQuestionId}
            setQuestionConsultant={setQuestionConsultant}
            setQuestionInstruction={setQuestionInstruction}
            setQuestionKeyPoints={setQuestionKeyPoints}
            setQuestionNotes={setQuestionNotes}
            setQuestionPrompt={setQuestionPrompt}
            setQuestionPromptMeta={setQuestionPromptMeta}
            setQuestionSchemaPaths={setQuestionSchemaPaths}
            setQuestionStandard={setQuestionStandard}
            setQuestionTitle={setQuestionTitle}
            setQuestionType={setQuestionType}
            setQuestionValidation={setQuestionValidation}
            setSearchQuery={setSearchQuery}
            setSelectedQuestionId={setSelectedQuestionId}
            setStageFilter={setStageFilter}
            stageFilter={stageFilter}
            stageOptions={stageOptions}
          />
        ) : null}

        {activeTab === "import" ? (
          <QuestionBankImportPanel
            draft={draft}
            importBody={importBody}
            importFormat={importFormat}
            importMode={importMode}
            isEditing={isEditing}
            isWorking={isWorking}
            messages={messages}
            onImport={handleImport}
            setImportBody={setImportBody}
            setImportFormat={setImportFormat}
            setImportMode={setImportMode}
          />
        ) : null}

        {activeTab === "reorder" ? (
          <QuestionBankReorderPanel
            draft={draft}
            isEditing={isEditing}
            isWorking={isWorking}
            messages={messages}
            onReorder={handleReorder}
            reorderError={reorderError}
            reorderList={reorderList}
            reorderStage={reorderStage}
            reorderStages={reorderStages}
            reorderVariant={reorderVariant}
            reorderVariants={reorderVariants}
            setReorderList={setReorderList}
            setReorderStage={setReorderStage}
            setReorderVariant={setReorderVariant}
          />
        ) : null}
      </div>
    </div>
  );
}
