#!/bin/bash

# Script to invalidate/restore the MongoDB password secret
# and bounce the API pods to trigger CrashLoopBackOff errors in Instana

set -e

NAMESPACE="${NAMESPACE:-library-system}"
SECRET_NAME="mongodb-credentials"
# ⚠️  Set MONGODB_PASSWORD to the same password you used in k8s-manifests/all-in-one.yaml
CORRECT_PASSWORD="${MONGODB_PASSWORD:-<your-mongodb-password>}"
BAD_PASSWORD="${MONGODB_BAD_PASSWORD:-<your-bad-mongodb-password>}"

# ==========================================
echo "=========================================="
echo "MongoDB Secret Invalidation Script"
echo "=========================================="
echo ""

# Check prerequisites
if ! command -v oc &> /dev/null; then
    echo "❌ Error: oc CLI is not installed"
    exit 1
fi

if ! oc whoami &> /dev/null; then
    echo "❌ Error: Not logged in to OpenShift"
    exit 1
fi

echo "✓ Logged in as: $(oc whoami)"
echo "✓ Namespace:    $NAMESPACE"
echo ""

# ==========================================
show_menu() {
    echo "What would you like to do?"
    echo ""
    echo "  1) Invalidate password  → triggers CrashLoopBackOff / errors in Instana"
    echo "  2) Restore password     → restores normal operation"
    echo "  3) Show current status  → show pod and secret state"
    echo "  0) Exit"
    echo ""
    read -p "Enter your choice: " -n 1 -r CHOICE
    echo ""
}

# ==========================================
invalidate_secret() {
    echo ""
    echo "Step 1: Patching secret with bad password..."
    oc patch secret $SECRET_NAME -n $NAMESPACE \
        --type='json' \
        -p="[{\"op\": \"replace\", \"path\": \"/data/password\", \"value\": \"$(echo -n $BAD_PASSWORD | base64)\"}]"
    echo "✓ Secret updated — password is now invalid"
    echo ""

    echo "Step 2: Restarting books-api and users-api pods..."
    oc rollout restart deployment/books-api deployment/users-api -n $NAMESPACE
    echo "✓ Pods restarted"
    echo ""

    echo "Step 3: Waiting for pods to reflect new state..."
    sleep 10
    oc get pods -n $NAMESPACE -l 'app in (books-api,users-api)'
    echo ""
    echo "=========================================="
    echo "✅ Done! Monitor Instana for errors."
    echo "=========================================="
    echo ""
    echo "Pods will enter CrashLoopBackOff as MongoDB"
    echo "authentication fails with the wrong password."
    echo ""
    echo "Watch pods:  oc get pods -n $NAMESPACE -w"
    echo "Watch logs:  oc logs -f deployment/books-api -n $NAMESPACE"
    echo ""
    echo "To restore:  NAMESPACE=$NAMESPACE ./invalidate-secret.sh  → choose option 2"
}

# ==========================================
restore_secret() {
    echo ""
    echo "Step 1: Restoring correct password in secret..."
    oc patch secret $SECRET_NAME -n $NAMESPACE \
        --type='json' \
        -p="[{\"op\": \"replace\", \"path\": \"/data/password\", \"value\": \"$(echo -n $CORRECT_PASSWORD | base64)\"}]"
    echo "✓ Secret restored — password is correct again"
    echo ""

    echo "Step 2: Restarting books-api and users-api pods..."
    oc rollout restart deployment/books-api deployment/users-api -n $NAMESPACE
    echo "✓ Pods restarted"
    echo ""

    echo "Step 3: Waiting for pods to become ready..."
    oc rollout status deployment/books-api -n $NAMESPACE --timeout=2m || true
    oc rollout status deployment/users-api -n $NAMESPACE --timeout=2m || true
    echo ""
    oc get pods -n $NAMESPACE -l 'app in (books-api,users-api)'
    echo ""
    echo "=========================================="
    echo "✅ Done! Application restored to normal."
    echo "=========================================="
}

# ==========================================
show_status() {
    echo ""
    echo "--- Pods ---"
    oc get pods -n $NAMESPACE
    echo ""
    echo "--- Secret (decoded password) ---"
    CURRENT=$(oc get secret $SECRET_NAME -n $NAMESPACE -o jsonpath='{.data.password}' | base64 -d)
    if [ "$CURRENT" = "$CORRECT_PASSWORD" ]; then
        echo "  password: ✅ VALID ($CORRECT_PASSWORD)"
    else
        echo "  password: ❌ INVALID ($CURRENT)"
    fi
    echo ""
}

# ==========================================
# Main loop
while true; do
    show_menu
    case $CHOICE in
        1) invalidate_secret ;;
        2) restore_secret ;;
        3) show_status ;;
        0) echo "Exiting."; exit 0 ;;
        *) echo "Invalid choice. Please enter 1, 2, 3, or 0." ;;
    esac
    echo ""
done

# Made with Bob
