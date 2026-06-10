# Quick Reference & Decision Tree

## Quick Reference - What Verification Outputs Mean

| Status | Meaning | Action |
|--------|---------|--------|
| `SUCCESS` | Pod running, ready, endpoint available | ✅ Incident resolved |
| `DEGRADED` | Pod running but not all checks pass | ⚠️ Monitor closely, may need retry |
| `FAILURE` | Pod not running or service unreachable | ❌ Rollback and investigate |
| `PENDING` | Verification in progress | ⏳ Wait for completion |

| Verification Check | What It Means | Critical? |
|-------------------|---------------|-----------|
| `pod_running` | Pod phase = Running | YES |
| `pod_ready` | Readiness probe passed | YES |
| `endpoint_available` | Service has endpoint pointing to pod | YES |
| `service_responding` | HTTP/gRPC request succeeded | YES |
| `metrics_normal` | CPU < limit, Memory < limit | NO (warning if high) |
| `no_crashes` | Restart count hasn't increased | YES |
| `no_error_events` | No ImagePullBackOff, OOMKill, etc. | YES |

## Decision Tree for SRE Actions

```
┌─────────────────────────────────────────┐
│  Pod/Service Issue Detected             │
└────────────┬────────────────────────────┘
             │
             ▼
   ┌─────────────────────────┐
   │ What's the pod status?  │
   └────┬────────┬────────┬──┘
        │        │        │
   Pending  Running   Failed/CrashLoop
        │        │        │
        ▼        ▼        ▼
   ┌────────┐ ┌──────┐ ┌─────────────────┐
   │ Scale  │ │Check │ │ Restart or      │
   │ Up?    │ │Ready?│ │ Delete Pod?     │
   └────┬───┘ └──┬───┘ └────────┬────────┘
        │        │              │
   YES │        │NO             │
        │        ▼              ▼
        │    ┌────────────────────────┐
        │    │ Increase CPU/Memory?   │
        │    │ Check Logs for errors? │
        │    └────────────────────────┘
        │
        ▼
   === ACTION CHOSEN ===
        │
   ┌────┴────────────────────────────┐
   │ Pre-execution verification      │
   │ ✓ RBAC allowed                  │
   │ ✓ Resources available           │
   │ ✓ No quota exceeded             │
   └────┬────────────────────────────┘
        │
        ▼
   === EXECUTE ===
   kubectl [action command]
        │
        ▼
   === VERIFY LOOP (every 2 seconds, max 30 seconds) ===
   
   poll_1 (T+2):  Pod Pending/Creating?      → Continue polling
   poll_2 (T+10): Pod Running?                 → Check ready
   poll_3 (T+20): Pod Ready + Endpoint?        → Check service
   poll_4 (T+30): Service responding?          → Check logs
        │
   ┌────┴──────────────────────┐
   │  All checks passed?        │
   │  YES        NO             │
   ▼            ▼               
SUCCESS      FAILURE
  │             │
  ▼             ▼
✅ Log       ❌ Log
  | result    | result
  |           |→ Add to failure
  |              troubleshooting
  |              queue
  ▼
Update stats
Update dashboards
Send notifications
```

## Verification Output Location Map

When decision made → Where verification happens → Where logs stored:

```
HEALING PAGE (h24-app/src/app/dashboard/healing/page.tsx)
    │
    ├─ runHealing() called
    │   │
    │   ├─ Pre-execution checks
    │   │   └── Logs to: console (dev) / monitoring (prod)
    │   │
    │   ├─ Execute kubectl command
    │   │   └── Logs to: api/healing/stream (stdout)
    │   │
    │   ├─ startVerificationPolling() called
    │   │   │
    │   │   ├─ Poll #1: GET /api/dashboard/pods
    │   │   │   └── Returns: pod status, ready, age
    │   │   │
    │   │   ├─ Poll #2: GET /api/dashboard/pods  
    │   │   │   └── Returns: ready condition, endpoints
    │   │   │
    │   │   ├─ Poll #3: GET /api/dashboard/pods
    │   │   │   └── Returns: service response check
    │   │   │
    │   │   └─ Final Result:
    │   │       └── Logs to: /api/healing/log-verification
    │   │
    │   └─ Save verification results
    │       └── storage location: 
    │           knowledgebase/logs/{date}/healing-session-{id}.json
    │
    └─ Post-action UI update
        ├── Show SUCCESS/FAILURE badge
        ├── Show verification timeline
        └── Store in localStorage + backend
```

