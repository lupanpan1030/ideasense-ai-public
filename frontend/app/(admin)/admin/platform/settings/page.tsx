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
import {
  fetchPlatformSettings,
  getPlatformSettingsErrorMessage,
  updatePlatformSettings,
  type PlatformSettingEntry,
  type PlatformSettingsErrorMessages,
} from "@/features/admin/platform-settings";
import { useAppLocale } from "@/lib/i18n/provider";

type LoadState = "idle" | "loading" | "ready" | "error";

const safeJsonStringify = (value: unknown): string => {
  try {
    return JSON.stringify(value ?? {}, null, 2);
  } catch {
    return "{}";
  }
};

const PLATFORM_SETTINGS_MESSAGES = {
  en: {
    actions: {
      add: "Add setting",
      addingNotice: "Setting added.",
      delete: "Delete",
      deletedNotice: "Setting deleted.",
      refresh: "Refresh",
      save: "Save",
      updatedNotice: "Setting updated.",
    },
    alerts: {
      actionFailed: "Action failed",
      loadFailed: "Unable to load settings",
      success: "Success",
    },
    confirmDelete: (key: string) => `Delete setting "${key}"?`,
    errors: {
      accessDenied: "You do not have access to manage platform settings.",
      default: "Unable to update platform settings.",
      emptyValue: "Value cannot be empty.",
      invalidJson: "Invalid JSON value.",
      keyRequired: "Key is required.",
      sessionExpired: "Your session expired. Please sign in again.",
      unavailable: "Platform settings are unavailable. Try again shortly.",
    },
    form: {
      keyLabel: "Key",
      keyPlaceholder: "e.g. platform.default_locale",
      valueLabel: "Value (JSON)",
    },
    page: {
      eyebrow: "Platform",
      subtitle: "Global configuration that applies to every organization.",
      title: "Platform settings",
    },
    settings: {
      description: "Update or remove existing keys.",
      empty: "No platform settings configured yet.",
      title: "Settings",
    },
    status: {
      loading: "Loading",
      ready: "Ready",
      system: "System",
      unknown: "Unknown",
    },
    summary: {
      description: "Quick view of platform configuration.",
      lastUpdated: "Last updated",
      status: "Status",
      title: "Summary",
      totalSettings: "Total settings",
    },
    table: {
      actions: "Actions",
      key: "Key",
      updatedAt: "Updated at",
      updatedBy: "Updated by",
      value: "Value",
    },
    newSetting: {
      description: "Create a new platform configuration key.",
      title: "Add setting",
    },
  },
  zh: {
    actions: {
      add: "新增设置",
      addingNotice: "设置已新增。",
      delete: "删除",
      deletedNotice: "设置已删除。",
      refresh: "刷新",
      save: "保存",
      updatedNotice: "设置已更新。",
    },
    alerts: {
      actionFailed: "操作失败",
      loadFailed: "无法加载设置",
      success: "成功",
    },
    confirmDelete: (key: string) => `删除设置“${key}”？`,
    errors: {
      accessDenied: "你没有管理平台设置的权限。",
      default: "无法更新平台设置。",
      emptyValue: "值不能为空。",
      invalidJson: "JSON 值无效。",
      keyRequired: "设置键不能为空。",
      sessionExpired: "登录状态已过期，请重新登录。",
      unavailable: "平台设置服务暂时不可用，请稍后再试。",
    },
    form: {
      keyLabel: "设置键",
      keyPlaceholder: "例如 platform.default_locale",
      valueLabel: "值（JSON）",
    },
    page: {
      eyebrow: "平台",
      subtitle: "适用于所有组织的全局配置。",
      title: "平台设置",
    },
    settings: {
      description: "更新或移除已有配置键。",
      empty: "还没有配置平台设置。",
      title: "设置列表",
    },
    status: {
      loading: "加载中",
      ready: "就绪",
      system: "系统",
      unknown: "未知",
    },
    summary: {
      description: "快速查看平台配置状态。",
      lastUpdated: "最近更新",
      status: "状态",
      title: "摘要",
      totalSettings: "设置总数",
    },
    table: {
      actions: "操作",
      key: "设置键",
      updatedAt: "更新时间",
      updatedBy: "更新人",
      value: "值",
    },
    newSetting: {
      description: "创建新的平台配置键。",
      title: "新增设置",
    },
  },
} as const;

type PlatformSettingsPageErrors = PlatformSettingsErrorMessages & {
  emptyValue: string;
  invalidJson: string;
};

const parseJson = (
  value: string,
  emptyMessage: string,
  invalidMessage: string
): unknown => {
  const trimmed = value.trim();
  if (!trimmed) {
    throw new Error(emptyMessage);
  }
  try {
    return JSON.parse(trimmed);
  } catch {
    throw new Error(invalidMessage);
  }
};

