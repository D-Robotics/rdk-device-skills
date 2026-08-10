#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 D-Robotics. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Refresh (or bootstrap) the local clones of the official D-Robotics doc repos
# that rdk-docs-reference searches. Keeps answers from going stale.
#
# Usage:
#   tools/update_docs.sh            # pull or clone into <repo>/.refs
#   RDK_DOCS_ROOT=/path update_docs.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCS_ROOT="${RDK_DOCS_ROOT:-$REPO_DIR/.refs}"
mkdir -p "$DOCS_ROOT"

for repo in rdk_x_doc rdk_s_doc; do
  dst="$DOCS_ROOT/$repo"
  if [ -d "$dst/.git" ]; then
    echo "[update] $repo"
    git -C "$dst" pull --ff-only || echo "warn: pull failed for $repo; keeping existing clone" >&2
  else
    echo "[clone] $repo"
    git clone --depth 1 --single-branch "https://github.com/D-Robotics/$repo.git" "$dst"
  fi
done

echo "docs ready under $DOCS_ROOT"
