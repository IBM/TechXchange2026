# Library System - Build and Deployment Guide

## Overview

This guide explains how to build Docker images and deploy the Library System application to OpenShift using Docker Hub as the container registry.

## Prerequisites

### Required Tools

1. **OpenShift CLI (oc)**
   - Install: https://docs.openshift.com/container-platform/latest/cli_reference/openshift_cli/getting-started-cli.html
   - Verify: `oc version`

2. **Docker (for local builds)**
   - Install: https://docs.docker.com/get-docker/
   - Verify: `docker --version`

3. **Docker Hub Account**
   - Sign up: https://hub.docker.com/signup
   - Free tier is sufficient

4. **OpenShift Cluster Access**
   - Must be logged in: `oc login`
   - Verify: `oc whoami`

---

## Quick Start

### Step 1: Build and Push Images to Docker Hub (Optional)
**Note:** If you are planning to just deploy the application without making changes, you can skip this step and go directly to next step".

```bash
cd library-system

# Login to Docker Hub
docker login

# Set your Docker Hub username
export DOCKER_USERNAME=your-dockerhub-username

# Build and push all images
chmod +x build-and-push-dockerhub.sh
./build-and-push-dockerhub.sh
```

The script will build and push:
- `your-username/library-books-api:latest`
- `your-username/library-users-api:latest`
- `your-username/library-web-ui:latest`
- `your-username/library-load-generator:latest`


### Step 2: Set the MongoDB Password

Before deploying, open [`k8s-manifests/all-in-one.yaml`](k8s-manifests/all-in-one.yaml) and replace the placeholder password with a strong password of your choice:

```yaml
stringData:
  username: mongodbadmin
  password: <your-mongodb-password>   # ← replace this
  database: library
```

> **Important:** Note down the password you set — you will need to export it as `MONGODB_PASSWORD` when running `invalidate-secret.sh` later.

### Step 3: Deploy to OpenShift

```bash
cd library-system

# Login to OpenShift
oc login

# Set the target namespace — defaults to "library-system" if not set
export NAMESPACE=<your-target-namespace>

# Set your Docker Hub username (only required if you built your own images)
export DOCKER_USERNAME=<your-dockerhub-username>
export IMAGE_TAG=<your-dockerimage-tag>

# Deploy the application
chmod +x deploy-to-ocp.sh
./deploy-to-ocp.sh
```

The deployment script will:
1. Create or switch to the target namespace (default: `library-system`)
2. Deploy MongoDB with persistent storage and secret for accessing MongoDB
3. Deploy Books API, Users API, and Web UI
4. Create routes for external access
5. Deploy load generator (scaled to 0 initially)

> **Tip:** You can deploy multiple isolated instances of the application by using a different `NAMESPACE` for each deployment:
> ```bash
> NAMESPACE=team-a-dev ./deploy-to-ocp.sh
> NAMESPACE=team-b-staging ./deploy-to-ocp.sh
> ```

### Step 4: Verify Deployment

```bash
# Set namespace if you used a custom one
export NAMESPACE=<your-target-namespace>   # or omit to use "library-system"

# Check all pods are running
oc get pods -n $NAMESPACE

# Get the application URL
oc get route web-ui -n $NAMESPACE

# Check logs
oc logs -f deployment/books-api -n $NAMESPACE
oc logs -f deployment/users-api -n $NAMESPACE
oc logs -f deployment/web-ui -n $NAMESPACE
```

### Step 5: Generate Traffic

```bash
cd library-system

# Use the same NAMESPACE as deployment (or omit for "library-system")
export NAMESPACE=<your-target-namespace>

# Start generating traffic
chmod +x generate-traffic.sh
./generate-traffic.sh
```

This will:
- Scale up the load generator to 1 replica
- Start sending requests to the application
- Verify all services are receiving traffic
- Check MongoDB connectivity
- Display real-time logs

---

### Generating Errors in Instana (Secret Invalidation)

The `invalidate-secret.sh` script corrupts the MongoDB password so that `books-api` and `users-api` fail to authenticate, enter `CrashLoopBackOff`, and generate a spike of erroneous calls visible in the Instana dashboard.

```bash
cd library-system

# Use the same NAMESPACE as deployment (or omit for "library-system")
export NAMESPACE=<your-target-namespace>

# Set this to the same password you configured in k8s-manifests/all-in-one.yaml
export MONGODB_PASSWORD=<your-mongodb-password>

# Set this to any invalid password (used to trigger authentication failures)
export MONGODB_BAD_PASSWORD=<any-wrong-password>

chmod +x invalidate-secret.sh
./invalidate-secret.sh
```

**Interactive Menu:**
```
==========================================
MongoDB Secret Invalidation Script
==========================================

What would you like to do?

  1) Invalidate password  → triggers CrashLoopBackOff / errors in Instana
  2) Restore password     → restores normal operation
  3) Show current status  → show pod and secret state
  0) Exit
```

**Option 1 — Invalidate:**
1. Patches `mongodb-credentials` secret with a wrong password
2. Restarts `books-api` and `users-api` deployments
3. Pods enter `CrashLoopBackOff` as MongoDB authentication fails
4. Instana dashboard shows a spike in erroneous calls for the `library-system` application

**Option 2 — Restore:**
1. Patches the secret back to the correct password
2. Restarts both deployments
3. Waits for pods to become healthy again

**Option 3 — Status:**
- Shows current pod states
- Decodes and shows whether the secret password is currently valid or invalid

**Monitoring the error spike:**

