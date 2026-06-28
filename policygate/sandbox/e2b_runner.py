from __future__ import annotations

from e2b import CommandExitException
from e2b_code_interpreter import Sandbox

WORKDIR = "/home/user"


def run_pytest(
    files: dict[str, str],
    test_filename: str,
    test_content: str,
    timeout: int = 120,
) -> dict:
    """Write files + a test into a fresh E2B sandbox, run pytest, return result.

    Returns {exit_code, stdout, stderr}. exit_code != 0 means the test FAILED
    (which is what we WANT when running the proving test on the original buggy code).
    """
    sbx = Sandbox.create(timeout=timeout + 30)
    try:
        for path, content in files.items():
            sbx.files.write(f"{WORKDIR}/{path}", content)
        sbx.files.write(f"{WORKDIR}/{test_filename}", test_content)

        cmd = "pip install -q pytest >/dev/null 2>&1; python -m pytest -q"
        try:
            res = sbx.commands.run(cmd, cwd=WORKDIR, timeout=timeout)
            return {"exit_code": res.exit_code, "stdout": res.stdout, "stderr": res.stderr}
        except CommandExitException as e:
            return {
                "exit_code": getattr(e, "exit_code", 1),
                "stdout": getattr(e, "stdout", ""),
                "stderr": getattr(e, "stderr", str(e)),
            }
    finally:
        sbx.kill()