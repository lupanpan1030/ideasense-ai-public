"use client";

import Link from "next/link";
import { ArrowRight, ShieldCheck } from "lucide-react";

import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale } from "@/lib/i18n/provider";
import type { MethodologyPageContent } from "@/components/marketing/methodology-page-types";
import {
  cx,
  eyebrowClassName,
  focusRingOnDark,
  focusRingOnLight,
  microLabelClassName,
  neutralMicroLabelClassName,
  SectionHeading,
  SectionReveal,
} from "@/components/marketing/methodology-page-utils";

export function OutputsSection({
  content,
  isZh,
}: {
  content: MethodologyPageContent;
  isZh: boolean;
}) {
  const locale = useAppLocale();

  return (
    <section className="pt-2 md:pt-4">
      <div className="grid gap-14 lg:grid-cols-[minmax(0,0.96fr)_minmax(0,1.04fr)] lg:items-center">
        <SectionReveal className="max-w-xl">
          <SectionHeading
            isZh={isZh}
            eyebrow={content.outputsSection.eyebrow}
            title={content.outputsSection.title}
            description={content.outputsSection.description}
          />

          <div className="mt-8 space-y-3">
            {content.outputs.map((item) => (
              <div
                key={item}
                className="flex items-start gap-3 rounded-[1.4rem] border border-black/6 bg-white/74 px-4 py-4"
              >
                <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-[#2563eb]" />
                <p
                  className={cx(
                    "text-sm text-[#475569]",
                    isZh ? "leading-[1.82]" : "leading-relaxed"
                  )}
                >
                  {item}
                </p>
              </div>
            ))}
          </div>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link
              href={buildLocalePath(locale, "/sample-report")}
              className={cx(
                "inline-flex items-center gap-2 rounded-full bg-[#0f172a] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#020617]",
                focusRingOnLight
              )}
            >
              {content.actions.sampleReport}
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href={buildLocalePath(locale, "/register")}
              className={cx(
                "inline-flex items-center rounded-full border border-black/8 bg-white px-5 py-3 text-sm font-medium text-[#0f172a] transition hover:border-[#2563eb]/18 hover:bg-[#f8fbff] hover:shadow-[0_12px_30px_rgba(15,23,42,0.08)]",
                focusRingOnLight
              )}
            >
              {content.actions.start}
            </Link>
          </div>
        </SectionReveal>

        <SectionReveal delay={0.08}>
          <ReportArtifact content={content.artifact} isZh={isZh} />
        </SectionReveal>
      </div>
    </section>
  );
}

function ReportArtifact({
  content,
  isZh,
}: {
  content: MethodologyPageContent["artifact"];
  isZh: boolean;
}) {
  return (
    <div className="relative mx-auto w-full max-w-[640px]">
      <div className="pointer-events-none absolute inset-x-[14%] top-[-8%] h-40 rounded-full bg-[radial-gradient(circle,rgba(37,99,235,0.16),transparent_68%)] blur-3xl" />

      <div className="relative overflow-hidden rounded-[2.6rem] border border-black/8 bg-white p-3 shadow-[0_30px_90px_rgba(15,23,42,0.14)]">
        <div className="overflow-hidden rounded-[2rem] border border-black/6 bg-[#f8fafc] p-5">
          <div className="flex items-center justify-between gap-4 border-b border-black/6 pb-4">
            <div>
              <p className={microLabelClassName(isZh)}>
                {content.eyebrow}
              </p>
              <p
                className={cx(
                  "mt-2 text-xl font-semibold text-[#0f172a]",
                  isZh ? "leading-[1.14] tracking-[-0.02em]" : "tracking-[-0.04em]"
                )}
              >
                {content.title}
              </p>
            </div>
            <div
              className={cx(
                "rounded-full border border-black/6 bg-white px-3 py-1 text-[#64748b]",
                isZh
                  ? "text-[12px] font-medium tracking-[0.04em]"
                  : "text-[11px] uppercase tracking-[0.18em]"
              )}
            >
              DVF
            </div>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-3">
            {content.summaryRows.map((row) => (
              <div
                key={row.label}
                className="rounded-[1.5rem] border border-black/6 bg-white px-4 py-4"
              >
                <p className={neutralMicroLabelClassName(isZh)}>
                  {row.label}
                </p>
                <p
                  className={cx(
                    "mt-3 text-base font-semibold text-[#0f172a]",
                    isZh ? "leading-[1.14] tracking-[-0.01em]" : "tracking-[-0.02em]"
                  )}
                >
                  {row.value}
                </p>
              </div>
            ))}
          </div>

          <div className="mt-5 grid gap-3 lg:grid-cols-[1.04fr_0.96fr]">
            <div className="rounded-[1.8rem] border border-black/6 bg-white px-5 py-5">
              <p className={neutralMicroLabelClassName(isZh)}>
                {content.scoreboardLabel}
              </p>
              <div className="mt-4 grid gap-3">
                {content.scoreboardRows.map((row) => (
                  <div key={row.label}>
                    <div
                      className={cx(
                        "flex items-center justify-between gap-4 text-[#64748b]",
                        isZh
                          ? "text-[12px] font-medium tracking-[0.04em]"
                          : "text-[11px] uppercase tracking-[0.16em]"
                      )}
                    >
                      <span>{row.label}</span>
                      <span>{row.value}</span>
                    </div>
                    <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-black/6">
                      <div
                        className="h-full rounded-full bg-[linear-gradient(90deg,rgba(59,130,246,0.92),rgba(147,197,253,0.96))]"
                        style={{ width: `${row.value}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[1.8rem] border border-black/6 bg-white px-5 py-5">
              <p className={neutralMicroLabelClassName(isZh)}>
                {content.modulesLabel}
              </p>
              <div className="mt-4 space-y-2">
                {content.modules.map((item) => (
                  <div
                    key={item}
                    className="rounded-[1.1rem] border border-black/6 bg-[#f8fafc] px-3 py-3 text-sm text-[#475569]"
                  >
                    {item}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            {content.exportChips.map((chip) => (
              <span
                key={chip}
                className={cx(
                  "rounded-full border border-black/6 bg-white px-3 py-1.5 text-[#64748b]",
                  isZh
                    ? "text-[12px] font-medium tracking-[0.04em]"
                    : "text-[11px] uppercase tracking-[0.18em]"
                )}
              >
                {chip}
              </span>
            ))}
          </div>

          {isZh ? (
            <div className="mt-5 rounded-[1.6rem] border border-black/6 bg-white px-4 py-4">
              <p className={microLabelClassName(isZh)}>
                {content.judgmentLabel}
              </p>
              <p className="mt-3 text-[15px] leading-[1.82] text-[#475569]">
                {content.judgmentText}
              </p>
            </div>
          ) : null}
        </div>
      </div>

      {!isZh ? (
        <div className="absolute -left-3 bottom-10 w-[220px] rounded-[1.6rem] border border-black/8 bg-white/86 p-5 shadow-[0_18px_48px_rgba(15,23,42,0.12)] backdrop-blur md:-left-6">
          <p className={microLabelClassName(isZh)}>
            {content.judgmentLabel}
          </p>
          <p className="mt-3 text-3xl font-semibold tracking-[-0.05em] text-[#0f172a]">
            79
            <span className="ml-1 text-base text-[#64748b]">/ 100</span>
          </p>
          <p className="mt-3 text-sm leading-relaxed text-[#475569]">
            {content.judgmentText}
          </p>
        </div>
      ) : null}
    </div>
  );
}

export function ClosingSection({
  content,
  isZh,
}: {
  content: MethodologyPageContent;
  isZh: boolean;
}) {
  const locale = useAppLocale();

  return (
    <section className="py-14 md:py-24">
      <SectionReveal>
        <div className="overflow-hidden rounded-[3rem] border border-white/10 bg-[#081223] px-7 py-8 text-white shadow-[0_34px_100px_rgba(2,6,23,0.22)] md:px-10 md:py-10">
          <div className="flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-2xl">
              <p className={eyebrowClassName(isZh, true)}>
                {content.closing.eyebrow}
              </p>
              <h2
                className={cx(
                  "mt-5 font-semibold text-white",
                  isZh
                    ? "text-[32px] leading-[1.18] tracking-[-0.018em] md:text-[2.7rem]"
                    : "text-4xl leading-[0.96] tracking-[-0.05em] md:text-5xl"
                )}
              >
                {content.closing.title}
              </h2>
              <p
                className={cx(
                  "mt-5 text-base text-white/66 md:text-lg",
                  isZh ? "leading-[1.86]" : "leading-relaxed"
                )}
              >
                {content.closing.description}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <Link
                href={buildLocalePath(locale, "/register")}
                className={cx(
                  "inline-flex items-center gap-2 rounded-full bg-white px-5 py-3 text-sm font-medium text-[#020617] transition hover:bg-white/92",
                  focusRingOnDark
                )}
              >
                {content.closing.primaryCta}
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href={buildLocalePath(locale, "/sample")}
                className={cx(
                  "inline-flex items-center rounded-full border border-white/12 bg-white/[0.06] px-5 py-3 text-sm font-medium text-white transition hover:bg-white/[0.1]",
                  focusRingOnDark
                )}
              >
                {content.closing.secondaryCta}
              </Link>
            </div>
          </div>
        </div>
      </SectionReveal>
    </section>
  );
}
