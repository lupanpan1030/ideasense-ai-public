import Link from "next/link";
import type { Metadata } from "next";
import { Badge } from "@/components/ui/badge";
import { buttonClassNames } from "@/components/ui/button";
import { MarketingSupportLinks } from "@/components/marketing/MarketingSupportLinks";
import { getSampleProjectsCached } from "@/features/sample/sample-api";
import { getRequestLocale } from "@/lib/i18n/request-locale";
import { APP_MESSAGES } from "@/lib/i18n/messages";
import { buildLocalePath } from "@/lib/i18n/config";

const focusRingOnLight =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2563eb]/30 focus-visible:ring-offset-2 focus-visible:ring-offset-[#f5f5f7]";

type SamplePageProps = {
  searchParams: Promise<{ stage?: string }>;
};

export async function generateMetadata(): Promise<Metadata> {
  const locale = await getRequestLocale();
  const isZh = locale === "zh";
  const fullTitle = isZh
    ? "IdeaSense AI | 示例工作区"
    : "IdeaSense AI | Sample Workspace";
  const description = isZh
    ? "在只读示例工作区中查看 IdeaSense AI 的项目、阶段访谈和报告流程。"
    : "Explore the read-only IdeaSense AI sample workspace with projects, staged interviews, and reports.";

  return {
    title: { absolute: fullTitle },
    description,
    alternates: {
      canonical: buildLocalePath(locale, "/sample"),
      languages: {
        en: buildLocalePath("en", "/sample"),
        zh: buildLocalePath("zh", "/sample"),
      },
    },
    openGraph: {
      title: fullTitle,
      description,
      url: buildLocalePath(locale, "/sample"),
      locale: isZh ? "zh_CN" : "en_US",
      type: "website",
    },
  };
}

export default async function SampleProjectsPage({ searchParams }: SamplePageProps) {
  const locale = await getRequestLocale();
  const messages = APP_MESSAGES[locale].samplePage;
  const isZh = locale === "zh";
  const localePrefix = `/${locale}`;
  const resolvedSearchParams = (await searchParams) ?? {};
  const stageFilter = (resolvedSearchParams.stage ?? "").toLowerCase();
  const isReportsView = stageFilter === "report";
  const projects = await getSampleProjectsCached();
  const filtered = isReportsView
    ? projects.filter((project) => project.stage.value === "report")
    : projects;

  const reportProjects = projects.filter((project) => project.stage.value === "report");
  const featuredProject = reportProjects[0] ?? projects[0] ?? null;
  const pageSubtitle = isReportsView
    ? messages.pageSubtitle.reports
    : messages.pageSubtitle.all;
  const totalProjects = projects.length;
  const totalReports = reportProjects.length;
  const totalInProgress = Math.max(totalProjects - totalReports, 0);

  return (
    <div className="sample-showcase-page">
      <div className="relative z-10 mx-auto max-w-6xl px-6 py-10 md:py-14">
        <section className="overflow-hidden rounded-[2.8rem] border border-black/6 bg-white/84 p-4 shadow-[0_28px_90px_rgba(15,23,42,0.08)] backdrop-blur md:p-5">
          <div className="rounded-[2.2rem] border border-black/6 bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(241,245,249,0.92))] p-6 md:p-8">
            <div className="grid gap-8 lg:grid-cols-[minmax(0,1.05fr)_minmax(320px,0.95fr)] lg:items-end">
              <div className="max-w-[760px]">
                <p className="text-[13px] font-medium tracking-[0.04em] text-[#2563eb]">
                  {messages.eyebrow}
                </p>
                <h1
                  className={[
                    "mt-5 font-semibold text-[#0f172a]",
                    isZh
                      ? "max-w-[11em] text-[clamp(2.35rem,4.8vw,4.1rem)] leading-[1.16] tracking-[-0.02em]"
                      : "max-w-[12ch] text-[clamp(2.7rem,5.2vw,4.8rem)] leading-[0.96] tracking-[-0.05em]",
                  ].join(" ")}
                >
                  {messages.title}
                </h1>
                <p
                  className={[
                    "mt-5 max-w-[42rem] text-[#475569]",
                    isZh
                      ? "text-[15px] leading-[1.9] md:text-[17px]"
                      : "text-base leading-relaxed md:text-lg",
                  ].join(" ")}
                >
                  {messages.description}
                </p>

                <div className="mt-8 flex flex-wrap items-center gap-3">
                  <Link className={buttonClassNames()} href={`${localePrefix}/sample-report`}>
                    {messages.viewFlagshipReport}
                  </Link>
                  <Link
                    className={buttonClassNames({ variant: "secondary" })}
                    href={`${localePrefix}/register`}
                  >
                    {messages.createProject}
                  </Link>
                </div>

                <div className="mt-10 grid gap-3 md:grid-cols-3">
                  <WorkspaceStat
                    label={messages.labels.totalProjects}
                    value={String(totalProjects)}
                  />
                  <WorkspaceStat
                    label={messages.labels.reportReady}
                    value={String(totalReports)}
                  />
                  <WorkspaceStat
                    label={messages.labels.inProgress}
                    value={String(totalInProgress)}
                  />
                </div>
              </div>

              {featuredProject ? (
                <div className="rounded-[2rem] border border-black/8 bg-[#f8fafc] p-5">
                  <div className="flex items-start justify-between gap-4 border-b border-black/6 pb-4">
                    <div>
                      <p className="text-[12px] font-medium tracking-[0.03em] text-[#2563eb]">
                        {messages.featured.eyebrow}
                      </p>
                      <p className="mt-3 text-[22px] font-semibold leading-[1.28] tracking-[-0.018em] text-[#0f172a]">
                        {featuredProject.title}
                      </p>
                    </div>
                    <Badge variant="outline">{messages.labels.readOnly}</Badge>
                  </div>

                  <p className="mt-4 text-[15px] leading-[1.9] text-[#475569]">
                    {messages.featured.description}
                  </p>

                  <div className="mt-5 rounded-[1.5rem] border border-black/6 bg-white px-4 py-4">
                    <p className="text-[12px] font-medium tracking-[0.03em] text-[#64748b]">
                      {resolveSampleStageLabel(featuredProject.stage.value, messages)}
                    </p>
                    <p className="mt-3 text-[16px] leading-[1.75] text-[#0f172a]">
                      {featuredProject.description}
                    </p>
                    <p className="mt-3 text-[13px] text-[#64748b]">
                      {messages.labels.updatedPrefix}{" "}
                      {formatSampleDate(featuredProject.updatedAt, locale)}
                    </p>
                  </div>

                  <div className="mt-5 flex flex-wrap items-center gap-3">
                    <Link
                      className={buttonClassNames({ variant: "secondary" })}
                      href={`${localePrefix}/sample-report`}
                    >
                      {messages.featured.primaryCta}
                    </Link>
                    <Link
                      className={buttonClassNames({ variant: "ghost" })}
                      href={`${localePrefix}/sample/${featuredProject.id}/chat`}
                    >
                      {messages.featured.secondaryCta}
                    </Link>
                  </div>

                  <p className="mt-4 text-[13px] leading-[1.7] text-[#64748b]">
                    {messages.featured.note}
                  </p>
                </div>
              ) : null}
            </div>
          </div>
        </section>

        <section className="mt-12">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-[760px]">
              <p className="text-[13px] font-medium tracking-[0.04em] text-[#2563eb]">
                {messages.grid.eyebrow}
              </p>
              <h2
                className={[
                  "mt-4 font-semibold text-[#0f172a]",
                  isZh
                    ? "text-[clamp(1.95rem,3.8vw,3.15rem)] leading-[1.2] tracking-[-0.018em]"
                    : "text-[clamp(2.3rem,4vw,3.9rem)] leading-[0.98] tracking-[-0.045em]",
                ].join(" ")}
              >
                {messages.grid.title}
              </h2>
              <p
                className={[
                  "mt-4 max-w-[42rem] text-[#475569]",
                  isZh
                    ? "text-[15px] leading-[1.88] md:text-[16px]"
                    : "text-base leading-relaxed",
                ].join(" ")}
              >
                {pageSubtitle}
              </p>
              <p
                className={[
                  "mt-3 max-w-[42rem] text-[#64748b]",
                  isZh
                    ? "text-[14px] leading-[1.85] md:text-[15px]"
                    : "text-sm leading-relaxed md:text-base",
                ].join(" ")}
              >
                {messages.grid.description}
              </p>
            </div>

            <div
              className="inline-flex w-fit items-center gap-2 rounded-full border border-black/8 bg-white/84 p-1 shadow-[0_12px_28px_rgba(15,23,42,0.05)]"
              role="tablist"
              aria-label={messages.tabsAriaLabel}
            >
              <Link
                role="tab"
                aria-selected={!isReportsView}
                className={[
                  "inline-flex min-h-11 items-center rounded-full px-4 py-2 text-sm font-medium transition",
                  focusRingOnLight,
                  !isReportsView
                    ? "bg-[#0f172a] text-white"
                    : "text-[#475569] hover:bg-black/5",
                ].join(" ")}
                href={`${localePrefix}/sample`}
              >
                {messages.tabs.all}
              </Link>
              <Link
                role="tab"
                aria-selected={isReportsView}
                className={[
                  "inline-flex min-h-11 items-center rounded-full px-4 py-2 text-sm font-medium transition",
                  focusRingOnLight,
                  isReportsView
                    ? "bg-[#0f172a] text-white"
                    : "text-[#475569] hover:bg-black/5",
                ].join(" ")}
                href={`${localePrefix}/sample?stage=report`}
              >
                {messages.tabs.reports}
              </Link>
            </div>
          </div>

          {filtered.length === 0 ? (
            <div className="mt-8 rounded-[2rem] border border-black/6 bg-white/78 p-10 text-center shadow-[0_20px_56px_rgba(15,23,42,0.05)]">
              <p className="text-[17px] font-medium text-[#0f172a]">
                {isZh ? "暂无可展示的样例" : "No samples to show yet"}
              </p>
              <p className="mt-3 text-[15px] leading-[1.8] text-[#475569]">
                {isZh
                  ? "样例正在准备中，请稍后再来查看。"
                  : "Samples are being prepared — please check back soon."}
              </p>
            </div>
          ) : null}
          <div className="mt-8 grid gap-5 lg:grid-cols-2 xl:grid-cols-3">
            {filtered.map((project) => {
              const href =
                project.stage.value === "report"
                  ? `${localePrefix}/sample/${project.id}/report`
                  : `${localePrefix}/sample/${project.id}/chat`;

              return (
                <Link
                  key={project.id}
                  className={[
                    "group block h-full rounded-[2rem]",
                    focusRingOnLight,
                  ].join(" ")}
                  href={href}
                >
                  <article className="flex h-full flex-col rounded-[2rem] border border-black/6 bg-white/78 p-6 shadow-[0_20px_56px_rgba(15,23,42,0.05)] transition duration-200 hover:-translate-y-0.5 hover:bg-white hover:shadow-[0_26px_74px_rgba(15,23,42,0.08)] group-focus-visible:-translate-y-0.5 group-focus-visible:bg-white group-focus-visible:shadow-[0_26px_74px_rgba(15,23,42,0.08)]">
                    <div className="flex items-center justify-between gap-4">
                      <Badge variant={project.stage.variant}>
                        {resolveSampleStageLabel(project.stage.value, messages)}
                      </Badge>
                      <span className="text-[13px] text-[#64748b]">
                        {messages.labels.updatedPrefix}{" "}
                        {formatSampleDate(project.updatedAt, locale)}
                      </span>
                    </div>

                    <h3
                      className={[
                        "mt-6 font-semibold text-[#0f172a]",
                        isZh
                          ? "text-[24px] leading-[1.28] tracking-[-0.015em]"
                          : "text-[28px] leading-[1.05] tracking-[-0.04em]",
                      ].join(" ")}
                    >
                      {project.title}
                    </h3>

                    <p
                      className={[
                        "mt-4 flex-1 text-[#475569]",
                        isZh
                          ? "text-[15px] leading-[1.86]"
                          : "text-base leading-relaxed",
                      ].join(" ")}
                    >
                      {project.description}
                    </p>

                    <div className="mt-6 flex items-center justify-between gap-4 border-t border-black/6 pt-4">
                      <span className="text-[13px] text-[#64748b]">
                        {project.stage.value === "report"
                          ? messages.labels.openReport
                          : messages.labels.openChat}
                      </span>
                      <span className="text-[14px] font-medium text-[#0f172a] transition group-hover:translate-x-0.5 group-focus-visible:translate-x-0.5">
                        →
                      </span>
                    </div>
                  </article>
                </Link>
              );
            })}
          </div>
        </section>

        <MarketingSupportLinks
          isZh={isZh}
          variant="panel"
          className="mt-12"
        />
      </div>
    </div>
  );
}

function WorkspaceStat({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-[1.4rem] border border-black/6 bg-white px-4 py-4">
      <p className="text-[12px] font-medium tracking-[0.03em] text-[#64748b]">
        {label}
      </p>
      <p className="mt-3 text-[20px] font-medium leading-[1.35] tracking-[-0.015em] text-[#0f172a]">
        {value}
      </p>
    </div>
  );
}

function resolveSampleStageLabel(
  stage: string,
  messages: (typeof APP_MESSAGES)["en"]["samplePage"]
) {
  if (stage === "problem" || stage === "market" || stage === "tech" || stage === "report") {
    return messages.stageLabels[stage];
  }
  return stage;
}

function formatSampleDate(value: string | null | undefined, locale: string) {
  if (!value) {
    return "—";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(locale === "zh" ? "zh-CN" : "en-US", {
    year: "numeric",
    month: locale === "zh" ? "numeric" : "short",
    day: "numeric",
  }).format(date);
}
