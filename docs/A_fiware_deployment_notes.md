# FIWARE Data Space Connector Deployment Notes

> **Group:** A – Data Exchange & Connector  
> **Technology:** FIWARE Data Space Connector (DSC)  
> **Research Focus:** Data Space Connector Deployment, Architecture, and Secure Data Exchange
---

This document records the deployment process of the **FIWARE Data Space Connector (DSC)** in a local Kubernetes environment, including:

- Deployment environment preparation
- Component dependencies
- Helm deployment workflow
- Local environment technology decisions
- Deployment issues and solutions
- Key configurations required for the demo

This document mainly targets development and debugging scenarios and aims to provide a reproducible local deployment environment for FIWARE DSC.

---

# 1. Overview

## 1.1 FIWARE DSC Deployment Context

The **FIWARE Data Space Connector (DSC)** is a core component in a Data Space architecture that enables trusted data exchange between different participants.

In this project, FIWARE DSC is deployed in a **Building Energy Data Space scenario**:

```
Building Energy Provider
         |
         |
         v
Data Space Connector
         |
         |
         v
Energy Consumer
```

The roles are:

### Provider

The Provider publishes:

- Building Energy Consumption Data
- Metadata
- Access Policies
- Contract Policies

### Consumer

The Consumer:

- Discovers available data products
- Performs identity authentication
- Requests data access
- Retrieves energy data

The local deployment is mainly used to validate:

- Data Offering creation workflow
- NGSI-LD data storage
- TMForum product catalog management
- Identity and Trust mechanisms
- ODRL Policy management
- Consumer data access workflow

---

## 1.2 Document Structure

| Document | Description |
|----------|-------------|
| README.md | Project introduction and quick start |
| ARCHITECTURE.md | Data Space architecture and communication workflow |
| Deployment Notes | Deployment environment and troubleshooting |
| Data Exchange Demo | Provider-Consumer data exchange demonstration |

Recommended reading order:

```
README
   ↓
ARCHITECTURE
   ↓
Deployment Notes
   ↓
Data Exchange Demo
```

---

# 2. Environment Setup

## 2.1 Hardware Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| Memory | 16 GB | ≥24 GB |
| CPU | 4 cores | 8 cores |
| Disk | 10 GB | SSD |
| OS | Linux/macOS | Ubuntu |

---

## 2.2 Required Tools

| Tool | Version | Purpose |
|------|---------|---------|
| Docker | 27.0+ | Container runtime |
| kubectl | Latest | Kubernetes management |
| Helm | 3.x | Kubernetes package deployment |
| Python | 3.10+ | Demo execution |
| uv | Latest | Python dependency management |

---

# 3. Kubernetes Environment

## 3.1 Local k3s Cluster

This project uses **k3s** as the local Kubernetes environment.

Reasons for selecting k3s:

- Lightweight Kubernetes distribution
- Fast startup time
- Suitable for local development and demonstrations

Start k3s:

```bash
docker run -d --name k3s-server \
    --privileged \
    -p 6443:6443 \
    -p 80:80 \
    -p 443:443 \
    -v k3s-data:/var/lib/rancher/k3s \
    rancher/k3s:latest server \
    --disable=traefik
```

Retrieve kubeconfig:

```bash
docker exec k3s-server \
    cat /etc/rancher/k3s/k3s.yaml > /tmp/k3s.yaml

export KUBECONFIG=/tmp/k3s.yaml
```

---

# 4. Deployment Architecture

The FIWARE DSC Helm Chart consists of multiple service components.

Overall deployment structure:

```
                         Trust Anchor
                              |
                              |
              +---------------+---------------+
              |                               |
          Provider                       Consumer
              |                               |
          Keycloak                       Keycloak
          Scorpio                       PostgreSQL
          TMForum
          APISIX
          OPA
          VCVerifier
          MongoDB
          PostgreSQL
```

Infrastructure:

- cert-manager
- postgres-operator
- nginx-ingress

---

# 5. Component Selection

## 5.1 Required Components

The following components are defined by the FIWARE DSC Helm Chart:

| Component | Role |
|-----------|------|
| Keycloak | OIDC Provider / Credential Management |
| MongoDB | Scorpio storage backend |
| PostgreSQL | Relational database |
| cert-manager | TLS certificate management |
| APISIX | API Gateway / Policy Enforcement Point |
| OPA | Policy Decision Point |
| ODRL-PAP | Policy management |
| VCVerifier | Verifiable Credential verification |
| DID Helper | DID document service |
| TMForum API | Product catalog management |
| Scorpio | NGSI-LD Context Broker |

