import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest
import yaml

ROOT = Path(__file__).resolve().parent.parent
CHECKOUT_ACTION = "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683"
CREATE_APP_TOKEN_ACTION = (
    "actions/create-github-app-token@"
    "fee1f7d63c2ff003460e3d139729b119787bc349"
)
MISSING = object()
MODULE_PATH = Path(__file__).with_name("sandbox.py")
SPEC = importlib.util.spec_from_file_location("sandbox", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
sandbox = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sandbox)


class DeviceReleaseContractTests(unittest.TestCase):
    def test_release_api_validator_accepts_only_published_stable_release(self):
        validator = ROOT / "tools" / "validate_release.py"
        self.assertTrue(validator.is_file(), validator)

        canonical_payload = {
            "tag_name": "v1.0.0",
            "html_url": "https://github.com/D-Robotics/rdk-device-skills/releases/tag/v1.0.0",
            "published_at": "2026-08-31T12:00:00Z",
            "draft": False,
            "prerelease": False,
        }
        invalid_mutations = (
            ("wrong tag_name: API v1.0.1 versus requested v1.0.0", "tag_name", "v1.0.1", "Release tag does not match the requested stable tag\n"),
            ("missing tag_name", "tag_name", MISSING, "Release tag_name must be a non-empty single-line string\n"),
            ("malformed tag_name", "tag_name", ["v1.0.0"], "Release tag_name must be a non-empty single-line string\n"),
            ("wrong html_url: noncanonical URL", "html_url", "https://example.test/releases/tag/v1.0.0", "Release URL is not canonical for the requested repository and tag\n"),
            ("missing html_url", "html_url", MISSING, "Release html_url must be a non-empty single-line string\n"),
            ("malformed html_url", "html_url", 1, "Release html_url must be a non-empty single-line string\n"),
            ("wrong published_at: empty time", "published_at", "", "Release published_at must be a non-empty single-line string\n"),
            ("missing published_at time", "published_at", MISSING, "Release published_at must be a non-empty single-line string\n"),
            ("malformed published_at", "published_at", {}, "Release published_at must be a non-empty single-line string\n"),
            ("wrong draft: true", "draft", True, "Release must be published, non-draft, and non-prerelease\n"),
            ("missing draft", "draft", MISSING, "Release must be published, non-draft, and non-prerelease\n"),
            ("malformed draft", "draft", "false", "Release must be published, non-draft, and non-prerelease\n"),
            ("wrong prerelease: true", "prerelease", True, "Release must be published, non-draft, and non-prerelease\n"),
            ("missing prerelease", "prerelease", MISSING, "Release must be published, non-draft, and non-prerelease\n"),
            ("malformed prerelease", "prerelease", 0, "Release must be published, non-draft, and non-prerelease\n"),
        )

        result = subprocess.run(
            [sys.executable, str(validator), "v1.0.0", "D-Robotics/rdk-device-skills"],
            input=json.dumps(canonical_payload), text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "tag=v1.0.0\nrelease_url=https://github.com/D-Robotics/rdk-device-skills/releases/tag/v1.0.0\npublished_at=2026-08-31T12:00:00Z\n",
        )

        for name, field, value, expected_error in invalid_mutations:
            with self.subTest(name=name):
                payload = canonical_payload.copy()
                if value is MISSING:
                    del payload[field]
                else:
                    payload[field] = value
                result = subprocess.run(
                    [sys.executable, str(validator), "v1.0.0", "D-Robotics/rdk-device-skills"],
                    input=json.dumps(payload), text=True, capture_output=True, check=False,
                )
                self.assertEqual(result.returncode, 1, result)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, expected_error)

    def test_every_canonical_skill_has_v1_frontmatter(self):
        paths = sorted((ROOT / "skills").rglob("SKILL.md"))
        self.assertTrue(paths, "expected canonical SKILL.md files under skills/")
        for path in paths:
            text = path.read_text(encoding="utf-8")
            self.assertRegex(text, r"(?m)^version:\s*1\.0\.0\s*$", str(path))

    def test_release_routes_have_no_retired_or_workspace_gaps(self):
        skills = sandbox.load_skills()
        self.assertEqual(sandbox.retired_route_problems(skills), [])
        self.assertEqual(sandbox.workspace_router_route_problems(skills), [])

    def test_release_or_recovery_dispatch_notifies_hub_with_api_verified_payload(self):
        workflow_path = ROOT / ".github" / "workflows" / "notify-hub-release.yml"
        workflow = workflow_path.read_text(encoding="utf-8")
        document = yaml.load(workflow, Loader=yaml.BaseLoader)

        self.assertEqual(
            document["on"],
            {
                "release": {"types": ["published"]},
                "workflow_dispatch": {
                    "inputs": {
                        "tag": {
                            "description": "Stable Release tag to recover",
                            "required": "true",
                            "type": "string",
                        }
                    }
                },
            },
        )
        self.assertEqual(document["permissions"], {"contents": "read"})
        self.assertNotIn("if", document["jobs"]["notify-hub"])
        steps = document["jobs"]["notify-hub"]["steps"]
        self.assertEqual(
            [step["uses"] for step in steps if "uses" in step],
            [CHECKOUT_ACTION, CREATE_APP_TOKEN_ACTION],
        )
        checkout_step = steps[0]
        self.assertEqual(checkout_step["uses"], CHECKOUT_ACTION)
        self.assertEqual(
            checkout_step["with"],
            {
                "ref": "${{ github.event.repository.default_branch }}",
                "persist-credentials": "false",
            },
        )

        release_step = next(
            step
            for step in steps
            if step.get("id") == "release"
        )
        self.assertEqual(
            release_step["env"],
            {"tag": "${{ inputs.tag || github.event.release.tag_name }}"},
        )
        resolve_step = next(
            step
            for step in steps
            if step.get("name") == "Resolve the verified release tag to its commit SHA"
        )
        self.assertEqual(resolve_step.get("id"), "resolve")
        self.assertEqual(resolve_step["env"], {"tag": "${{ steps.release.outputs.tag }}"})
        self.assertIn("^[0-9a-fA-F]{40}$", resolve_step["run"])

        token_step = next(
            step
            for step in steps
            if step.get("uses") == CREATE_APP_TOKEN_ACTION
        )
        self.assertEqual(
            token_step["with"],
            {
                "app-id": "${{ vars.RDK_RELEASE_DISPATCHER_APP_ID }}",
                "private-key": "${{ secrets.RDK_RELEASE_DISPATCHER_PRIVATE_KEY }}",
                "owner": "D-Robotics",
                "repositories": "rdk-skills",
                "permission-actions": "write",
            },
        )

        dispatch_step = steps[-1]
        self.assertEqual(
            dispatch_step["env"],
            {
                "schema_version": "1",
                "source_repo": "${{ github.repository }}",
                "tag": "${{ steps.release.outputs.tag }}",
                "release_url": "${{ steps.release.outputs.release_url }}",
                "target_sha": "${{ steps.resolve.outputs.target_sha }}",
                "published_at": "${{ steps.release.outputs.published_at }}",
            },
        )

        release_url = "https://api.github.com/repos/${GITHUB_REPOSITORY}/releases/tags/$tag"
        commit_url = "https://api.github.com/repos/${GITHUB_REPOSITORY}/commits/$tag"
        hub_url = "https://api.github.com/repos/D-Robotics/rdk-skills/actions/workflows/component-upgrade.yml/dispatches"
        request_method = r"(?i)(?:--request(?:=|\s+)|-X\s*)([A-Z]+)\b"
        source_write_body = r"(?i)(?:^|\s)(?:-d|--data(?:-[a-z]+)?|--json|--form(?:-string)?|-F|--upload-file|-T)(?:=|\s)"
        for source_run, expected_url in (
            (release_step["run"], release_url),
            (resolve_step["run"], commit_url),
        ):
            with self.subTest(source_get=expected_url):
                self.assertEqual(len(re.findall(r"\bcurl\b", source_run)), 1)
                self.assertEqual(source_run.count("https://api.github.com/"), 1)
                self.assertEqual(
                    re.findall(r'"(https://api\.github\.com/repos/[^"]+)"', source_run),
                    [expected_url],
                )
                self.assertEqual(
                    source_run.count('Authorization: Bearer ${{ github.token }}'),
                    1,
                )
                self.assertEqual(re.findall(request_method, source_run), [])
                self.assertNotRegex(source_run, r"(?i)(?:^|\s)(?:--head|-I)(?:=|\s|$)")
                self.assertNotRegex(source_run, source_write_body)

        self.assertIn(
            'python3 tools/validate_release.py "$tag" "$GITHUB_REPOSITORY"',
            release_step["run"],
        )
        dispatch_run = dispatch_step["run"]
        self.assertEqual(dispatch_run.count("https://api.github.com/"), 1)
        self.assertEqual(
            re.findall(r'"(https://api\.github\.com/repos/[^"]+)"', dispatch_run),
            [hub_url],
        )
        self.assertEqual(
            re.findall(request_method, dispatch_run),
            ["POST"],
        )
        self.assertEqual(
            dispatch_run.count('Authorization: Bearer ${{ steps.app-token.outputs.token }}'),
            1,
        )
        self.assertIn('--data "$payload"', dispatch_run)

        normalized_dispatch = " ".join(dispatch_run.split())
        expected_payload_literal = (
            "'{ref: \"main\", inputs: { "
            "schema_version: ($schema_version | tostring), "
            "source_repo: $source_repo, tag: $tag, release_url: $release_url, "
            "target_sha: $target_sha, published_at: $published_at, dry_run: \"false\" }}'"
        )
        self.assertEqual(normalized_dispatch.count(expected_payload_literal), 1)
        self.assertIn('--argjson schema_version "$schema_version"', dispatch_run)

        all_runs = "\n".join(step.get("run", "") for step in steps)
        self.assertEqual(len(re.findall(r"\bcurl\b", all_runs)), 3)
        self.assertEqual(all_runs.count("https://api.github.com/"), 3)
        self.assertEqual(
            re.findall(r'"(https://api\.github\.com/repos/[^"]+)"', all_runs),
            [release_url, commit_url, hub_url],
        )
        self.assertEqual(
            re.findall(request_method, all_runs),
            ["POST"],
        )
        for forbidden in (
            r"(?i)\bgit\s+push\b",
            r"(?i)\bgit\s+tag\b",
            r"(?i)\bgh\s+release\s+(?:create|edit|delete)\b",
            r"(?i)\bgh\s+api\b",
            r"(?i)api\.github\.com/repos/[^\s\"']+/git/(?:refs|tags)(?:/|\b)",
        ):
            self.assertNotRegex(all_runs, forbidden)
