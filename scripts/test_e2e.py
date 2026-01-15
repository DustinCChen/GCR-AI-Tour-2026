#!/usr/bin/env python3
"""
End-to-End Test Script for Social Insight Multi-Agent Workflow
Usage: python scripts/test_e2e.py [--mode mock|azure] [--verbose]
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class Colors:
    """ANSI color codes for terminal output."""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


def print_status(message: str) -> None:
    """Print success status."""
    print(f"{Colors.GREEN}✓{Colors.NC} {message}")


def print_error(message: str) -> None:
    """Print error status."""
    print(f"{Colors.RED}✗{Colors.NC} {message}")


def print_info(message: str) -> None:
    """Print info status."""
    print(f"{Colors.BLUE}ℹ{Colors.NC} {message}")


def print_header(message: str) -> None:
    """Print section header."""
    print(f"\n{Colors.BLUE}{message}{Colors.NC}")


def run_command(cmd: List[str], check: bool = True, capture: bool = False) -> Tuple[int, str]:
    """
    Run a shell command.
    
    Args:
        cmd: Command and arguments as list
        check: Whether to raise exception on non-zero exit
        capture: Whether to capture output
        
    Returns:
        Tuple of (exit_code, output)
    """
    try:
        if capture:
            result = subprocess.run(
                cmd,
                check=check,
                capture_output=True,
                text=True
            )
            return result.returncode, result.stdout
        else:
            result = subprocess.run(cmd, check=check)
            return result.returncode, ""
    except subprocess.CalledProcessError as e:
        if check:
            raise
        return e.returncode, ""


def check_python() -> bool:
    """Verify Python installation."""
    print_header("[Step 1/8] Verifying Python environment...")
    try:
        version = sys.version.split()[0]
        print_status(f"Python found: {version}")
        return True
    except Exception as e:
        print_error(f"Python check failed: {e}")
        return False


def check_prerequisites(repo_root: Path) -> bool:
    """Check that required files exist."""
    print_header("[Step 2/8] Checking prerequisites...")
    
    required_files = [
        "config/hot_api_list.json",
        "workflows/social_insight_workflow.yaml",
        "shared_tools/social_signal_tools.py",
        "shared_tools/maf_shared_tools_registry.py"
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = repo_root / file_path
        if full_path.exists():
            print_status(f"{file_path} exists")
        else:
            print_error(f"{file_path} not found")
            all_exist = False
    
    return all_exist


def validate_workflow(repo_root: Path) -> bool:
    """Validate workflow YAML."""
    print_header("[Step 3/8] Validating workflow YAML...")
    
    validator = repo_root / ".github/skills/maf-decalarative-yaml/scripts/validate_maf_workflow_yaml.py"
    workflow = repo_root / "workflows/social_insight_workflow.yaml"
    
    try:
        exit_code, _ = run_command([
            "python3",
            str(validator),
            str(workflow)
        ], capture=True)
        
        if exit_code == 0:
            print_status("Workflow YAML is valid")
            return True
        else:
            print_error("Workflow YAML validation failed")
            return False
    except Exception as e:
        print_error(f"Validation error: {e}")
        return False


def test_tools(repo_root: Path) -> bool:
    """Test shared tools registry."""
    print_header("[Step 4/8] Testing shared tools registry...")
    
    tool_script = repo_root / ".github/skills/maf-shared-tools/scripts/call_shared_tool.py"
    
    try:
        exit_code, output = run_command([
            "python3",
            str(tool_script),
            "--tool",
            "__list__"
        ], capture=True)
        
        if exit_code == 0:
            result = json.loads(output)
            tools = result.get("tools", [])
            print_status(f"Found {len(tools)} registered tools")
            for tool in tools:
                print(f"  - {tool}")
            return True
        else:
            print_error("Tool registry test failed")
            return False
    except Exception as e:
        print_error(f"Tool test error: {e}")
        return False


def generate_runner(repo_root: Path) -> bool:
    """Generate workflow runner."""
    print_header("[Step 5/8] Generating workflow runner...")
    
    runner_dir = repo_root / "generated/social_insight_runner"
    if runner_dir.exists():
        print_info("Removing existing runner...")
        import shutil
        shutil.rmtree(runner_dir)
    
    generator = repo_root / ".github/skills/maf-workflow-gen/scripts/generate_executable_workflow.py"
    workflow = repo_root / "workflows/social_insight_workflow.yaml"
    
    try:
        exit_code, _ = run_command([
            "python3",
            str(generator),
            "--in", str(workflow),
            "--out", str(runner_dir),
            "--force"
        ])
        
        if exit_code == 0:
            print_status(f"Runner generated at {runner_dir}")
            return True
        else:
            print_error("Runner generation failed")
            return False
    except Exception as e:
        print_error(f"Generation error: {e}")
        return False


def check_azure_credentials(verbose: bool = False) -> Dict[str, str]:
    """Check Azure credentials."""
    print_header("[Step 6/8] Checking Azure credentials...")
    
    credentials = {}
    
    # Check Azure CLI
    try:
        exit_code, _ = run_command(["az", "--version"], check=False, capture=True)
        if exit_code == 0:
            print_status("Azure CLI found")
            
            # Check if authenticated
            exit_code, _ = run_command(["az", "account", "show"], check=False, capture=True)
            if exit_code == 0:
                print_status("Azure CLI is authenticated")
            else:
                print_error("Azure CLI not authenticated. Please run: az login")
                return {}
        else:
            print_error("Azure CLI not found")
            return {}
    except FileNotFoundError:
        print_error("Azure CLI not found. Install from: https://docs.microsoft.com/cli/azure/install-azure-cli")
        return {}
    
    # Check environment variables
    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    model = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    
    # Try loading from .env file
    if not endpoint or not model:
        env_file = Path(".env")
        if env_file.exists():
            print_info("Loading environment from .env file...")
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key.strip()] = value.strip()
            
            endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
            model = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    
    if endpoint:
        print_status(f"AZURE_AI_PROJECT_ENDPOINT: {endpoint}")
        credentials["endpoint"] = endpoint
    else:
        print_error("AZURE_AI_PROJECT_ENDPOINT not set")
        print_info("Set it in .env file or export: export AZURE_AI_PROJECT_ENDPOINT=https://...")
        return {}
    
    if model:
        print_status(f"AZURE_AI_MODEL_DEPLOYMENT_NAME: {model}")
        credentials["model"] = model
    else:
        print_error("AZURE_AI_MODEL_DEPLOYMENT_NAME not set")
        print_info("Set it in .env file or export: export AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4")
        return {}
    
    return credentials


def run_workflow(repo_root: Path, mode: str, credentials: Dict[str, str]) -> bool:
    """Run the workflow."""
    print_header("[Step 7/8] Running workflow...")
    
    runner_dir = repo_root / "generated/social_insight_runner"
    os.chdir(runner_dir)
    
    try:
        if mode == "mock":
            print_info("Running in MOCK mode (using fallback tools)")
            exit_code, _ = run_command([
                "python3", "run.py",
                "--non-interactive",
                "--mock-agents"
            ])
        elif mode == "azure":
            print_info("Running with Azure AI Foundry")
            
            # Check if agent_id_map.json exists
            agent_map = runner_dir / "agent_id_map.json"
            if not agent_map.exists():
                print_info("Creating Azure AI Foundry agents...")
                
                # Generate agent spec
                run_command([
                    "python3",
                    str(repo_root / ".github/skills/maf-agent-create/scripts/create_agents_from_workflow.py"),
                    "--workflow", str(repo_root / "workflows/social_insight_workflow.yaml"),
                    "--write-spec", "agents.yaml"
                ])
                
                # Create agents
                run_command([
                    "python3",
                    str(repo_root / ".github/skills/maf-agent-create/scripts/create_agents_from_workflow.py"),
                    "--workflow", str(repo_root / "workflows/social_insight_workflow.yaml"),
                    "--model-deployment-name", credentials["model"],
                    "--spec", "agents.yaml",
                    "--write-id-map", "agent_id_map.json"
                ])
                
                print_status("Agents created")
            else:
                print_info("Using existing agent_id_map.json")
            
            exit_code, _ = run_command([
                "python3", "run.py",
                "--non-interactive",
                "--azure-ai",
                "--azure-ai-model-deployment-name", credentials["model"],
                "--azure-ai-agent-id-map-json", "agent_id_map.json"
            ])
        
        os.chdir(repo_root)
        
        if exit_code == 0:
            print_status("Workflow execution completed")
            return True
        else:
            print_error("Workflow execution failed")
            return False
            
    except Exception as e:
        print_error(f"Workflow execution error: {e}")
        os.chdir(repo_root)
        return False


def verify_outputs(repo_root: Path) -> bool:
    """Verify output files."""
    print_header("[Step 8/8] Verifying outputs...")
    
    output_dir = repo_root / "generated/social_insight_output"
    expected_files = [
        "raw_signals.json",
        "clusters/hotspots.json",
        "insights/insights.json",
        "report.md"
    ]
    
    all_exist = True
    for file_path in expected_files:
        full_path = output_dir / file_path
        if full_path.exists():
            size = full_path.stat().st_size
            size_str = f"{size / 1024:.1f}KB" if size > 1024 else f"{size}B"
            print_status(f"{file_path} ({size_str})")
        else:
            print_error(f"{file_path} not found")
            all_exist = False
    
    return all_exist


def main():
    """Main test execution."""
    parser = argparse.ArgumentParser(description="Run end-to-end test for Social Insight Workflow")
    parser.add_argument("--mode", choices=["mock", "azure"], default="mock",
                        help="Execution mode (default: mock)")
    parser.add_argument("--verbose", action="store_true",
                        help="Verbose output")
    args = parser.parse_args()
    
    # Get repository root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.resolve()
    os.chdir(repo_root)
    
    # Print header
    print(f"{Colors.BLUE}========================================{Colors.NC}")
    print(f"{Colors.BLUE}Social Insight Workflow E2E Test{Colors.NC}")
    print(f"{Colors.BLUE}========================================{Colors.NC}")
    print()
    print(f"Mode: {Colors.YELLOW}{args.mode}{Colors.NC}")
    print(f"Repository: {repo_root}")
    print()
    
    # Run test steps
    steps = [
        ("Python Environment", lambda: check_python()),
        ("Prerequisites", lambda: check_prerequisites(repo_root)),
        ("Workflow Validation", lambda: validate_workflow(repo_root)),
        ("Tools Registry", lambda: test_tools(repo_root)),
        ("Runner Generation", lambda: generate_runner(repo_root)),
    ]
    
    # Add Azure credential check for azure mode
    credentials = {}
    if args.mode == "azure":
        credentials = check_azure_credentials(args.verbose)
        if not credentials:
            print_error("Azure credentials check failed")
            sys.exit(1)
    else:
        print_header("[Step 6/8] Skipping Azure credentials (mock mode)")
        print_info("Using mock mode - no Azure credentials required")
    
    # Execute basic steps
    for step_name, step_func in steps:
        if not step_func():
            print_error(f"{step_name} failed")
            sys.exit(1)
    
    # Run workflow
    if not run_workflow(repo_root, args.mode, credentials):
        sys.exit(1)
    
    # Verify outputs
    if verify_outputs(repo_root):
        print()
        print(f"{Colors.GREEN}========================================{Colors.NC}")
        print(f"{Colors.GREEN}✓ E2E Test PASSED{Colors.NC}")
        print(f"{Colors.GREEN}========================================{Colors.NC}")
        print()
        print(f"Output directory: {Colors.BLUE}generated/social_insight_output{Colors.NC}")
        print()
        print("View the final report:")
        print(f"  {Colors.YELLOW}cat generated/social_insight_output/report.md{Colors.NC}")
        print()
        sys.exit(0)
    else:
        print()
        print(f"{Colors.RED}========================================{Colors.NC}")
        print(f"{Colors.RED}✗ E2E Test FAILED{Colors.NC}")
        print(f"{Colors.RED}========================================{Colors.NC}")
        print()
        print("Some output files are missing. Check the workflow execution logs above.")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
