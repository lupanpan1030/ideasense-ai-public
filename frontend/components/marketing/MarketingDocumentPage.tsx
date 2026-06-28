import Link from "next/link";

import { MarketingFooter } from "@/components/marketing/MarketingFooter";
import { MarketingPageHeader } from "@/components/marketing/MarketingPageHeader";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale } from "@/lib/i18n/provider";

const focusRingOnLight =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2563eb]/30 focus-visible:ring-offset-2 focus-visible:ring-offset-[#f5f5f7]";

type MarketingDocumentSection = {
  title: string;
  paragraphs: string[];
};

type MarketingDocumentPageProps = {
  eyebrow: string;
  title: string;
  summary: string;
  lastUpdatedLabel: string;
  lastUpdatedValue: string;
  sections: MarketingDocumentSection[];
  principles?: string[];
  primaryCtaLabel: string;
  secondaryCtaLabel: string;
  isZh: boolean;
};

export function MarketingDocumentPage({
  eyebrow,
  title,
  summary,
  lastUpdatedLabel,
  lastUpdatedValue,
  sections,
  principles,
  primaryCtaLabel,
  secondaryCtaLabel,
  isZh,
}: MarketingDocumentPageProps) {
  const locale = useAppLocale();

  return (
    <main className="min-h-screen bg-[#f5f5f7] text-[#0f172a]">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-x-0 top-0 h-[32rem] bg-[radial-gradient(circle_at_top,rgba(37,99,235,0.14),transparent_42%),radial-gradient(circle_at_16%_12%,rgba(255,255,255,0.88),transparent_34%)]" />
      </div>

      <div
        className={[
          "relative z-10 px-6 py-10 md:py-14",
          isZh ? "mx-auto max-w-[1120px] md:px-8" : "mx-auto max-w-5xl",
        ].join(" ")}
      >
        <MarketingPageHeader isZh={isZh} />

        <div
          className={[
            "mt-10 overflow-hidden border border-black/6 bg-white/82 shadow-[0_28px_90px_rgba(15,23,42,0.08)] backdrop-blur",
            isZh ? "rounded-[2.5rem] px-6 py-7 md:px-8 md:py-8" : "rounded-[2.8rem] px-7 py-8 md:px-10 md:py-10",
          ].join(" ")}
        >
          <p
            className={[
              "text-[#2563eb]",
              isZh
                ? "text-[13px] font-medium tracking-[0.04em]"
                : "text-xs uppercase tracking-[0.28em]",
            ].join(" ")}
          >
            {eyebrow}
          </p>
          <h1
            className={[
              "mt-5 font-semibold text-[#0f172a]",
              isZh
                ? "max-w-[11em] text-[clamp(2.3rem,4.6vw,4rem)] leading-[1.16] tracking-[-0.02em]"
                : "text-4xl leading-[0.96] tracking-[-0.05em] md:text-6xl",
            ].join(" ")}
          >
            {title}
          </h1>
          <p
            className={[
              "mt-5 max-w-3xl text-[#475569]",
              isZh
                ? "text-[15px] leading-[1.9] md:text-[17px]"
                : "text-base leading-relaxed md:text-lg",
            ].join(" ")}
          >
            {summary}
          </p>

          {principles?.length ? (
            <div
              className={[
                "mt-7 grid gap-3",
                isZh ? "md:grid-cols-3" : "sm:grid-cols-3",
              ].join(" ")}
            >
              {principles.map((item) => (
                <div
                  key={item}
                  className={[
                    "rounded-[1.4rem] border border-black/6 bg-white/88",
                    isZh ? "px-4 py-4 text-[15px] leading-[1.7]" : "px-4 py-4 text-sm leading-relaxed",
                  ].join(" ")}
                >
                  {item}
                </div>
              ))}
            </div>
          ) : null}

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link
              href={buildLocalePath(locale, "/register")}
              className={[
                "inline-flex items-center justify-center rounded-full bg-[#0f172a] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#020617]",
                focusRingOnLight,
              ].join(" ")}
            >
              {primaryCtaLabel}
            </Link>
            <Link
              href={buildLocalePath(locale, "/sample-report")}
              className={[
                "inline-flex items-center justify-center rounded-full border border-black/8 bg-white px-5 py-3 text-sm font-medium text-[#0f172a] transition hover:border-[#2563eb]/18 hover:bg-[#f8fbff] hover:shadow-[0_12px_30px_rgba(15,23,42,0.08)]",
                focusRingOnLight,
              ].join(" ")}
            >
              {secondaryCtaLabel}
            </Link>
          </div>

          <div className="mt-8 rounded-[1.8rem] border border-[#2563eb]/12 bg-[linear-gradient(180deg,rgba(37,99,235,0.06),rgba(255,255,255,0.94))] px-5 py-4">
            <p
              className={[
                "text-[#2563eb]",
                isZh
                  ? "text-[12px] font-medium tracking-[0.03em]"
                  : "text-[11px] uppercase tracking-[0.22em]",
              ].join(" ")}
            >
              {lastUpdatedLabel}
            </p>
            <p
              className={[
                "mt-2 font-medium text-[#334155]",
                isZh ? "text-[15px]" : "text-sm",
              ].join(" ")}
            >
              {lastUpdatedValue}
            </p>
          </div>
        </div>

        <div className="mt-8 space-y-4">
          {sections.map((section) => (
            <section
              key={section.title}
              className={[
                "rounded-[2rem] border border-black/6 bg-white/78 shadow-[0_20px_56px_rgba(15,23,42,0.05)]",
                isZh ? "px-5 py-6 md:px-6" : "px-6 py-6",
              ].join(" ")}
            >
              <h2
                className={[
                  "font-semibold text-[#0f172a]",
                  isZh
                    ? "text-[26px] leading-[1.3] tracking-[-0.015em]"
                    : "text-2xl tracking-[-0.04em]",
                ].join(" ")}
              >
                {section.title}
              </h2>
              <div className="mt-4 space-y-3">
                {section.paragraphs.map((paragraph) => (
                  <p
                    key={paragraph}
                    className={[
                      "text-[#475569]",
                      isZh
                        ? "text-[15px] leading-[1.9] md:text-[16px]"
                        : "text-sm leading-relaxed md:text-base",
                    ].join(" ")}
                  >
                    {paragraph}
                  </p>
                ))}
              </div>
            </section>
          ))}
        </div>

        <MarketingFooter isZh={isZh} className="mt-10" />
      </div>
    </main>
  );
}
