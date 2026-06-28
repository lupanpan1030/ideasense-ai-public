"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale } from "@/lib/i18n/provider";
import type { MethodologyPageContent } from "@/components/marketing/methodology-page-types";
import {
  bodyClassName,
  cx,
  eyebrowClassName,
  focusRingOnLight,
  heroTitleClassName,
  microLabelClassName,
  neutralMicroLabelClassName,
  SectionHeading,
  SectionReveal,
} from "@/components/marketing/methodology-page-utils";

export function HeroSection({
  content,
  isZh,
}: {
  content: MethodologyPageContent;
  isZh: boolean;
}) {
  const locale = useAppLocale();

  return (
    <section className="pt-8 md:pt-14">
      <div
        className={cx(
          "grid gap-10 lg:items-end",
          isZh
            ? "lg:grid-cols-[minmax(0,1.06fr)_minmax(320px,0.94fr)]"
            : "lg:grid-cols-[minmax(0,1fr)_minmax(340px,0.82fr)]"
        )}
      >
        <SectionReveal className="max-w-3xl">
          <p className={eyebrowClassName(isZh)}>
            {content.eyebrow}
          </p>
          <h1 className={heroTitleClassName(isZh)}>
            {content.title}
          </h1>
          <p className={cx(bodyClassName(isZh), isZh && "max-w-[39rem]")}>
            {content.description}
          </p>

          <div className="mt-9 flex flex-wrap items-center gap-3">
            <Link
              href={buildLocalePath(locale, "/register")}
              className={cx(
                "inline-flex items-center gap-2 rounded-full bg-[#0f172a] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#020617]",
                focusRingOnLight
              )}
            >
              {content.actions.start}
              {!isZh ? <ArrowRight className="h-4 w-4" /> : null}
            </Link>
            <Link
              href={buildLocalePath(locale, "/sample-report")}
              className={cx(
                "inline-flex items-center rounded-full border border-black/8 bg-white px-5 py-3 text-sm font-medium text-[#0f172a] transition hover:border-[#2563eb]/18 hover:bg-[#f8fbff] hover:shadow-[0_12px_30px_rgba(15,23,42,0.08)]",
                focusRingOnLight
              )}
            >
              {content.actions.sampleReport}
            </Link>
          </div>
        </SectionReveal>

        <SectionReveal delay={0.06}>
          <div
            className={cx(
              "relative overflow-hidden border border-black/6 bg-white/84 shadow-[0_28px_80px_rgba(15,23,42,0.08)] backdrop-blur",
              isZh ? "rounded-[2.5rem] p-4" : "rounded-[2.8rem] p-5"
            )}
          >
            <div className="pointer-events-none absolute inset-x-[12%] top-[-12%] h-44 rounded-full bg-[radial-gradient(circle,rgba(37,99,235,0.16),transparent_68%)] blur-3xl" />

            <div
              className={cx(
                "relative border border-black/6 bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(240,244,248,0.84))]",
                isZh ? "rounded-[2rem] p-6" : "rounded-[2.2rem] p-6"
              )}
            >
              <p className={microLabelClassName(isZh)}>
                {content.heroPanel.eyebrow}
              </p>
              {content.heroPanel.statement ? (
                <p
                  className={cx(
                    "mt-3 font-semibold text-[#0f172a]",
                    isZh
                      ? "text-[26px] leading-[1.28] tracking-[-0.02em]"
                      : "text-xl leading-[1.2] tracking-[-0.03em]"
                  )}
                >
                  {content.heroPanel.statement}
                </p>
              ) : null}

              {isZh ? (
                <div className="mt-5 grid gap-3 md:grid-cols-3">
                  {content.heroHighlights.map((item) => (
                    <div
                      key={item.label}
                      className="rounded-[1.4rem] border border-black/6 bg-white px-4 py-4"
                    >
                      <p className={neutralMicroLabelClassName(isZh)}>
                        {item.label}
                      </p>
                      <p className="mt-3 text-[17px] font-medium leading-[1.35] tracking-[-0.012em] text-[#0f172a]">
                        {item.value}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mt-5 space-y-3">
                  {content.heroHighlights.map((item) => (
                    <div
                      key={item.label}
                      className="rounded-[1.6rem] border border-black/6 bg-white/90 px-4 py-4"
                    >
                      <p className={neutralMicroLabelClassName(isZh)}>
                        {item.label}
                      </p>
                      <p
                        className={cx(
                          "mt-2 text-sm text-[#0f172a] md:text-[15px]",
                          isZh ? "leading-[1.8]" : "leading-relaxed"
                        )}
                      >
                        {item.value}
                      </p>
                    </div>
                  ))}
                </div>
              )}

              <div
                className={cx(
                  "mt-5 border border-[#2563eb]/10 bg-[linear-gradient(180deg,rgba(37,99,235,0.06),rgba(255,255,255,0.9))]",
                  isZh ? "rounded-[1.8rem] p-5" : "rounded-[1.8rem] p-5"
                )}
              >
                <p className={microLabelClassName(isZh)}>
                  {content.heroPanel.principleLabel}
                </p>
                <p
                  className={cx(
                    "mt-3 text-sm text-[#475569]",
                    isZh ? "leading-[1.82]" : "leading-relaxed"
                  )}
                >
                  {content.heroPanel.principleText}
                </p>
              </div>
            </div>
          </div>
        </SectionReveal>
      </div>
    </section>
  );
}

export function WhySection({
  content,
  isZh,
}: {
  content: MethodologyPageContent;
  isZh: boolean;
}) {
  const points = content.why.points.map((point) =>
    typeof point === "string"
      ? { title: point, description: "" }
      : point
  );

  return (
    <section className="py-14 md:py-24">
      <div className="grid gap-14 lg:grid-cols-[minmax(0,0.94fr)_minmax(0,1.06fr)] lg:items-start">
        <SectionReveal className="max-w-xl">
          <SectionHeading
            isZh={isZh}
            eyebrow={content.why.eyebrow}
            title={content.why.title}
            description={content.why.description}
          />

          <div
            className={cx(
              "mt-8 inline-flex items-center gap-2 border border-black/8 bg-white/84 shadow-[0_12px_28px_rgba(15,23,42,0.05)]",
              isZh
                ? "max-w-xl rounded-[1.35rem] px-4 py-3 text-[12px] font-medium tracking-[0.04em] text-[#475569]"
                : "rounded-full px-4 py-2 text-[11px] uppercase tracking-[0.18em] text-[#64748b]"
            )}
          >
            <span className="h-2 w-2 rounded-full bg-[#2563eb]" />
            {content.why.pill}
          </div>
        </SectionReveal>

        <div className={cx("grid gap-4", isZh ? "lg:grid-cols-3" : "sm:grid-cols-2")}>
          {points.map((point, index) => (
            <SectionReveal key={point.title} delay={index * 0.05}>
              <div className="h-full rounded-[2rem] border border-black/6 bg-white/78 p-6 shadow-[0_24px_64px_rgba(15,23,42,0.05)] backdrop-blur">
                <p className={microLabelClassName(isZh)}>
                  {String(index + 1).padStart(2, "0")}
                </p>
                <p
                  className={cx(
                    "mt-5 text-2xl font-semibold text-[#0f172a]",
                    isZh
                      ? "leading-[1.16] tracking-[-0.02em]"
                      : "leading-[1.02] tracking-[-0.04em]"
                  )}
                >
                  {point.title}
                </p>
                {point.description ? (
                  <p className="mt-4 text-[15px] leading-[1.9] text-[#64748b]">
                    {point.description}
                  </p>
                ) : null}
              </div>
            </SectionReveal>
          ))}
        </div>
      </div>
    </section>
  );
}
