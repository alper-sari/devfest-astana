<!--markdownlint-disable MD024 MD033 MD036 MD041 -->
<walkthrough-metadata>
  <meta name="title" content="Deploy DevOps Agent with Vertex AI Agent Engine and Native SPIFFE Identity" />
  <meta name="description" content="Learn how to build a DevOps AI agent with Gemini 3.8 Flash, deploy to Vertex AI Agent Engine with Zero Service Accounts, and manage permissions using native SPIFFE Agent Identity." />
  <meta name="keywords" content="Gemini, Google Cloud, Vertex AI, Agent Engine, ADK, SPIFFE, Agent Identity, Zero Trust, DevOps" />
</walkthrough-metadata>

# Build a DevOps Agent with Vertex AI & Native SPIFFE Identity

## Let's get started

![Tutorial header image](https://raw.githubusercontent.com/NucleusEngineering/serverless/main/.images/run.jpg)

Welcome to **DevFest Astana**! In this hands-on workshop, you will learn how to build and deploy an autonomous **DevOps & SRE Agent** using Google Cloud's **Agent Development Kit (ADK)** and **Gemini 3.8 Flash**.

Crucially, we will **NOT** use traditional Service Account keys or assign broad Service Account roles. Instead, we will deploy the agent to Google's **Vertex AI Agent Engine** using **Native SPIFFE Workload Identity (`AGENT_IDENTITY`)**.

<walkthrough-tutorial-difficulty difficulty="2"></walkthrough-tutorial-difficulty>

Estimated time:
<walkthrough-tutorial-duration duration="35"></walkthrough-tutorial-duration>

To get started, click **Start**.

## Project Setup

First, make sure you have the correct Google Cloud project selected with billing enabled.

<walkthrough-project-setup billing="true"></walkthrough-project-setup>

Next, enable the required APIs for Vertex AI, Cloud Storage, Cloud Run, and Cloud Build.

<walkthrough-enable-apis apis="aiplatform.googleapis.com,run.googleapis.com,cloudbuild.googleapis.com,storage.googleapis.com"></walkthrough-enable-apis>

Set your project environment variables in Cloud Shell:

```bash
export PROJECT_ID=$(gcloud config get-value project)
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
export REGION="us-central1"

echo "Project ID: $PROJECT_ID"
echo "Project Number: $PROJECT_NUMBER"
echo "Region: $REGION"
```

## Explore the DevOps Agent Code

Let's navigate to the agent directory and explore its structure.

```bash
cd devfest-astana/devops_agent
ls -la
```

The agent is organized into three primary files:
- `agent.py`: Defines the ADK `Agent` powered by **Gemini 3.8 Flash** with system instructions.
- `tools.py`: Implements DevOps tools (GCS bucket audits, Cloud Run inspection, and SPIFFE identity self-verification).
- `requirements.txt`: Python dependencies (`google-adk`, `google-cloud-aiplatform[agent_engines]`, `google-cloud-storage`, `google-cloud-run`).

Let's view the agent definition:

```bash
cat agent.py
```

Notice that the agent connects to Vertex AI using `gemini-3.8-flash` on the global endpoint, and registers tools for infrastructure observation without embedding any credentials or keys.

## Install ADK and Dependencies

We use `uv` (or `pip`) in Cloud Shell to manage our environment and run the Google Agent Development Kit CLI (`adk`).

Run the following commands to install dependencies:

```bash
python3 -m pip install --upgrade uv
uv pip install --system google-adk "google-cloud-aiplatform[adk,agent_engines]"
```

Verify that the ADK CLI is available:

```bash
adk --help
```

## Provision Agent Engine with Native `AGENT_IDENTITY`

In traditional architectures, workloads require a Service Account. In Google Cloud's modern Agent architecture, we provision a dedicated **`AGENT_IDENTITY` (SPIFFE)**.

Run the Python script below to create an Agent Engine instance configured with `IdentityType.AGENT_IDENTITY`:

```bash
python3 -c "
import vertexai
from vertexai import types

client = vertexai.Client(project='$PROJECT_ID', location='$REGION')
engine = client.agent_engines.create(
    config={'identity_type': types.IdentityType.AGENT_IDENTITY}
)
resource_name = engine.api_resource.name
engine_id = resource_name.split('/')[-1]

with open('.engine_id', 'w') as f:
    f.write(engine_id)

print(f'Successfully created Agent Engine with AGENT_IDENTITY!')
print(f'Engine Resource: {resource_name}')
print(f'Engine ID: {engine_id}')
"
```

Let's export the Engine ID to our environment:

```bash
export AGENT_ENGINE_ID=$(cat .engine_id)
echo "Agent Engine ID: $AGENT_ENGINE_ID"
```

## Inspect the SPIFFE Identity

Let's verify that Google Cloud has assigned a native SPIFFE identity rather than a service account!

Run a GET request to inspect the resource:

```bash
curl -s -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  https://$REGION-aiplatform.googleapis.com/v1beta1/projects/$PROJECT_NUMBER/locations/$REGION/reasoningEngines/$AGENT_ENGINE_ID | grep -E "(identityType|effectiveIdentity)"
```

You will observe:
- **`identityType`**: `"AGENT_IDENTITY"`
- **`effectiveIdentity`**: `agents.global.proj-<PROJECT_NUMBER>.system.id.goog/...`

Notice that there is **NO** service account email attached to the agent! The agent's identity is a cryptographically attested SPIFFE URI under Google's system trust domain.

## Deploy Agent Source Code

Now let's package and deploy our DevOps agent code into the newly created Agent Engine instance using ADK:

```bash
cd ..
adk deploy agent_engine \
  --project=$PROJECT_ID \
  --region=$REGION \
  --agent_engine_id=$AGENT_ENGINE_ID \
  devops_agent
```

Cloud Build will package the container and deploy it to the serverless Reasoning Engine runtime. This typically takes 2–3 minutes.

Once completed, you'll see a success message with your direct Console Playground URL!

## Zero Trust in Action: Triggering 403 Forbidden

In a Zero Trust architecture, workloads start with **Zero Permissions**. Because we did not attach a service account (or any broad default role), our agent has no access to Google Cloud Storage.

Let's test this by asking the agent to list storage buckets:

```bash
curl -s -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  https://$REGION-aiplatform.googleapis.com/v1beta1/projects/$PROJECT_NUMBER/locations/$REGION/reasoningEngines/$AGENT_ENGINE_ID:streamQuery \
  -d '{
    "class_method": "async_stream_query",
    "input": {
      "user_id": "workshop-attendee",
      "message": "List the storage buckets in our project"
    }
  }'
```

Observe the response! The agent tool calls `list_storage_buckets` and receives:

```text
403 GET ...: Caller does not have storage.buckets.list access to the Google Cloud project.
Permission 'storage.buckets.list' denied on resource.
```

Gemini 3.8 Flash catches this error, analyzes its own SPIFFE security context, and explains to the user that it lacks permissions and needs an IAM role bound to its SPIFFE principal!

## Authorize the Agent via SPIFFE Workload Identity

Now, let's grant the necessary read permission **strictly** to the agent's cryptographic SPIFFE identity:

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="principalSet://agents.global.proj-$PROJECT_NUMBER.system.id.goog/attribute.platformContainer/aiplatform/projects/$PROJECT_NUMBER" \
  --role="roles/viewer"
```

Notice what we did:
1. We did **NOT** create or distribute a JSON private key.
2. We did **NOT** grant permissions to a user or broad service account.
3. We bound the `roles/viewer` role directly to the `principalSet://agents.global...` SPIFFE identity.

## Verify Authorized Access

Now that permissions are bound to the SPIFFE principal, let's re-run the query:

```bash
curl -s -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  https://$REGION-aiplatform.googleapis.com/v1beta1/projects/$PROJECT_NUMBER/locations/$REGION/reasoningEngines/$AGENT_ENGINE_ID:streamQuery \
  -d '{
    "class_method": "async_stream_query",
    "input": {
      "user_id": "workshop-attendee",
      "message": "List the storage buckets in our project and verify your SPIFFE identity"
    }
  }'
```

Success! The agent now successfully executes `list_storage_buckets` and `get_agent_spiffe_identity`, returning:
1. A complete overview table of all GCS buckets in your project.
2. Security posture audit (Uniform Bucket-Level Access status).
3. Verified SPIFFE identity details and trust domain.

## Interactive Console Playground

You can also chat interactively with your DevOps Agent via the Google Cloud Console UI:

1. Open the [Vertex AI Agent Engine Console](https://console.cloud.google.com/vertex-ai/agents/agent-engines).
2. Select **DevOps Agent** (`$AGENT_ENGINE_ID`).
3. Click on the **Playground** tab.
4. Try asking questions such as:
   - *"What is your SPIFFE identity and security model?"*
   - *"List our Cloud Run serverless services and check their health."*
   - *"Which buckets currently have Uniform Bucket-Level Access disabled?"*

## Congratulations!

<walkthrough-conclusion-trophy></walkthrough-conclusion-trophy>

You have successfully built and deployed a production-grade DevOps Agent on Google Cloud with Native SPIFFE Agent Identity!

### What you learned:
* How to use Google's **Agent Development Kit (ADK)** with **Gemini 3.8 Flash**.
* The difference between legacy Service Accounts and **Native SPIFFE `AGENT_IDENTITY`**.
* Enforcing **Zero Trust**: Observing real-time `403 Forbidden` errors until permissions are explicitly granted.
* Granting granular IAM roles directly to `principalSet://agents.global...` principals.

<walkthrough-inline-feedback></walkthrough-inline-feedback>

## Clean Up

To avoid ongoing charges on your project, you can delete the deployed Reasoning Engine instance:

```bash
python3 -c "
import vertexai
client = vertexai.Client(project='$PROJECT_ID', location='$REGION')
client.agent_engines.delete(name='projects/$PROJECT_NUMBER/locations/$REGION/reasoningEngines/$AGENT_ENGINE_ID')
print('Deleted Agent Engine instance.')
"
```
