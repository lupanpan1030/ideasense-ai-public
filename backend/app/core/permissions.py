from __future__ import annotations

from typing import Literal, TypedDict

OrgRole = Literal["owner", "admin", "mentor", "student"]


class OrgCapabilities(TypedDict):
    is_org_admin: bool
    can_manage_org_settings: bool
    can_manage_prompts: bool
    can_manage_question_bank: bool
    can_manage_members: bool
    can_manage_invites: bool
    can_manage_cohorts: bool
    can_manage_assignments: bool
    can_manage_projects: bool
    can_manage_reports: bool
    can_transfer_ownership: bool


ORG_CAPABILITY_KEYS = tuple(OrgCapabilities.__annotations__.keys())
OrgCapabilityKey = Literal[
    "is_org_admin",
    "can_manage_org_settings",
    "can_manage_prompts",
    "can_manage_question_bank",
    "can_manage_members",
    "can_manage_invites",
    "can_manage_cohorts",
    "can_manage_assignments",
    "can_manage_projects",
    "can_manage_reports",
    "can_transfer_ownership",
]

ORG_ROLE_CAPABILITIES: dict[OrgRole, OrgCapabilities] = {
    "owner": {
        "is_org_admin": True,
        "can_manage_org_settings": True,
        "can_manage_prompts": True,
        "can_manage_question_bank": True,
        "can_manage_members": True,
        "can_manage_invites": True,
        "can_manage_cohorts": True,
        "can_manage_assignments": True,
        "can_manage_projects": True,
        "can_manage_reports": True,
        "can_transfer_ownership": True,
    },
    "admin": {
        "is_org_admin": True,
        "can_manage_org_settings": True,
        "can_manage_prompts": True,
        "can_manage_question_bank": True,
        "can_manage_members": True,
        "can_manage_invites": True,
        "can_manage_cohorts": True,
        "can_manage_assignments": True,
        "can_manage_projects": True,
        "can_manage_reports": True,
        "can_transfer_ownership": False,
    },
    "mentor": {
        "is_org_admin": False,
        "can_manage_org_settings": False,
        "can_manage_prompts": False,
        "can_manage_question_bank": False,
        "can_manage_members": False,
        "can_manage_invites": False,
        "can_manage_cohorts": False,
        "can_manage_assignments": False,
        "can_manage_projects": False,
        "can_manage_reports": False,
        "can_transfer_ownership": False,
    },
    "student": {
        "is_org_admin": False,
        "can_manage_org_settings": False,
        "can_manage_prompts": False,
        "can_manage_question_bank": False,
        "can_manage_members": False,
        "can_manage_invites": False,
        "can_manage_cohorts": False,
        "can_manage_assignments": False,
        "can_manage_projects": False,
        "can_manage_reports": False,
        "can_transfer_ownership": False,
    },
}


def resolve_org_capabilities(
    org_role: str | None,
    org_settings: dict | None = None,
) -> OrgCapabilities:
    base = ORG_ROLE_CAPABILITIES.get(org_role, ORG_ROLE_CAPABILITIES["student"])
    capabilities = dict(base)
    if (
        org_role == "admin"
        and org_settings
        and org_settings.get("allow_admin_transfer_ownership") is True
    ):
        capabilities["can_transfer_ownership"] = True
    return capabilities  # type: ignore[return-value]
