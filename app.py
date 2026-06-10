from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

from flask import Flask, jsonify, make_response, request


app = Flask(__name__)
MANUAL_HEAL_LAST_TRIGGERED_AT: datetime | None = None


@app.get("/")
def index() -> Any:
    return jsonify(
        {
            "status": "ok",
            "message": "Kubernetes observability helper is running.",
            "endpoints": {
                "health": "/health",
                "pods": "/pods",
            },
        }
    )


def _run_kubectl_json(args: List[str], timeout: int = 30) -> Tuple[Dict[str, Any] | None, str | None]:
    """Run kubectl and return parsed JSON or an error message."""
    try:
        result = subprocess.run(
            ["kubectl", *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None, "kubectl command timed out"
    except FileNotFoundError:
        return None, "kubectl not found on PATH"
    except Exception as exc:  # Defensive catch to keep API stable.
        return None, f"unexpected error running kubectl: {exc}"

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        return None, stderr or "kubectl command failed"

    try:
        return json.loads(result.stdout), None
    except json.JSONDecodeError:
        return None, "failed to parse kubectl JSON output"


def _run_kubectl_text(args: List[str], timeout: int = 30) -> Tuple[str | None, str | None]:
    try:
        result = subprocess.run(
            ["kubectl", *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None, "kubectl command timed out"
    except FileNotFoundError:
        return None, "kubectl not found on PATH"
    except Exception as exc:  # Defensive catch to keep API stable.
        return None, f"unexpected error running kubectl: {exc}"

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        return None, stderr or "kubectl command failed"

    return result.stdout, None


def _format_age(creation_timestamp: str | None) -> str:
    if not creation_timestamp:
        return "unknown"

    try:
        created_at = datetime.fromisoformat(creation_timestamp.replace("Z", "+00:00"))
    except ValueError:
        return "unknown"

    now = datetime.now(timezone.utc)
    age_seconds = int(max((now - created_at).total_seconds(), 0))

    days = age_seconds // 86400
    if days > 0:
        return f"{days}d"

    hours = age_seconds // 3600
    if hours > 0:
        return f"{hours}h"

    minutes = age_seconds // 60
    if minutes > 0:
        return f"{minutes}m"

    return f"{age_seconds}s"


def _sum_restarts(statuses: List[Dict[str, Any]]) -> int:
    return sum(int(container.get("restartCount", 0)) for container in statuses)


def _compute_ready(pod_status: Dict[str, Any]) -> bool:
    container_statuses = pod_status.get("containerStatuses") or []
    if container_statuses:
        return all(bool(container.get("ready", False)) for container in container_statuses)

    for condition in pod_status.get("conditions") or []:
        if condition.get("type") == "Ready":
            return condition.get("status") == "True"
    return False


def _safe_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_k8s_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _latest_warning_event_time(events: List[Dict[str, Any]]) -> datetime | None:
    latest: datetime | None = None
    for event in events:
        parsed = _parse_k8s_timestamp(event.get("event_time"))
        if parsed is None:
            parsed = _parse_k8s_timestamp(event.get("last_timestamp"))
        if parsed is None:
            parsed = _parse_k8s_timestamp(event.get("first_timestamp"))

        if parsed is None:
            continue

        if latest is None or parsed > latest:
            latest = parsed

    return latest


def _latest_failure_signal_time(events: List[Dict[str, Any]]) -> datetime | None:
    failure_reasons = {
        "BackOff",
        "Unhealthy",
        "Failed",
        "FailedCreate",
        "Evicted",
        "Killing",
        "CrashLoopBackOff",
        "OOMKilled",
    }

    failure_events = [event for event in events if str(event.get("reason") or "") in failure_reasons]
    return _latest_warning_event_time(failure_events)


def _isoformat_or_none(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _tail_text(value: str, max_chars: int = 2000) -> str:
    if len(value) <= max_chars:
        return value
    return value[-max_chars:]


def _probe_summary(probe: Dict[str, Any] | None) -> Dict[str, Any] | None:
    if not probe:
        return None

    probe_type = "unknown"
    if probe.get("httpGet"):
        probe_type = "http"
    elif probe.get("tcpSocket"):
        probe_type = "tcp"
    elif probe.get("exec"):
        probe_type = "exec"
    elif probe.get("grpc"):
        probe_type = "grpc"

    return {
        "type": probe_type,
        "initial_delay_seconds": probe.get("initialDelaySeconds"),
        "period_seconds": probe.get("periodSeconds"),
        "timeout_seconds": probe.get("timeoutSeconds"),
        "success_threshold": probe.get("successThreshold"),
        "failure_threshold": probe.get("failureThreshold"),
    }


def _extract_conditions(pod_status: Dict[str, Any]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for condition in pod_status.get("conditions") or []:
        output.append(
            {
                "type": condition.get("type"),
                "status": condition.get("status"),
                "reason": condition.get("reason"),
                "message": condition.get("message"),
                "last_transition_time": condition.get("lastTransitionTime"),
            }
        )
    return output


def _extract_owner_refs(metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    refs: List[Dict[str, Any]] = []
    for ref in metadata.get("ownerReferences") or []:
        refs.append(
            {
                "kind": ref.get("kind"),
                "name": ref.get("name"),
                "uid": ref.get("uid"),
                "controller": bool(ref.get("controller", False)),
            }
        )
    return refs


def _extract_volumes(pod_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    volumes: List[Dict[str, Any]] = []
    for volume in pod_spec.get("volumes") or []:
        volume_type = "unknown"
        for key in volume.keys():
            if key != "name":
                volume_type = key
                break
        volumes.append({"name": volume.get("name"), "type": volume_type})
    return volumes


def _extract_ports(container_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    ports: List[Dict[str, Any]] = []
    for port in container_spec.get("ports") or []:
        ports.append(
            {
                "name": port.get("name"),
                "container_port": port.get("containerPort"),
                "protocol": port.get("protocol", "TCP"),
            }
        )
    return ports


def _parse_top_pods(text: str) -> Dict[Tuple[str, str], Dict[str, str]]:
    usage: Dict[Tuple[str, str], Dict[str, str]] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split()
        if len(parts) < 4:
            continue
        namespace, pod_name, cpu, memory = parts[0], parts[1], parts[2], parts[3]
        usage[(namespace, pod_name)] = {"cpu": cpu, "memory": memory}
    return usage


def _parse_k8s_cpu(cpu_str: str | None) -> float | None:
    """Convert Kubernetes CPU format (e.g., '100m', '1', '500m') to millicores (float)."""
    if not cpu_str:
        return None
    cpu_str = cpu_str.strip().lower()
    try:
        if cpu_str.endswith('m'):
            return float(cpu_str[:-1])
        else:
            return float(cpu_str) * 1000
    except (ValueError, IndexError):
        return None


def _parse_k8s_memory(mem_str: str | None) -> float | None:
    """Convert Kubernetes memory format (e.g., '152Mi', '1Gi', '512') to bytes (float)."""
    if not mem_str:
        return None
    mem_str = mem_str.strip().upper()
    try:
        if mem_str.endswith('KI'):
            return float(mem_str[:-2]) * 1024
        elif mem_str.endswith('K'):
            return float(mem_str[:-1]) * 1000
        elif mem_str.endswith('MI'):
            return float(mem_str[:-2]) * 1024 * 1024
        elif mem_str.endswith('M'):
            return float(mem_str[:-1]) * 1000 * 1000
        elif mem_str.endswith('GI'):
            return float(mem_str[:-2]) * 1024 * 1024 * 1024
        elif mem_str.endswith('G'):
            return float(mem_str[:-1]) * 1000 * 1000 * 1000
        elif mem_str.endswith('TI'):
            return float(mem_str[:-2]) * 1024 * 1024 * 1024 * 1024
        elif mem_str.endswith('T'):
            return float(mem_str[:-1]) * 1000 * 1000 * 1000 * 1000
        elif mem_str.endswith('PI'):
            return float(mem_str[:-2]) * 1024 * 1024 * 1024 * 1024 * 1024
        elif mem_str.endswith('P'):
            return float(mem_str[:-1]) * 1000 * 1000 * 1000 * 1000 * 1000
        else:
            return float(mem_str)
    except (ValueError, IndexError):
        return None


def _index_warning_events(events_items: List[Dict[str, Any]]) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    indexed: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}

    for event in events_items:
        involved = event.get("involvedObject") or {}
        if involved.get("kind") != "Pod":
            continue

        namespace = event.get("metadata", {}).get("namespace", "")
        pod_name = involved.get("name", "")
        if not namespace or not pod_name:
            continue

        detail = {
            "type": event.get("type"),
            "reason": event.get("reason"),
            "message": event.get("message"),
            "count": event.get("count", 1),
            "first_timestamp": event.get("firstTimestamp"),
            "last_timestamp": event.get("lastTimestamp"),
            "event_time": event.get("eventTime"),
            "reporting_controller": event.get("reportingController"),
        }
        key = (namespace, pod_name)
        indexed.setdefault(key, []).append(detail)

    for key in indexed:
        indexed[key].sort(
            key=lambda item: item.get("event_time") or item.get("last_timestamp") or item.get("first_timestamp") or ""
        )
    return indexed


def _service_targets_pod(service: Dict[str, Any], pod_labels: Dict[str, str]) -> bool:
    selector = (service.get("spec") or {}).get("selector") or {}
    if not selector:
        return False
    for key, value in selector.items():
        if pod_labels.get(key) != value:
            return False
    return True


def _services_for_pod(
    namespace: str,
    pod_labels: Dict[str, str],
    services_items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    matched: List[Dict[str, Any]] = []
    for service in services_items:
        service_meta = service.get("metadata") or {}
        service_spec = service.get("spec") or {}
        if service_meta.get("namespace") != namespace:
            continue
        if not _service_targets_pod(service, pod_labels):
            continue

        service_ports = []
        for port in service_spec.get("ports") or []:
            service_ports.append(
                {
                    "name": port.get("name"),
                    "port": port.get("port"),
                    "target_port": port.get("targetPort"),
                    "protocol": port.get("protocol"),
                    "node_port": port.get("nodePort"),
                }
            )

        matched.append(
            {
                "name": service_meta.get("name"),
                "type": service_spec.get("type"),
                "cluster_ip": service_spec.get("clusterIP"),
                "external_ips": service_spec.get("externalIPs") or [],
                "ports": service_ports,
            }
        )
    return matched


def _get_container_log_tail(
    namespace: str,
    pod_name: str,
    container_name: str,
    tail_lines: int,
    previous: bool,
) -> Dict[str, Any]:
    args = [
        "logs",
        pod_name,
        "-n",
        namespace,
        "-c",
        container_name,
        "--tail",
        str(tail_lines),
    ]
    if previous:
        args.append("--previous")

    output, error = _run_kubectl_text(args, timeout=12)
    if error:
        return {"available": False, "error": error, "tail": ""}

    text = (output or "").strip()
    return {
        "available": True,
        "error": None,
        "tail": _tail_text(text),
    }


def _container_details(
    namespace: str,
    pod_name: str,
    pod_spec: Dict[str, Any],
    pod_status: Dict[str, Any],
    include_logs: bool,
    log_tail_lines: int,
) -> Dict[str, Any]:
    status_by_name = {
        container_status.get("name", ""): container_status
        for container_status in pod_status.get("containerStatuses") or []
    }
    init_status_by_name = {
        container_status.get("name", ""): container_status
        for container_status in pod_status.get("initContainerStatuses") or []
    }

    def build(entries: List[Dict[str, Any]], status_lookup: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        output: List[Dict[str, Any]] = []
        for container in entries:
            name = container.get("name", "")
            container_status = status_lookup.get(name, {})
            state = container_status.get("state") or {}
            last_state = container_status.get("lastState") or {}
            waiting = (state.get("waiting") or {})
            terminated = (state.get("terminated") or {})
            last_terminated = (last_state.get("terminated") or {})
            restart_count = int(container_status.get("restartCount", 0))

            details: Dict[str, Any] = {
                "name": name,
                "image": container.get("image"),
                "image_id": container_status.get("imageID"),
                "ready": bool(container_status.get("ready", False)),
                "started": container_status.get("started"),
                "restart_count": restart_count,
                "state": state,
                "last_state": last_state,
                "waiting_reason": waiting.get("reason"),
                "waiting_message": waiting.get("message"),
                "termination_reason": terminated.get("reason") or last_terminated.get("reason"),
                "termination_exit_code": terminated.get("exitCode") or last_terminated.get("exitCode"),
                "resources": {
                    "requests": (container.get("resources") or {}).get("requests") or {},
                    "limits": (container.get("resources") or {}).get("limits") or {},
                },
                "ports": _extract_ports(container),
                "volume_mounts": [
                    {
                        "name": mount.get("name"),
                        "mount_path": mount.get("mountPath"),
                        "read_only": bool(mount.get("readOnly", False)),
                    }
                    for mount in container.get("volumeMounts") or []
                ],
                "probes": {
                    "liveness": _probe_summary(container.get("livenessProbe")),
                    "readiness": _probe_summary(container.get("readinessProbe")),
                    "startup": _probe_summary(container.get("startupProbe")),
                },
                "recent_logs": {"current": None, "previous": None},
            }

            if include_logs:
                details["recent_logs"]["current"] = _get_container_log_tail(
                    namespace=namespace,
                    pod_name=pod_name,
                    container_name=name,
                    tail_lines=log_tail_lines,
                    previous=False,
                )
                details["recent_logs"]["previous"] = _get_container_log_tail(
                    namespace=namespace,
                    pod_name=pod_name,
                    container_name=name,
                    tail_lines=log_tail_lines,
                    previous=True,
                )

            output.append(details)
        return output

    return {
        "containers": build(pod_spec.get("containers") or [], status_by_name),
        "init_containers": build(pod_spec.get("initContainers") or [], init_status_by_name),
    }


def _extract_pods(
    items: List[Dict[str, Any]],
    services_items: List[Dict[str, Any]],
    warning_events: Dict[Tuple[str, str], List[Dict[str, Any]]],
    top_usage: Dict[Tuple[str, str], Dict[str, str]],
    include_logs: bool,
    log_tail_lines: int,
) -> List[Dict[str, Any]]:
    pods: List[Dict[str, Any]] = []
    for item in items:
        metadata = item.get("metadata", {})
        spec = item.get("spec", {})
        status = item.get("status", {})
        namespace = metadata.get("namespace", "")
        pod_name = metadata.get("name", "")
        pod_labels = metadata.get("labels") or {}

        all_statuses = []
        all_statuses.extend(status.get("initContainerStatuses") or [])
        all_statuses.extend(status.get("containerStatuses") or [])

        container_data = _container_details(
            namespace=namespace,
            pod_name=pod_name,
            pod_spec=spec,
            pod_status=status,
            include_logs=include_logs,
            log_tail_lines=log_tail_lines,
        )

        pod_warning_events = warning_events.get((namespace, pod_name), [])

        termination_signals = []
        for container in container_data["containers"] + container_data["init_containers"]:
            reason = container.get("termination_reason")
            if reason in {"OOMKilled", "Evicted", "Preempted"}:
                termination_signals.append(
                    {
                        "container": container.get("name"),
                        "reason": reason,
                        "exit_code": container.get("termination_exit_code"),
                    }
                )

        # Parse metrics from top_usage (if available)
        usage_data = top_usage.get((namespace, pod_name))
        cpu_usage = None
        memory_usage = None
        if usage_data:
            cpu_usage = _parse_k8s_cpu(usage_data.get("cpu"))
            memory_usage = _parse_k8s_memory(usage_data.get("memory"))

        pods.append(
            {
                "name": pod_name,
                "pod_name": pod_name,
                "namespace": namespace,
                "status": status.get("phase", "Unknown"),
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "ready": _compute_ready(status),
                "restart_count": _sum_restarts(all_statuses),
                "age": _format_age(metadata.get("creationTimestamp")),
                "identity": {
                    "service_account": spec.get("serviceAccountName"),
                    "labels": pod_labels,
                    "annotations": metadata.get("annotations") or {},
                    "uid": metadata.get("uid"),
                },
                "placement": {
                    "node_name": spec.get("nodeName"),
                    "node_selector": spec.get("nodeSelector") or {},
                    "tolerations": spec.get("tolerations") or [],
                    "affinity": spec.get("affinity") or {},
                    "owner_references": _extract_owner_refs(metadata),
                },
                "lifecycle": {
                    "creation_timestamp": metadata.get("creationTimestamp"),
                    "start_time": status.get("startTime"),
                    "phase": status.get("phase"),
                    "qos_class": status.get("qosClass"),
                    "conditions": _extract_conditions(status),
                },
                "networking": {
                    "pod_ip": status.get("podIP"),
                    "host_ip": status.get("hostIP"),
                    "dns_policy": spec.get("dnsPolicy"),
                    "host_network": bool(spec.get("hostNetwork", False)),
                    "services": _services_for_pod(namespace, pod_labels, services_items),
                },
                "storage": {
                    "volumes": _extract_volumes(spec),
                },
                "container_health": container_data,
                "resources": {
                    "usage": usage_data,
                },
                "events": {
                    "warning_events": pod_warning_events[-10:],
                    "termination_signals": termination_signals,
                },
            }
        )
    return pods


def _deployment_has_any_pod(deployment_name: str, namespace: str, pod_items: List[Dict[str, Any]]) -> bool:
    """Return True if any current pod appears to belong to the deployment."""
    prefix = f"{deployment_name}-"
    for pod in pod_items:
        metadata = pod.get("metadata") or {}
        if metadata.get("namespace") != namespace:
            continue

        owner_refs = metadata.get("ownerReferences") or []
        for owner in owner_refs:
            if owner.get("kind") == "ReplicaSet" and str(owner.get("name", "")).startswith(prefix):
                return True
    return False


def _build_not_running_entries_for_deployments(
    deployment_items: List[Dict[str, Any]],
    pod_items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Build synthetic pod-health rows for deployments that currently have no pods."""
    rows: List[Dict[str, Any]] = []

    for deployment in deployment_items:
        metadata = deployment.get("metadata") or {}
        spec = deployment.get("spec") or {}
        status = deployment.get("status") or {}

        name = metadata.get("name")
        namespace = metadata.get("namespace")
        if not name or not namespace:
            continue

        desired = int(spec.get("replicas", 1) or 0)
        available = int(status.get("availableReplicas", 0) or 0)
        has_any_pod = _deployment_has_any_pod(name, namespace, pod_items)

        if has_any_pod:
            continue

        if desired == 0 or available == 0:
            rows.append(
                {
                    "name": f"{name} (deployment)",
                    "namespace": namespace,
                    "status": "Failed",
                    "display_status": "Not Running",
                    "ready": False,
                    "restart_count": 0,
                    "age": _format_age(metadata.get("creationTimestamp")),
                    "identity": {
                        "service_account": None,
                        "labels": metadata.get("labels") or {},
                        "annotations": metadata.get("annotations") or {},
                        "uid": metadata.get("uid"),
                    },
                    "placement": {
                        "node_name": None,
                        "node_selector": {},
                        "tolerations": [],
                        "affinity": {},
                        "owner_references": [
                            {
                                "kind": "Deployment",
                                "name": name,
                                "uid": metadata.get("uid"),
                                "controller": True,
                            }
                        ],
                    },
                    "lifecycle": {
                        "creation_timestamp": metadata.get("creationTimestamp"),
                        "start_time": None,
                        "phase": "Failed",
                        "qos_class": None,
                        "conditions": [],
                    },
                    "networking": {
                        "pod_ip": None,
                        "host_ip": None,
                        "dns_policy": None,
                        "host_network": False,
                        "services": [],
                    },
                    "storage": {
                        "volumes": [],
                    },
                    "container_health": {
                        "containers": [],
                        "init_containers": [],
                    },
                    "resources": {
                        "usage": None,
                    },
                    "events": {
                        "warning_events": [],
                        "termination_signals": [],
                    },
                    "source": {
                        "kind": "Deployment",
                        "name": name,
                        "desired_replicas": desired,
                        "available_replicas": available,
                    },
                }
            )

    return rows


def _scale_deployment(namespace: str, name: str, replicas: int) -> Tuple[bool, str]:
    try:
        result = subprocess.run(
            ["kubectl", "scale", f"deployment/{name}", "-n", namespace, f"--replicas={replicas}"],
            capture_output=True,
            text=True,
            check=False,
            timeout=45,
        )
    except subprocess.TimeoutExpired:
        return False, f"scale command timed out for {namespace}/{name}"
    except FileNotFoundError:
        return False, "kubectl not found on PATH"
    except Exception as exc:  # Defensive catch to keep API stable.
        return False, f"unexpected error scaling deployment {namespace}/{name}: {exc}"

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        return False, stderr or f"failed to scale deployment {namespace}/{name}"

    return True, (result.stdout or "").strip() or f"scaled {namespace}/{name} to {replicas}"


def _detect_deployments_needing_heal(deployment_items: List[Dict[str, Any]], pod_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for deployment in deployment_items:
        metadata = deployment.get("metadata") or {}
        spec = deployment.get("spec") or {}
        status = deployment.get("status") or {}

        name = metadata.get("name")
        namespace = metadata.get("namespace")
        if not name or not namespace:
            continue

        desired = int(spec.get("replicas", 1) or 0)
        available = int(status.get("availableReplicas", 0) or 0)
        if desired > 0 and available > 0:
            continue

        if not _deployment_has_any_pod(name, namespace, pod_items):
            rows.append(
                {
                    "namespace": namespace,
                    "name": name,
                    "desired_replicas": desired,
                    "available_replicas": available,
                }
            )

    return rows


def _apply_manual_heal_gate(
    pods: List[Dict[str, Any]],
    required: bool,
    window_minutes: int,
) -> Dict[str, Any]:
    pending_count = 0

    for pod in pods:
        pod_events = (pod.get("events") or {}).get("warning_events") or []
        latest_warning = _latest_warning_event_time(pod_events)
        latest_failure_signal = _latest_failure_signal_time(pod_events)
        is_deployment_row = isinstance(pod.get("source"), dict)
        is_healthy = bool(pod.get("ready", False)) and pod.get("status") == "Running"

        if is_deployment_row:
            source = pod.get("source") or {}
            desired = int(source.get("desired_replicas", 0) or 0)
            available = int(source.get("available_replicas", 0) or 0)
            is_healthy = desired > 0 and available >= desired and pod.get("display_status") != "Not Running"

        pending_manual_heal = required and not is_healthy

        pod["healing_gate"] = {
            "required": required,
            "pending_manual_heal": pending_manual_heal,
            "last_warning_event_time": _isoformat_or_none(latest_warning),
            "last_failure_signal_time": _isoformat_or_none(latest_failure_signal),
            "last_manual_triggered_at": _isoformat_or_none(MANUAL_HEAL_LAST_TRIGGERED_AT),
            "healthy": is_healthy,
        }

        if pending_manual_heal:
            pending_count += 1
            pod["display_status"] = "Awaiting Manual Heal"

    return {
        "required": required,
        "window_minutes": window_minutes,
        "pending_count": pending_count,
        "last_manual_triggered_at": _isoformat_or_none(MANUAL_HEAL_LAST_TRIGGERED_AT),
    }


@app.get("/health")
def health() -> Any:
    return jsonify({"status": "ok"})


@app.post("/healing/trigger")
def trigger_healing() -> Any:
    global MANUAL_HEAL_LAST_TRIGGERED_AT

    pod_payload, pod_error = _run_kubectl_json(["get", "pods", "-A", "-o", "json"], timeout=45)
    deployment_payload, deployment_error = _run_kubectl_json(["get", "deployments", "-A", "-o", "json"], timeout=30)

    if pod_error or deployment_error:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Unable to inspect cluster state before healing.",
                    "pod_error": pod_error,
                    "deployment_error": deployment_error,
                }
            ),
            503,
        )

    pod_items = (pod_payload or {}).get("items", [])
    deployment_items = (deployment_payload or {}).get("items", [])
    heal_targets = _detect_deployments_needing_heal(deployment_items, pod_items)

    actions: List[Dict[str, Any]] = []
    for target in heal_targets:
        namespace = target["namespace"]
        name = target["name"]
        replicas = max(1, int(target.get("desired_replicas", 0) or 0))
        ok, message = _scale_deployment(namespace, name, replicas)
        actions.append(
            {
                "namespace": namespace,
                "name": name,
                "replicas": replicas,
                "success": ok,
                "message": message,
            }
        )

    MANUAL_HEAL_LAST_TRIGGERED_AT = datetime.now(timezone.utc)

    return jsonify(
        {
            "status": "accepted",
            "message": "Manual healing trigger processed.",
            "triggered_at": _isoformat_or_none(MANUAL_HEAL_LAST_TRIGGERED_AT),
            "actions": actions,
            "healed_targets": len([action for action in actions if action["success"]]),
        }
    )


@app.get("/pods")
def get_pods() -> Any:
    # Default to false to avoid expensive per-container log calls on large clusters.
    include_logs = request.args.get("include_logs", "false").strip().lower() not in {"0", "false", "no"}
    log_tail_lines = _safe_int(request.args.get("log_tail", "20"), 20)
    if log_tail_lines < 1:
        log_tail_lines = 1
    if log_tail_lines > 200:
        log_tail_lines = 200

    # Check if caller wants simplified format (for dashboard integration)
    simplified = request.args.get("simplified", "false").strip().lower() not in {"0", "false", "no"}

    manual_heal_required = request.args.get("manual_heal_required", "false").strip().lower() not in {
        "0",
        "false",
        "no",
    }
    manual_heal_window_minutes = _safe_int(request.args.get("manual_heal_window_minutes", "10"), 10)
    if manual_heal_window_minutes < 1:
        manual_heal_window_minutes = 1
    if manual_heal_window_minutes > 120:
        manual_heal_window_minutes = 120

    payload, error = _run_kubectl_json(["get", "pods", "-A", "-o", "json"], timeout=45)
    if error:
        return (
            jsonify(
                {
                    "error": "failed_to_fetch_pods",
                    "message": "Unable to query cluster pods via kubectl.",
                    "details": error,
                }
            ),
            503,
        )

    services_payload, services_error = _run_kubectl_json(["get", "services", "-A", "-o", "json"], timeout=30)
    deployments_payload, deployments_error = _run_kubectl_json(["get", "deployments", "-A", "-o", "json"], timeout=30)
    events_payload, events_error = _run_kubectl_json(
        ["get", "events", "-A", "-o", "json"],
        timeout=30,
    )
    top_text, top_error = _run_kubectl_text(["top", "pods", "-A", "--no-headers"], timeout=20)

    items = payload.get("items", []) if payload else []
    services_items = services_payload.get("items", []) if services_payload else []
    deployment_items = deployments_payload.get("items", []) if deployments_payload else []
    events_items = events_payload.get("items", []) if events_payload else []
    warning_events = _index_warning_events(events_items)
    top_usage = _parse_top_pods(top_text or "") if top_text else {}

    pods = _extract_pods(
        items=items,
        services_items=services_items,
        warning_events=warning_events,
        top_usage=top_usage,
        include_logs=include_logs,
        log_tail_lines=log_tail_lines,
    )
    pods.extend(_build_not_running_entries_for_deployments(deployment_items, items))
    manual_healing = _apply_manual_heal_gate(
        pods=pods,
        required=manual_heal_required,
        window_minutes=manual_heal_window_minutes,
    )

    # If simplified format is requested, return a minimal pod list
    if simplified:
        simplified_pods = [
            {
                "pod_name": p.get("pod_name"),
                "namespace": p.get("namespace"),
                "status": p.get("status"),
                "cpu_usage": p.get("cpu_usage"),
                "memory_usage": p.get("memory_usage"),
                "restart_count": p.get("restart_count"),
            }
            for p in pods
        ]
        response = make_response(
            jsonify({
                "pods": simplified_pods,
                "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            })
        )
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    response = make_response(
        jsonify(
            {
                "count": len(pods),
                "collection": {
                    "include_logs": include_logs,
                    "log_tail_lines": log_tail_lines,
                    "top_metrics_available": top_error is None,
                    "top_metrics_error": top_error,
                    "events_available": events_error is None,
                    "events_error": events_error,
                    "services_available": services_error is None,
                    "services_error": services_error,
                    "deployments_available": deployments_error is None,
                    "deployments_error": deployments_error,
                },
                "manual_healing": manual_healing,
                "pods": pods,
            }
        )
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
