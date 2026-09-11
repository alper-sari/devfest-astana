<!--markdownlint-disable MD024 MD033 MD036 MD041 -->
<walkthrough-metadata>
  <meta name="title" content="Not Risky Anymore: Enforcing Native IAM Boundaries for Production AI Agents" />
  <meta name="description" content="Learn how to build a DevOps AI agent with Gemini 3.8 Flash, deploy to Vertex AI Agent Engine with Zero Service Accounts, and manage permissions using native SPIFFE Agent Identity." />
  <meta name="keywords" content="Gemini, Google Cloud, Vertex AI, Agent Engine, ADK, SPIFFE, Agent Identity, Zero Trust, DevOps" />
</walkthrough-metadata>

# Not Risky Anymore: Enforcing Native IAM Boundaries for Production AI Agents

## Let's get started

![Tutorial header image](https://raw.githubusercontent.com/NucleusEngineering/serverless/main/.images/run.jpg)

Welcome to **DevFest Astana**! In this hands-on workshop, you will build and deploy an autonomous **DevOps & SRE Agent** using Google Cloud's **Agent Development Kit (ADK)** and **Gemini 3.8 Flash**.

Crucially, we will **NOT** use traditional Service Account keys or assign broad Service Account roles. Instead, we deploy to Google's **Vertex AI Agent Engine** using **Native SPIFFE Workload Identity (`AGENT_IDENTITY`)**.

You will experience real-world **Zero Trust** security:
1. Deploy the agent with **zero permissions** and observe an immediate **`403 Forbidden`** error in the Vertex AI Console Playground.
2. Grant read permissions **strictly** to the agent's cryptographic SPIFFE identity.
3. Watch the agent instantly succeed in discovering your cloud infrastructure!

<walkthrough-tutorial-difficulty difficulty="2"></walkthrough-tutorial-difficulty>

Estimated time:
<walkthrough-tutorial-duration duration="30"></walkthrough-tutorial-duration>

To get started, click **Start**.

## Project Setup

Make sure your Google Cloud project is selected with billing enabled.

<walkthrough-project-setup billing="true"></walkthrough-project-setup>

Enable the required Google Cloud APIs for Vertex AI, Cloud Storage, Cloud Run, and Cloud Build:

<walkthrough-enable-apis apis="aiplatform.googleapis.com,run.googleapis.com,cloudbuild.googleapis.com,storage.googleapis.com"></walkthrough-enable-apis>

Set up your project environment variables in Cloud Shell:

```bash
export PROJECT_ID=$(gcloud config get-value project)
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
export REGION="us-central1"

echo "Project ID: $PROJECT_ID"
echo "Project Number: $PROJECT_NUMBER"
echo "Region: $REGION"
```

## Explore the DevOps Agent Code

Make sure you are in the repository directory and explore the agent structure:

```bash
cd ~/cloudshell_open/devfest-astana
git pull
ls -la devops_agent
```

The agent is organized into three primary files:
- <walkthrough-editor-open-file filePath="devops_agent/agent.py">`devops_agent/agent.py`</walkthrough-editor-open-file>: Defines the ADK `Agent` powered by **Gemini 3.8 Flash** with system instructions.
- <walkthrough-editor-open-file filePath="devops_agent/tools.py">`devops_agent/tools.py`</walkthrough-editor-open-file>: Implements DevOps observation tools (Cloud Storage audits, Cloud Run inspection, and SPIFFE identity self-verification).
- <walkthrough-editor-open-file filePath="devops_agent/requirements.txt">`devops_agent/requirements.txt`</walkthrough-editor-open-file>: Dependencies (`google-adk`, `google-cloud-aiplatform[agent_engines]`, `google-cloud-storage`, `google-cloud-run`).

Let's inspect the agent definition:

```bash
cat devops_agent/agent.py
```

Notice that the agent connects to Vertex AI using `gemini-3.8-flash` on the global endpoint, and registers tools for infrastructure observation without embedding any credentials or keys.

## Install ADK CLI

We install the Google Agent Development Kit CLI (`adk`) to deploy our agent package to Vertex AI:

```bash
python3 -m pip install --quiet --upgrade uv
uv pip install --system --quiet google-adk "google-cloud-aiplatform[adk,agent_engines]"
```

Verify that the ADK CLI is ready:

```bash
adk --help
```

## Provision Agent Engine with Native `AGENT_IDENTITY`

In traditional setups, workloads inherit a project Service Account. In Google Cloud's modern Agent architecture, we provision a dedicated **`AGENT_IDENTITY` (SPIFFE)**.

Run the following command to provision a new Agent Engine instance configured with native `AGENT_IDENTITY`:

```bash
git pull
bash scripts/create_engine.sh
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

Notice that there is **NO** service account attached! The agent's identity is a cryptographically attested SPIFFE URI under Google's system trust domain.

## Deploy Agent Source Code

Now let's package and deploy our DevOps agent code into the newly created Agent Engine instance using ADK:

```bash
cd ~/cloudshell_open/devfest-astana
export AGENT_ENGINE_ID=$(cat .engine_id)

adk deploy agent_engine \
  --project=$PROJECT_ID \
  --region=$REGION \
  --agent_engine_id=$AGENT_ENGINE_ID \
  devops_agent
```

Cloud Build will package the container and deploy it to the serverless Reasoning Engine runtime. This takes approximately 2–3 minutes.

When finished, proceed to the next step to test the agent in the Google Cloud Console UI!

## Zero Trust Test: 403 Forbidden in UI

Generate your direct link to the **Vertex AI Agent Engine Console Playground**:

```bash
export AGENT_ENGINE_ID=$(cat .engine_id)
echo "Open Agent Playground in Google Cloud Console:"
echo "https://console.cloud.google.com/vertex-ai/agents/agent-engines/locations/$REGION/agent-engines/$AGENT_ENGINE_ID/playground?project=$PROJECT_ID"
```

### Action in Playground UI:
1. Click the URL printed above to open the **Playground** tab in your browser.
2. In the chat box at the bottom, type the following prompt and press Enter:

```text
List the storage buckets in our project
```

3. **Observe the result:**
   The agent executes the `list_storage_buckets` tool and immediately receives a **`403 Forbidden`** error!
   
   > `403 GET ... Caller does not have storage.buckets.list access to the Google Cloud project.`

**Why did this happen?**
Because this agent uses **Native `AGENT_IDENTITY`**, it does not inherit broad default service account permissions. It starts with **Zero Permissions**!

## Grant Access via SPIFFE Identity

Now let's grant the agent read access. Instead of granting permissions to a user or service account, we bind **`roles/viewer`** directly to the agent's **cryptographic SPIFFE identity**:

Run this command in Cloud Shell:

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="principalSet://agents.global.proj-$PROJECT_NUMBER.system.id.goog/attribute.platformContainer/aiplatform/projects/$PROJECT_NUMBER" \
  --role="roles/viewer"
```

Notice:
- No service account keys were generated or downloaded.
- No static credentials exist in our code or container.
- Permissions are scoped strictly to the `principalSet://agents.global...` identity!

## Live Verification: Success in UI!

Switch back to your **Vertex AI Agent Engine Playground** browser tab.

Send the exact same prompt again:

```text
List the storage buckets in our project and verify your SPIFFE identity
```

### Observe the Result:
Now that the SPIFFE principal has `roles/viewer`, the agent immediately succeeds!

You will see:
1. **SPIFFE Identity Verification Table**: Showing the agent's trust domain and cryptographic identity.
2. **Storage Buckets Overview Table**: Listing all Cloud Storage buckets in your project with their location and security posture (Uniform Bucket-Level Access).

## Optional: Prove Zero Trust by Revoking Access

Want to prove to your audience that access is 100% controlled by this SPIFFE binding?

Remove the role from the SPIFFE principal in Cloud Shell:

```bash
gcloud projects remove-iam-policy-binding $PROJECT_ID \
  --member="principalSet://agents.global.proj-$PROJECT_NUMBER.system.id.goog/attribute.platformContainer/aiplatform/projects/$PROJECT_NUMBER" \
  --role="roles/viewer"
```

Now switch back to the **Playground UI** and ask:

```text
List the storage buckets in our project
```

The agent will **immediately return 403 Forbidden again**!

This unequivocally proves:
- **Permission present** ➡️ Agent can observe infrastructure.
- **Permission removed** ➡️ Zero ambient access, zero credential leakage.

## Congratulations!

<walkthrough-conclusion-trophy></walkthrough-conclusion-trophy>

You have successfully built, deployed, and secured a production-grade DevOps Agent on Google Cloud with Native SPIFFE Agent Identity!

### What you learned:
* How to use Google's **Agent Development Kit (ADK)** with **Gemini 3.8 Flash**.
* The paradigm shift from static Service Accounts to **Native SPIFFE `AGENT_IDENTITY`**.
* Enforcing **Zero Trust**: Seeing live 403 Forbidden errors until permissions are explicitly granted.
* Granting and revoking granular IAM roles directly to `principalSet://agents.global...` principals.

---

### 👨‍💻 Workshop Author
**Prepared by:** **Alper Sarı**  
*Google Developer Expert (GDE) on Google Cloud*  
*DevFest Astana*

<walkthrough-inline-feedback></walkthrough-inline-feedback>

## Clean Up

To avoid ongoing charges on your project, you can delete the deployed Reasoning Engine instance:

```bash
bash scripts/delete_engine.sh
```
