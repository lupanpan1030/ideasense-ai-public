"use client";

import { FileText, Radar, ScanSearch, ShieldCheck } from "lucide-react";

import type { MethodologyPageContent } from "@/components/marketing/methodology-page-types";
import {
  cx,
  microLabelClassName,
  neutralMicroLabelClassName,
  SectionHeading,
  SectionReveal,
} from "@/components/marketing/methodology-page-utils";

export function ReviewSection({
  content,
  isZh,
}: {
  content: MethodologyPageContent;
  isZh: boolean;
}) {
  return (
    <section className="py-14 md:py-24">
      <div className="grid gap-14 lg:grid-cols-[minmax(0,0.94fr)_minmax(0,1.06fr)] lg:items-start">
        <SectionReveal className="max-w-xl">
          <SectionHeading
            isZh={isZh}
            eyebrow={content.review.eyebrow}
            title={content.review.title}
            description={content.review.description}
          />

          <div className="mt-8 rounded-[2rem] border border-black/6 bg-[linear-gradient(180deg,rgba(248,250,252,0.94),rgba(255,255,255,0.88))] p-5 shadow-[0_24px_64px_rgba(15,23,42,0.05)]">
            <p className={microLabelClassName(isZh)}>
              {content.review.gatesTitle}
            </p>
            <div className="mt-4 space-y-3">
              {content.review.gates.map((gate) => (
                <div
                  key={gate}
                  className="flex items-start gap-3 rounded-[1.4rem] border border-black/6 bg-white/84 px-4 py-4"
                >
                  <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-[#2563eb]" />
                  <p
                    className={cx(
                      "text-sm text-[#475569]",
                      isZh ? "leading-[1.82]" : "leading-relaxed"
                    )}
                  >
                    {gate}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </SectionReveal>

        <div className="grid gap-4">
          <SectionReveal>
            <div className="rounded-[2.4rem] border border-black/6 bg-white/80 p-7 shadow-[0_24px_72px_rgba(15,23,42,0.06)] md:p-8">
              <div className="space-y-4">
                {content.sessionSteps.map((step, index) => (
                  <ReviewStep
                    key={step.title}
                    index={index}
                    isZh={isZh}
                    title={step.title}
                    description={step.description}
                  />
                ))}
              </div>
            </div>
          </SectionReveal>

          <SectionReveal delay={0.08}>
            <div className="overflow-hidden rounded-[2.4rem] border border-white/10 bg-[#081223] p-7 text-white shadow-[0_30px_100px_rgba(2,6,23,0.22)] md:p-8">
              <SectionHeading
                isZh={isZh}
                eyebrow={content.uncertainty.eyebrow}
                title={content.uncertainty.title}
                description={content.uncertainty.description}
                dark
              />

              <div className="mt-8 space-y-3">
                {content.uncertainty.points.map((point) => (
                  <div
                  key={point}
                  className="rounded-[1.5rem] border border-white/10 bg-white/[0.05] px-4 py-4"
                >
                    <p
                      className={cx(
                        "text-sm text-white/72",
                        isZh ? "leading-[1.82]" : "leading-relaxed"
                      )}
                    >
                      {point}
                    </p>
                  </div>
                ))}
              </div>

              <div className="mt-6 flex flex-wrap gap-2">
                {content.uncertainty.chips.map((chip, index) => (
                  <span
                    key={chip}
                    className={cx(
                      "rounded-full border px-3 py-1.5",
                      isZh
                        ? "text-[12px] font-medium tracking-[0.04em]"
                        : "text-[11px] uppercase tracking-[0.16em]",
                      index === 2
                        ? "border-[#93c5fd]/24 bg-[#93c5fd]/12 text-[#dbeafe]"
                        : "border-white/10 bg-white/[0.05] text-white/56"
                    )}
                  >
                    {chip}
                  </span>
                ))}
              </div>
            </div>
          </SectionReveal>
        </div>
      </div>
    </section>
  );
}

function ReviewStep({
  index,
  isZh,
  title,
  description,
}: {
  index: number;
  isZh: boolean;
  title: string;
  description: string;
}) {
  if (isZh) {
    return (
      <div className="grid gap-4 rounded-[1.8rem] border border-black/6 bg-[linear-gradient(180deg,rgba(255,255,255,0.92),rgba(248,250,252,0.86))] px-5 py-5 md:grid-cols-[76px_minmax(0,1fr)]">
        <p className="text-[20px] font-semibold tracking-[-0.03em] text-[#2563eb]">
          {String(index + 1).padStart(2, "0")}
        </p>
        <div>
          <p className="text-[20px] font-medium leading-[1.35] tracking-[-0.015em] text-[#0f172a]">
            {title}
          </p>
          <p className="mt-3 text-[15px] leading-[1.9] text-[#64748b]">
            {description}
          </p>
        </div>
      </div>
    );
  }

  const icons = [ScanSearch, Radar, FileText];
  const Icon = icons[index] ?? ShieldCheck;

  return (
    <div className="rounded-[1.8rem] border border-black/6 bg-[linear-gradient(180deg,rgba(255,255,255,0.92),rgba(248,250,252,0.86))] px-5 py-5">
      <div className="flex items-start gap-4">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-black/6 bg-white text-[#2563eb]">
          <Icon className="h-4 w-4" />
        </div>
        <div>
          <p className={neutralMicroLabelClassName(isZh)}>
            {String(index + 1).padStart(2, "0")}
          </p>
          <p
            className={cx(
              "mt-3 text-xl font-semibold text-[#0f172a]",
              isZh ? "leading-[1.16] tracking-[-0.015em]" : "tracking-[-0.03em]"
            )}
          >
            {title}
          </p>
          <p
            className={cx(
              "mt-3 text-sm text-[#475569] md:text-base",
              isZh ? "leading-[1.84]" : "leading-relaxed"
            )}
          >
            {description}
          </p>
        </div>
      </div>
    </div>
  );
}