const getJsonFieldErrorMessage = (
  error: unknown,
  messages: PlatformSettingsPageErrors
): string => {
  if (error instanceof Error && error.message === messages.emptyValue) {
    return messages.emptyValue;
  }
  if (error instanceof Error && error.message === messages.invalidJson) {
    return messages.invalidJson;
  }
  return getPlatformSettingsErrorMessage(error, messages);
};

const formatTimestamp = (
  value: string | null,
  locale: "en" | "zh",
  unknownLabel: string
): string => {
  if (!value) {
    return unknownLabel;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return unknownLabel;
  }
  return date.toLocaleString(locale === "zh" ? "zh-CN" : "en-US");
};

const formatUpdatedBy = (
  entry: PlatformSettingEntry,
  systemLabel: string
): string =>
  entry.updatedByName ||
  entry.updatedByEmail ||
  entry.updatedBy ||
  systemLabel;

export default function PlatformSettingsPage() {
  const locale = useAppLocale();
  const messages = PLATFORM_SETTINGS_MESSAGES[locale];
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [entries, setEntries] = useState<PlatformSettingEntry[]>([]);
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [editErrors, setEditErrors] = useState<Record<string, string>>({});
  const [isWorking, setIsWorking] = useState(false);

  const [newKey, setNewKey] = useState("");
  const [newValue, setNewValue] = useState("{}");
  const [newError, setNewError] = useState<string | null>(null);

  const applyEntries = useCallback((nextEntries: PlatformSettingEntry[]) => {
    setEntries(nextEntries);
    const nextValues: Record<string, string> = {};
    nextEntries.forEach((entry) => {
      nextValues[entry.key] = safeJsonStringify(entry.value);
    });
    setEditValues(nextValues);
    setEditErrors({});
  }, []);

  const loadSettings = useCallback(async () => {
    setLoadState("loading");
    setLoadError(null);
    setActionError(null);
    setActionNotice(null);
    try {
      const response = await fetchPlatformSettings();
      applyEntries(response.entries);
      setLoadState("ready");
    } catch (error) {
      setLoadError(getPlatformSettingsErrorMessage(error, messages.errors));
      setLoadState("error");
    }
  }, [applyEntries, messages.errors]);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  const latestUpdated = useMemo(() => {
    if (!entries.length) {
      return null;
    }
    return entries.reduce<string | null>((latest, entry) => {
      if (!entry.updatedAt) {
        return latest;
      }
      if (!latest) {
        return entry.updatedAt;
      }
      return entry.updatedAt > latest ? entry.updatedAt : latest;
    }, null);
  }, [entries]);

  const handleSave = async (key: string) => {
    if (isWorking) {
      return;
    }
    setIsWorking(true);
    setActionError(null);
    setActionNotice(null);
    setEditErrors((prev) => ({ ...prev, [key]: "" }));
    try {
      const parsed = parseJson(
        editValues[key] ?? "",
        messages.errors.emptyValue,
        messages.errors.invalidJson
      );
      const response = await updatePlatformSettings({
        settings: { [key]: parsed as unknown },
      });
      applyEntries(response.entries);
      setActionNotice(messages.actions.updatedNotice);
    } catch (error) {
      const message = getJsonFieldErrorMessage(error, messages.errors);
      setEditErrors((prev) => ({ ...prev, [key]: message }));
      setActionError(getPlatformSettingsErrorMessage(error, messages.errors));
    } finally {
      setIsWorking(false);
    }
  };

  const handleDelete = async (key: string) => {
    if (isWorking) {
      return;
    }
    if (!window.confirm(messages.confirmDelete(key))) {
      return;
    }
    setIsWorking(true);
    setActionError(null);
    setActionNotice(null);
    try {
      const response = await updatePlatformSettings({ remove: [key] });
      applyEntries(response.entries);
      setActionNotice(messages.actions.deletedNotice);
    } catch (error) {
      setActionError(getPlatformSettingsErrorMessage(error, messages.errors));
    } finally {
      setIsWorking(false);
    }
  };

  const handleAdd = async () => {
    if (isWorking) {
      return;
    }
    setNewError(null);
    setActionError(null);
    setActionNotice(null);
    const key = newKey.trim();
    if (!key) {
      setNewError(messages.errors.keyRequired);
      return;
    }
    try {
      const parsed = parseJson(
        newValue,
        messages.errors.emptyValue,
        messages.errors.invalidJson
      );
      setIsWorking(true);
      const response = await updatePlatformSettings({
        settings: { [key]: parsed as unknown },
      });
      applyEntries(response.entries);
      setNewKey("");
      setNewValue("{}");
      setActionNotice(messages.actions.addingNotice);
    } catch (error) {
      const message = getJsonFieldErrorMessage(error, messages.errors);
      setNewError(message);
      setActionError(getPlatformSettingsErrorMessage(error, messages.errors));
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
          <p className="page-subtitle">{messages.page.subtitle}</p>
        </div>
      </div>

      {loadError ? (
        <Card variant="alert" role="alert">
          <CardHeader>
            <CardTitle>{messages.alerts.loadFailed}</CardTitle>
            <CardDescription>{loadError}</CardDescription>
          </CardHeader>
        </Card>
      ) : null}

      {actionNotice ? (
        <Card variant="soft" role="status" aria-live="polite">
          <CardHeader>
            <CardTitle>{messages.alerts.success}</CardTitle>
            <CardDescription>{actionNotice}</CardDescription>
          </CardHeader>
        </Card>
      ) : null}

      {actionError ? (
        <Card variant="alert" role="alert">
          <CardHeader>
            <CardTitle>{messages.alerts.actionFailed}</CardTitle>
            <CardDescription>{actionError}</CardDescription>
          </CardHeader>
        </Card>
      ) : null}

      <div className="platform-settings-grid">
        <Card>
          <CardHeader>
            <CardTitle>{messages.summary.title}</CardTitle>
            <CardDescription>{messages.summary.description}</CardDescription>
          </CardHeader>
          <CardContent className="platform-settings-summary">
            <div>
              <p className="text-muted">{messages.summary.totalSettings}</p>
              <strong>{entries.length}</strong>
            </div>
            <div>
              <p className="text-muted">{messages.summary.lastUpdated}</p>
              <strong>
                {formatTimestamp(latestUpdated, locale, messages.status.unknown)}
              </strong>
            </div>
            <div>
              <p className="text-muted">{messages.summary.status}</p>
              <Badge variant="secondary">
                {loadState === "loading"
                  ? messages.status.loading
                  : messages.status.ready}
              </Badge>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={loadSettings}
              disabled={loadState === "loading"}
            >
              {messages.actions.refresh}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{messages.newSetting.title}</CardTitle>
            <CardDescription>{messages.newSetting.description}</CardDescription>
          </CardHeader>
          <CardContent className="platform-settings-new">
            <label className="field">
              <span className="field__label">{messages.form.keyLabel}</span>
              <input
                className="input"
                value={newKey}
                onChange={(event) => setNewKey(event.target.value)}
                placeholder={messages.form.keyPlaceholder}
              />
            </label>
            <label className="field">
              <span className="field__label">{messages.form.valueLabel}</span>
              <textarea
                className="textarea"
                rows={5}
                value={newValue}
                onChange={(event) => setNewValue(event.target.value)}
              />
            </label>
            {newError ? (
              <p className="field__error" role="alert">
                {newError}
              </p>
            ) : null}
            <Button onClick={handleAdd} disabled={isWorking}>
              {messages.actions.add}
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{messages.settings.title}</CardTitle>
          <CardDescription>{messages.settings.description}</CardDescription>
        </CardHeader>
        <CardContent className="platform-settings-table">
          {entries.length ? (
            <table className="admin-platform-table">
              <thead>
                <tr>
                  <th scope="col">{messages.table.key}</th>
                  <th scope="col">{messages.table.value}</th>
                  <th scope="col">{messages.table.updatedBy}</th>
                  <th scope="col">{messages.table.updatedAt}</th>
                  <th scope="col">{messages.table.actions}</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => {
                  const errorId = editErrors[entry.key]
                    ? `platform-setting-${entry.key}-error`
                    : undefined;
                  return (
                    <tr key={entry.key}>
                      <td
                        className="platform-setting__key"
                        data-label={messages.table.key}
                      >
                        {entry.key}
                      </td>
                      <td data-label={messages.table.value}>
                        <textarea
                          className="textarea platform-setting__value"
                          rows={4}
                          value={editValues[entry.key] ?? ""}
                          aria-label={`${messages.table.value}: ${entry.key}`}
                          aria-describedby={errorId}
                          aria-invalid={Boolean(editErrors[entry.key]) || undefined}
                          onChange={(event) =>
                            setEditValues((prev) => ({
                              ...prev,
                              [entry.key]: event.target.value,
                            }))
                          }
                        />
                        {editErrors[entry.key] ? (
                          <p id={errorId} className="field__error" role="alert">
                            {editErrors[entry.key]}
                          </p>
                        ) : null}
                      </td>
                      <td data-label={messages.table.updatedBy}>
                        {formatUpdatedBy(entry, messages.status.system)}
                      </td>
                      <td data-label={messages.table.updatedAt}>
                        {formatTimestamp(
                          entry.updatedAt,
                          locale,
                          messages.status.unknown
                        )}
                      </td>
                      <td data-label={messages.table.actions}>
                        <div className="cluster-tight">
                          <Button
                            size="sm"
                            onClick={() => handleSave(entry.key)}
                            disabled={isWorking}
                          >
                            {messages.actions.save}
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleDelete(entry.key)}
                            disabled={isWorking}
                          >
                            {messages.actions.delete}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <p className="text-muted">{messages.settings.empty}</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
