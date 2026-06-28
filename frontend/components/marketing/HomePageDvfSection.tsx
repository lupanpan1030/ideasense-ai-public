"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";

import {
  HomePageSectionReveal,
  HomePageSectionShell,
} from "@/components/marketing/HomePageSectionShell";
import {
  type HomeContent,
  type MethodologyContent,
  cx,
  focusRingOnDark,
} from "@/components/marketing/home-page-utils";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale } from "@/lib/i18n/provider";

export function HomePageDvfSection({
  home,
  methodology,
  isZh,
}: {
  home: HomeContent;
  methodology: MethodologyContent;
  isZh: boolean;
}) {
  const locale = useAppLocale();

  return (
    <HomePageSectionShell id="process" className="pt-8 md:pt-12">
      <div className="mx-auto max-w-6xl px-6">
        <HomePageSectionReveal>
          <div className="overflow-hidden rounded-[3rem] border border-white/10 bg-[#020617] px-7 py-8 text-white shadow-[0_40px_120px_rgba(2,6,23,0.24)] md:px-10 md:py-12">
            <div className="mx-auto max-w-3xl text-center">
              <p className="text-xs uppercase tracking-[0.28em] text-[#93c5fd]">
                {home.process.eyebrow}
              </p>
              <h2 className="mt-5 text-4xl font-semibold leading-[0.96] tracking-[-0.05em] md:text-6xl">
                {home.process.title}
              </h2>
              <p className="mt-5 text-base leading-relaxed text-white/66 md:text-lg">
                {home.process.description}
              </p>
            </div>

            <div className="mt-10 grid gap-5 lg:grid-cols-3">
              {methodology.stages.map((stage, index) => (
                <DvfStageCard
                  key={stage.title}
                  index={index}
                  isZh={isZh}
                  stage={stage}
                />
              ))}
            </div>

            <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
              <Link
                href={buildLocalePath(locale, "/register")}
                className={cx(
                  "inline-flex items-center gap-2 rounded-full bg-white px-5 py-3 text-sm font-medium text-[#020617] transition hover:bg-white/92",
                  focusRingOnDark
                )}
              >
                {home.process.cta}
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href={buildLocalePath(locale, "/sample-report")}
                className={cx(
                  "inline-flex items-center rounded-full border border-white/12 bg-white/6 px-5 py-3 text-sm text-white transition hover:bg-white/10",
                  focusRingOnDark
                )}
              >
                {home.insights.cta}
              </Link>
            </div>
          </div>
        </HomePageSectionReveal>
      </div>
    </HomePageSectionShell>
  );
}

function DvfStageCard({
  index,
  isZh,
  stage,
}: {
  index: number;
  isZh: boolean;
  stage: MethodologyContent["stages"][number];
}) {
  return (
    <div className="group flex h-full flex-col overflow-hidden rounded-[2rem] border border-white/10 bg-white/[0.04] p-6 transition-colors duration-300 hover:bg-white/[0.06]">
      <div className="flex items-center justify-between gap-4">
        <span className="text-[11px] uppercase tracking-[0.24em] text-white/48">
          {stage.weight}
        </span>
        <span className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-white/56">
          {String(index + 1).padStart(2, "0")}
        </span>
      </div>

      <h3 className="mt-5 text-3xl font-semibold tracking-[-0.04em] text-white">
        {stage.title}
      </h3>
      <p className="mt-4 text-base leading-relaxed text-white/64">
        {stage.description}
      </p>

      <div className="mt-8 flex flex-1 items-end">
        <div className="w-full rounded-[1.7rem] border border-white/10 bg-black/22 p-4">
          <DvfVisual index={index} isZh={isZh} />
        </div>
      </div>
    </div>
  );
}

function DvfVisual({ index, isZh }: { index: number; isZh: boolean }) {
  if (index === 0) {
    const rows = [
      { label: isZh ? "痛点强度" : "Pain intensity", value: "84%" },
      { label: isZh ? "用户清晰度" : "Audience clarity", value: "76%" },
      { label: isZh ? "时机判断" : "Urgency signal", value: "71%" },
      { label: isZh ? "证据密度" : "Evidence density", value: "63%" },
    ];

    return (
      <div className="space-y-3">
        {rows.map((row, rowIndex) => (
          <div key={row.label}>
            <div className="flex items-center justify-between gap-4 text-[11px] uppercase tracking-[0.16em] text-white/48">
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
    const chips = isZh
      ? ["市场规模", "商业模式", "竞争压力"]
      : ["Market size", "Business model", "Competition"];

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
              <p className="text-[10px] uppercase tracking-[0.18em] text-white/46">
                {isZh ? "商业可行性" : "Viability"}
              </p>
            </div>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap justify-center gap-2">
          {chips.map((chip) => (
            <span
              key={chip}
              className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1 text-[11px] uppercase tracking-[0.15em] text-white/58"
            >
              {chip}
            </span>
          ))}
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
      <div className="mt-4 flex items-center justify-between gap-4 text-[11px] uppercase tracking-[0.16em] text-white/48">
        <span>{isZh ? "影响高" : "High impact"}</span>
        <span>{isZh ? "不确定性高" : "High uncertainty"}</span>
      </div>
    </div>
  );
}
