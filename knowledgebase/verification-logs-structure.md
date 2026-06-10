# Verification Logs Structure & Examples

## Log Directory Structure

```
knowledgebase/
├── logs/                          # Execution logs
│   ├── 2026-04-17/
│   │   ├── healing-session-001.json      # One healing session
│   │   ├── healing-session-002.json
│   │   └── index.json             # Daily summary
│   └── 2026-04-18/
│
├── verification-results/          # Aggregated verification data
│   ├── by-action/
│   │   ├── scale-up-stats.json
│   │   ├── restart-stats.json
│   │   └── delete-pod-stats.json
│   ├── by-namespace/
│   │   ├── default-summary.json
│   │   └── kube-system-summary.json
│   └── by-service/
│       ├── paymentservice-stats.json
│       └── frontend-stats.json
│
└── decisions/                     # Decision tree logs
    ├── 2026-04-17/
    │   ├── paymentservice-xyz-decision.json
    │   └── frontend-abc-decision.json
```

## Individual Healing Session Log

File: `logs/2026-04-17/healing-session-001.json`

```json
{
  "session_id": "heal-20260417-001",
  "timestamp_utc": "2026-04-17T09:30:00Z",
  "sre_user": "devops-team",
  "incident_id": "INC-2026-04-17-001",
  
  "detection": {
    "service_name": "paymentservice",
    "namespace": "default",
    "reason": "Pod not running",
    "confidence": 1.0,
    "detected_at": "2026-04-17T09:20:00Z"
  },
  
  "diagnosis": {
    "root_causes": [
      {
        "rank": 1,
        "cause": "Deployment scaled to 0 replicas",
        "probability": 0.95,
        "evidence": [
          "desired_replicas=0",
          "available_replicas=0",
          "no pods found"
        ]
      }
    ],
    "recommended_actions": [
      "scale-up",
      "check-deployment-config"
    ]
  },
  
  "sre_decision": {
    "action_chosen": "scale-up",
    "target_replicas": 1,
    "reason": "Service critical, needs to be up",
    "decided_at": "2026-04-17T09:30:00Z",
    "sre_notes": "User manually selected scale-up to 1 replica"
  },
  
  "pre_execution_check": {
    "timestamp": "2026-04-17T09:30:00Z",
    "deployment_exists": true,
    "rbac_allowed": true,
    "node_resources_available": true,
    "checks_passed": true,
    "status": "READY_TO_EXECUTE"
  },
  
  "execution": {
    "command": "kubectl scale deployment/paymentservice -n default --replicas=1",
    "executed_at": "2026-04-17T09:30:15Z",
    "duration_ms": 250,
    "exit_code": 0,
    "status": "SUCCESS"
  },
  
  "verification": {
    "started_at": "2026-04-17T09:30:16Z",
    "polls": [
      {
        "poll_number": 1,
        "timestamp": "2026-04-17T09:30:18Z",
        "pod_status": "Pending",
        "ready": false,
        "restarts": 0,
        "endpoints": 0
      },
      {
        "poll_number": 2,
        "timestamp": "2026-04-17T09:30:28Z",
        "pod_status": "Running",
        "ready": true,
        "restarts": 0,
        "endpoints": 1
      },
      {
        "poll_number": 3,
        "timestamp": "2026-04-17T09:30:38Z",
        "pod_status": "Running",
        "ready": true,
        "restarts": 0,
        "endpoints": 1,
        "final": true
      }
    ],
    "final_result": {
      "status": "SUCCESS",
      "verified_at": "2026-04-17T09:30:38Z",
      "total_duration_seconds": 23,
      "checks_passed": [
        "pod_running",
        "pod_ready",
        "endpoint_available",
        "service_responding",
        "metrics_normal"
      ],
      "checks_failed": [],
      "confidence_score": 0.99
    }
  },
  
  "post_action_state": {
    "deployment_replicas_desired": 1,
    "deployment_replicas_ready": 1,
    "pods_running": 1,
    "pod_names": ["paymentservice-895ff658d-8b4ts"],
    "service_endpoints": 1,
    "cpu_usage_m": 2.3,
    "memory_usage_mb": 24,
    "response_time_ms": 45,
    "last_error_events": []
  },
  
  "summary": {
    "incident_resolved": true,
    "service_restored": true,
    "action_outcome": "SUCCESS",
    "action_effectiveness": 1.0,
    "estimated_downtime_prevented_minutes": 5,
    "sre_satisfaction": "resolved"
  }
}
```

## Daily Summary Log

File: `logs/2026-04-17/index.json`

