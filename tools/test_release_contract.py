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

        self.assertEqual(document["on"], {"release": {"types": ["published"]}})
        self.assertEqual(document["permissions"], {"contents": "read"})
        self.assertIn("rdk-component-release", workflow)
        self.assertIn("RDK_RELEASE_BOT_PRIVATE_KEY", workflow)
        self.assertIn("github.event.release.prerelease", workflow)
        self.assertIn("actions/create-github-app-token@v2", workflow)
        self.assertIn("repos/D-Robotics/rdk-skills/dispatches", workflow)
        self.assertIn("^[0-9a-fA-F]{40}$", workflow)

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
