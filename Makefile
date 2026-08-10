# rdk-device-skills — single entry point for dev / CI tasks.

.PHONY: test validate index route docs-update lint

# Full sandbox run: index + routing suite + structural validation + docs search
test:
	python3 tools/sandbox.py test

# Structural checks only (frontmatter, sections, scripts, references)
validate:
	python3 tools/sandbox.py validate

# Print the skill index as JSON
index:
	python3 tools/sandbox.py index

# Route a single question: make route Q="40PIN 引脚定义是什么"
route:
	python3 tools/sandbox.py route "$(Q)"

# Refresh the local official-doc clones that rdk-docs-reference searches
docs-update:
	bash tools/update_docs.sh

# Bash syntax check for every script in the repo
lint:
	@fail=0; for f in install.sh skills/*/scripts/*.sh; do \
		bash -n "$$f" || { echo "FAIL $$f"; fail=1; }; \
	done; [ $$fail -eq 0 ] && echo "lint OK"
