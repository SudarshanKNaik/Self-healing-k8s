# Ayush - Healing Backend Logging System

## 🎯 Overview

Ayush is a comprehensive backend logging system that tracks every remediation option you select and executes during the self-healing process.

When you choose a remediation option (e.g., "Fast Restart", "Scale Replicas", "Investigate Dependencies") and click "Start Healing", all backend execution details are captured and stored in a markdown file (`ayush.md`) with:

- Which remediation option you selected
- The execution strategy (restart-workload, scale-replicas, dependency-first)
- Target pod/deployment and namespace
- Success/failure status
- Detailed execution outcomes
- Complete timestamp logs

## 🚀 Quick Start

### Start the Website

**Option 1: PowerShell (Windows)**
```powershell
.\start-healing-site.ps1
```

**Option 2: Node.js**
```bash
node start-healing-site.js
```

**Option 3: Direct npm**
```bash
cd h24-app
npm run dev
```

### Access the Dashboard

Once the server starts (usually takes 10-15 seconds), open:

```
http://localhost:3000/dashboard/healing
```

You'll see:
- Healing dashboard with pod/service selection
- Remediation options with scores and costs
- **New: Backend Execution Logs (Ayush)** section at the bottom

## 📝 How It Works

### 1. Select a Target
- Click on a pod or deployment from the "Targets" section
- It must be in a failure state (CrashLoopBackOff, Error, etc.) to show remediation options

### 2. Choose Remediation Option
The system shows 3 options:
- **Option 1: Fast Restart** - Quick pod restart (high risk, minimal downtime)
- **Option 2: Scale Replicas** - Horizontal scaling (medium risk, minimal downtime)  
- **Option 3: Dependency-First** - Full dependency analysis (low risk, more downtime)

### 3. Execute Healing
- Click the selected option to highlight it
- Click **"Start Healing"** button
- The backend logs everything in real-time

### 4. View Backend Logs
Two ways to see the logs:

**In the Dashboard:**
- Scroll to the bottom to the "Backend Execution Logs (Ayush)" section
- See real-time updates
- Download logs as markdown file
- View auto-refreshing logs

**In the File System:**
- Check `h24-app/ayush.md`
- Contains complete history of all healing executions

## 📊 Log Format

Each healing execution creates a markdown section like:

```markdown
## [4/17/2026, 2:45:30 PM] Fast Restart for pod-crash

**Status**: SUCCESS

### Selected Configuration
- **Remediation ID**: `option-1`
- **Strategy**: `restart-workload`
- **Scenario**: `pod-crash`
- **Dry Run**: No

### Target
- **Resource**: `pod/frontend-abc123`
- **Namespace**: `default`

### Outcome
Healing executed successfully. Status: completed

### Details
```json
{
  "status": "completed",
  "snapshot": {
    "applied_at": "2026-04-17T14:45:30Z",
    "pod_name": "frontend-abc123",
    "action": "killed pod"
  }
}
```

---
```

## 🎛️ Dashboard Features

### Backend Logs Viewer

Located at the bottom of the healing dashboard:

| Feature | Purpose |
|---------|---------|
| **Auto Refresh** | Automatically update logs every 2 seconds |
| **Refresh** | Manual refresh of logs |
| **Download** | Save logs as `ayush.md` file |
| **Clear** | Reset logs for fresh start |

## 🔍 Verification Checklist

After selecting an option and executing healing:

- [ ] Option name appears in the log
- [ ] Correct remediation strategy is shown (restart-workload/scale-replicas/dependency-first)
- [ ] Target pod/deployment name matches
- [ ] Namespace is correct (usually "default")
- [ ] Status shows SUCCESS or FAILED
- [ ] Timestamp is current
- [ ] Outcome details match what you expected

## 📁 File Locations

| Component | Location |
|-----------|----------|
| Healing Dashboard | `h24-app/src/app/dashboard/healing/page.tsx` |
| Logging System | `h24-app/src/lib/healing-logger.ts` |
| API Route | `h24-app/src/app/api/ai-agents/healing/start/route.ts` |
| Logs Viewer Component | `h24-app/src/components/dashboard/healing-logs-viewer.tsx` |
| Logs API | `h24-app/src/app/api/healing-logs/route.ts` |
| **Log Output** | `h24-app/ayush.md` |

