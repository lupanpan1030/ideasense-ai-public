import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type {
  QuestionBankDraft,
  QuestionBankQuestion,
} from "@/features/admin/question-banks";
import type { QuestionBankMessages } from "@/features/admin/question-bank-messages";
import {
  formatQuestionBankQuestionLabel,
  formatQuestionBankStageValue,
} from "@/features/admin/question-bank-view-model";

type QuestionBankQuestionGroup = {
  stage: string;
  variant: string;
  questions: QuestionBankQuestion[];
};

type QuestionBankQuestionsPanelProps = {
  activeDetail: QuestionBankDraft | null;
  filteredQuestions: QuestionBankQuestion[];
  groupedQuestions: QuestionBankQuestionGroup[];
  isEditing: boolean;
  isWorking: boolean;
  messages: QuestionBankMessages;
  onQuestionSave: () => void;
  questionConsultant: string;
  questionError: string | null;
  questionInstruction: string;
  questionKeyPoints: string;
  questionNotes: string;
  questionPrompt: string;
  questionPromptMeta: string;
  questionSchemaPaths: string;
  questionStandard: string;
  questionTitle: string;
  questionType: string;
  questionValidation: string;
  searchQuery: string;
  selectedQuestion: QuestionBankQuestion | null;
  selectedQuestionId: string | null;
  setQuestionConsultant: (value: string) => void;
  setQuestionInstruction: (value: string) => void;
  setQuestionKeyPoints: (value: string) => void;
  setQuestionNotes: (value: string) => void;
  setQuestionPrompt: (value: string) => void;
  setQuestionPromptMeta: (value: string) => void;
  setQuestionSchemaPaths: (value: string) => void;
  setQuestionStandard: (value: string) => void;
  setQuestionTitle: (value: string) => void;
  setQuestionType: (value: string) => void;
  setQuestionValidation: (value: string) => void;
  setSearchQuery: (value: string) => void;
  setSelectedQuestionId: (value: string) => void;
  setStageFilter: (value: string) => void;
  stageFilter: string;
  stageOptions: string[];
};

