import type { Metadata } from "next";

import { MarketingDocumentPage } from "@/components/marketing/MarketingDocumentPage";
import { buildLocalePath } from "@/lib/i18n/config";
import { getRequestLocale } from "@/lib/i18n/request-locale";
import { SITE_OPERATOR_NAME, SITE_PRIVACY_EMAIL } from "@/lib/site";

export async function generateMetadata(): Promise<Metadata> {
  const locale = await getRequestLocale();
  const isZh = locale === "zh";
  const pageTitle = isZh ? "隐私说明" : "Privacy";
  const fullTitle = `IdeaSense AI | ${pageTitle}`;
  const description = isZh
    ? "了解 IdeaSense AI 如何处理账号、项目、评审与报告相关信息，以及独立运营产品当前适用的数据边界。"
    : "Understand how IdeaSense AI handles account, project, review, and report data, and the current data boundaries for this independently operated product.";

  return {
    title: {
      absolute: fullTitle,
    },
    description,
    alternates: {
      canonical: buildLocalePath(locale, "/privacy"),
      languages: {
        en: buildLocalePath("en", "/privacy"),
        zh: buildLocalePath("zh", "/privacy"),
      },
    },
    openGraph: {
      title: fullTitle,
      description,
      url: buildLocalePath(locale, "/privacy"),
    },
  };
}

