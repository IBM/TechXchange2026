#!/bin/bash

# Lab Namespace Cleanup Script
# Deletes all user-deployed resources inside one or more OpenShift projects,
# leaving the namespace, service account, and RBAC intact so participants
# can redeploy from scratch.
#
# Usage:
#   ./cleanup-lab-namespace.sh <namespace> [namespace2 ...]
#   ./cleanup-lab-namespace.sh lb1
#   ./cleanup-lab-namespace.sh lb1 lb2 lb3
#   ./cleanup-lab-namespace.sh lb{1..10}   (shell brace expansion)
#
# What is deleted (in order):
#   Deployments, DeploymentConfigs, StatefulSets, DaemonSets, Jobs, CronJobs
#   ReplicaSets, ReplicationControllers
#   Pods (any stragglers)
#   Services, Routes, Ingresses
#   ConfigMaps, Secrets  (skips service-account-token / dockercfg secrets)
#   PersistentVolumeClaims
#   HorizontalPodAutoscalers, PodDisruptionBudgets
#   ServiceAccounts created by the user  (skips default / lab-participant / builder / deployer)
#   RoleBindings created by the user     (skips system: prefixed and the SA admin binding)
#   ImageStreams, BuildConfigs, Builds   (OpenShift-specific)
#
# What is preserved:
#   The namespace/project itself
#   The lab-participant service account and its admin RoleBinding
#   The default, builder, deployer service accounts
#   System secrets and pull-secret tokens

set -euo pipefail

# ─── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
# ──────────────────────────────────────────────────────────────────────────────

# ─── Argument validation ──────────────────────────────────────────────────────
if [[ $# -eq 0 ]]; then
    echo -e "${RED}Usage: $0 <namespace> [namespace2 ...]${RESET}"
    echo ""
    echo "  Examples:"
    echo "    $0 lb1"
    echo "    $0 lb1 lb2 lb3"
    echo "    $0 \$(seq -f 'lb%.0f' 1 10 | tr '\\n' ' ')"
    exit 1
fi
# ──────────────────────────────────────────────────────────────────────────────

# ─── Prerequisite checks ──────────────────────────────────────────────────────
if ! command -v oc &> /dev/null; then
    echo -e "${RED}❌ Error: oc CLI is not installed or not in PATH${RESET}"
    exit 1
fi

if ! oc whoami &> /dev/null; then
    echo -e "${RED}❌ Error: Not logged in to OpenShift. Run 'oc login' first.${RESET}"
    exit 1
fi
# ──────────────────────────────────────────────────────────────────────────────

# Service accounts to preserve (never delete)
PRESERVED_SA="default builder deployer lab-participant pipeline"

# ─── Helper: delete all instances of a resource type in a namespace ───────────
delete_all() {
    local kind="$1"
    local ns="$2"
    local extra_flags="${3:-}"

    local count
    count=$(oc get "$kind" -n "$ns" --no-headers 2>/dev/null | wc -l | tr -d ' ')

    if [[ "$count" -gt 0 ]]; then
        echo -e "  ${CYAN}→ Deleting $count $kind …${RESET}"
        # shellcheck disable=SC2086
        oc delete "$kind" --all -n "$ns" $extra_flags --ignore-not-found=true > /dev/null
        echo -e "  ${GREEN}✓ $kind deleted${RESET}"
    else
        echo -e "  ✓ No $kind found — skipping"
    fi
}
# ──────────────────────────────────────────────────────────────────────────────

# ─── Main cleanup loop ────────────────────────────────────────────────────────
for NS in "$@"; do

    echo ""
    echo -e "${BOLD}==========================================${RESET}"
    echo -e "${BOLD}  Cleaning namespace: ${CYAN}$NS${RESET}"
    echo -e "${BOLD}==========================================${RESET}"

    # Verify the project exists
    if ! oc get namespace "$NS" &> /dev/null; then
        echo -e "  ${YELLOW}⚠  Namespace '$NS' does not exist — skipping${RESET}"
        continue
    fi

    # ── Workloads ────────────────────────────────────────────────────────────
    echo ""
    echo -e "  ${BOLD}[Workloads]${RESET}"
    delete_all deployments        "$NS"
    delete_all deploymentconfigs  "$NS"
    delete_all statefulsets       "$NS"
    delete_all daemonsets         "$NS"
    delete_all jobs               "$NS"
    delete_all cronjobs           "$NS"
    delete_all replicasets        "$NS"
    delete_all replicationcontrollers "$NS"
    delete_all pods               "$NS" "--grace-period=0 --force"

    # ── Networking ───────────────────────────────────────────────────────────
    echo ""
    echo -e "  ${BOLD}[Networking]${RESET}"
    delete_all services  "$NS"
    delete_all routes    "$NS"
    delete_all ingresses "$NS"

    # ── Configuration ────────────────────────────────────────────────────────
    echo ""
    echo -e "  ${BOLD}[Configuration]${RESET}"
    delete_all configmaps "$NS"

    # Delete only user secrets (skip system tokens and pull secrets)
    echo -e "  ${CYAN}→ Deleting user secrets (skipping tokens/dockercfg) …${RESET}"
    oc get secrets -n "$NS" --no-headers 2>/dev/null \
        | awk '{print $1, $2}' \
        | grep -vE '(kubernetes\.io/service-account-token|kubernetes\.io/dockercfg|bootstrap\.kubernetes\.io)' \
        | awk '{print $1}' \
        | xargs -r oc delete secret -n "$NS" --ignore-not-found=true > /dev/null && \
        echo -e "  ${GREEN}✓ User secrets deleted${RESET}" || true

    # ── Storage ──────────────────────────────────────────────────────────────
    echo ""
    echo -e "  ${BOLD}[Storage]${RESET}"
    delete_all persistentvolumeclaims "$NS"

    # ── Autoscaling / disruption ──────────────────────────────────────────────
    echo ""
    echo -e "  ${BOLD}[Autoscaling / Policy]${RESET}"
    delete_all horizontalpodautoscalers "$NS"
    delete_all poddisruptionbudgets     "$NS"

    # ── OpenShift build / image resources ─────────────────────────────────────
    echo ""
    echo -e "  ${BOLD}[OpenShift Build / Image]${RESET}"
    delete_all buildconfigs "$NS"
    delete_all builds       "$NS"
    delete_all imagestreams "$NS"

    # ── User-created service accounts (preserve system ones) ──────────────────
    echo ""
    echo -e "  ${BOLD}[Service Accounts]${RESET}"
    echo -e "  ${CYAN}→ Removing user-created service accounts …${RESET}"
    oc get serviceaccounts -n "$NS" --no-headers 2>/dev/null \
        | awk '{print $1}' \
        | grep -vxFf <(echo "$PRESERVED_SA" | tr ' ' '\n') \
        | xargs -r oc delete serviceaccount -n "$NS" --ignore-not-found=true > /dev/null && \
        echo -e "  ${GREEN}✓ Done${RESET}" || true

    echo ""
    echo -e "  ${GREEN}${BOLD}✅ Namespace '$NS' is clean and ready for redeployment.${RESET}"
done
# ──────────────────────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}==========================================${RESET}"
echo -e "${GREEN}${BOLD}✅ Cleanup complete for: $*${RESET}"
echo -e "${BOLD}==========================================${RESET}"
echo ""
echo "  Namespaces are intact. Service accounts and RBAC preserved."
echo "  Participants can now redeploy from scratch."
echo ""

# Made with Bob
