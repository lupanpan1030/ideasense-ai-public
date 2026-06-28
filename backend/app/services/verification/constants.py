"""Constants for verification service."""

_SECTION_KEYS = ("problem", "market", "tech", "dvf", "lean_canvas")
_VERDICT_KEYS = ("supported", "contradicted", "uncertain")
_DEFAULT_TAVILY_URL = "https://api.tavily.com/search"

_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "your",
    "their",
    "they",
    "are",
    "was",
    "were",
    "have",
    "has",
    "had",
    "will",
    "would",
    "should",
    "could",
    "may",
    "might",
    "can",
    "not",
    "but",
    "about",
    "over",
    "under",
    "between",
    "within",
    "using",
    "use",
    "uses",
    "used",
    "than",
    "then",
    "also",
    "more",
    "most",
    "some",
    "such",
    "any",
    "each",
    "other",
    "only",
    "very",
}
_STRONG_CLAIM_KEYWORDS = {
    "market size",
    "tam",
    "sam",
    "som",
    "cagr",
    "growth",
    "roi",
    "revenue",
    "pricing",
    "price",
    "pay",
    "willingness to pay",
    "users",
    "customer count",
    "churn",
    "cac",
    "ltv",
    "conversion",
    "retention",
    "adoption",
    "active users",
    "pipeline",
    "launch",
    "timeline",
    "weeks",
    "months",
    "days",
    "availability",
    "uptime",
    "sla",
    "latency",
    "throughput",
    "performance",
    "security",
    "compliance",
    "gdpr",
    "hipaa",
    "soc 2",
    "iso 27001",
}
_FALLBACK_BLOCKED_DOMAINS = {
    "reddit.com",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "x.com",
    "twitter.com",
    "quora.com",
}
_INTERNAL_STRONG_TOKENS = {
    "the user",
    "user identified",
    "user provided",
    "user confirmed",
    "user plans",
    "user will",
    "we plan",
    "we will",
    "our plan",
    "our team",
    "the team",
    "founder",
    "mvp",
    "roadmap",
    "timeline",
    "launch",
    "go-live",
    "external services",
    "tech stack",
    "architecture",
    "will use",
    "will rely",
    "integration",
    "hosting",
    "vendor",
    "supabase",
    "vercel",
    "stripe",
    "openai",
}
_INTERNAL_CLAIM_TOKENS = {
    "user ",
    "respondent",
    "internal",
    "team plan",
    "product plan",
    "implementation plan",
    "execution plan",
}
_EXTERNAL_HINT_TOKENS = {
    "market",
    "tam",
    "sam",
    "som",
    "cagr",
    "pricing",
    "price",
    "subscription",
    "competitor",
    "competition",
    "industry",
    "segment",
    "geography",
    "region",
    "company size",
    "saas",
    "b2b",
    "ai",
}
_MARKET_SEARCHABLE_QIDS = {
    "S2Q3",   # pricing evidence
    "S2Q4",   # initial segment size + why now
    "S2Q5",   # competitors/positioning
    "S2Q6",   # sales cycle / adoption barriers
    "S2Q9",   # TAM/SAM/SOM (optional)
    "S2Q10",  # demand signals
    "S2Q11",  # substitutes / switching triggers
}
_VERIFICATION_PRIORITY_BY_QID = {
    # Market (high)
    "S2Q5": "high",   # competitors/positioning
    "S2Q9": "high",   # TAM/SAM/SOM
    "S2Q10": "high",  # demand signals
    "S2Q11": "high",  # substitutes/switching
    # Market (medium)
    "S2Q3": "medium",  # pricing snapshot
    "S2Q6": "medium",  # GTM motion
    "S2Q7": "medium",  # unit economics
    # Tech pro (high)
    "S3Q7": "high",   # security/compliance
    "S3Q10": "high",  # data access/quality
    "S3Q13": "high",  # compliance readiness
    # Tech pro (medium)
    "S3Q5": "medium",   # data/AI/scale
    "S3Q8": "medium",   # dependencies
    "S3Q11": "medium",  # AI guardrails
    "S3Q12": "medium",  # reliability/QA
    "S3Q14": "medium",  # high reliability plan
    # Tech lite (high)
    "L3Q3": "high",   # sensitive data check
    "L3Q9": "high",   # data availability
    "L3Q10": "high",  # compliance plan
    # Tech lite (medium)
    "L3Q4": "medium",   # external services
    "L3Q11": "medium",  # AI guardrails
    "L3Q12": "medium",  # high reliability plan
}
_KNOWN_COMPETITORS = [
    "Notion",
    "Airtable",
    "Productboard",
    "Coda",
    "Miro",
    "Trello",
    "Asana",
    "Jira",
    "Confluence",
    "Google Sheets",
    "Google Docs",
    "Microsoft Excel",
    "Excel",
]
_ANCHOR_TERMS = {
    "idea",
    "ideas",
    "validation",
    "startup",
    "entrepreneur",
    "decision",
    "evaluation",
    "innovation",
}
