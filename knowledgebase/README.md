# Knowledgebase - Overview & Navigation

This knowledgebase helps you understand, track, and verify the self-healing system's remediation actions.

## 📚 Files in This Knowledgebase

### 1. **remediation-actions.md** - Action Reference Guide
**What it contains:**
- 5 available remediation actions (scale-up, restart, delete, resources, etc.)
- When to use each action
- Expected outcomes for each
- State transition diagrams
- Decision matrix for choosing actions

**When to use:**
- Understanding what actions are available
- Determining which action to take for a given problem
- Checking expected outcomes before clicking "Heal"

**Example:** "My payment service pod is stuck, should I delete it or restart?"
→ Use the decision matrix in this file

---

### 2. **verification-templates.md** - Verification Templates & Checklists
**What it contains:**
- Pre-action verification JSON template
- Post-action verification JSON template
- Success criteria for each action type
- Failure criteria (how to know it didn't work)
- Verification polling strategy

**When to use:**
- Understanding what "SUCCESS" vs "FAILURE" means
- Checking if verification is complete
- Setting expectations for verification timelines

**Example:** "The healing is taking 45 seconds, is that normal?"
→ Check the polling strategy - usually should complete within 30 seconds maximum

---

### 3. **verification-logs-structure.md** - Log Formats & Data Structure
**What it contains:**
- Directory structure for storing healing logs
- Complete JSON schema for individual healing sessions
- Daily summary log format
- Action statistics aggregation format
- Real-time verification output log (text format)
- Query examples for finding specific logs

**When to use:**
- Understanding WHERE logs are stored
- Finding healing sessions from past incidents
- Aggregating statistics across days/services
- Auditing what actions were taken

**Example:** "Did we successfully scale-up paymentservice yesterday?"
→ Query logs using examples in this file

---

### 4. **troubleshooting-guide.md** - Common Issues & Verification Scenarios
**What it contains:**
- 4 real-world failure scenarios with diagnosis steps
- How to spot issues from verification outputs
- Verification log indicators for each problem
- Next actions to take when something fails
- Comprehensive checklists per action type
- How to enable verification logging in the code

**When to use:**
- Healing action failed and you don't know why
- Troubleshooting a service that won't come back up
- Learning what to check when things go wrong
- Understanding verification log error messages

**Example:** "Pod is running but service still not responding"
→ Go to "Scenario 4" for diagnosis steps

---

### 5. **quick-reference.md** - Decision Tree & Fast Lookup
**What it contains:**
- Quick reference tables (status meanings, verification output meanings)
- Visual decision tree for choosing actions
- Expected timeline for each action type
- How to find specific logs with commands
- JSON schema validation rules
- One-line script for success rate analysis

**When to use:**
- Quick lookup of what a status means
- Deciding which action to take (visual tree)
- Checking if timing is normal
- Generating a quick report

**Example:** "What does 'DEGRADED' status mean?"
→ Look at the status table in this file

---

### 6. **sample-verification-outputs.md** - Real Example Outputs
**What it contains:**
- Example #1: Successful scale-up (complete JSON)
- Example #2: Failed scale-up with error details
- Example #3: Successful restart
- Explanation of each field
- How to use samples for debugging

**When to use:**
- Comparing your healing result to expected output
- Understanding the JSON structure (see real data)
- Training new SREs on what success looks like
- Debugging why your result differs from expected

**Example:** "My healing took 50 seconds but the example shows 13, why?"
→ Compare the JSON structures to find differences

---

## 📋 Quick Navigation

### "I need to choose an action"
1. Check service status
2. Look at **remediation-actions.md** → Decision Matrix
3. Use **quick-reference.md** → Flowchart

### "I executed a healing action"
1. Wait for verification to complete (watch the UI)
2. Check **verification-templates.md** → Success Criteria for your action
3. Look at the verification timeline expected in **quick-reference.md**

### "My healing failed"
1. Look at verification output (FAILURE status)
2. Check **troubleshooting-guide.md** for similar scenario
3. Follow diagnosis steps and next actions
4. Find previous failures in logs

### "I want to audit past incidents"
1. Use **verification-logs-structure.md** → How to Query
2. Search through `knowledgebase/logs/` directory
3. Use jq filters to find specific actions/failures
4. Generate reports using scripts in **quick-reference.md**

### "I'm training a new SRE"
1. Start with **quick-reference.md** → Read status table
2. Show **remediation-actions.md** → Action types and when to use
3. Walk through **sample-verification-outputs.md** → Example #1 (success)
4. Show **troubleshooting-guide.md** → Example #2 (failure)

---

## 📁 Logs Directory Structure

When you execute healing actions, they get logged here:

```
knowledgebase/
├── logs/
│   ├── 2026-04-17/
│   │   ├── healing-session-001.json          ← Individual sessions
│   │   ├── healing-session-002.json
│   │   └── index.json                        ← Daily summary
│   └── 2026-04-18/
│
├── verification-results/
│   ├── by-action/
│   │   ├── scale-up-stats.json               ← Success rates
│   │   ├── restart-stats.json
│   │   └── delete-pod-stats.json
│   └── by-service/                           ← Per-service stats
│
└── samples/
    ├── healing-session-scale-up-success.json
    ├── healing-session-scale-up-failure.json
    └── healing-session-restart-success.json
```

## 🔍 What Gets Verified

For each healing action, the system verifies:

| Check | What | Why |
|-------|------|-----|
| **Pod Created** | Pod object exists in Kubernetes | Confirms deployment accepted the scale |
| **Pod Running** | Pod phase = "Running" | Container started successfully |
| **Pod Ready** | Readiness probe passes | Application is ready for traffic |
| **Endpoint Available** | Service lists this pod | Load balancer knows about the pod |
| **Service Responding** | HTTP/gRPC request succeeds | Actual traffic works end-to-end |
| **No Crashes** | Restart count unchanged | Pod didn't immediately fail |
| **No Errors** | No OOMKill, ImagePullBackOff | Resource/image issues not present |

---

## 📊 Sample Verification Timeline

```
Scale-Up Action:
T+0s:   Command executed
T+2s:   Poll #1 → Pod Pending? (checking)
T+10s:  Poll #2 → Pod Running? (checking)
T+20s:  Poll #3 → Service responsive? (checking)
T+30s:  FINAL → Success or Failure determination
TOTAL:  ~20 seconds (typical)

Restart Action:
T+0s:   Command executed
T+2s:   Poll #1 → Old pod Terminating, new pod Pending (checking)
T+10s:  Poll #2 → New pod Running? (checking)
T+20s:  Poll #3 → Service responsive? (checking)
T+30s:  FINAL → Success or Failure
TOTAL:  ~15 seconds (typical)
```

---

## 💾 How Verification Data is Stored

### During Healing:
1. **In Memory (UI)**: Polls stored in React state
2. **In Transit**: Sent to `/api/healing/stream` endpoint
3. **Logs Visible**: Real-time in browser console

### After Healing:
1. **Backend Storage**: `knowledgebase/logs/{date}/healing-session-{id}.json`
2. **Statistics Updated**: `knowledgebase/verification-results/by-action/{action}-stats.json`
3. **Service Stats**: `knowledgebase/verification-results/by-service/{service}-stats.json`

### Query Recent Sessions:
```bash
# Find all healing sessions from today
find knowledgebase/logs/$(date +%Y-%m-%d) -name "healing-session-*.json"

# Find all failures
grep -r "FAILURE" knowledgebase/logs/

# Find all scale-ups for a service
grep -r "paymentservice" knowledgebase/logs/ | grep "scale-up"

# Success rate for today
cat knowledgebase/logs/$(date +%Y-%m-%d)/index.json | jq '.successful_healings / .total_incidents'
```

---

## ✅ Verification Success Indicators

Look for these in the verification output to know action succeeded:

✅ **SUCCESS** Status:
- `"status": "SUCCESS"` in `verification.final_result`
- `confidence_score > 0.9`
- All items in `checks_passed` list
- Empty `checks_failed` list
- `total_duration_seconds < 60`

⚠️ **DEGRADED** Status:
- `"status": "DEGRADED"`
- Pod running but not all checks pass
- May need retry or manual investigation

❌ **FAILURE** Status:
- `"status": "FAILURE"`
- Check `failure_reason` field
- Read `failure_details` for explanation
- Follow troubleshooting guide

---

## 🎓 Examples by Scenario

| Scenario | Read This |
|----------|-----------|
| Choosing between actions | quick-reference.md (flowchart) + remediation-actions.md (matrix) |
| Understanding timing | quick-reference.md (timeline) or sample-verification-outputs.md (examples) |
| Action failed, need to fix | troubleshooting-guide.md (pick scenario 1-4) |
| Finding past incidents | verification-logs-structure.md (query examples) |
| Training new SRE | sample-verification-outputs.md + troubleshooting-guide.md |
| Auditing success rates | quick-reference.md (analysis scripts) |

---

## 🚀 Getting Started

**For SREs (using the system):**
1. Read: remediation-actions.md (5 min)
2. Skim: quick-reference.md (3 min)
3. Practice: Execute a healing action and watch verification

**For Operators (maintaining the system):**
1. Read: verification-templates.md (5 min)
2. Study: verification-logs-structure.md (5 min)
3. Review: sample-verification-outputs.md (5 min)
4. Implement: API endpoint for logging (see troubleshooting-guide.md)

**For Incidents (something is broken):**
1. Look up: troubleshooting-guide.md (find matching scenario)
2. Check: verification log for error messages
3. Execute: Recommended next actions from guide

---

## 📝 Notes for Dashboard Integration

The healing dashboard (h24-app) should:
1. Display verification status in real-time
2. Store successful verifications in `knowledgebase/logs/{date}/healing-session-{id}.json`
3. Update action statistics after each healing
4. Show timeline chart from validation timeline
5. Highlight failures for SRE review

See **verific-logs-structure.md** → "How to Enable Verification Logging" for code integration.
