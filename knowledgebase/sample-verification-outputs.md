# Sample Verification Outputs

This file contains real example outputs showing what verification looks like for each action type.

## Example 1: Successful Scale-Up

**File**: `knowledgebase/samples/healing-session-scale-up-success.json`

```json
{
  "session_id": "heal-20260417-paymentservice-001",
  "timestamp_utc": "2026-04-17T09:30:00Z",
  "sre_user": "devops-team-morning",
  "incident_id": "INC-2026-04-17-010",
  
  "detection": {
    "service_name": "paymentservice",
    "namespace": "default",
    "reason": "Service not responding to health checks",
    "confidence": 0.99,
    "detected_at": "2026-04-17T09:20:00Z"
  },
  
  "sre_decision": {
    "action_chosen": "scale-up",
    "target_replicas": 1,
    "reason": "Critical payment service down, scaling up to restore availability",
    "decided_at": "2026-04-17T09:30:00Z"
  },
  
  "execution": {
    "command": "kubectl scale deployment/paymentservice -n default --replicas=1",
    "executed_at": "2026-04-17T09:30:15Z",
    "duration_ms": 245,
    "exit_code": 0,
    "stdout": "deployment.apps/paymentservice scaled"
  },
  
  "verification": {
    "started_at": "2026-04-17T09:30:16Z",
    "strategy": "polling_with_backoff",
    "max_polls": 5,
    "poll_interval_seconds": 2,
    "timeout_seconds": 30,
    
    "polls": [
      {
        "poll_number": 1,
        "timestamp": "2026-04-17T09:30:18Z",
        "deployment": {
          "desired_replicas": 1,
          "ready_replicas": 0,
          "available_replicas": 0,
          "updated_replicas": 1
        },
        "pods": {
          "total": 1,
          "running": 0,
          "pending": 1,
          "details": [
            {
              "name": "paymentservice-895ff658d-abc12",
              "phase": "Pending",
              "ready": false,
              "restart_count": 0,
              "age_seconds": 2
            }
          ]
        },
        "events": [
          "SuccessfulCreate: Created pod: paymentservice-895ff658d-abc12",
          "Scheduled: Successfully assigned to minikube"
        ],
        "checks": {
          "pod_created": true,
          "pod_running": false,
          "pod_ready": false,
          "endpoints_available": false,
          "service_responsive": false
        }
      },
      {
        "poll_number": 2,
        "timestamp": "2026-04-17T09:30:28Z",
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
          "details": [
            {
              "name": "paymentservice-895ff658d-abc12",
              "phase": "Running",
              "ready": true,
              "restart_count": 0,
              "age_seconds": 12,
              "ready_condition": {
                "status": "True",
                "last_transition_time": "2026-04-17T09:30:24Z"
              }
            }
          ]
        },
        "service": {
          "name": "paymentservice",
          "namespace": "default",
          "type": "ClusterIP",
          "cluster_ip": "10.96.235.100",
          "endpoints": 1,
          "endpoint_ips": ["10.244.1.105"],
          "ports": [
            {
              "name": "grpc",
              "port": 50051,
              "target_port": 50051,
              "protocol": "TCP"
            }
          ]
        },
        "connectivity_check": {
          "test_method": "k8s endpoint query",
          "result": "PASS",
          "endpoint_ip": "10.244.1.105:50051",
          "response_time_ms": 5
        },
        "checks": {
          "pod_created": true,
          "pod_running": true,
          "pod_ready": true,
          "endpoints_available": true,
          "service_responsive": true
        }
      }
    ],
    
    "final_result": {
      "status": "SUCCESS",
      "verified_at": "2026-04-17T09:30:28Z",
      "total_duration_seconds": 13,
      "polls_required": 2,
      "all_checks_passed": true,
      "confidence_score": 0.99,
      
      "checks_passed": [
        "pod_created_successfully",
        "pod_transitioned_to_running",
        "pod_reached_ready_state",
        "readiness_probe_passed",
        "service_endpoint_updated",
        "service_responding",
        "no_error_events",
        "no_restart_loops"
      ],
      
      "checks_failed": [],
      
      "metrics": {
        "deployment_ready_time_seconds": 10,
        "pod_startup_time_seconds": 12,
        "endpoint_update_time_seconds": 8,
        "first_response_time_ms": 45
      }
    },
    
    "post_action_state": {
      "timestamp": "2026-04-17T09:30:38Z",
      "deployment": {
        "name": "paymentservice",
        "namespace": "default",
        "replicas_desired": 1,
        "replicas_current": 1,
        "replicas_ready": 1,
        "replicas_available": 1
      },
      "pods": {
        "total": 1,
        "statuses": {
          "running": 1,
          "pending": 0,
          "failed": 0
        }
      },
      "pod_list": [
        {
          "name": "paymentservice-895ff658d-abc12",
          "phase": "Running",
          "ready": true,
          "restarts": 0,
          "age": "20s"
        }
      ],
      "service_status": {
        "name": "paymentservice",
        "endpoints": 1,
        "endpoint_ready": true
      },
      "resource_usage": {
        "cpu_millicores": 2.5,
        "memory_megabytes": 24
      },
      "recent_events": [
        "Scheduled: Successfully assigned pod to minikube",
        "Pulled: Successfully pulled image",
        "Created: Created container",
        "Started: Started container",
        "Ready: readiness probe indicates success"
      ]
    },
    
    "summary": {
      "incident_resolved": true,
      "service_restored": true,
      "downtime_duration_seconds": 600,
      "time_to_resolution_seconds": 38,
      "root_cause": "Deployment was scaled to 0 replicas (manual)",
      "action_effectiveness_score": 1.0,
      "sre_notes": "Successfully scaled paymentservice from 0 to 1 replica. Service fully operational.",
      "recommended_next_steps": "Monitor for stability, investigate why deployment was scaled to 0"
    }
  }
}
```

