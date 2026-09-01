import importlib.util
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = Path(__file__).with_name("sandbox.py")
SPEC = importlib.util.spec_from_file_location("sandbox", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
sandbox = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sandbox)


class DeviceReleaseContractTests(unittest.TestCase):
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

    def test_published_release_notifies_hub_with_verified_payload(self):
        workflow_path = ROOT / ".github" / "workflows" / "notify-hub-release.yml"
        workflow = workflow_path.read_text(encoding="utf-8")
        document = yaml.load(workflow, Loader=yaml.BaseLoader)
        app_token_action = (
            "actions/create-github-app-token@"
            "fee1f7d63c2ff003460e3d139729b119787bc349"
        )

        self.assertEqual(document["on"], {"release": {"types": ["published"]}})
        self.assertEqual(document["permissions"], {"contents": "read"})
        self.assertIn("RDK_RELEASE_DISPATCHER_PRIVATE_KEY", workflow)
        self.assertIn("github.event.release.prerelease", workflow)
        self.assertEqual(
            [
                step["uses"]
                for step in document["jobs"]["notify-hub"]["steps"]
                if "uses" in step
            ],
            [app_token_action],
        )
        self.assertIn(
            "repos/D-Robotics/rdk-skills/actions/workflows/component-upgrade.yml/dispatches",
            workflow,
        )
        self.assertIn("^[0-9a-fA-F]{40}$", workflow)

        token_step = next(
            step
            for step in document["jobs"]["notify-hub"]["steps"]
            if step.get("uses") == app_token_action
        )
        self.assertEqual(
            token_step["with"]["app-id"],
            "${{ vars.RDK_RELEASE_DISPATCHER_APP_ID }}",
        )
        self.assertEqual(
            token_step["with"]["private-key"],
            "${{ secrets.RDK_RELEASE_DISPATCHER_PRIVATE_KEY }}",
        )
        self.assertEqual(token_step["with"]["permission-actions"], "write")
        self.assertNotIn("permission-contents", token_step["with"])

        expected_payload_fields = {
            "schema_version",
            "source_repo",
            "tag",
            "release_url",
            "target_sha",
            "published_at",
        }
        self.assertEqual(
            set(document["jobs"]["notify-hub"]["steps"][-1]["env"]),
            expected_payload_fields,
        )