## Expected Verification Timeline

### Scale-Up Action
```
T+0s:   Command executed
T+2s:   Poll #1: Pod should be Pending/Creating
T+10s:  Poll #2: Pod should be Running
T+15s:  Pod should be Ready
T+20s:  Poll #3: Endpoints should appear
T+25s:  Service should be responding
T+30s:  Final check + log result

EXPECTED TOTAL: ~23 seconds (from command to success)
```

### Restart Action
```
T+0s:   Command executed (rollout restart)
T+2s:   Poll #1: Old pod Terminating, new pod Pending
T+8s:   Poll #2: New pod should be Running
T+15s:  New pod should be Ready
T+20s:  Endpoints updated
T+30s:  Final check + log result

EXPECTED TOTAL: ~18 seconds (from command to success)
```

### Delete Pod Action
```
T+0s:   Command executed
T+2s:   Poll #1: Pod being deleted
T+5s:   Poll #2: Pod gone, replacement Pending
T+15s:  Poll #3: Replacement Running & Ready
T+20s:  Endpoints updated
T+30s:  Final check + log result

EXPECTED TOTAL: ~20 seconds (from command to success)
```

## Verification Log JSON Schema

```json
{
  "required_fields": [
    "session_id",
    "timestamp_utc",
    "sre_user",
    "action_chosen",
    "target_namespace",
    "target_deployment",
    "execution.status",
    "execution.exit_code",
    "verification.started_at",
    "verification.polls[].timestamp",
    "verification.polls[].pod_status",
    "verification.polls[].ready",
    "verification.final_result.status",
    "verification.final_result.confidence_score"
  ],
  
  "optional_fields": [
    "incident_id",
    "sre_notes",
    "pre_state.*",
    "post_state.*",
    "diagnosis.*"
  ],
  
  "valid_status_values": [
    "SUCCESS",
    "FAILURE",
    "DEGRADED",
    "PENDING"
  ],
  
  "valid_action_types": [
    "scale-up",
    "restart-deployment",
    "delete-pod",
    "increase-resources",
    "check-logs"
  ]
}
```

## How to Find Specific Healing Outcomes

### Find all successful scale-ups
```bash
grep -r "scale-up" knowledgebase/ | grep "SUCCESS"
```

### Find all failures in namespace
```bash
jq 'select(.target_namespace=="default" and .verification.final_result.status=="FAILURE")' \
  knowledgebase/logs/*/*  session*.json
```

### Get success rate by action
```bash
for action in scale-up restart-deployment delete-pod; do
  total=$(grep -c "\"action_chosen\": \"$action\"" knowledgebase/logs/*/*healing*.json)
  success=$(grep -c "\"action_chosen\": \"$action\"" knowledgebase/logs/*/*healing*.json | grep SUCCESS)
  echo "$action: $success/$total"
done
```

### Find slowest healing actions
```bash
jq 'sort_by(.verification.final_result.total_duration_seconds) | reverse | .[] | 
    {action: .sre_decision.action_chosen, duration: .verification.final_result.total_duration_seconds}' \
  knowledgebase/logs/*/*healing*.json
```

### Generate daily report
```bash
python3 << 'EOF'
import json
import glob
from datetime import datetime

logs = glob.glob('knowledgebase/logs/*/healing-session-*.json')
results = {"total": 0, "success": 0, "failure": 0, "actions": {}}

for log_file in logs:
    with open(log_file) as f:
        session = json.load(f)
        results["total"] += 1
        
        status = session["verification"]["final_result"]["status"]
        if status == "SUCCESS":
            results["success"] += 1
        elif status == "FAILURE":
            results["failure"] += 1
            
        action = session["sre_decision"]["action_chosen"]
        if action not in results["actions"]:
            results["actions"][action] = {"total": 0, "success": 0}
        results["actions"][action]["total"] += 1
        if status == "SUCCESS":
            results["actions"][action]["success"] += 1

print(f"Total: {results['total']}")
print(f"Success: {results['success']} ({results['success']/results['total']*100:.1f}%)")
print(f"Failure: {results['failure']}")

for action, stats in results["actions"].items():
    rate = stats["success"] / stats["total"] * 100
    print(f"{action}: {stats['success']}/{stats['total']} ({rate:.1f}%)")
EOF
```