## 🛠️ Troubleshooting

### Logs not appearing?

1. **Check server is running**
   ```powershell
   curl http://localhost:3000/api/healing-logs
   ```

2. **Clear logs and try again**
   - Click "Clear" button in the logs viewer
   - Select a remediation option
   - Click "Start Healing"

3. **Check file exists**
   ```powershell
   Test-Path "h24-app/ayush.md"
   ```

### Logs viewer not showing?
- Ensure "Auto Refresh" is enabled
- Check browser console for errors (F12)
- Clear browser cache (Ctrl+Shift+Delete)

### Can't start website?
```powershell
# Check Node.js is installed
node --version

# Check npm dependencies
cd h24-app
npm install

# Try dev server directly
npm run dev
```

## 🔧 Configuration

### Log File Location
The log file is always created at: `h24-app/ayush.md`

To change the default location, edit `src/lib/healing-logger.ts`:

```typescript
const LOG_FILE_PATH = path.join(process.cwd(), "ayush.md"); // Change here
```

### Auto-refresh Interval
Default: 2 seconds

To change, edit `src/components/dashboard/healing-logs-viewer.tsx`:

```typescript
const interval = setInterval(fetchLogs, 2000); // Change 2000 to desired ms
```

## 📚 API Endpoints

### Get Logs
```bash
GET /api/healing-logs
```

Response:
```json
{
  "ok": true,
  "logs": "# Ayush Logs\n...",
  "filePath": "ayush.md",
  "timestamp": "2026-04-17T14:45:30Z"
}
```

### Clear Logs
```bash
GET /api/healing-logs?action=clear
```

Response:
```json
{
  "ok": true,
  "message": "Logs cleared successfully"
}
```

## 🎓 Example Workflow

```
1. Terminal
   $ .\start-healing-site.ps1
   ✓ Dev server starting at http://localhost:3000

2. Browser
   → Navigate to http://localhost:3000/dashboard/healing

3. Dashboard
   → See available pods/services
   → Select "frontend" pod
   → See 3 remediation options appear

4. Choose Option
   → click "Fast Restart" option
   → see it highlighted in green

5. Execute
   → click "Start Healing" button
   → healing process runs

6. View Logs
   → scroll to "Backend Execution Logs (Ayush)" section
   → see real-time updates
   → verify selected option is being executed

7. Verify
   → check logs show:
     ✓ Remediation: "restart-workload"
     ✓ Target: "pod/frontend"
     ✓ Status: "SUCCESS"
```

## 🎨 Log Viewer UI

```
┌─────────────────────────────────────────────────┐
│ 📝 Backend Execution Logs (Ayush)               │
│ [✓] Auto Refresh  [Refresh] [Download] [Clear] │
├─────────────────────────────────────────────────┤
│                                                 │
│ ## [4/17/2026, 2:45:30 PM] Fast Restart...    │
│                                                 │
│ **Status**: SUCCESS                             │
│ ...                                             │
│                                                 │
└─────────────────────────────────────────────────┘
```

## 🚨 Important Notes

- Logs are stored **server-side** in `ayush.md`
- Each healing execution appends to the file (no overwrites)
- Use "Clear" button to reset logs between test runs
- Logs persist across server restarts
- Download logs regularly for backup

## 📞 Support

If you encounter issues:

1. Check console errors: `F12` in browser
2. Check server logs in terminal
3. Check `ayush.md` file exists and is writable
4. Verify you have read/write permissions on `h24-app/` directory
5. Make sure port 3000 is not in use

## ✅ Success Indicators

You'll know everything is working when:

- ✅ Dev server starts without errors
- ✅ Dashboard loads at `http://localhost:3000/dashboard/healing`
- ✅ Logs viewer appears at the bottom of the page
- ✅ "Auto Refresh" checkbox is available
- ✅ After healing runs, new logs appear
- ✅ `ayush.md` file contains your execution logs

---

**Happy Healing! 🎉**
