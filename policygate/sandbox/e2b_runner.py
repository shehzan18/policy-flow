from __future__ import annotations

from e2b import CommandExitException
from e2b_code_interpreter import Sandbox

WORKDIR = "/home/user"


def run_pytest(
    files: dict[str, str],
    test_filename: str,
    test_content: str,
    requirements: str = "",
    timeout: int = 180,
) -> dict:
    """Write files + a test into a fresh E2B sandbox, run pytest, return result.

    If `requirements` is provided, it's written as requirements.txt and pip-installed
    before the test runs — so verification works on real repos with dependencies.
    """
    sbx = Sandbox.create(timeout=timeout + 60)
    try:
        for path, content in files.items():
            sbx.files.write(f"{WORKDIR}/{path}", content)
        sbx.files.write(f"{WORKDIR}/{test_filename}", test_content)

        install = "pip install -q pytest"
        if requirements.strip():
            sbx.files.write(f"{WORKDIR}/requirements.txt", requirements)
            install += " && pip install -q -r requirements.txt"
        cmd = f"{install} >/dev/null 2>&1; python -m pytest -q"

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