# Remediation Actions Reference

This file documents all available remediation actions and their expected outcomes.

## Available Actions

### 1. Scale Deployment Up
- **Action ID**: `scale-up`
- **Command**: `kubectl scale deployment/{name} -n {namespace} --replicas={target}`
- **When to use**: Pod/service is not running, insufficient replicas
- **Pre-condition**: Deployment exists with `replicas=0` or insufficient count
- **Expected outcome**: Pods transition from Pending → Running
- **Verification**: 
  - Check pod status becomes "Running"
  - Check readiness probes pass
  - Check endpoint is accessible

### 2. Restart Deployment
- **Action ID**: `restart-deployment`
- **Command**: `kubectl rollout restart deployment/{name} -n {namespace}`
- **When to use**: Pod is stuck, needs fresh start
- **Pre-condition**: Pod exists but not healthy
- **Expected outcome**: Old pods terminate, new pods created
- **Verification**:
  - Old pod names gone from `kubectl get pods`
  - New pod names appear with age "0s-1s"
  - Pod status changes: Terminating → Running

### 3. Delete Pod
- **Action ID**: `delete-pod`
- **Command**: `kubectl delete pod {name} -n {namespace}`
- **When to use**: Pod in CrashLoopBackOff, Evicted, or Failed state
- **Pre-condition**: Single unhealthy pod in deployment
- **Expected outcome**: Pod deleted, deployment controller creates replacement
- **Verification**:
  - Pod disappears immediately
  - Deployment creates new pod automatically
  - New pod healthy within 30 seconds

### 4. Increase Resource Limits
- **Action ID**: `increase-resources`
- **Command**: `kubectl patch deployment {name} -n {namespace} -p '{"spec":{"template":{"spec":{"containers":[{"name":"{container}","resources":{"limits":{"memory":"512Mi","cpu":"500m"}}}]}}}}'`
- **When to use**: Pod OOMKilled or high resource pressure
- **Pre-condition**: High memory/CPU usage detected, OOMKill events
- **Expected outcome**: Resource limits increased, pod restarts
- **Verification**:
  - Check resource limits changed in pod spec
  - Check new pod started
  - Check no more OOMKill events

### 5. Check & Fix Port Issues
- **Action ID**: `fix-port-binding`
- **Command**: `kubectl port-forward service/{name} {port}:{port} -n {namespace}`
- **When to use**: Service not reachable, networking issue
- **Pre-condition**: Pod running but endpoint not responding
- **Expected outcome**: Port forward established, service accessible
- **Verification**:
  - Port forward successful
  - Service responds on forwarded port
  - Liveness probe succeeds

## Decision Matrix

| Pod Status | Restart Count | Events | Recommended Action |
|------------|---------------|--------|-------------------|
| Pending | Any | CreateContainerConfigError | Delete Pod → Scale Up |
| CrashLoopBackOff | >5 | BackOff, Failed | Delete Pod, Check Logs |
| OOMKilled | >2 | OOMKill | Increase Memory Limits |
| Evicted | Any | Evicted | Add Node or Increase Resources |
| ImagePullBackOff | Any | Failed pulling image | Check image availability |
| NotReady | >3 | Unhealthy | Restart Deployment |

## Execution Flow

```
Decision (SRE selects action)
  ↓
Pre-execution verification (current state)
  ↓
Execute remediation command
  ↓
Poll pod status (every 2 seconds, max 30 seconds)
  ↓
Post-execution verification (new state)
  ↓
Success/Failure determination
  ↓
Log result to verification log
```

## State Transitions to Monitor

### For Scale-Up
```
Desired Replicas: 0 → 1
Pod Phase: N/A → Pending → Running
Ready Status: N/A → False → True
```

### For Restart
```
Pod Age: Any → 0s
Restart Count: N → N+1
Pod Name: Changes (hash changes)
```

### For Delete
```
Pod Phase: Running/Failed → Terminating → Gone
Replacement Pod: Created automatically
Age: 0s
```