## 5.2 Local Deployment Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Kubernetes | k3s | Lightweight local cluster |
| Ingress | nginx-ingress | Stable and flexible |
| Domain | nip.io | No hosts file modification required |
| Database Operator | Zalando PostgreSQL Operator | Chart compatibility |
| Demo Language | Python | Fast development |
| Package Manager | uv | Dependency management |

---

# 6. Namespace Structure

```
trust-anchor/
    TIR service

provider/
    Keycloak
    Scorpio
    TMForum API
    APISIX
    OPA
    PostgreSQL
    MongoDB

consumer/
    Keycloak
    PostgreSQL

ingress-nginx/

cert-manager/

postgres-operator/
```

---

# 7. Deployment Process

## 7.1 One-click Deployment

The complete deployment can be started using:

```bash
just up
```

Manual deployment:

```bash
just k3s-start
just k3s-wait
just deploy-infra
just deploy-apps
just smoke-test
```

## 7.2 Infrastructure Deployment

### cert-manager

```bash
helm install cert-manager jetstack/cert-manager \
    --namespace cert-manager \
    --create-namespace \
    --set crds.enabled=true \
    --wait
```

### PostgreSQL Operator

```bash
helm install postgres-operator \
    postgres-operator/postgres-operator \
    --namespace postgres-operator \
    --create-namespace \
    --wait
```

## 7.3 Application Deployment

### Trust Anchor

```bash
helm install trust-anchor charts/trust-anchor \
    -f k3s/trust-anchor.yaml \
    --namespace trust-anchor \
    --create-namespace
```

### Provider

```bash
helm install provider charts/data-space-connector \
    -f k3s/provider.yaml \
    --namespace provider \
    --create-namespace
```

### Consumer

Create keystore password:

```bash
kubectl create secret generic keystore-password \
    --from-literal=password=changeit \
    -n consumer
```

Deploy Consumer:

```bash
helm install consumer charts/data-space-connector \
    -f k3s/consumer.yaml \
    --namespace consumer \
    --create-namespace
```

---

# 8. Deployment Issues and Solutions

## 8.1 Image Pull Failure

**Problem:**

`ImagePullBackOff`

**Cause:**

Some images depend on external registries, which may have unstable network access.

**Solution:**

- Retry deployment
- Configure image mirrors
- Preload required images locally

Check:

```bash
kubectl describe pod <pod-name>
```

## 8.2 Missing CRD

**Problem:**

`Pending`

**Cause:**

Required Kubernetes Operator CRDs are missing.

**Solution:**

Install:

- postgres-operator

MongoDB configuration:

```yaml
mongo-operator:
  enabled: false

managedMongo:
  enabled: true
```

## 8.3 cert-manager Missing

**Problem:**

TLS Secret Pending

**Cause:**

Ingress resources depend on cert-manager for certificate provisioning.

**Solution:**

```bash
helm install cert-manager jetstack/cert-manager \
    --set crds.enabled=true
```

---

# 9. Data Exchange Demo

## 9.1 Demo Architecture

The overall workflow:

```
                 Data Space


      +-----------------------------+
      |                             |
Provider Connector          Consumer Connector
      |                             |
Data Offering              Discovery
      |
Contract Negotiation
      |
Data Transfer
      |
Energy Data Access
      +-----------------------------+
```

---

# 10. Mock Demo

## 10.1 Purpose

The Mock Demo is designed to quickly validate the business workflow of the Data Space Protocol.

**Characteristics:**

- No Kubernetes dependency
- No FIWARE DSC dependency
- FastAPI-based Provider simulation
- Python-based Consumer simulation

**Suitable for:**

- Learning Data Space workflows
- Rapid business logic development
- Presentation demonstrations

## 10.2 Workflow

```
Consumer
   |
Authentication
   |
Provider API
   |
Catalog Discovery
   |
Data Offering
   |
Contract Negotiation
   |
Agreement
   |
Transfer Process
   |
Data Access
```

---

# 11. Real Cluster Demo

## 11.1 Purpose

The Real Cluster Demo uses the deployed FIWARE DSC environment.

It validates:

- Keycloak authentication
- Scorpio NGSI-LD storage
- TMForum Product Catalog
- Trust Anchor
- ODRL Policy management
- Data retrieval

**Architecture:**

```
Python Client
      |
      v
nginx-ingress
      |
      v
FIWARE DSC Cluster
      |
      v
+----------------+
|                |
Scorpio      TMForum API
      |
      v
Energy Data
```

---

# 12. Real Cluster Workflow

## Step 1. Service Health Check

The demo checks:

- Trust Anchor
- Keycloak
- TMForum API
- Scorpio
- Dashboard
- Verifier

**Purpose:**

Ensure that the Data Space infrastructure is running correctly.

## Step 2. Create Data Offering

