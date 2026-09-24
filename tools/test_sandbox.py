import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).with_name("sandbox.py")
SPEC = importlib.util.spec_from_file_location("sandbox", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
sandbox = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sandbox)


class WorkspaceRouterContractTests(unittest.TestCase):
    def check_routes(self, skills):
        checker = getattr(sandbox, "workspace_router_route_problems", lambda _skills: [])
        return checker(skills)

    def load_target_skills(self):
        skills = {}
        for name in sandbox.WORKSPACE_ROUTER_ROUTES:
            path = MODULE_PATH.parents[1] / "skills" / name / "SKILL.md"
            text = path.read_text(encoding="utf-8")
            frontmatter = sandbox.parse_frontmatter(text)
            skills[name] = {"description": frontmatter.get("description", ""), "text": text}
        return skills

    def test_missing_availability_gate_is_rejected(self):
        skills = {
            "rdk-hardware": {
                "description": "Own-model conversion: X5 -> x5-router.",
                "text": "Route own-model conversion to `x5-router`.",
            }
        }

        problems = self.check_routes(skills)

        self.assertTrue(problems)
        self.assertTrue(any("x5-router" in problem for problem in problems))

    def test_availability_check_must_stop_handoff_before_install_fallback(self):
        skills = {
            "rdk-board-delegate": {
                "description": "drobotics-router handoff is availability-gated.",
                "text": """\
## Workspace router availability gate
check whether `drobotics-router` is available in the current session.
Mention `rdk-pack-installer` and `OE Tool Chain (S)`, then restart and retry.
""",
            }
        }

        problems = self.check_routes(skills)

        self.assertTrue(any("atomic fallback" in problem for problem in problems))

    def test_repository_workspace_router_routes_satisfy_contract(self):
        routes = getattr(sandbox, "WORKSPACE_ROUTER_ROUTES", {})
        if not routes:
            self.fail("workspace router contract is not defined")
        problems = self.check_routes(self.load_target_skills())

        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