```bash
# Watch pods enter CrashLoopBackOff
oc get pods -n $NAMESPACE -w

# Watch the authentication error in logs
oc logs -f deployment/books-api -n $NAMESPACE
```
---

## Detailed Instructions

### Building Images with Docker

#### Prerequisites Check

```bash
# Check Docker is installed and running
docker --version
docker info

# Login to Docker Hub
docker login
# Enter your username and password
```

#### Build Script Usage

```bash
cd library-system

# Interactive mode (will prompt for username)
./build-and-push-dockerhub.sh

# With environment variables
export DOCKER_USERNAME=myusername
export IMAGE_TAG=v1.0.0
./build-and-push-dockerhub.sh

# Inline variables
DOCKER_USERNAME=myusername IMAGE_TAG=latest ./build-and-push-dockerhub.sh
```

#### What Gets Built

| Service | Image Name | Description |
|---------|------------|-------------|
| books-api | `username/library-books-api:tag` | Python Flask API for books management |
| users-api | `username/library-users-api:tag` | Python Flask API for user management |
| web-ui | `username/library-web-ui:tag` | Node.js Express frontend |
| load-generator | `username/library-load-generator:tag` | Python traffic generator |

#### Build Output

```
==========================================
Docker Hub Build and Push Script
==========================================

✓ Docker is running
✓ Docker Hub username: myusername
✓ Image tag: latest

This script will build and push the following images:
  - myusername/library-books-api:latest
  - myusername/library-users-api:latest
  - myusername/library-web-ui:latest
  - myusername/library-load-generator:latest

Continue? (y/n) y

==========================================
Building and Pushing Images
==========================================

==========================================
Processing books-api
==========================================
Building myusername/library-books-api:latest...
✓ Build successful

Pushing myusername/library-books-api:latest to Docker Hub...
✓ Push successful

[... similar output for other services ...]

==========================================
✅ All Images Built and Pushed!
==========================================
```

### Deploying to OpenShift

#### Prerequisites Check

```bash
# Check OpenShift CLI is installed
oc version

# Check you're logged in
oc whoami

# Check cluster info
oc cluster-info
```

#### Deployment Script Usage

```bash
cd library-system

# Basic deployment — uses namespace "library-system" and default image tag
./deploy-to-ocp.sh

# Deploy to a custom namespace
NAMESPACE=my-custom-namespace ./deploy-to-ocp.sh

# With custom Docker Hub username
export DOCKER_USERNAME=myusername
./deploy-to-ocp.sh

# With custom namespace, username, and image tag (all combined)
NAMESPACE=team-a-dev DOCKER_USERNAME=myusername IMAGE_TAG=v1.0.0 ./deploy-to-ocp.sh
```

All companion scripts read the same `NAMESPACE` variable, so set it once and all scripts target the same deployment:

```bash
export NAMESPACE=team-a-dev
./deploy-to-ocp.sh
./generate-traffic.sh
```

#### Deployment Output

```
==========================================
Library System Deployment (Docker Hub)
==========================================

✓ Logged in as: developer
✓ Namespace: team-a-dev
✓ Docker Hub username: myusername
✓ Image tag: latest

Step 1: Creating namespace...
✓ Namespace ready

Step 2: Verifying Docker Hub images...
Images to be used:
  - myusername/library-books-api:latest
  - myusername/library-users-api:latest
  - myusername/library-web-ui:latest
  - myusername/library-load-generator:latest

Are these images available on Docker Hub? (y/n) y

Step 3: Deploying all resources...
✓ Resources deployed

Step 4: Waiting for MongoDB to be ready...
✓ MongoDB ready

Step 5: Waiting for application services to be ready...
Waiting for books-api...
Waiting for users-api...
Waiting for web-ui...

==========================================
✅ Deployment Complete!
==========================================

📚 Library System is ready!

Access the application:
  http://web-ui-team-a-dev.apps.your-cluster.com

Check pod status:
  oc get pods -n team-a-dev

View logs:
  oc logs -f deployment/web-ui -n team-a-dev
  oc logs -f deployment/books-api -n team-a-dev
  oc logs -f deployment/users-api -n team-a-dev

Start load generator:
  oc scale deployment/load-generator --replicas=1 -n team-a-dev

Generate traffic and verify Instana:
  ./generate-traffic.sh
```

---

### Generating Traffic

The `generate-traffic.sh` script helps you:
- Start the load generator
- Verify traffic flow through all services
- Check MongoDB connectivity
- Monitor Instana integration

```bash
cd library-system
./generate-traffic.sh
```

**What it does:**
1. Checks load generator status
2. Scales up load generator if needed (to 1 replica)
3. Verifies all services are running
4. Shows load generator logs
5. Checks web-ui, books-api, and users-api logs
6. Tests direct API calls to verify MongoDB
7. Checks MongoDB pod status
8. Verifies Instana annotations
9. Checks for Instana initialization in logs

**Traffic Flow:**
```
Load Generator → Web UI → Books API → MongoDB
                       → Users API → MongoDB
```

**Monitoring Traffic:**

```bash
# Set namespace if you used a custom one (or omit for "library-system")
export NAMESPACE=<your-target-namespace>

# Watch load generator in real-time
oc logs -f deployment/load-generator -n $NAMESPACE

# Watch books-api
oc logs -f deployment/books-api -n $NAMESPACE

# Watch users-api
oc logs -f deployment/users-api -n $NAMESPACE

# Increase traffic
oc set env deployment/load-generator REQUESTS_PER_MINUTE=60 -n $NAMESPACE

# Stop traffic
oc scale deployment/load-generator --replicas=0 -n $NAMESPACE
```

---

*Made with Bob*