---

## Example 2: Failed Scale-Up (Resource Constraints)

**File**: `knowledgebase/samples/healing-session-scale-up-failure.json`

```json
{
  "session_id": "heal-20260417-frontend-002",
  "timestamp_utc": "2026-04-17T14:45:00Z",
  "sre_user": "devops-oncall",
  
  "sre_decision": {
    "action_chosen": "scale-up",
    "target_replicas": 3,
    "reason": "Frontend service under heavy load, scaling to 3 replicas"
  },
  
  "execution": {
    "command": "kubectl scale deployment/frontend -n default --replicas=3",
    "executed_at": "2026-04-17T14:45:15Z",
    "duration_ms": 180,
    "exit_code": 0,
    "stdout": "deployment.apps/frontend scaled"
  },
  
  "verification": {
    "polls": [
      {
        "poll_number": 1,
        "timestamp": "2026-04-17T14:45:18Z",
        "deployment": {
          "desired_replicas": 3,
          "ready_replicas": 1,
          "available_replicas": 1
        },
        "pods": {
          "total": 3,
          "running": 1,
          "pending": 2,
          "failed": 0,
          "details": [
            {
              "name": "frontend-5b699d5c96-old1",
              "phase": "Running",
              "ready": true
            },
            {
              "name": "frontend-5b699d5c96-new1",
              "phase": "Pending",
              "ready": false,
              "events": ["Scheduled", "Pulling image"]
            },
            {
              "name": "frontend-5b699d5c96-new2",
              "phase": "Pending",
              "ready": false,
              "events": ["FailedScheduling: insufficient memory"]
            }
          ]
        }
      },
      {
        "poll_number": 2,
        "timestamp": "2026-04-17T14:45:28Z",
        "deployment": {
          "desired_replicas": 3,
          "ready_replicas": 2,
          "available_replicas": 2,
          "conditions": [
            {
              "type": "Progressing",
              "status": "False",
              "reason": "ProgressDeadlineExceeded",
              "message": "ReplicaSet \"frontend-5b699d5c96\" failed progressing."
            }
          ]
        },
        "pods": {
          "total": 3,
          "running": 2,
          "pending": 1,
          "failed": 0,
          "details": [
            {
              "name": "frontend-5b699d5c96-old1",
              "phase": "Running",
              "ready": true
            },
            {
              "name": "frontend-5b699d5c96-new1",
              "phase": "Running",
              "ready": true
            },
            {
              "name": "frontend-5b699d5c96-new2",
              "phase": "Pending",
              "ready": false,
              "events": [
                "FailedScheduling: Node minikube does not have sufficient memory",
                "FailedScheduling: 0/1 nodes available, required: {memory=256Mi, cpu=100m}"
              ]
            }
          ]
        }
      },
      {
        "poll_number": 3,
        "timestamp": "2026-04-17T14:45:38Z",
        "deployment": {
          "desired_replicas": 3,
          "ready_replicas": 2,
          "available_replicas": 2
        },
        "pods": {
          "total": 3,
          "running": 2,
          "pending": 1,
          "failed": 0,
          "details": [
            {
              "name": "frontend-5b699d5c96-new2",
              "phase": "Pending",
              "ready": false,
              "pending_reason": "Unschedulable",
              "events": [
                "FailedScheduling: Node minikube does not have sufficient memory. Required: 256Mi, Available: 128Mi"
              ]
            }
          ]
        }
      }
    ],
    
    "final_result": {
      "status": "FAILURE",
      "verified_at": "2026-04-17T14:45:38Z",
      "total_duration_seconds": 23,
      "polls_required": 3,
      "confidence_score": 0.95,
      
      "failure_reason": "insufficient_node_resources",
      "failure_details": {
        "type": "ResourceConstraint",
        "message": "Node does not have sufficient memory for 3 replicas",
        "resource_type": "memory",
        "required": "768Mi (256Mi per pod × 3)",
        "available": "128Mi",
        "deficit": "640Mi"
      },
      
      "checks_passed": [
        "deployment_scaling_command_executed",
        "deployment_spec_updated",
        "partial_pods_running"
      ],
      
      "checks_failed": [
        "all_replicas_scheduled",
        "all_pods_running",
        "desired_replicas_ready",
        "service_at_full_capacity"
      ]
    },
    
    "post_action_state": {
      "deployment": {
        "desired": 3,
        "ready": 2,
        "available": 2
      },
      "pods": {
        "total": 3,
        "running": 2,
        "pending": 1,
        "failed": 0
      },
      "service_endpoints": 2,
      "service_degraded": true
    },
    
    "summary": {
      "incident_resolved": false,
      "service_restored": false,
      "root_cause": "Insufficient node memory for desired replica count",
      "action_effectiveness_score": 0.33,
      
      "recommended_actions": [
        {
          "priority": 1,
          "action": "Check node resources",
          "command": "kubectl top nodes"
        },
        {
          "priority": 2,
          "action": "Scale to 2 instead of 3",
          "command": "kubectl scale deployment/frontend -n default --replicas=2"
        },
        {
          "priority": 3,
          "action": "Add more nodes or increase node memory",
          "command": "minikube config set memory 4096"
        }
      ],
      
      "sre_notes": "Scale-up partially failed. Only 2/3 pods scheduled due to insufficient memory. Service degraded but partially operational with 2 replicas."
    }
  }
}
```

