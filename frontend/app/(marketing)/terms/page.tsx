import type { Metadata } from "next";

import { MarketingDocumentPage } from "@/components/marketing/MarketingDocumentPage";
import { buildLocalePath } from "@/lib/i18n/config";
import { getRequestLocale } from "@/lib/i18n/request-locale";
import { SITE_CONTACT_EMAIL, SITE_OPERATOR_NAME } from "@/lib/site";

export async function generateMetadata(): Promise<Metadata> {
  const locale = await getRequestLocale();
  const isZh = locale === "zh";
  const pageTitle = isZh ? "使用条款" : "Terms of Use";
  const fullTitle = `IdeaSense AI | ${pageTitle}`;
  const description = isZh
    ? "查看 IdeaSense AI 公开站点、样例内容、注册流程与结构化评审服务当前适用的使用条款。"
    : "Review the current terms that apply to the IdeaSense AI public site, sample content, registration flows, and structured review service.";

  return {
    title: {
      absolute: fullTitle,
    },
    description,
    alternates: {
      canonical: buildLocalePath(locale, "/terms"),
      languages: {
        en: buildLocalePath("en", "/terms"),
        zh: buildLocalePath("zh", "/terms"),
      },
    },
    openGraph: {
      title: fullTitle,
      description,
      url: buildLocalePath(locale, "/terms"),
    },
  };
}

