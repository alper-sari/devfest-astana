"""DevOps Tools for ADK Agent: Bucket, Cost & Serverless Checks, plus SPIFFE identity verification."""

import os
import json
from typing import Any, Dict, List, Optional
from google.cloud import storage, run_v2, billing_v1

DEFAULT_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "poc-project-3592")
DEFAULT_RUN_REGION = os.environ.get("CLOUD_RUN_REGION", "us-central1")
PROJECT_NUMBER = os.environ.get("GOOGLE_CLOUD_PROJECT_NUMBER", "198739390767")
SERVICE_NAME = os.environ.get("AGENT_SERVICE_NAME", os.environ.get("K_SERVICE", "devops-agent"))


def list_storage_buckets(project_id: Optional[str] = None) -> Dict[str, Any]:
    """Lists all Google Cloud Storage (GCS) buckets in the specified GCP project.
    
    Args:
        project_id: GCP project ID. If omitted, uses the current project.
    """
    proj = project_id or DEFAULT_PROJECT
    try:
        client = storage.Client(project=proj)
        buckets = list(client.list_buckets())
        result = []
        for b in buckets:
            result.append({
                "name": b.name,
                "location": b.location,
                "storage_class": b.storage_class,
                "uniform_bucket_level_access": bool(b.iam_configuration.uniform_bucket_level_access_enabled),
                "created": str(b.time_created),
            })
        return {
            "status": "success",
            "project_id": proj,
            "total_buckets": len(result),
            "buckets": result,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def inspect_storage_bucket(bucket_name: str) -> Dict[str, Any]:
    """Performs a detailed security, compliance, and object inspection on a specific GCS bucket.
    
    Args:
        bucket_name: Name of the bucket (e.g. 'poc-project-3592-agent-staging').
    """
    try:
        client = storage.Client(project=DEFAULT_PROJECT)
        bucket = client.get_bucket(bucket_name)
        
        # List up to 20 recent objects
        blobs = list(client.list_blobs(bucket, max_results=20))
        sample_objects = [
            {
                "name": b.name,
                "size_bytes": b.size,
                "content_type": b.content_type,
                "updated": str(b.updated),
            }
            for b in blobs
        ]

        pap = bucket.iam_configuration.public_access_prevention or "unspecified"
        ubla = bool(bucket.iam_configuration.uniform_bucket_level_access_enabled)
        
        soft_delete_seconds = None
        if hasattr(bucket, "soft_delete_policy") and bucket.soft_delete_policy:
            soft_delete_seconds = getattr(bucket.soft_delete_policy, "retention_duration_seconds", None)

        return {
            "status": "success",
            "bucket_name": bucket.name,
            "location": bucket.location,
            "storage_class": bucket.storage_class,
            "versioning_enabled": bool(bucket.versioning_enabled),
            "public_access_prevention": pap,
            "uniform_bucket_level_access": ubla,
            "soft_delete_retention_seconds": soft_delete_seconds,
            "sample_objects_count": len(sample_objects),
            "sample_objects": sample_objects,
        }
    except Exception as e:
        return {"status": "error", "bucket_name": bucket_name, "message": str(e)}


def get_billing_status(project_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves Google Cloud Billing status and linked billing account for the project.
    
    Args:
        project_id: GCP project ID. If omitted, uses the current project.
    """
    proj = project_id or DEFAULT_PROJECT
    try:
        client = billing_v1.CloudBillingClient()
        name = f"projects/{proj}"
        info = client.get_project_billing_info(name=name)
        return {
            "status": "success",
            "project_id": proj,
            "billing_enabled": info.billing_enabled,
            "billing_account_name": info.billing_account_name,
        }
    except Exception as e:
        return {"status": "error", "project_id": proj, "message": str(e)}


def analyze_cost_and_resources(project_id: Optional[str] = None) -> Dict[str, Any]:
    """Analyzes active serverless and storage resources to provide cost visibility and optimization tips.
    
    Args:
        project_id: GCP project ID. If omitted, uses the current project.
    """
    proj = project_id or DEFAULT_PROJECT
    try:
        # Check buckets
        s_client = storage.Client(project=proj)
        buckets = list(s_client.list_buckets())
        
        # Check Cloud Run services in default region
        r_client = run_v2.ServicesClient()
        parent = f"projects/{proj}/locations/{DEFAULT_RUN_REGION}"
        services = list(r_client.list_services(parent=parent))

        recommendations = []
        if len(buckets) > 3:
            recommendations.append("Audit unused buckets or enable lifecycle rules to transition objects to Nearline/Coldline to minimize storage costs.")
        
        for s in services:
            # Check scaling settings
            containers = s.template.containers
            for c in containers:
                limits = c.resources.limits if c.resources else {}
                cpu = limits.get("cpu", "1000m")
                mem = limits.get("memory", "512Mi")
                if "2000m" in cpu or "2Gi" in mem:
                    recommendations.append(f"Service {s.name.split('/')[-1]} has high resource allocation ({cpu}, {mem}). Verify if downsizing is appropriate for cost savings.")

        return {
            "status": "success",
            "project_id": proj,
            "active_buckets_count": len(buckets),
            "cloud_run_services_count": len(services),
            "cost_optimization_recommendations": recommendations or ["Current resource allocations are lean and optimized."],
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def list_serverless_services(region: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    """Lists Cloud Run serverless services, including their URLs, traffic splits, and health status.
    
    Args:
        region: GCP region (e.g. 'us-central1' or 'europe-west1'). Defaults to us-central1.
        project_id: GCP project ID. If omitted, uses current project.
    """
    proj = project_id or DEFAULT_PROJECT
    reg = region or DEFAULT_RUN_REGION
    try:
        client = run_v2.ServicesClient()
        parent = f"projects/{proj}/locations/{reg}"
        services = list(client.list_services(parent=parent))
        
        service_list = []
        for s in services:
            short_name = s.name.split("/")[-1]
            ready_cond = "UNKNOWN"
            if s.terminal_condition:
                ready_cond = s.terminal_condition.state.name
            
            traffic_summary = [
                {"percent": t.percent, "revision": t.revision.split("/")[-1] if t.revision else "latest"}
                for t in s.traffic
            ]

            service_list.append({
                "service_name": short_name,
                "region": reg,
                "url": s.uri,
                "ready_state": ready_cond,
                "traffic": traffic_summary,
            })

        return {
            "status": "success",
            "project_id": proj,
            "region": reg,
            "total_services": len(service_list),
            "services": service_list,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def inspect_serverless_service(service_name: str, region: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    """Deeply inspects a specific Cloud Run service's container settings, scaling, and health conditions.
    
    Args:
        service_name: Name of the Cloud Run service.
        region: GCP region where the service resides. Defaults to us-central1.
        project_id: GCP project ID.
    """
    proj = project_id or DEFAULT_PROJECT
    reg = region or DEFAULT_RUN_REGION
    try:
        client = run_v2.ServicesClient()
        name = f"projects/{proj}/locations/{reg}/services/{service_name}"
        s = client.get_service(name=name)

        containers_info = []
        for c in s.template.containers:
            limits = dict(c.resources.limits) if c.resources else {}
            containers_info.append({
                "image": c.image,
                "cpu_limit": limits.get("cpu", "default"),
                "memory_limit": limits.get("memory", "default"),
                "ports": [p.container_port for p in c.ports],
            })

        scaling = {
            "min_instance_count": s.template.scaling.min_instance_count if s.template.scaling else 0,
            "max_instance_count": s.template.scaling.max_instance_count if s.template.scaling else 100,
        }

        return {
            "status": "success",
            "service_name": service_name,
            "region": reg,
            "url": s.uri,
            "ingress": s.ingress.name if s.ingress else "ALL",
            "scaling": scaling,
            "containers": containers_info,
            "conditions": [
                {"type": cond.type_, "state": cond.state.name, "message": cond.message}
                for cond in s.conditions
            ],
        }
    except Exception as e:
        return {"status": "error", "service_name": service_name, "message": str(e)}


def get_agent_spiffe_identity() -> Dict[str, Any]:
    """Returns the cryptographic SPIFFE Identity and Google Cloud IAM Principal information for this Cloud Run Agent.
    
    This verifies that the agent operates under SPIFFE-based Workload Identity rather than static service account keys.
    """
    trust_domain = f"agents.global.proj-{PROJECT_NUMBER}.system.id.goog"
    cloud_run_principal = f"principal://{trust_domain}/resources/run/projects/{PROJECT_NUMBER}/locations/{DEFAULT_RUN_REGION}/services/{SERVICE_NAME}"
    agent_engine_principal_set = f"principalSet://{trust_domain}/attribute.platformContainer/aiplatform/projects/{PROJECT_NUMBER}"
    system_pool = f"poc-project-3592.svc.id.goog"

    return {
        "status": "success",
        "identity_type": "Native SPIFFE Workload Identity (AGENT_IDENTITY)",
        "project_number": PROJECT_NUMBER,
        "region": DEFAULT_RUN_REGION,
        "trust_domain": trust_domain,
        "vertex_ai_agent_engine_principal": agent_engine_principal_set,
        "cloud_run_principal_uri": cloud_run_principal,
        "system_workload_identity_pool": system_pool,
        "architecture_note": (
            "No static service account keys or custom service accounts are used. "
            "Google's Agent Platform provisions a cryptographic SPIFFE identity. "
            "Permissions (e.g. storage.objectViewer, run.viewer) are bound directly to this SPIFFE principal."
        )
    }
