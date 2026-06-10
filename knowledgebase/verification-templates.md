# Verification Checklist & Templates

## Pre-Action Verification Template

Use this when capturing state BEFORE remediation action:

```json
{
  "timestamp": "2026-04-17T09:30:00Z",
  "action_id": "scale-up",
  "target_namespace": "default",
  "target_deployment": "paymentservice",
  "target_pod": "paymentservice-895ff658d-8b4ts",
  
  "pre_state": {
    "deployment": {
      "desired_replicas": 0,
      "ready_replicas": 0,
      "available_replicas": 0,
      "updated_replicas": 0
    },
    "pods": {
      "total": 0,
      "running": 0,
      "pending": 0,
      "failed": 0,
      "names": []
    },
    "events": {
      "warning_count": 0,
      "recent_events": []
    },
    "metrics": {
      "cpu_usage_m": null,
      "memory_usage_mb": null
    },
    "service_health": {
      "endpoints": 0,
      "accessible": false
    }
  }
}
```

## Post-Action Verification Template

Use this when capturing state AFTER remediation action:

```json
{
  "timestamp": "2026-04-17T09:35:00Z",
  "action_executed_at": "2026-04-17T09:30:15Z",
  "action_duration_seconds": 285,
  "action_id": "scale-up",
  "target_namespace": "default",
  "target_deployment": "paymentservice",
  
  "post_state": {
    "deployment": {
      "desired_replicas": 1,
      "ready_replicas": 1,
      "available_replicas": 1,
      "updated_replicas": 1
    },
    "pods": {
      "total": 1,
      "running": 1,
      "pending": 0,
      "failed": 0,
      "names": ["paymentservice-895ff658d-xyz12"],
      "details": [
        {
          "name": "paymentservice-895ff658d-xyz12",
          "status": "Running",
          "ready": true,
          "restart_count": 0,
          "age_seconds": 15
        }
      ]
    },
    "events": {
      "warning_count": 0,
      "recent_events": ["Successfully assigned", "Started container"]
    },
    "metrics": {
      "cpu_usage_m": 2.5,
      "memory_usage_mb": 24
    },
    "service_health": {
      "endpoints": 1,
      "accessible": true,
      "response_time_ms": 45
    }
  },
  
  "verification_result": {
    "status": "SUCCESS",
    "checks_passed": [
      "desired_replicas_matched",
      "pod_running",
      "readiness_probe_passed",
      "service_endpoint_available",
      "metrics_normal"
    ],
    "checks_failed": [],
    "confidence_score": 0.98
  }
}
```

## Success Criteria by Action Type

### Scale-Up Criteria
- ✅ Desired replicas matches requested
- ✅ Ready replicas ≥ desired replicas
- ✅ Pod status = "Running"
- ✅ Pod ready condition = True
- ✅ Service has at least 1 endpoint
- ✅ Service responds to requests within 500ms
- ✅ No OOMKill or CPU throttle events in last 30 seconds
- ✅ Restart count stable (no new restarts)

### Restart Criteria
- ✅ Old pod name removed from cluster
- ✅ New pod created (different hash)
- ✅ New pod status = "Running" within 60 seconds
- ✅ New pod ready condition = True
- ✅ New pod age < 60 seconds
- ✅ No ConfigMap/Secret errors in events
- ✅ Service endpoints remain > 0 (no downtime)

### Delete Pod Criteria
- ✅ Pod removed from `kubectl get pods` output
- ✅ Deployment controller detects missing pod
- ✅ Replacement pod created automatically
- ✅ Replacement pod reaches Running state within 45 seconds
- ✅ Service endpoints never reached zero (if deployment has replicas > 1)
- ✅ No service interruption detected

### Increase Resources Criteria
- ✅ Pod resource limits updated in spec
- ✅ Pod restarted (age < 60 seconds)
- ✅ New pod status = "Running"
- ✅ No new OOMKill events after action
- ✅ Memory usage < new limit
- ✅ CPU usage < new limit

## Failure Criteria (Action Did Not Work)

- ❌ Pod stuck in Pending after 60 seconds
- ❌ Unable to pull image (ImagePullBackOff)
- ❌ ReadinessProbe fails continuously
- ❌ Pod immediately crashes (CrashLoopBackOff within 30 seconds)
- ❌ Service remains unreachable
- ❌ Resource requests exceed node capacity
- ❌ RBAC permissions denied

## Verification Polling Strategy

```
For each verification:
  
  Poll #1 at T+2 seconds
    → Check basic state (running, pending?)
    
  Poll #2 at T+5 seconds
    → Check ready condition
    
  Poll #3 at T+10 seconds
    → Check readiness probes
    
  Poll #4 at T+20 seconds
    → Check service endpoints
    
  Poll #5 at T+30 seconds
    → Final health check
    
  If pod not Running by T+30s → Mark as FAILURE
  If Running but not Ready by T+30s → Mark as DEGRADED
  If all checks pass by T+30s → Mark as SUCCESS
```
