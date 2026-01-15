#!/bin/bash
# End-to-End Test Script for Social Insight Multi-Agent Workflow
# Usage: ./scripts/test_e2e.sh [mock|azure]

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default mode
MODE="${1:-mock}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Social Insight Workflow E2E Test${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Mode: ${YELLOW}${MODE}${NC}"
echo -e "Repository: ${REPO_ROOT}"
echo ""

# Function to print status
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Step 1: Verify Python
echo -e "${BLUE}[Step 1/8] Verifying Python environment...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_status "Python found: $PYTHON_VERSION"
else
    print_error "Python 3 not found. Please install Python 3.8+"
    exit 1
fi

# Step 2: Check prerequisites
echo ""
echo -e "${BLUE}[Step 2/8] Checking prerequisites...${NC}"

if [ ! -f "config/hot_api_list.json" ]; then
    print_error "config/hot_api_list.json not found"
    exit 1
fi
print_status "Config file exists"

if [ ! -f "workflows/social_insight_workflow.yaml" ]; then
    print_error "workflows/social_insight_workflow.yaml not found"
    exit 1
fi
print_status "Workflow YAML exists"

# Step 3: Validate workflow YAML
echo ""
echo -e "${BLUE}[Step 3/8] Validating workflow YAML...${NC}"
python3 .github/skills/maf-decalarative-yaml/scripts/validate_maf_workflow_yaml.py \
    workflows/social_insight_workflow.yaml
print_status "Workflow YAML is valid"

# Step 4: Test shared tools
echo ""
echo -e "${BLUE}[Step 4/8] Testing shared tools registry...${NC}"
TOOLS_COUNT=$(python3 .github/skills/maf-shared-tools/scripts/call_shared_tool.py \
    --tool __list__ | python3 -c "import sys, json; print(len(json.load(sys.stdin)['tools']))")
print_status "Found $TOOLS_COUNT registered tools"

# Step 5: Generate workflow runner
echo ""
echo -e "${BLUE}[Step 5/8] Generating workflow runner...${NC}"
if [ -d "generated/social_insight_runner" ]; then
    print_info "Removing existing runner..."
    rm -rf generated/social_insight_runner
fi

python3 .github/skills/maf-workflow-gen/scripts/generate_executable_workflow.py \
    --in workflows/social_insight_workflow.yaml \
    --out generated/social_insight_runner \
    --force
print_status "Runner generated at generated/social_insight_runner/"

# Step 6: Check Azure credentials (if azure mode)
if [ "$MODE" = "azure" ]; then
    echo ""
    echo -e "${BLUE}[Step 6/8] Checking Azure credentials...${NC}"
    
    # Check if az CLI is available
    if command -v az &> /dev/null; then
        print_status "Azure CLI found"
        
        # Check if logged in
        if az account show &> /dev/null; then
            print_status "Azure CLI is authenticated"
        else
            print_error "Azure CLI not authenticated. Please run: az login"
            exit 1
        fi
    else
        print_error "Azure CLI not found. Install from: https://docs.microsoft.com/cli/azure/install-azure-cli"
        exit 1
    fi
    
    # Check environment variables
    if [ -z "$AZURE_AI_PROJECT_ENDPOINT" ]; then
        if [ -f ".env" ]; then
            print_info "Loading environment from .env file..."
            export $(cat .env | grep -v '^#' | xargs)
        fi
    fi
    
    if [ -z "$AZURE_AI_PROJECT_ENDPOINT" ]; then
        print_error "AZURE_AI_PROJECT_ENDPOINT not set"
        print_info "Set it in .env file or export it: export AZURE_AI_PROJECT_ENDPOINT=https://..."
        exit 1
    fi
    print_status "AZURE_AI_PROJECT_ENDPOINT: $AZURE_AI_PROJECT_ENDPOINT"
    
    if [ -z "$AZURE_AI_MODEL_DEPLOYMENT_NAME" ]; then
        print_error "AZURE_AI_MODEL_DEPLOYMENT_NAME not set"
        print_info "Set it in .env file or export it: export AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4"
        exit 1
    fi
    print_status "AZURE_AI_MODEL_DEPLOYMENT_NAME: $AZURE_AI_MODEL_DEPLOYMENT_NAME"
else
    echo ""
    echo -e "${BLUE}[Step 6/8] Skipping Azure credentials (mock mode)${NC}"
    print_info "Using mock mode - no Azure credentials required"
fi

# Step 7: Run the workflow
echo ""
echo -e "${BLUE}[Step 7/8] Running workflow...${NC}"
cd generated/social_insight_runner

if [ "$MODE" = "mock" ]; then
    print_info "Running in MOCK mode (using fallback tools)"
    python3 run.py --non-interactive --mock-agents
elif [ "$MODE" = "azure" ]; then
    print_info "Running with Azure AI Foundry"
    
    # Check if we have agent_id_map.json, if not create agents first
    if [ ! -f "agent_id_map.json" ]; then
        print_info "Creating Azure AI Foundry agents..."
        python3 ../../.github/skills/maf-agent-create/scripts/create_agents_from_workflow.py \
            --workflow ../../workflows/social_insight_workflow.yaml \
            --write-spec agents.yaml
        
        python3 ../../.github/skills/maf-agent-create/scripts/create_agents_from_workflow.py \
            --workflow ../../workflows/social_insight_workflow.yaml \
            --model-deployment-name "$AZURE_AI_MODEL_DEPLOYMENT_NAME" \
            --spec agents.yaml \
            --write-id-map agent_id_map.json
        
        print_status "Agents created"
    else
        print_info "Using existing agent_id_map.json"
    fi
    
    python3 run.py \
        --non-interactive \
        --azure-ai \
        --azure-ai-model-deployment-name "$AZURE_AI_MODEL_DEPLOYMENT_NAME" \
        --azure-ai-agent-id-map-json agent_id_map.json
else
    print_error "Unknown mode: $MODE. Use 'mock' or 'azure'"
    exit 1
fi

cd "$REPO_ROOT"
print_status "Workflow execution completed"

# Step 8: Verify outputs
echo ""
echo -e "${BLUE}[Step 8/8] Verifying outputs...${NC}"

OUTPUT_DIR="generated/social_insight_output"
EXPECTED_FILES=(
    "raw_signals.json"
    "clusters/hotspots.json"
    "insights/insights.json"
    "report.md"
)

ALL_EXIST=true
for file in "${EXPECTED_FILES[@]}"; do
    if [ -f "$OUTPUT_DIR/$file" ]; then
        SIZE=$(du -h "$OUTPUT_DIR/$file" | cut -f1)
        print_status "$file (${SIZE})"
    else
        print_error "$file not found"
        ALL_EXIST=false
    fi
done

if [ "$ALL_EXIST" = true ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ E2E Test PASSED${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "Output directory: ${BLUE}$OUTPUT_DIR${NC}"
    echo ""
    echo -e "View the final report:"
    echo -e "  ${YELLOW}cat $OUTPUT_DIR/report.md${NC}"
    echo ""
    exit 0
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}✗ E2E Test FAILED${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo -e "Some output files are missing. Check the workflow execution logs above."
    echo ""
    exit 1
fi
