import subprocess
import json

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running command: {cmd}\n{result.stderr}")
        return None
    return result.stdout.strip()

print("--- Kubernetes Cluster Status ---")

print("\n1. Pod Status (default namespace):")
pods = run_cmd("kubectl get pods -o wide")
if pods:
    print(pods)

print("\n2. Service Endpoints:")
services = run_cmd("kubectl get svc")
if services:
    print(services)

print("\n3. Recent logs from an OpenTelemetry Collector pod (if present):")
# Try to find the otel pod using typical labels
otel_pods_json = run_cmd("kubectl get pods -l app.kubernetes.io/name=opentelemetry-collector -o json")
if otel_pods_json:
    try:
        pods_data = json.loads(otel_pods_json)
        if pods_data.get('items'):
            otel_pod_name = pods_data['items'][0]['metadata']['name']
            logs = run_cmd(f"kubectl logs {otel_pod_name} --tail=20")
            print(f"Logs from {otel_pod_name}:")
            print(logs)
        else:
            print("No OpenTelemetry Collector pods found with label app.kubernetes.io/name=opentelemetry-collector.")
            print("You may need to adjust the label selector in the script if your pod uses a different label.")
    except Exception as e:
        print(f"Failed to parse pod JSON: {e}")
