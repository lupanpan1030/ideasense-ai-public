"use client";

import { MarketingFooter } from "@/components/marketing/MarketingFooter";
import { MarketingPageHeader } from "@/components/marketing/MarketingPageHeader";
import {
  ClosingSection,
  FrameworkSection,
  HeroSection,
  OutputsSection,
  ReviewSection,
  WhySection,
} from "@/components/marketing/MethodologyPageSections";
import type { MethodologyPageContent } from "@/components/marketing/methodology-page-types";

export function MethodologyPageView({
  content,
  isZh,
}: {
  content: MethodologyPageContent;
  isZh: boolean;
}) {
  return (
    <div className="relative overflow-x-hidden bg-[linear-gradient(180deg,#f8fafc_0%,#f5f5f7_48%,#eef2f7_100%)] text-[#0f172a]">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-x-0 top-0 h-[42rem] bg-[radial-gradient(circle_at_top,rgba(37,99,235,0.16),transparent_42%),radial-gradient(circle_at_18%_12%,rgba(255,255,255,0.9),transparent_34%)]" />
        <div className="absolute inset-x-0 top-[26rem] h-[40rem] bg-[radial-gradient(circle_at_center,rgba(15,23,42,0.05),transparent_48%)]" />
        <div className="absolute inset-x-0 bottom-0 h-[24rem] bg-[linear-gradient(180deg,rgba(245,245,247,0)_0%,rgba(235,240,246,0.68)_100%)]" />
      </div>

      <div className="relative z-10 mx-auto max-w-6xl px-5 py-8 md:px-6 md:py-14">
        <MarketingPageHeader isZh={isZh} />
        <HeroSection content={content} isZh={isZh} />
        <WhySection content={content} isZh={isZh} />
        <FrameworkSection content={content} isZh={isZh} />
        <ReviewSection content={content} isZh={isZh} />
        <OutputsSection content={content} isZh={isZh} />
        <ClosingSection content={content} isZh={isZh} />
        <MarketingFooter isZh={isZh} className="mt-10" />
      </div>
    </div>
  );
}
