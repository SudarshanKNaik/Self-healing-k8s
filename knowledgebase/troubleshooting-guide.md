# Troubleshooting Guide & Verification Scenarios

## Common Healing Failures & Verification Steps

### Scenario 1: Scale-Up Fails - Pod Stuck in Pending

**Problem**: You chose "scale-up" action but pod remains in Pending state after 30 seconds.

**How to Verify the Issue**:
```bash
# Check deployment status
kubectl get deployment paymentservice -n default
# Output should show: READY 1/1, but if READY 0/1, something's wrong

# Check pod details
kubectl describe pod paymentservice-895ff658d-8b4ts -n default
# Look in Events section for:
#   - FailedScheduling: Node resources unavailable
#   - PodSchedulingFailure: Affinity/taints issue
```

**Verification Log Indicators**:
```json
{
  "poll_3": {
    "pod_status": "Pending",
    "ready": false,
    "events": ["FailedScheduling: insufficient memory"]
  },
  "verification_result": {
    "status": "FAILURE",
    "reason": "pod_failed_to_schedule"
  }
}
```

**Next Actions**:
- [ ] Check node capacity: `kubectl top nodes`
- [ ] Check pod resource requests
- [ ] Check node affinity rules
- [ ] Manual fix: `kubectl patch deployment paymentservice -n default -p '{"spec":{"template":{"spec":{"nodeSelector":null}}}}'`

---

### Scenario 2: Restart Action - Pod Crashes Immediately

**Problem**: You chose "restart-deployment" but pod enters CrashLoopBackOff.

**How to Verify the Issue**:
```bash
# Check pod logs
kubectl logs paymentservice-895ff658d-xyz12 -n default
# Look for:
#   - Panic errors
#   - Configuration errors  
#   - Missing dependencies

# Check previous logs (from before crash)
kubectl logs paymentservice-895ff658d-xyz12 -n default --previous

# Check pod events
kubectl describe pod paymentservice-895ff658d-xyz12 -n default
# Look for:
#   - CrashLoopBackOff: Back-off restarting failed container
#   - Error: ImagePullBackOff
```

**Verification Log Indicators**:
```json
{
  "polls": [
    {
      "poll_number": 1,
      "pod_status": "Running",
      "restart_count": 0
    },
    {
      "poll_number": 2,
      "pod_status": "CrashLoopBackOff",
      "restart_count": 1,
      "last_state": {
        "terminated": {
          "reason": "Error",
          "exit_code": 1
        }
      }
    }
  ],
  "verification_result": {
    "status": "FAILURE",
    "reason": "pod_crash_loop_detected"
  }
}
```

**Next Actions**:
- [ ] Review application logs
- [ ] Check ConfigMap/Secret mounts
- [ ] Verify environment variables
- [ ] Check database connectivity
- [ ] Rollback to previous image: `kubectl rollout undo deployment/paymentservice -n default`

---

### Scenario 3: Delete Pod - Replacement Not Created

**Problem**: You chose "delete-pod" but no replacement pod created (deployment was scaled to 0).

**How to Verify the Issue**:
```bash
# Check deployment replica count
kubectl get deployment paymentservice -n default
# Output: READY 0/1 or READY 0/0 (bad!)

# Check if deployment exists
kubectl get deployment paymentservice -n default -o json | jq '.spec.replicas'
# Should return 1 or higher, if returns 0 that's the problem

# Check events
kubectl get events -n default --sort-by='.lastTimestamp'
# Look for "Killing pod" but no "Created" events after
```

**Verification Log Indicators**:
```json
{
  "execution": {
    "command": "kubectl delete pod paymentservice-895ff658d-8b4ts -n default",
    "status": "SUCCESS"
  },
  "verification": {
    "polls": [
      {
        "poll_number": 2,
        "total_pods": 0,
        "pods_running": 0,
        "pods_pending": 0
      }
    ],
    "verification_result": {
      "status": "FAILURE",
      "reason": "no_replacement_pod_created",
      "note": "Deployment replica count is 0"
    }
  }
}
```

**Next Actions**:
- [ ] Scale deployment to desired replicas: `kubectl scale deployment/paymentservice -n default --replicas=1`
- [ ] Verify scaling occurred in next verification check
- [ ] Check deployment spec for issues

---

### Scenario 4: Scale-Up Success But Service Unreachable

**Problem**: Pod is running and ready, but service still doesn't respond.

