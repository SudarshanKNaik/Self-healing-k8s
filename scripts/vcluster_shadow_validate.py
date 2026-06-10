from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class ShadowConfig:
    source_kind: str
    source_name: str
    source_namespace: str
    vcluster_name: str
    vcluster_namespace: str
    vcluster_values_file: str
    sandbox_namespace: str
    observation_seconds: int
    poll_seconds: int
    cleanup: bool
    replicas: Optional[int]
    cpu_request: Optional[str]
    cpu_limit: Optional[str]
    memory_request: Optional[str]
    memory_limit: Optional[str]
    env_vars: Dict[str, str]
    restart_policy: Optional[str]


class ShadowValidationError(RuntimeError):
    pass


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short_name(name: str, suffix: str, max_len: int = 63) -> str:
    combined = f"{name}-{suffix}"
    if len(combined) <= max_len:
        return combined
    trim = max_len - len(suffix) - 1
    return f"{name[:trim]}-{suffix}"


def _run(
    cmd: List[str],
    timeout: int = 60,
    stdin_text: Optional[str] = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        cmd,
        input=stdin_text,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if check and proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        detail = stderr or stdout or "command failed"
        raise ShadowValidationError(f"{' '.join(cmd)} -> {detail}")
    return proc


def _require_binary(binary: str) -> None:
    if shutil.which(binary) is None:
        raise ShadowValidationError(f"Missing required binary on PATH: {binary}")


def _run_kubectl_json(args: List[str], timeout: int = 60) -> Dict[str, Any]:
    proc = _run(["kubectl", *args], timeout=timeout)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ShadowValidationError(f"Failed to parse kubectl JSON output: {exc}") from exc


def _run_vcluster_kubectl(
    cfg: ShadowConfig,
    kubectl_args: List[str],
    timeout: int = 60,
    stdin_text: Optional[str] = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        "vcluster",
        "connect",
        cfg.vcluster_name,
        "-n",
        cfg.vcluster_namespace,
        "--",
        "kubectl",
        *kubectl_args,
    ]
    return _run(cmd, timeout=timeout, stdin_text=stdin_text, check=check)


def _ensure_namespace(namespace: str) -> None:
    exists = _run(["kubectl", "get", "ns", namespace], check=False)
    if exists.returncode == 0:
        return
    _run(["kubectl", "create", "ns", namespace], timeout=45)


def _vcluster_exists(name: str, namespace: str) -> bool:
    proc = _run(["vcluster", "list", "-n", namespace], check=False, timeout=45)
    if proc.returncode != 0:
        return False

    for line in (proc.stdout or "").splitlines():
        parts = line.split()
        if parts and parts[0] == name:
            return True
    return False


def ensure_vcluster(cfg: ShadowConfig) -> None:
    _ensure_namespace(cfg.vcluster_namespace)

    if _vcluster_exists(cfg.vcluster_name, cfg.vcluster_namespace):
        return

    cmd = [
        "vcluster",
        "create",
        cfg.vcluster_name,
        "-n",
        cfg.vcluster_namespace,
        "--connect=false",
    ]

    if cfg.vcluster_values_file:
        cmd.extend(["--values", cfg.vcluster_values_file])

    _run(cmd, timeout=300)


def ensure_sandbox_namespace(cfg: ShadowConfig) -> None:
    proc = _run_vcluster_kubectl(
        cfg,
        ["get", "ns", cfg.sandbox_namespace],
        timeout=45,
        check=False,
    )
    if proc.returncode == 0:
        return
    _run_vcluster_kubectl(cfg, ["create", "ns", cfg.sandbox_namespace], timeout=45)


def _clean_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = deepcopy(meta)
    for field in [
        "uid",
        "resourceVersion",
        "generation",
        "creationTimestamp",
        "managedFields",
        "selfLink",
    ]:
        cleaned.pop(field, None)

    annotations = cleaned.get("annotations") or {}
    annotations.pop("kubectl.kubernetes.io/last-applied-configuration", None)
    if annotations:
        cleaned["annotations"] = annotations
    else:
        cleaned.pop("annotations", None)

    return cleaned


def _inject_or_replace_env(container: Dict[str, Any], env_vars: Dict[str, str]) -> None:
    if not env_vars:
        return

    env_list = container.get("env") or []
    env_index = {item.get("name"): i for i, item in enumerate(env_list) if item.get("name")}

    for key, value in env_vars.items():
        record = {"name": key, "value": value}
        if key in env_index:
            env_list[env_index[key]] = record
        else:
            env_list.append(record)

    container["env"] = env_list


def _apply_resource_mutations(container: Dict[str, Any], cfg: ShadowConfig) -> None:
    needs_resource_change = any(
        [cfg.cpu_request, cfg.cpu_limit, cfg.memory_request, cfg.memory_limit]
    )
    if not needs_resource_change:
        return

    resources = container.get("resources") or {}
    requests = resources.get("requests") or {}
    limits = resources.get("limits") or {}

    if cfg.cpu_request:
        requests["cpu"] = cfg.cpu_request
    if cfg.memory_request:
        requests["memory"] = cfg.memory_request
    if cfg.cpu_limit:
        limits["cpu"] = cfg.cpu_limit
    if cfg.memory_limit:
        limits["memory"] = cfg.memory_limit

    resources["requests"] = requests
    resources["limits"] = limits
    container["resources"] = resources


def _sanitize_pod_spec(pod_spec: Dict[str, Any]) -> None:
    for field in ["nodeName", "hostIP", "hostIPC", "hostPID", "hostNetwork"]:
        pod_spec.pop(field, None)


def _containers_from_manifest(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    kind = manifest.get("kind", "")
    if kind == "Deployment":
        template_spec = ((manifest.get("spec") or {}).get("template") or {}).get("spec") or {}
        return template_spec.get("containers") or []
    if kind == "Pod":
        pod_spec = (manifest.get("spec") or {})
        return pod_spec.get("containers") or []
    return []


def build_shadow_manifest(cfg: ShadowConfig, source_obj: Dict[str, Any], run_id: str) -> Dict[str, Any]:
    kind = source_obj.get("kind")
    if kind not in {"Deployment", "Pod"}:
        raise ShadowValidationError("Only Deployment and Pod kinds are supported")

    manifest = deepcopy(source_obj)
    manifest.pop("status", None)

    metadata = _clean_metadata(manifest.get("metadata") or {})
    source_name = metadata.get("name", cfg.source_name)
    shadow_name = _short_name(f"shadow-{source_name}", run_id)

    labels = metadata.get("labels") or {}
    labels["shadow.validation/run-id"] = run_id
    labels["shadow.validation/source-kind"] = cfg.source_kind.lower()
    labels["shadow.validation/source-name"] = cfg.source_name
    labels["shadow.validation/source-namespace"] = cfg.source_namespace

    metadata["name"] = shadow_name
    metadata["namespace"] = cfg.sandbox_namespace
    metadata["labels"] = labels
    manifest["metadata"] = metadata

    if kind == "Deployment":
        spec = manifest.get("spec") or {}
        if cfg.replicas is not None:
            spec["replicas"] = cfg.replicas

        selector = spec.get("selector") or {}
        match_labels = selector.get("matchLabels") or {}
        match_labels["shadow.validation/run-id"] = run_id
        selector["matchLabels"] = match_labels
        spec["selector"] = selector

        template = spec.get("template") or {}
        template_meta = _clean_metadata(template.get("metadata") or {})
        template_labels = template_meta.get("labels") or {}
        template_labels["shadow.validation/run-id"] = run_id
        template_meta["labels"] = template_labels
        template["metadata"] = template_meta

        template_spec = template.get("spec") or {}
        _sanitize_pod_spec(template_spec)

        for container in template_spec.get("containers") or []:
            _inject_or_replace_env(container, cfg.env_vars)
            _apply_resource_mutations(container, cfg)

        template["spec"] = template_spec
        spec["template"] = template
        manifest["spec"] = spec

    if kind == "Pod":
        spec = manifest.get("spec") or {}
        _sanitize_pod_spec(spec)

        if cfg.restart_policy:
            spec["restartPolicy"] = cfg.restart_policy

        for container in spec.get("containers") or []:
            _inject_or_replace_env(container, cfg.env_vars)
            _apply_resource_mutations(container, cfg)

        manifest["spec"] = spec

    return manifest


def apply_manifest_in_vcluster(cfg: ShadowConfig, manifest: Dict[str, Any]) -> None:
    manifest_text = json.dumps(manifest)
    _run_vcluster_kubectl(
        cfg,
        ["apply", "-f", "-"],
        timeout=90,
        stdin_text=manifest_text,
    )


def _collect_pod_statuses(cfg: ShadowConfig, run_id: str) -> List[Dict[str, Any]]:
    proc = _run_vcluster_kubectl(
        cfg,
        [
            "get",
            "pods",
            "-n",
            cfg.sandbox_namespace,
            "-l",
            f"shadow.validation/run-id={run_id}",
            "-o",
            "json",
        ],
        timeout=45,
    )
    payload = json.loads(proc.stdout)
    return payload.get("items") or []


def _sum_restarts(pod: Dict[str, Any]) -> int:
    statuses = ((pod.get("status") or {}).get("containerStatuses") or [])
    return sum(int(item.get("restartCount", 0)) for item in statuses)


def _is_pod_ready(pod: Dict[str, Any]) -> bool:
    statuses = ((pod.get("status") or {}).get("containerStatuses") or [])
    if statuses:
        return all(bool(item.get("ready", False)) for item in statuses)

    for cond in ((pod.get("status") or {}).get("conditions") or []):
        if cond.get("type") == "Ready":
            return cond.get("status") == "True"
    return False


def _try_top_usage(cfg: ShadowConfig) -> Dict[str, Dict[str, str]]:
    proc = _run_vcluster_kubectl(
        cfg,
        ["top", "pods", "-n", cfg.sandbox_namespace, "--no-headers"],
        timeout=25,
        check=False,
    )
    if proc.returncode != 0:
        return {}

    usage: Dict[str, Dict[str, str]] = {}
    for line in (proc.stdout or "").splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        usage[parts[0]] = {"cpu": parts[1], "memory": parts[2]}
    return usage


def _get_pod_logs(cfg: ShadowConfig, pod_name: str, tail_lines: int = 50) -> str:
    proc = _run_vcluster_kubectl(
        cfg,
        [
            "logs",
            pod_name,
            "-n",
            cfg.sandbox_namespace,
            "--tail",
            str(tail_lines),
        ],
        timeout=30,
        check=False,
    )
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").strip()


def observe_and_evaluate(cfg: ShadowConfig, workload_name: str, run_id: str) -> Dict[str, Any]:
    start = time.time()
    last_pods: List[Dict[str, Any]] = []

    while time.time() - start < cfg.observation_seconds:
        last_pods = _collect_pod_statuses(cfg, run_id)
        time.sleep(max(1, cfg.poll_seconds))

    usage = _try_top_usage(cfg)

    pod_summaries: List[Dict[str, Any]] = []
    total_restarts = 0
    stable = True
    notes: List[str] = []

    if not last_pods:
        stable = False
        notes.append("No pods were scheduled in the observation window")

    for pod in last_pods:
        meta = pod.get("metadata") or {}
        status = pod.get("status") or {}
        pod_name = meta.get("name", "")
        phase = status.get("phase", "Unknown")
        restarts = _sum_restarts(pod)
        ready = _is_pod_ready(pod)
        total_restarts += restarts

        if phase not in {"Running", "Succeeded"} or not ready:
            stable = False

        if restarts > 0:
            stable = False
            notes.append(f"Pod {pod_name} restarted {restarts} time(s)")

        waiting_messages: List[str] = []
        for cs in status.get("containerStatuses") or []:
            waiting = ((cs.get("state") or {}).get("waiting") or {})
            if waiting.get("reason"):
                waiting_messages.append(
                    f"{cs.get('name')}: {waiting.get('reason')} {waiting.get('message', '').strip()}".strip()
                )

        if waiting_messages:
            stable = False
            notes.extend(waiting_messages)

        pod_summaries.append(
            {
                "name": pod_name,
                "phase": phase,
                "ready": ready,
                "restarts": restarts,
                "usage": usage.get(pod_name),
                "logs_tail": _get_pod_logs(cfg, pod_name),
            }
        )

    if stable and not notes:
        notes.append("Workload remained healthy during the observation window")

    result = {
        "workload": workload_name,
        "status": "stable" if stable else "unstable",
        "restarts": total_restarts,
        "notes": "; ".join(notes[:6]),
        "details": {
            "run_id": run_id,
            "observed_at": _now_utc(),
            "observation_seconds": cfg.observation_seconds,
            "sandbox_namespace": cfg.sandbox_namespace,
            "pods": pod_summaries,
        },
    }
    return result


def cleanup_shadow(cfg: ShadowConfig, manifest: Dict[str, Any]) -> None:
    kind = manifest.get("kind", "").lower()
    name = ((manifest.get("metadata") or {}).get("name"))
    if not kind or not name:
        return

    _run_vcluster_kubectl(
        cfg,
        [
            "delete",
            kind,
            name,
            "-n",
            cfg.sandbox_namespace,
            "--ignore-not-found=true",
            "--wait=false",
        ],
        timeout=30,
        check=False,
    )


def _parse_env(env_items: List[str]) -> Dict[str, str]:
    envs: Dict[str, str] = {}
    for item in env_items:
        if "=" not in item:
            raise ShadowValidationError(f"Invalid --env value (expected KEY=VALUE): {item}")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ShadowValidationError("Environment variable name cannot be empty")
        envs[key] = value
    return envs


def parse_args() -> ShadowConfig:
    parser = argparse.ArgumentParser(
        description="Run shadow workload validation in an isolated vCluster sandbox.",
    )
    parser.add_argument("--source-kind", choices=["deployment", "pod"], required=True)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--source-namespace", default="default")

    parser.add_argument("--vcluster-name", default="shadow-sandbox")
    parser.add_argument("--vcluster-namespace", default="vcluster-sandbox")
    parser.add_argument("--vcluster-values", default="k8s/vcluster-values.yaml")
    parser.add_argument("--sandbox-namespace", default="shadow-validation")

    parser.add_argument("--window-seconds", type=int, default=45)
    parser.add_argument("--poll-seconds", type=int, default=5)
    parser.add_argument("--cleanup", dest="cleanup", action="store_true")
    parser.add_argument("--no-cleanup", dest="cleanup", action="store_false")
    parser.set_defaults(cleanup=True)

    parser.add_argument("--replicas", type=int)
    parser.add_argument("--cpu-request")
    parser.add_argument("--cpu-limit")
    parser.add_argument("--memory-request")
    parser.add_argument("--memory-limit")
    parser.add_argument("--env", action="append", default=[])
    parser.add_argument("--restart-policy", choices=["Always", "OnFailure", "Never"])
    args = parser.parse_args()

    if args.window_seconds < 5:
        raise ShadowValidationError("--window-seconds must be at least 5")

    if args.poll_seconds < 1:
        raise ShadowValidationError("--poll-seconds must be at least 1")

    return ShadowConfig(
        source_kind=args.source_kind,
        source_name=args.source_name,
        source_namespace=args.source_namespace,
        vcluster_name=args.vcluster_name,
        vcluster_namespace=args.vcluster_namespace,
        vcluster_values_file=args.vcluster_values,
        sandbox_namespace=args.sandbox_namespace,
        observation_seconds=args.window_seconds,
        poll_seconds=args.poll_seconds,
        cleanup=args.cleanup,
        replicas=args.replicas,
        cpu_request=args.cpu_request,
        cpu_limit=args.cpu_limit,
        memory_request=args.memory_request,
        memory_limit=args.memory_limit,
        env_vars=_parse_env(args.env),
        restart_policy=args.restart_policy,
    )


def main() -> int:
    try:
        cfg = parse_args()
        _require_binary("kubectl")
        _require_binary("vcluster")

        ensure_vcluster(cfg)
        ensure_sandbox_namespace(cfg)

        source_obj = _run_kubectl_json(
            [
                "get",
                cfg.source_kind,
                cfg.source_name,
                "-n",
                cfg.source_namespace,
                "-o",
                "json",
            ],
            timeout=45,
        )

        run_id = str(int(time.time()))[-8:]
        manifest = build_shadow_manifest(cfg, source_obj, run_id)
        apply_manifest_in_vcluster(cfg, manifest)

        workload_name = (manifest.get("metadata") or {}).get("name", "shadow-workload")
        result = observe_and_evaluate(cfg, workload_name, run_id)

        print(json.dumps(result, indent=2))

        if cfg.cleanup:
            cleanup_shadow(cfg, manifest)

        return 0
    except ShadowValidationError as exc:
        print(json.dumps({"error": str(exc), "status": "failed"}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
