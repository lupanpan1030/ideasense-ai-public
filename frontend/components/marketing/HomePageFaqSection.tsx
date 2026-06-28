import { useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { buildLocalePath } from "@/lib/i18n/config";
import { useAppLocale } from "@/lib/i18n/provider";
import { HomePageSectionReveal, HomePageSectionShell } from "./HomePageSectionShell";
import {
  EASE_OUT,
  type HomeContent,
  cx,
  focusRingOnLight,
} from "./home-page-utils";

export function FaqAndCtaSection({
  home,
}: {
  home: HomeContent;
}) {
  const locale = useAppLocale();
  const [openIndex, setOpenIndex] = useState(0);

  return (
    <HomePageSectionShell id="faq" className="pb-24 md:pb-32">
      <div className="mx-auto max-w-6xl px-6">
        <div className="grid gap-10 lg:grid-cols-[minmax(0,1.04fr)_minmax(320px,25.5rem)] lg:items-start xl:gap-14">
          <div>
            <HomePageSectionReveal className="max-w-2xl">
              <p className="text-xs uppercase tracking-[0.24em] text-[#2563eb]">
                {home.faq.eyebrow}
              </p>
              <h2 className="mt-5 text-4xl font-semibold leading-[0.96] tracking-[-0.05em] text-[#0f172a] md:text-6xl">
                {home.faq.title}
              </h2>
              <p className="mt-6 max-w-xl text-base leading-relaxed text-[#475569] md:text-lg">
                {home.faq.description}
              </p>
            </HomePageSectionReveal>

            <div className="mt-10 space-y-4">
              {home.faq.items.map((item, index) => {
                const isOpen = openIndex === index;

                return (
                  <HomePageSectionReveal key={item.id} delay={0.12 + index * 0.05}>
                    <div
                      className={cx(
                        "overflow-hidden rounded-[1.85rem] border bg-white/80 shadow-[0_18px_52px_rgba(15,23,42,0.05)] transition-[border-color,box-shadow,background-color] duration-300",
                        isOpen
                          ? "border-[#2563eb]/12 bg-white shadow-[0_24px_64px_rgba(37,99,235,0.08)]"
                          : "border-black/6"
                      )}
                    >
                      <button
                        type="button"
                        onClick={() => setOpenIndex(isOpen ? -1 : index)}
                        aria-expanded={isOpen}
                        className="flex w-full cursor-pointer items-center justify-between gap-6 px-6 py-5 text-left transition-colors hover:bg-black/[0.015] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2563eb]/30 md:px-7"
                      >
                        <span className="max-w-4xl text-lg font-medium tracking-[-0.02em] text-[#0f172a]">
                          {item.question}
                        </span>
                        <span className="shrink-0 text-2xl leading-none text-[#2563eb]">
                          {isOpen ? "−" : "+"}
                        </span>
                      </button>

                      <AnimatePresence initial={false}>
                        {isOpen ? (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: "auto", opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.28, ease: EASE_OUT }}
                            className="overflow-hidden"
                          >
                            <div className="border-t border-black/6 px-6 py-5 md:px-7">
                              <p className="max-w-4xl text-base leading-relaxed text-[#475569]">
                                {item.answer}
                              </p>
                            </div>
                          </motion.div>
                        ) : null}
                      </AnimatePresence>
                    </div>
                  </HomePageSectionReveal>
                );
              })}
            </div>
          </div>

          <HomePageSectionReveal delay={0.08} className="lg:sticky lg:top-28 lg:justify-self-end lg:w-full lg:max-w-[25.5rem] lg:self-start">
            <div className="overflow-hidden rounded-[2rem] border border-black/6 bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(248,250,252,0.88))] p-6 shadow-[0_22px_60px_rgba(15,23,42,0.06)] backdrop-blur md:p-7">
              <p className="text-xs uppercase tracking-[0.24em] text-[#2563eb]">
                {home.closing.eyebrow}
              </p>
              <h3 className="mt-4 max-w-[16rem] text-[2.55rem] font-semibold leading-[0.94] tracking-[-0.055em] text-[#0f172a] md:text-[2.9rem]">
                {home.closing.title}
              </h3>
              <p className="mt-4 text-base leading-relaxed text-[#475569]">
                {home.closing.description}
              </p>

              <div className="mt-7 space-y-3">
                <Link
                  href={buildLocalePath(locale, "/register")}
                  className={cx(
                    "inline-flex w-full items-center justify-center gap-2 rounded-full bg-[#0f172a] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#020617]",
                    focusRingOnLight
                  )}
                >
                  {home.closing.primaryCta}
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  href={buildLocalePath(locale, "/sample")}
                  className={cx(
                    "inline-flex w-full items-center justify-center rounded-full border border-black/8 bg-white px-5 py-3 text-sm font-medium text-[#0f172a] transition hover:border-[#2563eb]/18 hover:bg-[#f8fbff] hover:shadow-[0_12px_30px_rgba(15,23,42,0.08)]",
                    focusRingOnLight
                  )}
                >
                  {home.closing.secondaryCta}
                </Link>
              </div>

              <p className="mt-5 text-sm leading-relaxed text-[#64748b]">
                {home.closing.footnote}
              </p>
            </div>
          </HomePageSectionReveal>
        </div>
      </div>
    </HomePageSectionShell>
  );
}
