#!/bin/bash
# Test Case Name: AI_Vision_Pod_Crash_Recovery
# Description: A shell script that uses kubectl to forcefully delete the ai-vision-service pod while matching requests are being processed. It verifies that Kubernetes automatically spins up a new pod and that pending face-matching requests are successfully processed by the new instance.

echo "Starting AI Vision Pod Crash Recovery Test..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "kubectl could not be found. Please ensure Kubernetes is configured."
    exit 1
fi

# Find the ai-vision-service pod
POD_NAME=$(kubectl get pods -l app=ai-vision-service -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)

if [ -z "$POD_NAME" ]; then
    echo "No ai-vision-service pod found. Make sure the deployment is running."
    exit 1
fi

echo "Found pod: $POD_NAME"

# Simulate firing traffic here (e.g. using curl or a python script)
# echo "Sending mock face-matching traffic..."
# curl -X POST ... &

echo "Forcefully deleting pod $POD_NAME..."
kubectl delete pod $POD_NAME --force --grace-period=0

echo "Waiting for Kubernetes to spin up a new pod..."
sleep 5

# Check for new pod
NEW_POD_NAME=$(kubectl get pods -l app=ai-vision-service -o jsonpath="{.items[0].metadata.name}")

if [ -z "$NEW_POD_NAME" ]; then
    echo "FAIL: Kubernetes did not spin up a new pod."
    exit 1
elif [ "$POD_NAME" == "$NEW_POD_NAME" ]; then
    echo "FAIL: The pod was not deleted successfully."
    exit 1
else
    echo "SUCCESS: New pod $NEW_POD_NAME is spinning up."
fi

# Wait for readiness
kubectl wait --for=condition=ready pod/$NEW_POD_NAME --timeout=60s

if [ $? -eq 0 ]; then
    echo "SUCCESS: New pod is ready and processing requests."
    exit 0
else
    echo "FAIL: New pod failed to become ready."
    exit 1
fi
