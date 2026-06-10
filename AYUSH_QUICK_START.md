# 🎯 Ayush Logging System - Quick Start Guide

## ✅ Website Status
✓ **Live at**: http://localhost:3000/dashboard/healing

**Server Details:**
- Local: http://localhost:3000
- Network: http://172.25.1.76:3000
- Status: ✓ Running

## 📋 What Was Set Up

You now have a complete **Ayush Backend Logging System** that:

1. **Captures Every Healing Execution**
   - Records which remediation option YOU choose
   - Logs the execution strategy (restart, scale, dependency-first)
   - Stores target pod/deployment info
   - Records success/failure status

2. **Stores Logs in ayush.md**
   - Location: `h24-app/ayush.md`
   - Markdown formatted for easy reading
   - Timestamps for each execution
   - Complete execution details

3. **Displays Logs in Real-Time**
   - New "Backend Execution Logs" section at bottom of healing dashboard
   - Auto-refresh every 2 seconds
   - Download button to save logs
   - Clear button to reset

## 🚀 How to Test It

### Step 1: Open the Dashboard
```
http://localhost:3000/dashboard/healing
```

### Step 2: Select a Target
- Look for pods/services in the "Targets" section
- Select one from the list (they must be running first)
- Example: `default/frontend-xyz`, `default/payment-service`, etc.

### Step 3: Wait for Options
- Once selected, 3 remediation options appear below
- Option 1: **Fast Restart** (high risk, quick)
- Option 2: **Scale Replicas** (medium risk)
- Option 3: **Investigate Dependencies** (low risk, slower)

### Step 4: Choose an Option
- Click on one of the option cards to select it
- It will be highlighted in green

### Step 5: Start Healing
- Click the **"Start Healing"** button
- Watch the execution happen

### Step 6: View Logs
- Scroll down to **"Backend Execution Logs (Ayush)"** section
- Logs appear in real-time
- You'll see:
  ✓ Which option you selected
  ✓ The remediation strategy used
  ✓ The target pod/namespace
  ✓ Success or failure
  ✓ Timestamp and details

## 📝 Log File Location

After running a healing execution, you can also view the logs directly:

**File**: `d:\k8s-self-healing\h24-app\ayush.md`

Open in any text editor to see the complete markdown-formatted logs.

## 🎮 Dashboard Controls

In the "Backend Execution Logs" section:

| Button | Action |
|--------|--------|
| **Auto Refresh** | Checkbox - automatically update logs every 2s |
| **Refresh** | Manual refresh button |
| **Download** | Save logs as `ayush.md` file |
| **Clear** | Reset all logs (for fresh start) |

## 🔍 What Gets Logged

Each healing execution records:

```markdown
## [Timestamp] [Selected Option Name]

**Status**: SUCCESS or FAILED

### Selected Configuration
- **Remediation ID**: option-1, option-2, option-3
- **Strategy**: restart-workload, scale-replicas, or dependency-first
- **Scenario**: pod-crash, high-cpu, service-unavailable
- **Dry Run**: Yes/No

### Target
- **Resource**: pod name or deployment name
- **Namespace**: default (or custom namespace)

### Outcome
[Description of what happened]

### Details
[JSON with technical execution details]
```

## 🎯 Verification Checklist

After each healing execution, verify in the logs:

- [ ] The remediation option name appears (Fast Restart, etc.)
- [ ] The correct strategy is logged (restart-workload, etc.)
- [ ] The target pod/service name matches what you selected
- [ ] The namespace is correct
- [ ] Status shows SUCCESS
- [ ] Timestamp is current
- [ ] Details section shows execution results

## 📂 Files Created/Modified

**New Files:**
- `src/lib/healing-logger.ts` - Logging engine
- `src/app/api/healing-logs/route.ts` - API endpoint
- `src/components/dashboard/healing-logs-viewer.tsx` - UI component
- `AYUSH_LOGGING_GUIDE.md` - Complete guide (this folder)

**Modified Files:**
- `src/app/api/ai-agents/healing/start/route.ts` - Added logging
- `src/app/dashboard/healing/page.tsx` - Added logs viewer UI

**Log Output:**
- `h24-app/ayush.md` - Generated after first healing run

## 🚨 Troubleshooting

### "Logs not appearing?"
1. Clear logs with the "Clear" button
2. Select a remediation option
3. Click "Start Healing"
4. Enable "Auto Refresh" checkbox
5. Wait 2-3 seconds for logs to appear

### "Can't see log viewer?"
1. Scroll to bottom of healing dashboard page
2. Look for blue card titled "Backend Execution Logs (Ayush)"
3. If not there, check server logs for errors

### "No targets showing?"
1. Make sure a pod/service is actually running
2. Try with built-in services like: `frontend`, `redis`, `postgres`
3. Check Kubernetes cluster is healthy: `kubectl get pods -A`

## 🎓 Example Execution

```
SCENARIO: Try it now!

1. In browser, go to: http://localhost:3000/dashboard/healing

2. Scroll to "Targets" section

3. Click on any available pod (e.g., "frontend")

4. See 3 remediation options appear

5. Click "Fast Restart" option (should turn green)

6. Click "Start Healing" button (blue button)

7. Healing process runs (might show "Dry Run" message)

8. Scroll down to "Backend Execution Logs" section

9. See logs update in real-time:
   ✓ Remediation ID: option-1
   ✓ Strategy: restart-workload
   ✓ Target: frontend pod
   ✓ Status: SUCCESS
   ✓ Timestamp: [current time]

10. Click "Download" to save logs as ayush.md
```

## 💡 Key Features

✨ **What Makes This Special:**
1. **Option Tracking** - See exactly which option you chose
2. **Real-Time Updates** - Logs appear instantly in dashboard
3. **Markdown Format** - Easy to read and share
4. **Persistent Storage** - All logs saved in `ayush.md`
5. **Strategy Verification** - Confirm the right strategy was used
6. **Target Verification** - Verify correct pod/service was targeted
7. **Status Tracking** - See success or failure immediately

## 🔗 Useful Links

- **Dashboard**: http://localhost:3000/dashboard/healing
- **Healing Overview**: http://localhost:3000/dashboard (if available)
- **API Logs Endpoint**: http://localhost:3000/api/healing-logs

## ✅ Success Indicators

You'll know it's working when:
- ✅ Website loads at http://localhost:3000
- ✅ Dashboard shows healing page
- ✅ Can select targets/pods
- ✅ Remediation options appear  
- ✅ "Backend Execution Logs" section visible
- ✅ After running healing, logs appear in real-time
- ✅ `ayush.md` file exists in `h24-app/` folder

---

**🎉 You're all set! Start testing the healing system now!**

**Questions?** Check `AYUSH_LOGGING_GUIDE.md` for detailed documentation.