```json
{
  "date": "2026-04-17",
  "total_incidents": 3,
  "total_healing_actions": 3,
  "successful_healings": 3,
  "failed_healings": 0,
  "degraded_healings": 0,
  "average_resolution_time_seconds": 18,
  
  "healing_sessions": [
    {
      "session_id": "heal-20260417-001",
      "service": "paymentservice",
      "action": "scale-up",
      "result": "SUCCESS",
      "duration_seconds": 23
    },
    {
      "session_id": "heal-20260417-002",
      "service": "frontend",
      "action": "restart-deployment",
      "result": "SUCCESS",
      "duration_seconds": 15
    },
    {
      "session_id": "heal-20260417-003",
      "service": "redis-cart",
      "action": "delete-pod",
      "result": "SUCCESS",
      "duration_seconds": 18
    }
  ],
  
  "action_statistics": {
    "scale-up": {
      "count": 1,
      "success_rate": 1.0,
      "avg_time_seconds": 23
    },
    "restart-deployment": {
      "count": 1,
      "success_rate": 1.0,
      "avg_time_seconds": 15
    },
    "delete-pod": {
      "count": 1,
      "success_rate": 1.0,
      "avg_time_seconds": 18
    }
  },
  
  "namespace_statistics": {
    "default": {
      "incidents": 3,
      "success_rate": 1.0
    }
  },
  
  "generated_at": "2026-04-17T23:59:59Z"
}
```

## Action Statistics File

File: `verification-results/by-action/scale-up-stats.json`

```json
{
  "action_type": "scale-up",
  "stats_period": "all_time",
  "last_updated": "2026-04-17T09:35:00Z",
  
  "execution_statistics": {
    "total_executions": 42,
    "successful": 41,
    "failed": 1,
    "success_rate": 0.976,
    "avg_execution_time_ms": 245,
    "min_execution_time_ms": 180,
    "max_execution_time_ms": 350
  },
  
  "verification_statistics": {
    "avg_verification_time_seconds": 20,
    "pod_running_by_5s_percent": 0.88,
    "pod_ready_by_15s_percent": 0.95,
    "endpoints_available_by_20s_percent": 0.98,
    "avg_confidence_score": 0.97
  },
  
  "failure_analysis": {
    "failures": [
      {
        "session_id": "heal-20260410-015",
        "reason": "insufficient_node_resources",
        "node": "worker-2",
        "memory_available": "128Mi",
        "memory_requested": "256Mi"
      }
    ],
    "common_issues": [
      {
        "issue": "ImagePullBackOff after scale-up",
        "occurrences": 2,
        "mitigation": "Verify image registry access"
      }
    ]
  },
  
  "by_service": {
    "paymentservice": {
      "count": 12,
      "success_rate": 1.0,
      "avg_time_seconds": 18
    },
    "frontend": {
      "count": 15,
      "success_rate": 0.93,
      "avg_time_seconds": 22
    },
    "redis-cart": {
      "count": 15,
      "success_rate": 1.0,
      "avg_time_seconds": 15
    }
  }
}
```

## Real-time Verification Output Log

File: `logs/2026-04-17/healing-session-001-verification.log`

```log
[09:30:16] INFO: Starting verification for session heal-20260417-001
[09:30:16] INFO: Target: paymentservice (default namespace)
[09:30:16] INFO: Action: scale-up (desired replicas: 1)
[09:30:16] ===== POLL #1 (T+2s) =====
[09:30:18] INFO: Querying deployment status...
[09:30:18] INFO: Desired: 1, Ready: 0, Updated: 0
[09:30:18] INFO: Querying pod status...
[09:30:18] INFO: Found 1 pod: paymentservice-895ff658d-8b4ts
[09:30:18] INFO: Pod phase: Pending
[09:30:18] DEBUG: Pod events: SuccessfulCreate, Scheduled
[09:30:18] WARNING: Pod not yet running (expected for scale-up)
[09:30:18] ✓ Check: Deployment is scaling
[09:30:18] ✗ Check: Pod running (will recheck)
[09:30:18] ✗ Check: Service endpoint available (will recheck)

[09:30:20] ===== POLL #2 (T+10s) =====
[09:30:28] INFO: Querying deployment status...
[09:30:28] INFO: Desired: 1, Ready: 1, Updated: 1
[09:30:28] INFO: Querying pod status...
[09:30:28] INFO: Found 1 pod: paymentservice-895ff658d-8b4ts
[09:30:28] INFO: Pod phase: Running
[09:30:28] INFO: Pod ready condition: True
[09:30:28] DEBUG: Pod events: Started, Ready
[09:30:28] ✓ Check: Deployment ready
[09:30:28] ✓ Check: Pod running
[09:30:28] ✓ Check: Pod ready
[09:30:28] INFO: Querying service endpoints...
[09:30:28] INFO: Service has 1 endpoint (10.244.1.105:50051)
[09:30:28] ✓ Check: Service endpoint available

[09:30:28] ===== FINAL VERIFICATION =====
[09:30:38] INFO: All critical checks passed
[09:30:38] INFO: Confidence score: 0.99
[09:30:38] SUCCESS: Healing action completed successfully
[09:30:38] Total time: 23 seconds
[09:30:38] Logging result to verification-results...
```

## How to Query These Logs

### Find all scale-up actions
```bash
cat logs/*/healing-session-*.json | jq 'select(.sre_decision.action_chosen=="scale-up")'
```

### Find failed healing actions
```bash
cat logs/*/healing-session-*.json | jq 'select(.verification.final_result.status=="FAILURE")'
```

### Get success rate for paymentservice
```bash
cat verification-results/by-service/paymentservice-stats.json | jq '.success_rate'
```

### Find slowest healing actions (over 60 seconds)
```bash
cat logs/*/healing-session-*.json | jq 'select(.verification.final_result.total_duration_seconds > 60)'
```