Energy entities are stored in Scorpio:

```http
POST /ngsi-ld/v1/entities
```

Example:

```json
{
  "id": "urn:ngsi-ld:Building:BLD-001",
  "type": "Building"
}
```

A `ProductSpecification` is created through TMForum API.

It describes:

- Data product type
- Data capability

A `ProductOffering` defines:

- Data access method
- Policies

Example:

```
Building Energy Consumption Offering
```

## Step 3. Policy Management

The Offering contains ODRL Policies.

**Access Policy**

Defines:

- Who can access the data

**Contract Policy**

Defines:

- Data usage restrictions

Example:

```
Consumer can use data
but cannot redistribute
Delete after P30D
```

## Step 4. Consumer Discovery

Consumer queries:

```http
GET ProductOffering
```

Returns:

- Data product
- Policy
- Metadata

## Step 5. Authentication

Consumer authenticates using Keycloak:

```
Consumer
    |
    v
Keycloak
    |
    v
Access Token
```

Returns:

- OIDC Token

## Step 6. Contract Negotiation

**Current implementation:**

Contract negotiation is simulated using a local state machine because the Contract Management API is not fully exposed as a REST interface.

Workflow:

```
REQUESTED
     ↓
CONFIRMED
     ↓
AGREED
```

## Step 7. Data Access

Consumer retrieves data from Scorpio:

```http
GET /ngsi-ld/v1/entities/{building-id}
```

Returns:

- NGSI-LD Entity

---

# 13. Implementation Decisions

## 13.1 FIWARE Standard Components

| Standard | Implementation |
|----------|----------------|
| NGSI-LD | Scorpio |
| TMForum API | Product Catalog |
| DID | did:web |
| ODRL | Policy Definition |
| OIDC | Keycloak |
| Trust Registry | TIR |

## 13.2 Demo Choices

| Decision | Choice | Reason |
|----------|--------|--------|
| Language | Python | Fast development |
| Mock Framework | FastAPI | Lightweight |
| HTTP Client | httpx | Async support |
| State Storage | dataclass | Simple demo |
| Data Storage | JSON | Reproducible |
| Authentication Mock | JWT | Easy testing |

## 13.3 Real Cluster Choices

| Decision | Choice |
|----------|--------|
| Kubernetes | k3s |
| Ingress | nginx |
| Domain | nip.io |
| Data Storage | Scorpio |
| Catalog | TMForum API |
| Policy | ODRL |

---

# 14. Development Issues

## 14.1 Contract Management API

**Problem:**

`contract-management` endpoint returns 404

**Cause:**

The service is mainly used for internal workflow communication rather than public REST APIs.

**Solution:**

The demo uses:

```python
@dataclass
class NegotiationState:
    state: str
```

to simulate:

- Contract Negotiation
- Transfer Process

## 14.2 Scorpio Empty Query

**Problem:**

```http
GET /ngsi-ld/v1/entities
```

returns:

```http
400
```

**Cause:**

Scorpio does not return all entities for an empty query.

**Solution:**

Health checks allow this response.

## 14.3 TMForum Policy Format

**Problem:**

ProductOffering policy structure changes after serialization.

**Cause:**

TMForum JSON serialization may convert between:

- Array
- Object

**Solution:**

The demo applies normalization during parsing.

## 14.4 Keycloak Token Endpoint

**Problem:**

Different versions return different field names.

Possible formats:

- `token_endpoint`
- `token-service`

**Solution:**

The client supports both formats.

## 14.5 nginx-ingress

**Problem:**

Ingress returns 404.

**Cause:**

Missing:

```yaml
ingressClassName: nginx
```

**Solution:**

```bash
kubectl patch ingress <ingress-name> \
    --type merge \
    -p '{"spec":{"ingressClassName":"nginx"}}'
```

---

# 15. Extension Guide

## 15.1 Add New Data Product

**Steps:**

1. Add new metadata
2. Add new dataset
3. Create new Data Offering
4. Update API

**Directory:**

```
demo/data/scenarios/
    new-scenario/
        data/
        metadata/
        mock-api/
```

## 15.2 Replace Mock Contract Negotiation

**Future implementation:**

Replace:

- local dataclass

with:

- real Contract Management API

## 15.3 Add New Consumer

**Required:**

- Keycloak user
- Client credential
- Consumer workflow

---

# 16. Summary

The FIWARE Data Space Connector deployment provides a complete local Data Space environment for validating trusted data exchange workflows.

The deployed environment demonstrates:

- Identity and trust management
- Data product publication
- Policy-controlled data access
- NGSI-LD based data exchange
- Provider-Consumer interaction workflow

This deployment serves as the technical foundation for the Building Energy Data Space demonstration.
