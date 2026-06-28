#!/usr/bin/env bash

set -euo pipefail

BASE_URL="${1:-}"

if [[ -z "${BASE_URL}" ]]; then
  echo "Usage: scripts/verify_multilingual_release.sh <base-url>" >&2
  exit 1
fi

BASE_URL="${BASE_URL%/}"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

pass() {
  echo "PASS: $*"
}

expect_redirect() {
  local path="$1"
  local expected="$2"
  local headers
  headers="$(curl -sSI "${BASE_URL}${path}")"
  local location
  location="$(printf '%s\n' "${headers}" | awk 'BEGIN{IGNORECASE=1} /^location:/ {sub(/\r$/, "", $2); print $2; exit}')"
  [[ -n "${location}" ]] || fail "${path} did not return a redirect"
  [[ "${location}" == "${expected}" || "${location}" == "${BASE_URL}${expected}" ]] || fail "${path} redirected to ${location}, expected ${expected}"
  pass "${path} redirects to ${expected}"
}

expect_status_without_redirect() {
  local path="$1"
  local expected_status="$2"
  local headers
  headers="$(curl -sSI "${BASE_URL}${path}")"
  local status
  status="$(printf '%s\n' "${headers}" | awk 'NR==1 {print $2}')"
  local location
  location="$(printf '%s\n' "${headers}" | awk 'BEGIN{IGNORECASE=1} /^location:/ {sub(/\r$/, "", $2); print $2; exit}')"
  [[ "${status}" == "${expected_status}" ]] || fail "${path} returned ${status}, expected ${expected_status}"
  [[ -z "${location}" ]] || fail "${path} unexpectedly redirected to ${location}"
  pass "${path} returns ${expected_status} without redirect"
}

expect_html_locale() {
  local path="$1"
  local locale="$2"
  local body
  body="$(curl -fsSL "${BASE_URL}${path}")"
  grep -q "lang=\"${locale}\"" <<<"${body}" || fail "${path} missing html lang=${locale}"
  grep -q "data-locale=\"${locale}\"" <<<"${body}" || fail "${path} missing data-locale=${locale}"
  pass "${path} renders html locale ${locale}"
}

expect_redirect "/" "/en"
expect_redirect "/projects" "/en/projects"
expect_redirect "/zh/projects" "/zh/login"

expect_status_without_redirect "/en/login" "200"
expect_status_without_redirect "/zh/login" "200"
expect_status_without_redirect "/en/methodology" "200"
expect_status_without_redirect "/zh/methodology" "200"

expect_html_locale "/en/login" "en"
expect_html_locale "/zh/login" "zh"
expect_html_locale "/en/methodology" "en"
expect_html_locale "/zh/methodology" "zh"

pass "multilingual release verification completed"
