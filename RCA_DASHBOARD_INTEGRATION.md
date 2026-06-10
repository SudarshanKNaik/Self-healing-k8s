# RCA Dashboard Integration - Healing Page

## Overview

The AI Self-Healing Observability dashboard (healing page) has been enhanced to integrate with the RCA (Root Cause Analysis) agent for real-time RCA findings display and automatic remediation recommendation.

## What Was Integrated

### 1. **RCA Analysis Types** (`src/app/dashboard/healing/page.tsx`)

Added TypeScript types to represent RCA findings:

```typescript
type RCAIssue = {
  id: string;
  status: "ACTIVE" | "RESOLVED";
  rootCause: string;
  failureChain: string[];
  confidence: number;
  reasoning: string;
};

type RCAMetricsSummary = {
  severityScore: number;
  sustainedSignalCount: number;
  affectedPods?: string[];
  timeInAnomalyMs?: number;
};

type RCAAnalysisResult = {
  observer: {...};
  rca: {
    action: "APPEND" | "UPDATE" | "RESOLVE" | "NO_ACTION";
    issues: RCAIssue[];
    rootCause: string;
    failureChain: string[];
    confidence: number;
    reasoning: string;
    executor: {...};
  };
}
```

### 2. **State Management**

Added three new state hooks to track RCA analysis:

```typescript
const [rcaAnalysis, setRcaAnalysis] = useState<RCAAnalysisResult | null>(null);
const [rcaLoading, setRcaLoading] = useState(false);
const [rcaError, setRcaError] = useState<string>("");
```

### 3. **RCA Analysis Fetching** (`fetchRCAAnalysis` Function)

Created a new function to fetch RCA analysis when healing starts:

```typescript
const fetchRCAAnalysis = useCallback(async (clusterState?: Record<string, unknown>) => {
  setRcaLoading(true);
  setRcaError("");
  try {
    const res = await fetch("/api/rca/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(clusterState || {}),
    });
    
    const data = (await res.json()) as { ok?: boolean; error?: string } & Partial<RCAAnalysisResult>;
    if (!res.ok || !data.observer || !data.rca) {
      throw new Error(data.error || `Failed to analyze with RCA (${res.status})`);
    }
    
    setRcaAnalysis(data as RCAAnalysisResult);
    return data as RCAAnalysisResult;
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    setRcaError(errorMsg);
    return null;
  } finally {
    setRcaLoading(false);
  }
}, []);
```

### 4. **RCA Integration into Healing Flow**

Modified `startHealing()` to:
1. Build cluster state from current targets with proper field mapping:
   ```typescript
   const clusterStatePayload = {
     pods: targets.map(t => ({
       name: t.pod_name,
       namespace: t.namespace,
       status: t.status,
       cpu: t.cpu_usage,
       memory: t.memory_usage,
       restarts: t.restart_count,
     })),
   };
   ```

2. Call `fetchRCAAnalysis()` before starting healing
3. Auto-select remediation if RCA confidence > 0.7 and no selection made
4. Include RCA findings in the healing start API payload:
   ```typescript
   rcaAnalysis: rcaResult ? {
     triggerRCA: rcaResult.observer.triggerRCA,
     rootCause: rcaResult.rca.rootCause,
     failureChain: rcaResult.rca.failureChain,
     confidence: rcaResult.rca.confidence,
     reasoning: rcaResult.rca.reasoning,
     action: rcaResult.rca.action,
   } : null,
   ```

### 5. **RCA Findings Display Card**

Added a new visual card that displays RCA findings in real-time:

**Location**: Between the toolbar and healing decision options

**Displays**:
- **Root Cause**: Primary failing service/pod (blue section)
  - Shows which service is the root cause
  - Displays cascade count (number of affected services)
  
- **Confidence**: Statistical confidence of analysis (purple section)
  - Shows confidence percentage (0-100%)
  - Visual progress bar
  
- **Failure Chain**: Cascade visualization (orange section)
  - Shows the chain of service failures
  - Root cause marked as "ROOT:"
  - Previous services marked with "→"
  
- **Analysis Reasoning**: LLM-generated explanation
  - Explains why this was identified as root cause
  - Shows the analysis logic

- **Loading/Error States**:
  - Shows "Analyzing cluster state with RCA engine..." during fetch
  - Displays error message if analysis fails

## Data Flow

```
1. User selects target pod/deployment
   ↓
2. User clicks "Start Healing"
   ↓
3. startHealing() is called
   ↓
4. Cluster state is built from current targets
   ↓
5. fetchRCAAnalysis(clusterState) is called
   ↓
6. POST to /api/rca/analyze with cluster state
   ↓
7. RCA agent analyzes and returns findings
   ↓
8. rcaAnalysis state is updated
   ↓
9. RCA findings card becomes visible in UI
   ↓
10. Healing start API is called with RCA data included
   ↓
11. Executor can use RCA findings to inform remediation
```