export default async function PrivacyPage() {
  const locale = await getRequestLocale();
  const isZh = locale === "zh";
  const privacyEmail = SITE_PRIVACY_EMAIL;

  const content = isZh
    ? {
        eyebrow: "隐私说明",
        title: "你的信息，应该只服务于你的判断。",
        summary:
          `这份页面说明 IdeaSense 在账号、会话、结构化评审、报告输出与样例体验中如何处理信息。IdeaSense AI 当前由 ${SITE_OPERATOR_NAME} 独立设计与运营，本页说明的是这个独立产品当前适用的数据边界。`,
        lastUpdatedLabel: "最后更新",
        lastUpdatedValue: "2026年4月12日",
        principles: [
          "最小必要收集",
          "不出售项目内容",
          "删除、导出与更正应保持可能",
        ],
        primaryCtaLabel: "开始第一次验证",
        secondaryCtaLabel: "查看示例报告",
        sections: [
          {
            title: "适用范围与联系方式",
            paragraphs: [
              `IdeaSense AI 当前是由 ${SITE_OPERATOR_NAME} 独立设计与运营的软件产品。本文中的 “IdeaSense”“我们” 或 “本服务” 均指该独立产品及其运营者。`,
              "本说明适用于 IdeaSense 的公开站点、Sample Workspace、Sample Report、账号注册与登录、邮箱验证、密码重置、组织邀请、分阶段评审流程，以及与这些体验直接相关的后台处理。",
              `如果你希望咨询隐私问题、请求导出或删除数据，当前可使用 ${privacyEmail} 联系我们。若后续使用其他正式隐私联系渠道，我们会在本页更新。`,
            ],
          },
          {
            title: "我们处理的信息类别",
            paragraphs: [
              "这通常包括你主动提交的信息，例如姓名或显示名、邮箱地址、登录与认证相关记录、邮箱验证与密码重置记录、组织邀请信息、项目输入、对话内容、阶段总结、评分结果和报告内容。",
              "当你访问站点或使用产品时，也会产生技术与安全相关数据，例如 IP 地址、设备/浏览器信息、请求日志、时间戳、错误日志、风控记录、速率限制记录以及必要的审计数据。",
            ],
          },
          {
            title: "这些信息为何存在",
            paragraphs: [
              "我们处理这些信息，主要是为了提供服务本身，包括账号创建与登录、会话管理、邮箱验证、密码重置、组织协作、项目保存、分阶段评审、评分与报告生成，以及样例体验。",
              "在必要范围内，我们也会将部分数据用于平台安全、故障排查、滥用检测、速率限制、产品改进与合规处理。对于适用 UK/EU 规则的场景，我们通常依赖履行合同、合法利益、法定义务，以及在需要时取得的同意作为处理依据。",
            ],
          },
          {
            title: "浏览器存储、Cookie 与验证码",
            paragraphs: [
              "当前产品会使用浏览器本地存储、会话存储和第一方 Cookie 来维持部分功能。例如，登录状态可能会保存在本地存储或会话存储中，语言偏好会通过 Cookie 记住，邀请令牌也可能在浏览器本地暂存，直到被接受或清除。",
              "在注册、登录、验证邮箱或重置密码等高风险入口，系统也可能接入 hCaptcha 或 reCAPTCHA。启用后，相关提供方会按其机制处理浏览器和设备信息，以帮助我们识别自动化滥用。",
            ],
          },
          {
            title: "服务提供方与模型提供方",
            paragraphs: [
              "为了提供当前产品，我们可能会使用若干基础设施与处理方，例如数据库与托管服务、邮件发送服务、验证码服务、以及一个或多个 AI/模型提供方。根据当前仓库配置，这类供应商可能包括 Resend、OpenAI、Google Gemini、AWS Bedrock、DeepSeek，以及在研究/验证功能启用时使用的搜索或研究服务。",
              "并非所有供应商都会在每个部署环境中同时启用。我们的目标是让这些供应商只接触提供其服务所必需的数据，而不是默认获得完整项目内容。",
            ],
          },
          {
            title: "共享边界与跨境处理",
            paragraphs: [
              "我们不会出售你的项目内容。只有在提供服务、支持组织协作、满足法律义务、保护平台安全，或使用必要处理方时，相关数据才可能被共享。",
              "由于部分服务提供方可能位于你所在司法辖区之外，你的数据也可能在其他国家或地区被处理。出现这类情形时，我们会尽量使用最小必要共享、访问控制和合同安排来降低风险。",
            ],
          },
          {
            title: "保留期限",
            paragraphs: [
              "我们不会对所有数据承诺完全相同的保留周期。一般来说，账号资料、项目内容与报告会在账号持续有效、项目仍在使用，或为处理支持、争议、备份与法律义务仍有必要的期间内保留。",
              "验证码记录、速率限制记录、安全审计数据、邮箱验证/重置/邀请令牌以及相关日志，通常会按更短的运营与安全窗口保存，并在不再需要后过期、删除或去标识化。",
            ],
          },
          {
            title: "你的权利与选择",
            paragraphs: [
              "你可以请求访问、更正、导出或删除部分数据；在适用法律允许的情况下，你也可能享有反对某些处理、限制处理、撤回同意或向监管机构投诉的权利。",
              "在产品层面，请尽量不要提交你无权处理的第三方敏感信息。如果你不希望某些内容被保留，也请避免把它们输入到样例或测试环境中。",
            ],
          },
          {
            title: "未成年人",
            paragraphs: [
              "IdeaSense 并不是为儿童而设计的产品。若适用法律对未成年人数据有更严格要求，你应在具备适当授权的前提下使用服务。",
              "如果我们得知某些数据是在不符合适用规则的情况下提交的，我们会尽量删除或限制继续处理。",
            ],
          },
          {
            title: "更新与变更",
            paragraphs: [
              "随着产品、基础设施和法律要求变化，我们可能更新本说明。页面顶部的“最后更新”日期会随之变化。",
              "如果变更会实质影响你对数据使用方式的理解，我们会尽量通过站内提示、账号通知或其他合理方式提醒你。",
            ],
          },
        ],
      }
    : {
        eyebrow: "Privacy",
        title: "Your information should serve your judgment, not someone else's business model.",
        summary:
          `This page explains how IdeaSense handles information across accounts, sessions, structured review flows, report generation, and sample experiences. IdeaSense AI is an independently operated product built by ${SITE_OPERATOR_NAME}, and this notice describes the current data boundaries for that service.`,
        lastUpdatedLabel: "Last updated",
        lastUpdatedValue: "April 12, 2026",
        principles: [
          "Minimal necessary collection",
          "No sale of project content",
          "Deletion, export, and correction should remain possible",
        ],
        primaryCtaLabel: "Start Free",
        secondaryCtaLabel: "View Sample Report",
        sections: [
          {
            title: "Scope and contact",
            paragraphs: [
              `IdeaSense AI is currently an independently operated software product built and run by ${SITE_OPERATOR_NAME}. In this notice, “IdeaSense AI”, “we”, “us”, and “the service” refer to that product and its operator.`,
              "This notice applies to the IdeaSense public site, Sample Workspace, Sample Report, account registration and login, email verification, password reset, organization invitations, staged review flows, and the backend processing directly required to support those experiences.",
              `For privacy questions or requests, you can currently contact us at ${privacyEmail}. If we later publish a different dedicated privacy channel, we will update this page.`,
            ],
          },
          {
            title: "Categories of information we handle",
            paragraphs: [
              "This generally includes information you actively submit, such as account details, email address, authentication-related records, email verification and password reset records, organization invitation details, project inputs, chat/review content, stage summaries, scores, and report content.",
              "We also generate technical and security-related data when you use the service, such as IP address, browser or device information, request logs, timestamps, error logs, rate-limit records, abuse-prevention signals, and necessary audit records.",
            ],
          },
          {
            title: "Why we use this information",
            paragraphs: [
              "We use this information to provide the service itself, including account creation and login, session management, email verification, password reset, organization collaboration, project persistence, staged review, scoring, report generation, and sample experiences.",
              "Where necessary, we also use limited data for platform security, debugging, abuse prevention, rate limiting, product improvement, and legal compliance. For UK/EU-style contexts, our legal bases will generally include contract performance, legitimate interests, legal obligations, and consent where consent is the appropriate basis.",
            ],
          },
          {
            title: "Browser storage, cookies, and captcha",
            paragraphs: [
              "The current product uses browser local storage, session storage, and first-party cookies for certain functions. For example, sign-in state may be retained in local or session storage, language preference may be remembered through a cookie, and invitation tokens may be stored locally until they are accepted or cleared.",
              "On higher-risk entry points such as registration, login, email verification, or password reset, we may also use hCaptcha or reCAPTCHA. When enabled, those providers may process browser and device information to help identify automated abuse.",
            ],
          },
          {
            title: "Service providers and model providers",
            paragraphs: [
              "To operate the current product, we may use infrastructure and processors such as database or hosting providers, email delivery providers, captcha providers, and one or more AI/model providers. Based on the current product configuration, these categories may include services such as Resend, OpenAI, Google Gemini, AWS Bedrock, DeepSeek, and, where research or verification features are enabled, search or research providers.",
              "Not every provider is active in every deployment. Our goal is to expose processors only to the information reasonably necessary for the service they perform, rather than sharing full project content by default.",
            ],
          },
          {
            title: "Sharing boundaries and international processing",
            paragraphs: [
              "We do not sell your project content. Sharing should happen only where necessary to provide the service, support organization collaboration, comply with law, protect platform security, or use necessary processors.",
              "Because some providers may operate in jurisdictions other than your own, information may also be processed outside your country or region. Where that happens, we try to rely on data minimization, access controls, and contractual safeguards to reduce risk.",
            ],
          },
          {
            title: "Retention",
            paragraphs: [
              "We do not promise a single retention period for every category of data. In general, account data, project content, and reports may be retained while the account remains active or while retention is reasonably necessary for support, disputes, backups, legal obligations, or security review.",
              "Captcha records, rate-limit records, security audit data, email verification/reset/invitation tokens, and related logs are typically kept for shorter operational and security windows, then allowed to expire, be deleted, or be de-identified when no longer needed.",
            ],
          },
          {
            title: "Your rights and choices",
            paragraphs: [
              "You may request access to, correction of, export of, or deletion of portions of your data. Depending on the law that applies to you, you may also have rights to object to certain processing, restrict processing, withdraw consent, or complain to a regulator.",
              "At a practical level, you should avoid submitting sensitive personal information or third-party information that you do not have authority to use, especially in sample or testing flows.",
            ],
          },
          {
            title: "Children",
            paragraphs: [
              "IdeaSense is not designed as a product for children. If laws in your jurisdiction impose stricter rules for minors, you should use the service only with appropriate authorization.",
              "If we learn that information was submitted in a way that does not comply with applicable rules, we will try to delete it or limit further processing.",
            ],
          },
          {
            title: "Changes to this notice",
            paragraphs: [
              "We may update this notice as the product, infrastructure, or legal requirements evolve. The date at the top of the page reflects the latest revision.",
              "If a change would materially affect how a reasonable user understands our handling of information, we will try to provide additional notice through the site, the product, or another reasonable channel.",
            ],
          },
        ],
      };

  return <MarketingDocumentPage {...content} isZh={isZh} />;
}
