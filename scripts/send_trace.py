import json
import urllib.request
import urllib.error
import time
import os

# Load config
config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'endpoints.json')
try:
    with open(config_path, 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    print(f"Error: Could not find config file at {config_path}")
    exit(1)

OTEL_ENDPOINT = config.get("otel_endpoint", "http://localhost:30080/v1/traces")
print(f"Sending trace to {OTEL_ENDPOINT}...")

# Sample Trace Data in OTLP JSON format
trace_data = {
    "resourceSpans": [
        {
            "resource": {
                "attributes": [
                    {
                        "key": "service.name",
                        "value": {
                            "stringValue": "external-testing-service"
                        }
                    }
                ]
            },
            "scopeSpans": [
                {
                    "scope": {
                        "name": "manual-test-script",
                        "version": "1.0.0"
                    },
                    "spans": [
                        {
                            "traceId": "5B8EFFF798C3E5C6B41364F30BB511EF",
                            "spanId": "38EF11270258B0EB",
                            "name": "test-transaction",
                            "kind": 2, 
                            "startTimeUnixNano": str(time.time_ns()),
                            "endTimeUnixNano": str(time.time_ns() + 1000000000), # 1 second later
                            "attributes": [
                                {
                                    "key": "http.method",
                                    "value": {
                                        "stringValue": "GET"
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ]
}

req = urllib.request.Request(OTEL_ENDPOINT)
req.add_header('Content-Type', 'application/json')

try:
    data = json.dumps(trace_data).encode('utf-8')
    response = urllib.request.urlopen(req, data)
    print(f"Trace sent successfully! Response code: {response.getcode()}")
except urllib.error.URLError as e:
    print(f"Failed to send trace: {e}")
    print("Please make sure the OpenTelemetry NodePort is applied and minikube IP is properly configured in config/endpoints.json")