export function QuestionBankQuestionsPanel({
  activeDetail,
  filteredQuestions,
  groupedQuestions,
  isEditing,
  isWorking,
  messages,
  onQuestionSave,
  questionConsultant,
  questionError,
  questionInstruction,
  questionKeyPoints,
  questionNotes,
  questionPrompt,
  questionPromptMeta,
  questionSchemaPaths,
  questionStandard,
  questionTitle,
  questionType,
  questionValidation,
  searchQuery,
  selectedQuestion,
  selectedQuestionId,
  setQuestionConsultant,
  setQuestionInstruction,
  setQuestionKeyPoints,
  setQuestionNotes,
  setQuestionPrompt,
  setQuestionPromptMeta,
  setQuestionSchemaPaths,
  setQuestionStandard,
  setQuestionTitle,
  setQuestionType,
  setQuestionValidation,
  setSearchQuery,
  setSelectedQuestionId,
  setStageFilter,
  stageFilter,
  stageOptions,
}: QuestionBankQuestionsPanelProps) {
  return (
    <div className="question-bank-panel stack-lg">
      <Card>
        <CardHeader>
          <CardTitle>
            {messages.questions.title}{" "}
            <Badge variant="secondary">
              {isEditing ? messages.editor.draft : messages.editor.active}
            </Badge>
          </CardTitle>
          <CardDescription>{messages.questions.description}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="question-bank-filters">
            <label className="field">
              <span className="field__label">{messages.questions.stage}</span>
              <select
                className="input"
                value={stageFilter}
                onChange={(event) => setStageFilter(event.target.value)}
              >
                <option value="all">{messages.questions.allStages}</option>
                {stageOptions.map((stage) => (
                  <option key={stage} value={stage}>
                    {formatQuestionBankStageValue(stage, messages.stages)}
                  </option>
                ))}
              </select>
            </label>
            <label className="field question-bank-search">
              <span className="field__label">{messages.questions.search}</span>
              <input
                className="input"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder={messages.questions.searchPlaceholder}
              />
            </label>
            <Badge variant="outline">
              {filteredQuestions.length} {messages.questions.items}
            </Badge>
          </div>

          {filteredQuestions.length ? (
            <div className="question-bank-list">
              {groupedQuestions.map((group) => (
                <div key={`${group.stage}-${group.variant}`}>
                  <p className="question-bank-group">
                    {formatQuestionBankStageValue(group.stage, messages.stages)} /{" "}
                    {group.variant}
                  </p>
                  {group.questions.map((question) => (
                    <button
                      key={question.questionId}
                      type="button"
                      className={
                        question.questionId === selectedQuestionId
                          ? "question-bank-item question-bank-item--active"
                          : "question-bank-item"
                      }
                      onClick={() => setSelectedQuestionId(question.questionId)}
                    >
                      {formatQuestionBankQuestionLabel(question)}
                    </button>
                  ))}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted">
              {activeDetail
                ? messages.questions.noQuestions
                : messages.questions.noActive}
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{messages.editor.title}</CardTitle>
          <CardDescription>{messages.editor.description}</CardDescription>
        </CardHeader>
        <CardContent className="question-bank-editor">
          {selectedQuestion ? (
            <>
              <div className="question-bank-editor__meta">
                <Badge variant="outline">
                  {formatQuestionBankStageValue(
                    selectedQuestion.stage,
                    messages.stages
                  )}{" "}
                  / {selectedQuestion.variant}
                </Badge>
                <Badge variant="secondary">
                  {isEditing ? messages.editor.draft : messages.editor.active}
                </Badge>
                <Badge variant="secondary">
                  {messages.editor.order} {selectedQuestion.orderIndex}
                </Badge>
              </div>
              <label className="field">
                <span className="field__label">{messages.editor.titleField}</span>
                <input
                  className="input"
                  value={questionTitle}
                  onChange={(event) => setQuestionTitle(event.target.value)}
                  readOnly={!isEditing}
                />
              </label>
              <label className="field">
                <span className="field__label">{messages.editor.type}</span>
                <input
                  className="input"
                  value={questionType}
                  onChange={(event) => setQuestionType(event.target.value)}
                  readOnly={!isEditing}
                />
              </label>
              <label className="field">
                <span className="field__label">{messages.editor.prompt}</span>
                <textarea
                  className="textarea"
                  rows={4}
                  value={questionPrompt}
                  onChange={(event) => setQuestionPrompt(event.target.value)}
                  readOnly={!isEditing}
                />
              </label>
              <label className="field">
                <span className="field__label">
                  {messages.editor.standardQuestion}
                </span>
                <textarea
                  className="textarea"
                  rows={3}
                  value={questionStandard}
                  onChange={(event) => setQuestionStandard(event.target.value)}
                  readOnly={!isEditing}
                />
              </label>
              <label className="field">
                <span className="field__label">{messages.editor.consultant}</span>
                <textarea
                  className="textarea"
                  rows={3}
                  value={questionConsultant}
                  onChange={(event) => setQuestionConsultant(event.target.value)}
                  readOnly={!isEditing}
                />
              </label>
              <label className="field">
                <span className="field__label">
                  {messages.editor.instruction}
                </span>
                <textarea
                  className="textarea"
                  rows={3}
                  value={questionInstruction}
                  onChange={(event) => setQuestionInstruction(event.target.value)}
                  readOnly={!isEditing}
                />
              </label>
              <label className="field">
                <span className="field__label">
                  {messages.editor.validationRule}
                </span>
                <textarea
                  className="textarea"
                  rows={2}
                  value={questionValidation}
                  onChange={(event) => setQuestionValidation(event.target.value)}
                  readOnly={!isEditing}
                />
              </label>
              <label className="field">
                <span className="field__label">
                  {messages.editor.schemaPaths}
                </span>
                <textarea
                  className="textarea"
                  rows={3}
                  value={questionSchemaPaths}
                  onChange={(event) => setQuestionSchemaPaths(event.target.value)}
                  placeholder={messages.editor.onePerLine}
                  readOnly={!isEditing}
                />
              </label>
              <label className="field">
                <span className="field__label">
                  {messages.editor.expectedKeyPoints}
                </span>
                <textarea
                  className="textarea"
                  rows={3}
                  value={questionKeyPoints}
                  onChange={(event) => setQuestionKeyPoints(event.target.value)}
                  placeholder={messages.editor.onePerLine}
                  readOnly={!isEditing}
                />
              </label>
              <label className="field">
                <span className="field__label">{messages.editor.promptMeta}</span>
                <textarea
                  className="textarea"
                  rows={4}
                  value={questionPromptMeta}
                  onChange={(event) => setQuestionPromptMeta(event.target.value)}
                  readOnly={!isEditing}
                />
              </label>
              <label className="field">
                <span className="field__label">{messages.editor.notes}</span>
                <textarea
                  className="textarea"
                  rows={2}
                  value={questionNotes}
                  onChange={(event) => setQuestionNotes(event.target.value)}
                  readOnly={!isEditing}
                />
              </label>
              {questionError ? (
                <p className="field__error">{questionError}</p>
              ) : null}
              {isEditing ? (
                <Button onClick={onQuestionSave} disabled={isWorking}>
                  {messages.actions.saveChanges}
                </Button>
              ) : (
                <p className="text-muted">{messages.editor.switchToEdit}</p>
              )}
            </>
          ) : (
            <p className="text-muted">{messages.editor.selectPrompt}</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
