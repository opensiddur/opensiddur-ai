"""Run the electronic book's JavaScript under Node, from unittest.

The book's scripts are plain browser scripts with no build step, so a test loads them into
Node as they are and calls into the globals they define. Node is found as `$OPENSIDDUR_NODE`,
or else `node` on the PATH.

Without Node the JavaScript tests are skipped, unless `$OPENSIDDUR_REQUIRE_JS` is 1, as CI
sets it: there a missing Node is a failure, so that the tests cannot pass by not running.
"""

import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path
from typing import Any

ASSETS = Path(__file__).resolve().parents[2] / "exporter" / "html" / "assets"

_RUNNER = """
const fs = require("fs");
const vm = require("vm");
const request = JSON.parse(fs.readFileSync(0, "utf8"));
for (const script of request.scripts) {
  vm.runInThisContext(fs.readFileSync(script, "utf8"), { filename: script });
}
const call = new Function("args", request.body);
process.stdout.write(JSON.stringify(call(request.args)));
"""


def node_executable() -> str | None:
    return os.environ.get("OPENSIDDUR_NODE") or shutil.which("node")


def require_node(test_case: unittest.TestCase) -> str:
    """The Node executable, or skip the test (fail it, under $OPENSIDDUR_REQUIRE_JS)."""
    node = node_executable()
    if node is None:
        if os.environ.get("OPENSIDDUR_REQUIRE_JS") == "1":
            test_case.fail("Node is required ($OPENSIDDUR_REQUIRE_JS=1) but was not found")
        test_case.skipTest("Node not found; set $OPENSIDDUR_NODE or put node on the PATH")
    return node


def run_js(node: str, body: str, args: Any = None, scripts: tuple[str, ...] = ("condition.js",)) -> Any:
    """Load `scripts` from the assets directory, then run `body` as a function of `args`.

    `body` returns a JSON-serialisable value, which is returned decoded.
    """
    request = {
        "scripts": [str(ASSETS / script) for script in scripts],
        "body": body,
        "args": args,
    }
    completed = subprocess.run(
        [node, "-e", _RUNNER],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    if completed.returncode != 0:
        raise AssertionError(f"node failed:\n{completed.stderr}")
    return json.loads(completed.stdout)
