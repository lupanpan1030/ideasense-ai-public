"use client";

import Image from "next/image";
import Link from "next/link";
import { ArrowRight, ExternalLink } from "lucide-react";

import {
  HomePageSectionReveal,
  HomePageSectionShell,
} from "@/components/marketing/HomePageSectionShell";
import {
  MARKETING_ASSETS,
  type HomeContent,
  type MethodologyContent,
  cx,
  focusRingOnDark,
} from "@/components/marketing/home-page-utils";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale } from "@/lib/i18n/provider";

export function HomePageTrustSection({
  home,
  methodology,
  isZh,
}: {
  home: HomeContent;
  methodology: MethodologyContent;
  isZh: boolean;
}) {
  const locale = useAppLocale();
  const founder = home.team.members[0];
  const summaryCards = [
    {
      label: isZh ? "适合对象" : "Built for",
      value: home.hero.audience,
    },
    {
      label: isZh ? "会话方式" : "Session format",
      value:
        methodology.sessionSteps[0]?.description ?? methodology.sessionTitle,
    },
    {
      label: isZh ? "核心产出" : "Core output",
      value: methodology.outputs[1] ?? methodology.outputs[0],
    },
  ];

  return (
    <HomePageSectionShell id="team" className="pt-10 md:pt-16">
      <div className="mx-auto max-w-6xl px-6">
        <HomePageSectionReveal>
          <div className="overflow-hidden rounded-[3rem] border border-white/10 bg-[#081223] p-7 text-white shadow-[0_34px_100px_rgba(2,6,23,0.22)] md:p-10">
            <div className="grid gap-10 lg:grid-cols-[320px_minmax(0,1fr)] lg:items-center">
              <a
                href={founder?.href ?? "https://www.ethanchenlu.com"}
                target="_blank"
                rel="noopener noreferrer"
                title={
                  isZh
                    ? `个人主页：${founder?.name ?? "Ethan Lu"}`
                    : `Personal website: ${founder?.name ?? "Ethan Lu"}`
                }
                aria-label={
                  isZh
                    ? `打开 ${founder?.name ?? "Ethan Lu"} 的个人主页`
                    : `Open ${founder?.name ?? "Ethan Lu"} personal website`
                }
                className="relative block overflow-hidden rounded-[2.2rem] border border-white/10 bg-white/[0.04] p-2 transition-colors hover:border-[#93c5fd]/45 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#93c5fd]/60"
              >
                <div className="relative aspect-[4/5] overflow-hidden rounded-[1.7rem] bg-[#111827]">
                  <Image
                    src={founder?.image ?? MARKETING_ASSETS.founderPortrait}
                    alt={founder?.name ?? "Founder"}
                    fill
                    sizes="(max-width: 1024px) 100vw, 320px"
                    className="object-cover"
                  />
                  <div className="absolute inset-x-0 bottom-0 bg-[linear-gradient(180deg,rgba(2,6,23,0)_0%,rgba(2,6,23,0.82)_100%)] p-5">
                    <p className="text-xl font-semibold tracking-[-0.04em] text-white">
                      {founder?.name ?? "ethan"}
                    </p>
                    <p className="mt-1 text-sm text-white/60">
                      {founder?.role ?? home.team.title}
                    </p>
                    <p className="mt-3 inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-medium text-white/82 backdrop-blur">
                      <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                      {isZh ? "个人主页" : "Personal website"}
                    </p>
                  </div>
                </div>
              </a>

              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-[#93c5fd]">
                  {home.team.eyebrow}
                </p>
                <h2 className="mt-5 text-4xl font-semibold leading-[0.96] tracking-[-0.05em] md:text-6xl">
                  {home.team.title}
                </h2>
                <p className="mt-6 max-w-2xl text-base leading-relaxed text-white/66 md:text-lg">
                  {home.team.description}
                </p>

                <div className="mt-8 grid gap-4 md:grid-cols-3">
                  {summaryCards.map((card) => (
                    <div
                      key={card.label}
                      className="rounded-[1.7rem] border border-white/10 bg-white/[0.05] p-5"
                    >
                      <p className="text-[11px] uppercase tracking-[0.22em] text-[#93c5fd]">
                        {card.label}
                      </p>
                      <p className="mt-3 text-sm leading-relaxed text-white/66">
                        {card.value}
                      </p>
                    </div>
                  ))}
                </div>

                <div className="mt-8 rounded-[2rem] border border-white/10 bg-white/[0.06] p-6">
                  <p className="text-[11px] uppercase tracking-[0.22em] text-[#93c5fd]">
                    {home.team.collaborationTitle}
                  </p>
                  <p className="mt-4 max-w-2xl text-lg font-medium tracking-[-0.03em] text-white">
                    {home.team.collaborationDescription}
                  </p>

                  <div className="mt-6 flex flex-wrap items-center gap-3">
                    <Link
                      href={buildLocalePath(locale, "/register")}
                      className={cx(
                        "inline-flex items-center gap-2 rounded-full bg-white px-5 py-3 text-sm font-medium text-[#020617] transition hover:bg-white/92",
                        focusRingOnDark
                      )}
                    >
                      {home.hero.primaryCta}
                      <ArrowRight className="h-4 w-4" />
                    </Link>
                    <Link
                      href={buildLocalePath(locale, "/sample-report")}
                      className={cx(
                        "inline-flex items-center rounded-full border border-white/12 bg-white/[0.05] px-5 py-3 text-sm text-white transition hover:bg-white/[0.08]",
                        focusRingOnDark
                      )}
                    >
                      {home.hero.reportCta}
                    </Link>
                  </div>

                  <p className="mt-5 text-sm text-white/52">
                    {home.team.collaborationFootnote}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </HomePageSectionReveal>
      </div>
    </HomePageSectionShell>
  );
}
