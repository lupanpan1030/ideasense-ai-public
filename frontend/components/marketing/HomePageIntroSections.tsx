"use client";

import Image from "next/image";
import Link from "next/link";
import { ArrowRight, FileText, Radar, ScanSearch } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";

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

export function HomePageHeroSection({
  home,
  isZh,
}: {
  home: HomeContent;
  isZh: boolean;
}) {
  const locale = useAppLocale();
  const prefersReducedMotion = useReducedMotion();

  return (
    <section className="relative px-5 pb-14 pt-8 md:px-6 md:pb-20 md:pt-12">
      <div className="mx-auto max-w-6xl">
        <div className="mx-auto max-w-3xl text-center">
          <div className="inline-flex items-center rounded-full border border-white/80 bg-white/72 px-4 py-2 text-[11px] uppercase tracking-[0.28em] text-[#2563eb] shadow-[0_14px_32px_rgba(15,23,42,0.04)] backdrop-blur">
            {home.hero.badge}
          </div>
          <p className="mx-auto mt-4 max-w-2xl text-sm text-[#475569] md:text-base">
            {home.hero.meta}
          </p>

          <h1 className="mt-5 text-[clamp(3rem,7vw,5.6rem)] font-semibold leading-[0.94] tracking-[-0.045em] text-[#0f172a]">
            {home.hero.headline}
          </h1>
          <p className="mx-auto mt-4 max-w-3xl text-lg font-medium tracking-[-0.03em] text-[#1e293b] md:text-[1.35rem]">
            {home.hero.subheadline}
          </p>
          <p className="mx-auto mt-3 max-w-2xl text-base leading-relaxed text-[#475569] md:text-lg">
            {home.hero.description}
          </p>

          <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
            <Link
              href={buildLocalePath(locale, "/register")}
              className={cx(
                "inline-flex items-center gap-2 rounded-full bg-[#0f172a] px-6 py-3 text-sm font-medium text-white transition hover:bg-[#020617]",
                focusRingOnLight
              )}
            >
              {home.hero.primaryCta}
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href={buildLocalePath(locale, "/sample-report")}
              className={cx(
                "inline-flex items-center gap-2 rounded-full border border-black/8 bg-white/80 px-6 py-3 text-sm font-medium text-[#0f172a] transition hover:border-[#2563eb]/18 hover:bg-[#f8fbff] hover:shadow-[0_12px_30px_rgba(15,23,42,0.08)]",
                focusRingOnLight
              )}
            >
              {home.hero.reportCta}
            </Link>
          </div>

          <div className="mt-4 flex flex-wrap items-center justify-center gap-4 text-sm text-[#475569]">
            <Link
              href={buildLocalePath(locale, "/sample")}
              className={cx(
                "transition hover:text-[#0f172a] hover:underline hover:underline-offset-4 focus-visible:rounded-sm focus-visible:underline focus-visible:underline-offset-4",
                focusRingOnLight
              )}
            >
              {home.hero.sampleCta}
            </Link>
            <span className="hidden h-1 w-1 rounded-full bg-[#cbd5e1] sm:inline-block" />
            <span>{home.hero.audience}</span>
          </div>
        </div>

        <div className="relative mx-auto mt-8 max-w-[1080px] md:mt-10">
          <div className="pointer-events-none absolute inset-x-12 -top-10 h-44 rounded-full bg-[radial-gradient(circle,rgba(37,99,235,0.18),transparent_68%)] blur-3xl" />

          <div className="relative rounded-[2.8rem] border border-white/70 bg-[#060b16] p-2 shadow-[0_42px_140px_rgba(15,23,42,0.22)]">
            <div className="relative aspect-[16/10] overflow-hidden rounded-[2.2rem] border border-white/10 bg-[#020617]">
              {!prefersReducedMotion ? (
                <video
                  className="h-full w-full object-cover"
                  autoPlay
                  muted
                  loop
                  playsInline
                  preload="metadata"
                  poster={MARKETING_ASSETS.heroPoster}
                >
                  <source src={MARKETING_ASSETS.heroVideoWebm} type="video/webm" />
                  <source src={MARKETING_ASSETS.heroVideoMp4} type="video/mp4" />
                </video>
              ) : (
                <Image
                  src={MARKETING_ASSETS.heroPoster}
                  alt={home.hero.backgroundAlt}
                  fill
                  loading="eager"
                  sizes="(max-width: 1024px) 100vw, 1100px"
                  className="object-cover"
                />
              )}

              <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(2,6,23,0.02)_0%,rgba(2,6,23,0.14)_100%)]" />

              <div className="absolute left-4 right-4 top-4 flex items-center justify-between rounded-full border border-white/12 bg-black/24 px-4 py-2 text-[11px] uppercase tracking-[0.22em] text-white/70 backdrop-blur md:left-6 md:right-6 md:top-6">
                <span>{isZh ? "结构化评审工作区" : "Structured review workspace"}</span>
                <span>{isZh ? "开放注册" : "Open registration"}</span>
              </div>

              <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between rounded-full border border-white/12 bg-black/28 px-4 py-2 text-[11px] uppercase tracking-[0.2em] text-white/74 backdrop-blur md:bottom-6 md:left-6 md:right-6">
                <span>{isZh ? "真实 Dogfooding 录屏" : "Live dogfooding capture"}</span>
                <span>{isZh ? "DVF 77 / 100" : "DVF 77 / 100"}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function HomePageProblemSection({
  home,
  methodology,
  isZh,
}: {
  home: HomeContent;
  methodology: MethodologyContent;
  isZh: boolean;
}) {
  const locale = useAppLocale();
  const prefersReducedMotion = useReducedMotion();
  const cards = [
    {
      icon: ScanSearch,
      label: isZh ? "追问" : "Interrogate",
      title: methodology.sessionSteps[1]?.title ?? home.features.title,
      description:
        methodology.sessionSteps[1]?.description ?? home.features.description,
    },
    {
      icon: Radar,
      label: isZh ? "量化" : "Quantify",
      title: isZh ? "把模糊判断拆成可解释信号" : "Turn intuition into explainable signals",
      description: methodology.description,
    },
    {
      icon: FileText,
      label: isZh ? "落到决策" : "Decide",
      title: isZh ? "把最危险的问题放到桌面上" : "Bring the most dangerous unknowns forward",
      description: home.closing.description,
    },
  ];

  return (
    <HomePageSectionShell id="features">
      <div className="mx-auto max-w-6xl px-6">
        <div className="grid gap-12 lg:grid-cols-[minmax(0,1.06fr)_minmax(0,0.94fr)] lg:items-start xl:gap-16">
          <HomePageSectionReveal className="max-w-[39rem] lg:pr-6">
            <p className="text-xs uppercase tracking-[0.24em] text-[#2563eb]">
              {home.features.eyebrow}
            </p>
            <h2 className="mt-5 text-4xl font-semibold leading-[0.96] tracking-[-0.05em] text-[#0f172a] md:text-6xl">
              {home.features.title}
            </h2>
            <p className="mt-6 text-base leading-relaxed text-[#475569] md:text-lg">
              {home.features.description}
            </p>

            <div className="mt-8 flex flex-col items-start gap-4">
              <Link
                href={buildLocalePath(locale, "/methodology")}
                className={cx(
                  "inline-flex items-center gap-2 rounded-full border border-black/8 bg-white px-5 py-3 text-sm font-medium text-[#0f172a] transition hover:border-[#2563eb]/18 hover:bg-[#f8fbff] hover:shadow-[0_12px_30px_rgba(15,23,42,0.08)]",
                  focusRingOnLight
                )}
              >
                {home.features.cta}
                <ArrowRight className="h-4 w-4" />
              </Link>
              <span className="max-w-md text-sm leading-relaxed text-[#475569]">
                {isZh
                  ? "从第一轮追问到最终报告，整个评审流程都保持透明可追踪。"
                  : "The review flow stays transparent from the first prompt to the final report."}
              </span>
            </div>

            <div className="mt-10 max-w-lg rounded-[1.85rem] border border-black/6 bg-white/58 p-5 shadow-[0_20px_56px_rgba(15,23,42,0.05)] backdrop-blur md:p-6">
              <p className="text-[11px] uppercase tracking-[0.24em] text-[#2563eb]">
                {home.process.eyebrow}
              </p>
              <p className="mt-3 text-[1.45rem] font-semibold leading-[1.05] tracking-[-0.04em] text-[#0f172a] md:text-[1.7rem]">
                {home.process.title}
              </p>
              <p className="mt-4 text-sm leading-relaxed text-[#475569] md:text-[15px]">
                {home.process.description}
              </p>

              <div className="mt-5 flex flex-wrap gap-2">
                {cards.map((card) => (
                  <span
                    key={card.label}
                    className="rounded-full border border-black/6 bg-[#f8fbff] px-3 py-2 text-[11px] uppercase tracking-[0.18em] text-[#2563eb]"
                  >
                    {card.label}
                  </span>
                ))}
              </div>
            </div>
          </HomePageSectionReveal>

          <div className="grid gap-5 lg:ml-auto lg:max-w-[30rem]">
            {cards.map((card, index) => {
              const Icon = card.icon;

              return (
                <motion.div
                  key={card.label}
                  initial={
                    prefersReducedMotion
                      ? undefined
                      : { opacity: 0, x: 20, y: 26, scale: 0.985 }
                  }
                  whileInView={
                    prefersReducedMotion
                      ? undefined
                      : { opacity: 1, x: 0, y: 0, scale: 1 }
                  }
                  viewport={{ once: true, amount: 0.3 }}
                  transition={
                    prefersReducedMotion
                      ? undefined
                      : {
                          delay: 0.08 + index * 0.14,
                          type: "spring",
                          stiffness: 88,
                          damping: 18,
                          mass: 0.9,
                        }
                  }
                >
                  <div className="rounded-[2rem] border border-black/6 bg-white/72 p-6 shadow-[0_24px_64px_rgba(15,23,42,0.05)] backdrop-blur transition-[transform,box-shadow,border-color] duration-500 ease-out hover:-translate-y-1 hover:border-[#2563eb]/12 hover:shadow-[0_30px_72px_rgba(37,99,235,0.08)] md:p-7">
                    <div className="flex items-start gap-4">
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-black/6 bg-[#eff6ff] text-[#2563eb]">
                        <Icon className="h-5 w-5" />
                      </div>
                      <div className="max-w-[25rem]">
                        <p className="text-[11px] uppercase tracking-[0.24em] text-[#2563eb]">
                          {card.label}
                        </p>
                        <h3 className="mt-3 text-[1.85rem] font-semibold leading-[1.08] tracking-[-0.04em] text-[#0f172a]">
                          {card.title}
                        </h3>
                        <p className="mt-4 text-base leading-relaxed text-[#475569]">
                          {card.description}
                        </p>
                      </div>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      </div>
    </HomePageSectionShell>
  );
}
