"""Re-run only guideline_compiler + pdf_renderer (assets are already generated)."""
import asyncio, os, sys, json
from dotenv import load_dotenv
load_dotenv()

async def run_agent_async(name: str):
    print(f"[{name}] Starting...")
    proc = await asyncio.create_subprocess_exec(
        "python", f"agents/{name}.py",
        cwd=os.path.dirname(os.path.abspath(__file__)),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    print(f"[{name}] Completed (Return code: {proc.returncode})")
    if proc.returncode != 0:
        if stdout: print(f"[{name}] stdout:\n{stdout.decode().strip()}")
        if stderr: print(f"[{name}] stderr:\n{stderr.decode().strip()}")
    return proc.returncode

async def main():
    # Fix agent log — remove the error line
    log_path = os.path.join("workspace", "agent_log.txt")
    with open(log_path, "r", encoding="utf-8") as f:
        lines = [l for l in f.readlines() if "ERROR" not in l]
    with open(log_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    rc = await run_agent_async("guideline_compiler")
    if rc != 0:
        print("guideline_compiler failed!")
        sys.exit(1)

    rc = await run_agent_async("pdf_renderer")
    if rc != 0:
        print("pdf_renderer failed!")
        sys.exit(1)

    print("✅ Brand guidelines PDF → workspace/brand_guidelines.pdf")

if __name__ == "__main__":
    asyncio.run(main())