**How to Verify the Issue**:
```bash
# Check if pod has service selector
kubectl get pod paymentservice-895ff658d-xyz12 -n default -o json | jq '.metadata.labels'

# Check service selector
kubectl get service paymentservice -n default -o json | jq '.spec.selector'

# They should match! If not, pod won't be in service endpoints

# Check service endpoints
kubectl get endpoints paymentservice -n default
# Output should show: ENDPOINTS (IP:PORT), e.g., 10.244.1.105:50051

# Test connectivity
kubectl run -it --rm debug --image=busybox --restart=Never -- sh
# Inside pod: nslookup paymentservice.default.svc.cluster.local
# Inside pod: wget -O- paymentservice.default:50051
```

**Verification Log Indicators**:
```json
{
  "verification": {
    "polls": [
      {
        "poll_number": 2,
        "pod_status": "Running",
        "pod_ready": true,
        "pod_labels": {"app": "paymentservice"},
        "service_endpoints": 0,
        "service_selector": {"app": "paymentservice", "version": "v2"}
      }
    ],
    "verification_result": {
      "status": "FAILURE", 
      "reason": "pod_not_in_service_endpoints",
      "mismatch": "pod_missing_label_version=v2"
    }
  }
}
```

**Next Actions**:
- [ ] Update pod labels: `kubectl patch pod paymentservice-895ff658d-xyz12 -n default -p '{"metadata":{"labels":{"version":"v2"}}}'`
- [ ] Verify service sees endpoint: `kubectl get endpoints paymentservice -n default`
- [ ] Rerun verification

---

## Verification Checklist per Action

### For SCALE-UP Actions
- [ ] Desired replicas increased
- [ ] Ready replicas matches desired within 30s
- [ ] Pod transitions Pending → Running
- [ ] Pod ready condition = True
- [ ] Service endpoints > 0
- [ ] Service responds within 500ms
- [ ] No resource request errors
- [ ] Metrics show CPU < limit
- [ ] Metrics show Memory < limit
- [ ] No restart events after scaling

### For RESTART Actions
- [ ] Old pod terminated
- [ ] New pod created (different hash in name)
- [ ] New pod Running within 45s
- [ ] New pod ready condition = True
- [ ] Service downtime < 5 seconds (if multi-replica)
- [ ] No ConfigMap/Secret errors
- [ ] Restart counter incremented
- [ ] Application logs show normal start
- [ ] Service endpoints maintained

### For DELETE-POD Actions  
- [ ] Target pod removed immediately
- [ ] Replacement created automatically
- [ ] Replacement Running within 45s
- [ ] Replacement ready condition = True
- [ ] Service endpoints stayed > 0 during replacement
- [ ] No errors in pod events
- [ ] New pod has age < 60 seconds

### For INCREASE-RESOURCES Actions
- [ ] Resource limits updated in deployment spec
- [ ] Pod restarted (age reset)
- [ ] New pod Running within 60s
- [ ] Memory usage reported < new limit
- [ ] CPU usage reported < new limit
- [ ] No OOMKill events after action
- [ ] No CPU throttle events after action
- [ ] Application performance improved

---

## How to Enable Verification Logging

### 1. Modify Healing Page Component
In `h24-app/src/app/dashboard/healing/page.tsx`:

```typescript
// After remediation action completes:
const verificationLog = {
  session_id: `heal-${new Date().toISOString()}`,
  action_chosen: selectedStrategy,
  target_pod: targetName,
  timestamp_utc: new Date().toISOString(),
  verification_results: polls,  // Array of poll objects
  final_status: success ? "SUCCESS" : "FAILURE"
};

// Save to backend
await fetch('/api/healing/log-verification', {
  method: 'POST',
  body: JSON.stringify(verificationLog)
});
```

### 2. Create API Endpoint
Create: `h24-app/src/app/api/healing/log-verification/route.ts`

```typescript
export async function POST(request: Request) {
  const log = await request.json();
  
  // Save to file or database
  const logsDir = `./knowledgebase/logs/${new Date().toISOString().split('T')[0]}/`;
  const filename = `${logsDir}healing-session-${log.session_id}.json`;
  
  // Write file
  await writeFileSync(filename, JSON.stringify(log, null, 2));
  
  // Update stats
  await updateActionStats(log.action_chosen, log.final_status);
  
  return Response.json({ saved: true });
}
```

### 3. Query and Review Logs

```bash
# Find all healing sessions
ls knowledgebase/logs/*/healing-session-*.json

# View specific session
cat knowledgebase/logs/2026-04-17/healing-session-001.json | jq '.'

# Find all failures
grep -r "FAILURE" knowledgebase/logs/*/

# Generate report
python3 scripts/analysis-healing-logs.py knowledgebase/logs/
```