## Auto-Selection Logic

When the user clicks "Start Healing":

1. **If no remediation is selected**:
   - Fetch RCA analysis
   - If RCA confidence > 0.70:
     - Create `rcaActionInfo` with RCA findings
     - Include in healing start payload
     - Executor can use this to select strategy

2. **If remediation is already selected**:
   - Still fetch and include RCA analysis
   - User's selection takes precedence
   - RCA provides additional context for execution

## API Integration

The dashboard communicates with:

### `/api/rca/analyze` (POST)
- **Input**: Cluster state with pods array
- **Output**: Complete RCA analysis with observer and RCA sections
- **Usage**: Called from `startHealing()` with current targets

### `/api/ai-agents/healing/start` (POST)
- **Enhanced Input**: Now includes `rcaAnalysis` field
- **Fields**: rootCause, failureChain, confidence, reasoning, action

## Field Mapping

The healing page maps HealingTarget fields to RCA cluster state:

| Dashboard Field | RCA Field | Type | Notes |
|-----------------|-----------|------|-------|
| `pod_name` | `name` | string | Pod/deployment name |
| `namespace` | `namespace` | string | Kubernetes namespace |
| `status` | `status` | string | Pod/deployment status |
| `cpu_usage` | `cpu` | number | CPU usage percentage |
| `memory_usage` | `memory` | number | Memory usage percentage |
| `restart_count` | `restarts` | number | Pod restart count |

## Display Styling

The RCA findings card uses the dashboard's color scheme:

- **Blue**: Root cause section (primary finding)
- **Purple**: Confidence metric (statistical confidence)
- **Orange**: Failure chain (warning/cascade)
- **Tan/Beige**: Reasoning section (explanation)
- **Light Gray**: Loading/error states

## Error Handling

The integration includes comprehensive error handling:

1. **RCA Fetch Failures**:
   - Error message displayed in card
   - Healing still proceeds with LLM-only options
   - No cascade to other components

2. **Network Issues**:
   - Automatic retry not implemented (user can try again)
   - Error displayed to user
   - Healing process not blocked

3. **Validation**:
   - Type-safe RCAAnalysisResult structure
   - Null checks for optional fields
   - Confidence bounds validation

## User Experience

### Before (LLM Only)
1. Select pod
2. See Gemini remediation options
3. Choose one
4. Start healing
5. Executor applies remediation

### After (RCA Enhanced)
1. Select pod
2. Click "Start Healing"
3. RCA analysis fetches automatically
4. See RCA findings displayed in real-time
5. See how RCA findings align with Gemini options
6. Choose remediation (informed by both RCA and LLM)
7. Start healing with RCA context
8. Executor uses RCA + Gemini + user choice for remediation

## Technical Notes

### Thread Safety
- State updates use React's `useState` hooks
- No race conditions between fetch and UI updates
- Loading state prevents multiple simultaneous fetches

### Performance
- RCA analysis is lightweight (dependency graph traversal)
- Single POST request to /api/rca/analyze
- No polling or continuous updates
- Results cached in component state

### Backward Compatibility
- Healing still works without RCA (rcaAnalysis can be null)
- LLM remediation options still displayed
- User can still manually select remediation options
- RCA is additive, not replacement for LLM

## Testing Checklist

Before deploying to production, verify:

- [ ] RCA findings display correctly with sample data
- [ ] Confidence bar renders properly (0-100%)
- [ ] Failure chain visualization is clear
- [ ] Loading state shows during fetch
- [ ] Error state shows on RCA API failure
- [ ] Auto-selection logic works (confidence > 0.70)
- [ ] Healing starts successfully with RCA data
- [ ] Executor receives RCA fields in payload
- [ ] Metrics align between observer and RCA

## Integration Points

The healing dashboard now integrates with:

1. **Observer Agent**: Provides anomaly detection context
2. **RCA Agent**: Provides root cause analysis
3. **RCA Persistent Report**: Supplies issue history and lifecycle
4. **Healing Executor**: Uses RCA recommendations for remediation strategy
5. **LLM (Gemini)**: Provides alternative remediation options

## Future Enhancements

Potential improvements for future versions:

1. Historical RCA results display (from persistent report)
2. RCA confidence threshold configuration UI
3. RCA reasoning detail expansion/collapse
4. Cascade impact calculator (estimated blast radius)
5. RCA recommendation visualization (flowchart of failure)
6. Audit trail of RCA decisions applied
7. RCA model performance metrics
8. Custom RCA rule configuration
