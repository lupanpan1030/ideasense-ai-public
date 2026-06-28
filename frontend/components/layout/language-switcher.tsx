"use client";

import { useState } from "react";
import {
  SUPPORTED_APP_LOCALES,
  buildLocalePath,
  type AppLocale,
} from "@/lib/i18n/config";
import { useAppLocale, useAppMessages } from "@/lib/i18n/provider";
import { useRouter } from "next/navigation";

type LanguageSwitcherProps = {
  tone?: "surface" | "inverse";
  compact?: boolean;
  className?: string;
  ariaLabel?: string;
};

export function LanguageSwitcher({
  tone = "surface",
  compact = false,
  className = "",
  ariaLabel,
}: LanguageSwitcherProps) {
  const [isPending, setIsPending] = useState(false);
  const router = useRouter();
  const locale = useAppLocale();
  const messages = useAppMessages().localeSwitcher;

  const containerClassName = [
    "inline-flex items-center gap-1 rounded-full border p-1",
    tone === "inverse"
      ? "border-white/25 bg-white/10 text-white backdrop-blur"
      : "border-[var(--color-border)] bg-[var(--color-surface-alt)] text-[var(--color-text)]",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  const buildOptionClassName = (optionLocale: AppLocale) => {
    const isActive = optionLocale === locale;
    return [
      "inline-flex min-h-[2.75rem] min-w-[3rem] items-center justify-center rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)]/40",
      isActive
        ? tone === "inverse"
          ? "bg-white text-[var(--color-text)] shadow-[0_8px_24px_rgba(0,0,0,0.18)]"
          : "bg-[var(--color-surface)] text-[var(--color-text)] shadow-sm"
        : tone === "inverse"
          ? "text-white/80 hover:bg-white/10 hover:text-white"
          : "text-[var(--color-text-muted)] hover:bg-[var(--color-surface)] hover:text-[var(--color-text)]",
    ].join(" ");
  };

  const handleSelect = (nextLocale: AppLocale) => {
    if (nextLocale === locale || isPending) {
      return;
    }

    const pathname = window.location.pathname;
    const targetPath = buildLocalePath(
      nextLocale,
      pathname,
      window.location.search
    );

    setIsPending(true);
    router.push(`${targetPath}${window.location.hash}`);
  };

  return (
    <div className="inline-flex flex-col gap-2">
      <div
        role="radiogroup"
        aria-label={ariaLabel ?? messages.ariaLabel}
        aria-busy={isPending}
        className={containerClassName}
      >
        {SUPPORTED_APP_LOCALES.map((optionLocale) => {
          const option = messages.locales[optionLocale];
          return (
            <button
              key={optionLocale}
              type="button"
              role="radio"
              aria-checked={optionLocale === locale}
              aria-label={option.full}
              className={buildOptionClassName(optionLocale)}
              onClick={() => handleSelect(optionLocale)}
              disabled={isPending}
            >
              {compact ? option.short : option.full}
            </button>
          );
        })}
      </div>
      <span className="sr-only" aria-live="polite">
        {isPending ? messages.switching : ""}
      </span>
    </div>
  );
}