---

## Example 3: Successful Restart Action

**File**: `knowledgebase/samples/healing-session-restart-success.json`

```json
{
  "session_id": "heal-20260417-redis-cart-003",
  "timestamp_utc": "2026-04-17T11:15:00Z",
  "sre_user": "devops-team",
  
  "sre_decision": {
    "action_chosen": "restart-deployment",
    "reason": "Pod in NotReady state, needs fresh start to clear stuck connections"
  },
  
  "execution": {
    "command": "kubectl rollout restart deployment/redis-cart -n default",
    "executed_at": "2026-04-17T11:15:10Z",
    "duration_ms": 320
  },
  
  "verification": {
    "polls": [
      {
        "poll_number": 1,
        "timestamp": "2026-04-17T11:15:12Z",
        "pods": {
          "total": 2,
          "running": 1,
          "terminating": 1,
          "pending": 0,
          "details": [
            {
              "name": "redis-cart-84bd76dc9c-old99",
              "phase": "Terminating",
              "age_seconds": 144000,
              "deletion_timestamp": "2026-04-17T11:15:12Z"
            },
            {
              "name": "redis-cart-84bd76dc9c-new00",
              "phase": "Pending",
              "age_seconds": 2,
              "restart_count": 0
            }
          ]
        },
        "events": [
          "Killing pod: redis-cart-84bd76dc9c-old99",
          "Created pod: redis-cart-84bd76dc9c-new00"
        ]
      },
      {
        "poll_number": 2,
        "timestamp": "2026-04-17T11:15:22Z",
        "pods": {
          "total": 1,
          "running": 1,
          "pending": 0,
          "terminating": 0,
          "details": [
            {
              "name": "redis-cart-84bd76dc9c-new00",
              "phase": "Running",
              "ready": true,
              "age_seconds": 12,
              "restart_count": 0,
              "hash_change": "old99 → new00 (confirms new pod)"
            }
          ]
        }
      }
    ],
    
    "final_result": {
      "status": "SUCCESS",
      "verified_at": "2026-04-17T11:15:22Z",
      "total_duration_seconds": 12,
      "confidence_score": 1.0,
      
      "checks_passed": [
        "old_pod_terminated",
        "new_pod_created",
        "pod_hash_changed",
        "pod_running",
        "pod_ready",
        "service_endpoints_maintained",
        "no_downtime_detected"
      ]
    }
  }
}
```

## How to Use These Samples

1. **Copy as Templates**: When creating new healing sessions, use the structure from these examples

2. **Compare Your Results**: If your healing took 40 seconds but example took 13 seconds, investigate why (network delays, resource constraints, etc.)

3. **Debug Failures**: If your scale-up failed, compare to Example 2 (failure case) to identify similar issues

4. **Train SREs**: Share these examples with team to show expected behaviors

5. **Automated Analysis**: Parse these with scripts to identify patterns:
   - Average time to resolution by action type
   - Success rates by service
   - Common failure modes
   - Performance trends over time
