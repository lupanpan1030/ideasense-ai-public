"use client";

import Image from "next/image";
import Link from "next/link";
import { ArrowRight, ShieldCheck } from "lucide-react";

import {
  HomePageSectionReveal,
  HomePageSectionShell,
} from "@/components/marketing/HomePageSectionShell";
import {
  MARKETING_ASSETS,
  type HomeContent,
  type MethodologyContent,
  cx,
  focusRingOnLight,
} from "@/components/marketing/home-page-utils";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale } from "@/lib/i18n/provider";

export function HomePageReportSection({
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
    <HomePageSectionShell className="pt-10 md:pt-16">
      <div className="relative mx-auto max-w-6xl px-6">
        <div className="grid gap-14 lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)] lg:items-center">
          <HomePageSectionReveal className="max-w-xl">
            <p className="text-xs uppercase tracking-[0.24em] text-[#2563eb]">
              {home.insights.eyebrow}
            </p>
            <h2 className="mt-5 text-4xl font-semibold leading-[0.96] tracking-[-0.05em] text-[#0f172a] md:text-6xl">
              {home.insights.title}
            </h2>
            <p className="mt-6 text-base leading-relaxed text-[#475569] md:text-lg">
              {home.insights.description}
            </p>

            <div className="mt-8 space-y-3">
              {methodology.outputs.slice(0, 3).map((output) => (
                <div
                  key={output}
                  className="flex items-start gap-3 rounded-[1.4rem] border border-black/6 bg-white/74 px-4 py-4"
                >
                  <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-[#2563eb]" />
                  <p className="text-sm leading-relaxed text-[#475569]">
                    {output}
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
                {home.insights.cta}
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href={buildLocalePath(locale, "/register")}
                className={cx(
                  "inline-flex items-center rounded-full border border-black/8 bg-white px-5 py-3 text-sm font-medium text-[#0f172a] transition hover:border-[#2563eb]/18 hover:bg-[#f8fbff] hover:shadow-[0_12px_30px_rgba(15,23,42,0.08)]",
                  focusRingOnLight
                )}
              >
                {home.hero.primaryCta}
              </Link>
            </div>

            <p className="mt-5 text-sm text-[#64748b]">{home.insights.footnote}</p>
          </HomePageSectionReveal>

          <HomePageSectionReveal delay={0.08}>
            <div className="relative mx-auto w-full max-w-[660px] pb-20 md:pb-16">
              <div className="pointer-events-none absolute inset-x-[14%] top-[-8%] h-40 rounded-full bg-[radial-gradient(circle,rgba(37,99,235,0.16),transparent_68%)] blur-3xl" />

              <div className="relative overflow-hidden rounded-[2.4rem] border border-black/8 bg-white p-3 shadow-[0_30px_90px_rgba(15,23,42,0.14)]">
                <div className="relative aspect-[16/10] overflow-hidden rounded-[1.9rem] border border-black/6 bg-[#f8fafc]">
                  <Image
                    src={MARKETING_ASSETS.reportCover}
                    alt={home.insights.imageAlts.primary}
                    fill
                    loading="eager"
                    sizes="(max-width: 1024px) 100vw, 640px"
                    className="object-cover"
                  />
                </div>
              </div>

              <div className="absolute -right-2 top-16 hidden w-[34%] overflow-hidden rounded-[1.5rem] border border-black/8 bg-white p-1.5 shadow-[0_22px_60px_rgba(15,23,42,0.14)] sm:block md:-right-8 md:top-14">
                <div className="relative aspect-[4/5] overflow-hidden rounded-[1.1rem] border border-black/6 bg-[#f8fafc]">
                  <Image
                    src={MARKETING_ASSETS.reportDetail}
                    alt={home.insights.imageAlts.secondary}
                    fill
                    sizes="(max-width: 1024px) 34vw, 220px"
                    className="object-cover"
                  />
                </div>
              </div>

              <div className="absolute bottom-0 left-4 right-4 flex items-center gap-4 rounded-[1.35rem] border border-black/8 bg-white/90 p-4 shadow-[0_18px_48px_rgba(15,23,42,0.12)] backdrop-blur md:left-6 md:right-auto md:w-[430px]">
                <div className="shrink-0">
                  <p className="text-[10px] uppercase tracking-[0.22em] text-[#2563eb]">
                    {isZh ? "决策建议" : "Decision band"}
                  </p>
                  <p className="mt-1 text-3xl font-semibold tracking-[-0.05em] text-[#0f172a]">
                    77
                    <span className="ml-1 text-sm text-[#64748b]">/100</span>
                  </p>
                </div>
                <p className="text-sm leading-relaxed text-[#475569]">
                  {isZh
                    ? "有护栏地推进：先验证完成率和报告可追溯性。"
                    : "Proceed with guardrails: validate completion and report traceability first."}
                </p>
              </div>
            </div>
          </HomePageSectionReveal>
        </div>
      </div>
    </HomePageSectionShell>
  );
}
