"use client";

import type { MethodologyPageContent } from "@/components/marketing/methodology-page-types";
import {
  cx,
  microLabelClassName,
  SectionHeading,
  SectionReveal,
} from "@/components/marketing/methodology-page-utils";

export function FrameworkSection({
  content,
  isZh,
}: {
  content: MethodologyPageContent;
  isZh: boolean;
}) {
  return (
    <section className="pt-4 md:pt-8">
      <SectionReveal>
        <div className="overflow-hidden rounded-[3rem] border border-white/10 bg-[#020617] px-7 py-8 text-white shadow-[0_40px_120px_rgba(2,6,23,0.24)] md:px-10 md:py-12">
          <div className={cx("mx-auto", isZh ? "max-w-[720px]" : "max-w-3xl text-center")}>
            <SectionHeading
              isZh={isZh}
              eyebrow={content.framework.eyebrow}
              title={content.framework.title}
              description={content.framework.description}
              dark
            />
          </div>

          <div className="mt-10 grid gap-5 lg:grid-cols-3">
            {content.stages.map((stage, index) => (
              <SectionReveal key={stage.displayTitle ?? stage.title} delay={index * 0.06}>
                <FrameworkCard
                  stage={stage}
                  index={index}
                  isZh={isZh}
                  visualContent={content.frameworkVisual}
                />
              </SectionReveal>
            ))}
          </div>
        </div>
      </SectionReveal>
    </section>
  );
}

function FrameworkCard({
  stage,
  index,
  isZh,
  visualContent,
}: {
  stage: MethodologyPageContent["stages"][number];
  index: number;
  isZh: boolean;
  visualContent: MethodologyPageContent["frameworkVisual"];
}) {
  const primaryTitle = isZh ? stage.title : stage.displayTitle ?? stage.title;
  const secondaryTitle = isZh ? stage.displayTitle : stage.displayTitle ? stage.title : null;

  return (
    <div className="group flex h-full flex-col overflow-hidden rounded-[2rem] border border-white/10 bg-white/[0.04] p-6 transition-colors duration-300 hover:bg-white/[0.06]">
      <div className="flex items-center justify-between gap-4">
        <span className={microLabelClassName(isZh, true)}>
          {stage.weight}
        </span>
        <span
          className={cx(
            "rounded-full border border-white/10 bg-white/[0.05] px-3 py-1 text-white/56",
            isZh
              ? "text-[12px] font-medium tracking-[0.05em]"
              : "text-[11px] uppercase tracking-[0.18em]"
          )}
        >
          {String(index + 1).padStart(2, "0")}
        </span>
      </div>

      <h3
        className={cx(
          "mt-5 font-semibold text-white",
          isZh
            ? "text-[24px] leading-[1.24] tracking-[-0.015em]"
            : "text-3xl tracking-[-0.04em]"
        )}
      >
        {primaryTitle}
      </h3>
      {secondaryTitle ? (
        <p className={microLabelClassName(isZh, true)}>
          {secondaryTitle}
        </p>
      ) : null}
      <p
        className={cx(
          "mt-4 text-base text-white/64",
          isZh ? "leading-[1.82]" : "leading-relaxed"
        )}
      >
        {stage.description}
      </p>

      <div className="mt-8 flex flex-1 items-end">
        <div className="w-full rounded-[1.7rem] border border-white/10 bg-black/22 p-4">
          <FrameworkVisual
            index={index}
            isZh={isZh}
            visualContent={visualContent}
          />
          <div className="mt-4 flex flex-wrap gap-2">
            {stage.checks.map((check) => (
              <span
                key={check}
                className={cx(
                  "rounded-full border border-white/10 bg-white/[0.05] px-3 py-1.5 text-white/58",
                  isZh
                    ? "text-[12px] font-medium tracking-[0.04em]"
                    : "text-[11px] uppercase tracking-[0.16em]"
                )}
              >
                {check}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function FrameworkVisual({
  index,
  isZh,
  visualContent,
}: {
  index: number;
  isZh: boolean;
  visualContent: MethodologyPageContent["frameworkVisual"];
}) {
  if (index === 0) {
    const rows = visualContent.desirabilityRows;

    return (
      <div className="space-y-3">
        {rows.map((row, rowIndex) => (
          <div key={row.label}>
            <div
              className={cx(
                "flex items-center justify-between gap-4 text-white/48",
                isZh
                  ? "text-[12px] font-medium tracking-[0.04em]"
                  : "text-[11px] uppercase tracking-[0.16em]"
              )}
            >
              <span>{row.label}</span>
              <span>{row.value}</span>
            </div>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/8">
              <div
                className="h-full rounded-full bg-[linear-gradient(90deg,rgba(191,219,254,0.95),rgba(96,165,250,0.92))]"
                style={{ width: `${84 - rowIndex * 9}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (index === 1) {
    return (
      <div className="grid place-items-center">
        <div
          className="grid h-32 w-32 place-items-center rounded-full"
          style={{
            background:
              "conic-gradient(rgba(147,197,253,1) 0deg, rgba(59,130,246,0.94) 266deg, rgba(255,255,255,0.12) 266deg 360deg)",
          }}
        >
          <div className="grid h-24 w-24 place-items-center rounded-full bg-[#081223] text-center">
            <div>
              <p className="text-3xl font-semibold tracking-[-0.05em] text-white">
                74
              </p>
              <p
                className={cx(
                  "text-white/46",
                  isZh
                    ? "text-[11px] font-medium tracking-[0.04em]"
                    : "text-[10px] uppercase tracking-[0.18em]"
                )}
              >
                {visualContent.viabilityLabel}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const highlightedCells = new Set([2, 6, 11]);

  return (
    <div>
      <div className="grid grid-cols-4 gap-2">
        {Array.from({ length: 16 }, (_, cellIndex) => (
          <div
            key={cellIndex}
            className={cx(
              "h-11 rounded-2xl border",
              highlightedCells.has(cellIndex)
                ? "border-[#93c5fd]/30 bg-[linear-gradient(180deg,rgba(59,130,246,0.28),rgba(255,255,255,0.08))]"
                : "border-white/8 bg-white/[0.04]"
            )}
          />
        ))}
      </div>
      <div
        className={cx(
          "mt-4 flex items-center justify-between gap-4 text-white/48",
          isZh
            ? "text-[12px] font-medium tracking-[0.04em]"
            : "text-[11px] uppercase tracking-[0.16em]"
        )}
      >
        <span>{visualContent.feasibilityAxes.left}</span>
        <span>{visualContent.feasibilityAxes.right}</span>
      </div>
    </div>
  );
}
