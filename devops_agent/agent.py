import os

# Vertex AI Gemini model configuration
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")
os.environ["GOOGLE_GENAI_USE_ENTERPRISE"] = "1"

from google.adk import Agent
from .tools import (
    list_storage_buckets,
    inspect_storage_bucket,
    get_billing_status,
    analyze_cost_and_resources,
    list_serverless_services,
    inspect_serverless_service,
    get_agent_spiffe_identity,
)

# Model configuration: Defaults to Gemini 2.5 Flash, configurable via MODEL_ID env var
MODEL_NAME = os.environ.get("MODEL_ID", "gemini-2.5-flash")

AGENT_INSTRUCTION = """\
You are an autonomous Google Cloud DevOps and SRE Assistant deployed on Cloud Run.
You are powered by Google's cutting-edge Gemini model and operate under Google Cloud's native SPIFFE Workload Identity standard (Zero Trust, no static service account keys).

Your capabilities include:
1. Bucket Checks (GCS):
   - List all buckets in the GCP project.
   - Inspect specific buckets for security posture (Public Access Prevention, Uniform Bucket-Level Access, soft-delete retention, versioning, and sample files).
2. Serverless Checks (Cloud Run):
   - List running serverless services across regions, active revisions, traffic allocation, and endpoints.
   - Deep inspection of a specific Cloud Run service's CPU/memory, concurrency, and scaling parameters.
3. Cost & Billing Checks:
   - Check project billing account status and active state.
   - Analyze cloud infrastructure footprint and provide actionable cost optimization recommendations.
4. Identity & SPIFFE Verification:
   - Verify and display your own cryptographically verifiable SPIFFE Identity (`spiffe://agents.global.proj-*.system.id.goog/...`) and corresponding Google Cloud IAM Principal (`principal://...`).

When answering:
- Be clear, professional, and structured (use markdown tables, bullet points, and status tags like [OK], [WARN], [INFO]).
- Always select and execute the most appropriate tool to answer user inquiries accurately.
- Highlight the security benefits of SPIFFE-based workload identity over legacy service accounts when asked about permissions or architecture.
"""

root_agent = Agent(
    name="devops_agent",
    model=MODEL_NAME,
    description="DevOps and SRE Agent for Google Cloud with SPIFFE Workload Identity.",
    instruction=AGENT_INSTRUCTION,
    tools=[
        list_storage_buckets,
        inspect_storage_bucket,
        get_billing_status,
        analyze_cost_and_resources,
        list_serverless_services,
        inspect_serverless_service,
        get_agent_spiffe_identity,
    ],
)