export default async function TermsPage() {
  const locale = await getRequestLocale();
  const isZh = locale === "zh";
  const legalEmail = SITE_CONTACT_EMAIL;

  const content = isZh
    ? {
        eyebrow: "使用条款",
        title: "使用条款",
        summary:
          `这份页面说明你在访问和使用 IdeaSense 网站、样例内容、账号能力与结构化评审服务时应遵守的基本规则。IdeaSense AI 当前由 ${SITE_OPERATOR_NAME} 独立设计与运营，本页说明的是这个独立产品当前适用的使用边界。`,
        lastUpdatedLabel: "最后更新",
        lastUpdatedValue: "2026年4月12日",
        principles: [
          "样例只用于演示",
          "输出帮助判断，不构成保证",
          "账号与输入内容由使用者负责",
        ],
        primaryCtaLabel: "开始第一次验证",
        secondaryCtaLabel: "查看示例报告",
        sections: [
          {
            title: "适用范围与接受方式",
            paragraphs: [
              `IdeaSense AI 当前是由 ${SITE_OPERATOR_NAME} 独立设计与运营的软件产品。本文中的 “IdeaSense”“我们” 或 “本服务” 均指该独立产品及其运营者。`,
              "这些条款适用于 IdeaSense 的公开站点、Sample Workspace、Sample Report、注册登录流程、组织邀请能力，以及与结构化评审、评分和报告相关的产品体验。",
              "当你访问站点、创建账号、使用样例内容或继续使用产品时，通常表示你接受这些条款。如果你不同意，请不要继续使用相关服务。若你对条款有问题，当前可通过 " + legalEmail + " 联系我们。",
            ],
          },
          {
            title: "服务是什么，不是什么",
            paragraphs: [
              "IdeaSense 提供的是一套用于早期想法验证、结构化评审和报告生成的产品体验。它可以帮助你更系统地整理问题、假设、证据、风险与下一步动作。",
              "它不是投资建议、法律意见、税务意见、雇佣意见或任何形式的结果保证。无论评分、建议或报告如何呈现，它们都不能替代你自己的业务判断、专业顾问意见或合规责任。",
            ],
          },
          {
            title: "样例内容与公开页面",
            paragraphs: [
              "站点中的样例页面、样例项目、样例工作区和样例报告主要用于展示产品能力、结构和体验，不代表真实商业结论，也不应被理解为对任何项目、行业或结果的正式背书。",
              "你可以浏览和评估这些内容，但不应把样例内容包装成你的正式成果、正式顾问意见，或误导第三方认为其代表 IdeaSense 对某个具体项目的承诺。",
            ],
          },
          {
            title: "账号、访问与安全",
            paragraphs: [
              "你需要对账号凭据、登录状态以及通过账号发生的操作负责。若你发现未授权访问、账号异常或邀请误用，应尽快修改相关凭据并联系我们。",
              "我们可能在部分入口启用邮箱验证、速率限制、验证码、邀请校验或其他安全措施。你不得绕过、破坏、探测或规避这些访问控制与风控机制。",
            ],
          },
          {
            title: "你的输入内容与使用责任",
            paragraphs: [
              "你应只提交你有权使用、分享和处理的内容。这包括但不限于文本输入、项目资料、组织信息、邀请对象信息、上传内容、以及任何进入评审或报告的材料。",
              "你不得利用本服务提交违法内容、侵权内容、机密泄露材料、第三方敏感个人信息、恶意脚本、滥用请求，或任何会损害平台、用户、组织协作或第三方权利的内容。",
            ],
          },
          {
            title: "可接受使用与禁止行为",
            paragraphs: [
              "你同意不会利用本服务从事违法、侵权、骚扰、攻击、抓取、恶意自动化、模型滥用、反向工程、绕过访问限制、批量探测漏洞，或其他会破坏平台稳定性与公平使用的行为。",
              "除非我们明确允许，你也不应复制、镜像、再分发、出租、转售或冒充官方版本发布站点内容、品牌元素、样例材料、报告结构或产品界面。",
            ],
          },
          {
            title: "知识产权与反馈",
            paragraphs: [
              "站点设计、品牌元素、样例内容、界面结构、报告展示方式以及相关材料，除非另有说明，均归 IdeaSense 或相关权利方所有。",
              "如果你主动向我们提交反馈、建议或改进意见，我们可以在不向你额外支付报酬的情况下，将这些反馈用于改进产品、页面、方法或运营方式。",
            ],
          },
          {
            title: "输出、限制与免责声明",
            paragraphs: [
              "AI 生成的问题、总结、评分、风险提示和报告内容，可能存在不完整、不准确、过时或不适用于特定场景的情况。你仍需自行判断是否继续、暂停、修改或采取其他行动。",
              "我们不承诺服务持续不中断、绝对无误、完全无漏洞，也不保证任何商业结果、融资结果、技术落地结果、组织协作结果或合规结果一定实现。",
            ],
          },
          {
            title: "暂停、终止与变更",
            paragraphs: [
              "如果我们认为某个账号、组织或使用行为违反这些条款、危及平台安全、损害其他用户，或给基础设施带来异常风险，我们可以限制、暂停或终止相关访问。",
              "我们也可能更新产品、功能、定价、样例内容、公开页面和这些条款。页面顶部的“最后更新”日期会反映最新版本，继续使用服务通常意味着接受更新后的版本。",
            ],
          },
        ],
      }
    : {
        eyebrow: "Terms",
        title: "Terms of Use",
        summary:
          `This page sets the basic rules for accessing and using the IdeaSense website, sample materials, account features, and structured review experience. IdeaSense AI is an independently operated product built by ${SITE_OPERATOR_NAME}, and these terms describe the practical boundaries that apply today.`,
        lastUpdatedLabel: "Last updated",
        lastUpdatedValue: "April 12, 2026",
        principles: [
          "Samples are for demonstration",
          "Outputs support judgment but do not guarantee outcomes",
          "Users remain responsible for accounts and submitted content",
        ],
        primaryCtaLabel: "Start Free",
        secondaryCtaLabel: "View Sample Report",
        sections: [
          {
            title: "Scope and acceptance",
            paragraphs: [
              `IdeaSense AI is currently an independently operated software product built and run by ${SITE_OPERATOR_NAME}. In these terms, “IdeaSense AI”, “we”, “us”, and “the service” refer to that product and its operator.`,
              "These terms apply to the IdeaSense public website, Sample Workspace, Sample Report, registration and login flows, organization invitations, and the product experience related to structured review, scoring, and report generation.",
              "By accessing the site, creating an account, using sample content, or continuing to use the service, you generally agree to these terms. If you do not agree, do not continue using the relevant services. For questions, you can currently contact us at " + legalEmail + ".",
            ],
          },
          {
            title: "What the service is, and is not",
            paragraphs: [
              "IdeaSense provides a product experience for early-stage idea validation, structured review, and report generation. It is intended to help users organize problems, assumptions, evidence, risks, and next actions more rigorously.",
              "It is not legal advice, investment advice, tax advice, employment advice, or a guarantee of results. Scores, recommendations, and reports do not replace your own judgment, professional advice, or compliance responsibilities.",
            ],
          },
          {
            title: "Samples and public content",
            paragraphs: [
              "Sample pages, sample projects, sample workspaces, and sample reports are provided mainly to demonstrate product capabilities, structure, and experience. They do not represent formal conclusions about a real business, project, or market.",
              "You may review these materials, but you should not present them as your own formal advisory output or mislead others into thinking they are a binding commitment or endorsement from IdeaSense.",
            ],
          },
          {
            title: "Accounts, access, and security",
            paragraphs: [
              "You are responsible for account credentials, access state, and actions taken through your account. If you become aware of unauthorized access, suspicious account activity, or invite misuse, you should promptly secure the account and contact us.",
              "We may enforce email verification, rate limits, captcha, invitation checks, and similar security controls. You must not bypass, disrupt, test around, or attempt to defeat those access and abuse-prevention mechanisms.",
            ],
          },
          {
            title: "Your submitted content and responsibilities",
            paragraphs: [
              "You should submit only content that you are authorized to use, share, and process. That includes text inputs, project materials, organization information, invitee information, uploaded content, and anything that enters the review or reporting flow.",
              "You must not use the service to submit unlawful material, infringing material, leaked confidential material, third-party sensitive personal information, malicious code, abusive requests, or anything that could harm the platform, other users, collaborative organizations, or third-party rights.",
            ],
          },
          {
            title: "Acceptable use and prohibited conduct",
            paragraphs: [
              "You agree not to use the service for unlawful, infringing, harassing, hostile, scraping, abusive automation, model abuse, reverse engineering, access-control bypass, vulnerability probing, or other conduct that harms platform stability or fair use.",
              "Unless we clearly permit it, you should not copy, mirror, redistribute, rent, resell, or present the site content, branding, sample materials, report structures, or product interface as an official release or licensed derivative.",
            ],
          },
          {
            title: "Intellectual property and feedback",
            paragraphs: [
              "Site design, branding, sample materials, interface structures, report presentation patterns, and related materials remain the property of IdeaSense or the relevant rights holders unless stated otherwise.",
              "If you voluntarily send us feedback, suggestions, or improvement ideas, we may use them to improve the product, pages, methodology, or operations without separate compensation to you.",
            ],
          },
          {
            title: "Outputs, limitations, and disclaimers",
            paragraphs: [
              "AI-generated questions, summaries, scores, risk flags, and reports may be incomplete, inaccurate, outdated, or unsuitable for a particular context. You remain responsible for deciding whether to proceed, pause, change direction, or seek additional review.",
              "We do not promise uninterrupted service, error-free output, perfect accuracy, or guaranteed business, fundraising, technical delivery, collaboration, or compliance outcomes.",
            ],
          },
          {
            title: "Suspension, termination, and changes",
            paragraphs: [
              "If we believe an account, organization, or usage pattern violates these terms, threatens platform security, harms other users, or creates unusual infrastructure risk, we may limit, suspend, or terminate the relevant access.",
              "We may also update the product, features, pricing, sample content, public pages, and these terms over time. The date at the top of the page reflects the latest revision, and continued use generally means you accept the updated version.",
            ],
          },
        ],
      };

  return <MarketingDocumentPage {...content} isZh={isZh} />;
}
