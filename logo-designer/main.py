import asyncio
import json
import os

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
        if stdout:
            print(f"[{name}] stdout:\n{stdout.decode().strip()}")
        if stderr:
            print(f"[{name}] stderr:\n{stderr.decode().strip()}")
    
    return proc.returncode

def check_agent_log(name: str) -> bool:
    log_path = os.path.join("workspace", "agent_log.txt")
    if not os.path.exists(log_path):
        return False
        
    with open(log_path, "r", encoding="utf-8") as f:
        log_content = f.read()
        
    for line in log_content.splitlines():
        if "STATUS: ERROR" in line:
            print(f"Pipeline halted! Found error in log: {line.strip()}")
            import sys
            sys.exit(1)
            
    return True

async def main():
    try:
        with open("user_input.json", "r", encoding="utf-8") as f:
            user_input = json.load(f)
            print(f"Company Name: {user_input.get('company_name', 'Unknown')}")
    except FileNotFoundError:
        print("user_input.json not found")
        return

    os.makedirs("workspace", exist_ok=True)
    with open(os.path.join("workspace", "agent_log.txt"), "w", encoding="utf-8") as f:
        f.write("")

    # 1. brand_strategist (sequential)
    await run_agent_async("brand_strategist")
    check_agent_log("brand_strategist")

    # 2. logo_designer (sequential)
    await run_agent_async("logo_designer")
    check_agent_log("logo_designer")

    # 3. colour_architect (sequential) - MUST complete before image_generator starts
    await run_agent_async("colour_architect")
    check_agent_log("colour_architect")

    # 4. typography_director + image_generator (PARALLEL via asyncio.gather)
    await asyncio.gather(
        run_agent_async("typography_director"),
        run_agent_async("image_generator")
    )
    check_agent_log("typography_director")
    check_agent_log("image_generator")

    # 5. guideline_compiler (sequential)
    await run_agent_async("guideline_compiler")
    check_agent_log("guideline_compiler")

    # 6. pdf_renderer (sequential)
    await run_agent_async("pdf_renderer")
    check_agent_log("pdf_renderer")

    print("✅ Brand guidelines PDF → workspace/brand_guidelines.pdf")

if __name__ == "__main__":
    asyncio.run(main())
