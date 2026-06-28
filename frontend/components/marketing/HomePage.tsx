"use client";

import { useReducedMotion } from "framer-motion";

import { FaqAndCtaSection } from "@/components/marketing/HomePageFaqSection";
import { MarketingHeader } from "@/components/marketing/HomePageHeader";
import {
  HomePageDvfSection,
  HomePageHeroSection,
  HomePageProblemSection,
  HomePageReportSection,
  HomePageTrustSection,
} from "@/components/marketing/HomePageSections";
import { MarketingFooter } from "@/components/marketing/MarketingFooter";
import {
  MARKETING_SECTION_IDS,
  type SectionId,
  useActiveMarketingSection,
  useMarketingPageContent,
} from "@/components/marketing/home-page-utils";
import { useAppLocale } from "@/lib/i18n/provider";

export default function HomePage() {
  const locale = useAppLocale();
  const prefersReducedMotion = useReducedMotion();
  const marketing = useMarketingPageContent();
  const home = marketing.home;
  const methodology = marketing.methodology;
  const isZh = locale === "zh";
  const activeSection = useActiveMarketingSection([...MARKETING_SECTION_IDS]);

  const scrollToTop = () => {
    window.scrollTo({
      top: 0,
      behavior: prefersReducedMotion ? "auto" : "smooth",
    });
  };

  const scrollToSection = (sectionId: SectionId) => {
    document.getElementById(sectionId)?.scrollIntoView({
      behavior: prefersReducedMotion ? "auto" : "smooth",
      block: "start",
    });
  };

  return (
    <div className="relative overflow-x-hidden bg-[linear-gradient(180deg,#f8fafc_0%,#f5f5f7_48%,#eef2f7_100%)] text-[#0f172a]">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-x-0 top-0 h-[42rem] bg-[radial-gradient(circle_at_top,rgba(37,99,235,0.16),transparent_42%),radial-gradient(circle_at_18%_12%,rgba(255,255,255,0.88),transparent_34%)]" />
        <div className="absolute inset-x-0 top-[24rem] h-[38rem] bg-[radial-gradient(circle_at_center,rgba(15,23,42,0.05),transparent_48%)]" />
        <div className="absolute inset-x-0 bottom-0 h-[24rem] bg-[linear-gradient(180deg,rgba(245,245,247,0)_0%,rgba(235,240,246,0.68)_100%)]" />
      </div>

      <MarketingHeader
        activeSection={activeSection}
        content={home}
        onNavigate={scrollToSection}
        onScrollTop={scrollToTop}
      />

      <main className="relative z-10">
        <HomePageHeroSection home={home} isZh={isZh} />
        <HomePageProblemSection
          home={home}
          methodology={methodology}
          isZh={isZh}
        />
        <HomePageDvfSection home={home} methodology={methodology} isZh={isZh} />
        <HomePageReportSection home={home} methodology={methodology} isZh={isZh} />
        <HomePageTrustSection home={home} methodology={methodology} isZh={isZh} />
        <FaqAndCtaSection home={home} />
      </main>

      <div className="relative z-10 mx-auto max-w-6xl px-6 pb-10">
        <MarketingFooter isZh={isZh} />
      </div>
    </div>
  );
}
