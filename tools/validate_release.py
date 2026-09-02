# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 D-Robotics. All rights reserved.
"""Validate and emit the trusted fields from a GitHub Release API response."""

import json
import re
import sys

STABLE_TAG = re.compile(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z")


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def required_string(release: dict[str, object], field: str) -> str:
    value = release.get(field)
    if not isinstance(value, str) or not value or "\n" in value or "\r" in value:
        fail(f"Release {field} must be a non-empty single-line string")
    return value


def main() -> None:
    if len(sys.argv) != 3:
        fail("usage: validate_release.py EXPECTED_TAG OWNER/REPOSITORY")
    expected_tag, repository = sys.argv[1:]
    if not STABLE_TAG.fullmatch(expected_tag):
        fail("requested tag is not a stable semantic version")
    if not re.fullmatch(r"[^/\s]+/[^/\s]+", repository):
        fail("repository must be OWNER/REPOSITORY")
    try:
        release = json.load(sys.stdin)
    except json.JSONDecodeError:
        fail("Release API response is not JSON")
    if not isinstance(release, dict):
        fail("Release API response must be an object")
    tag = required_string(release, "tag_name")
    release_url = required_string(release, "html_url")
    published_at = required_string(release, "published_at")
    if tag != expected_tag or not STABLE_TAG.fullmatch(tag):
        fail("Release tag does not match the requested stable tag")
    if release_url != f"https://github.com/{repository}/releases/tag/{tag}":
        fail("Release URL is not canonical for the requested repository and tag")
    if release.get("draft") is not False or release.get("prerelease") is not False:
        fail("Release must be published, non-draft, and non-prerelease")
    print(f"tag={tag}")
    print(f"release_url={release_url}")
    print(f"published_at={published_at}")


if __name__ == "__main__":
    main()
