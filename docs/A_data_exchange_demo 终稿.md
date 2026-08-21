# FIWARE DSC Data Exchange Demo

This document describes a data exchange demo based on the **FIWARE Data Space Connector (DSC)**.

The demo uses a **Building Energy Data Space** scenario to simulate the complete data exchange workflow between:

- Data Provider
- Data Consumer
- Data Product Publication
- Catalog Discovery
- Identity Authentication
- Contract Negotiation
- Data Transfer

This document contains two demo implementations:

1. Mock Demo
2. Real Cluster Demo

The two demos validate different aspects of the Data Space workflow:

| Demo | Purpose |
|------|---------|
| Mock Demo | Validate Data Space business workflow and API design |
| Real Cluster Demo | Validate FIWARE DSC component integration in a real deployment environment |

---

# 1. Background

## 1.1 Building Energy Data Space Scenario

This project uses **building energy data** as the example data product.

The overall scenario is:

```
Building Energy Provider
         |
         v
Data Space Connector
         |
         v
Energy Consumer
```

The **Provider** publishes:

- Building Energy Consumption Data
- Metadata
- Access Policy
- Contract Policy

The **Consumer**:

- Discovers available data products
- Performs identity authentication
- Requests data access
- Retrieves energy data

---

# 2. Demo Architecture

The overall data exchange workflow is:

```
                Data Space

    +-------------------------------+
    |                               |
Provider Connector          Consumer Connector
    |                               |
    |                               |
Data Offering                 Discovery
    |
    |
Contract Negotiation
    |
    |
Data Transfer
    |
    |
Energy Data Access
    +-------------------------------+
```

---

# 3. Mock Demo

## 3.1 Purpose

The Mock Demo is designed to quickly validate the business workflow of the Data Space Protocol.

Features:

- No Kubernetes dependency
- No FIWARE DSC service dependency
- Uses FastAPI to simulate Provider services
- Uses Python Client to simulate Consumer behavior

It is suitable for:

- Understanding the basic Data Space workflow
- Rapid business logic modification
- Presentation demonstrations

---

## 3.2 Workflow

The complete workflow is:

```
Consumer
   |
   | 1. Authentication
   v
Provider API
   |
   | 2. Catalog Discovery
   v
Data Offering
   |
   | 3. Contract Negotiation
   v
Agreement
   |
   | 4. Transfer Process
   v
Data Access
```

---

## Step 1. Authentication

The Consumer requests an access token:

```
POST /auth/token
```

The Provider:

- Validates client credentials
- Generates JWT token

Response:

```
access_token
```

---

## Step 2. Catalog Discovery

The Consumer queries available data products:

```
GET /api/catalog
```

The Provider returns:

- Data Offering
- Metadata
- Contract information

Example:

```json
{
  "id": "building-energy-hourly",
  "type": "DataOffering",
  "dataset": "Building Energy Consumption"
}
```

---

## Step 3. Contract Negotiation

The Consumer sends:

```
POST /api/contract-negotiations
```

The negotiation lifecycle:

```
REQUESTED
    ↓
CONFIRMED
    ↓
AGREED
```

Generated information:

- negotiationId
- contractId

---

## Step 4. Data Transfer

The Consumer starts a transfer process:

```
POST /api/transfer-processes
```

Transfer lifecycle:

```
REQUESTED
    ↓
STARTED
    ↓
COMPLETED
```

---

## Step 5. Data Access

The Consumer retrieves building energy data:

```
GET /api/energy/buildings/hourly
```

Example response:

```json
{
  "buildingId": "BLD-001",
  "timestamp": "2026-08-01T10:00",
  "energyConsumption": 125.6
}
```

---

# 4. Real Cluster Demo

## 4.1 Purpose

The Real Cluster Demo uses a real FIWARE DSC deployment environment.

It validates:

- Keycloak Authentication
- Scorpio NGSI-LD Storage
- TMForum Product Catalog
- Trust Anchor
- ODRL Policy
- Data Retrieval

Architecture:

```
Python Client
      |
      v
nginx-ingress
      |
      v
FIWARE DSC Cluster
      |
      +----------------+
      |                |
   Scorpio        TMForum API
      |
Energy Data
```

---

## 4.2 Workflow

### Step 1. Service Health Check

The demo first checks the availability of core services:

Including:

- Trust Anchor
- Keycloak
- TMForum API
- Scorpio
- Dashboard
- Verifier

**Purpose:**

Ensure that the Data Space infrastructure is running correctly.

---

### Step 2. Create Data Offering

In the real demo:

Data entities are stored in Scorpio:

```
POST /ngsi-ld/v1/entities
```

A Building Entity is created:

```json
{
  "id": "urn:ngsi-ld:Building:BLD-001",
  "type": "Building"
}
```

Then, through TMForum API:

### ProductSpecification

Describes:

- Data product type
- Data capabilities

### ProductOffering

Describes:

- Data access method
- Policies

Example:

```
Building Energy Consumption Offering
```

---

### Step 3. Policy Management

The Product Offering contains ODRL policies.

Including:

### Access Policy

Defines:

- Who can access the data

### Contract Policy

Defines:

- Data usage restrictions

Example:

```
Consumer can use data
```

but:

```
Consumer cannot redistribute data
```

Data retention:

```
Delete after P30D
```

---

### Step 4. Consumer Discovery

The Consumer queries:

```
GET ProductOffering
```

and obtains:

- Data products
- Policies
- Metadata

---

### Step 5. Authentication

The Consumer uses Keycloak.

Workflow:

```
Consumer
    |
    v
Keycloak
    |
    v
Access Token
```

Returned:

```
OIDC Token
```

---

### Step 6. Contract Negotiation

Currently:

Because the Contract Management API does not fully expose REST endpoints, the demo uses a local state machine simulation.

Workflow:

```
REQUESTED
    ↓
CONFIRMED
    ↓
AGREED
```

---

### Step 7. Data Access

Finally, data is retrieved from Scorpio:

```
GET /ngsi-ld/v1/entities/{building-id}
```

Returned:

NGSI-LD Entity

---

# 5. Implementation Decisions

## 5.1 FIWARE Standard Components

| Standard | Implementation |
|----------|----------------|
| NGSI-LD | Scorpio |
| TMForum API | Product Catalog |
| DID | did:web |
| ODRL | Policy Definition |
| OIDC | Keycloak |
| Trust Registry | TIR |

---

## 5.2 Mock Demo Choices

| Decision | Choice | Reason |
|----------|--------|--------|
| Language | Python | Fast development |
| Mock Framework | FastAPI | Lightweight |
| HTTP Client | httpx | Async support |
| State Storage | dataclass | Simple demo implementation |
| Data Storage | JSON | Reproducible |
| Authentication Mock | JWT | Easy testing |

---

## 5.3 Real Cluster Choices

| Decision | Choice |
|----------|--------|
| Kubernetes | k3s |
| Ingress | nginx |
| Domain | nip.io |
| Data Storage | Scorpio |
| Catalog | TMForum API |
| Policy | ODRL |

---

# 6. Development Issues

## 6.1 Contract Management API

### Problem

```
contract-management endpoint returns 404
```

### Reason

The service is mainly designed for internal process communication rather than a public REST API.

### Solution

The demo uses:

```python
@dataclass
class NegotiationState:
    state: str
```

to simulate:

- Contract Negotiation
- Transfer Process

---

## 6.2 Scorpio Empty Query

### Problem

Request:

```
GET /ngsi-ld/v1/entities
```

returns:

```
400
```

### Reason

Scorpio does not provide a default entity list for empty queries.

### Solution

Health checks allow `400` as an expected response.

---

## 6.3 TMForum Policy Format

### Problem

The Policy structure changes after creating ProductOffering.

### Reason

TMForum JSON serialization may transform `array` and `object` formats.

### Solution

The demo performs normalization when reading policies.

---

## 6.4 Keycloak Token Endpoint

### Problem

Different Keycloak versions return different fields.

Possible formats:

- `token_endpoint`
- `token-service`

### Solution

The client supports both formats.

---

## 6.5 nginx-ingress

### Problem

Ingress returns `404`.

### Cause

Missing:

```
ingressClassName: nginx
```

### Solution

```bash
kubectl patch ingress <ingress-name> \
    --type merge \
    -p '{"spec":{"ingressClassName":"nginx"}}'
```

---

# 7. Extension Guide

## 7.1 Add New Data Product

Steps:

1. Add new metadata
2. Add new dataset
3. Create new Data Offering
4. Update API

Directory:

```
demo/data/scenarios/
```

Example:

```
new-scenario/
    data/
    metadata/
    mock-api/
```

---

## 7.2 Replace Mock Contract Negotiation

If Contract Management API becomes fully available:

Replace:

```
local dataclass
```

with:

```
real API call
```

---

## 7.3 Add New Consumer

Add:

- Keycloak user
- Client credential
- Consumer workflow

---

# 8. Related Documents

| Document         | Description                        |
| ---------------- | ---------------------------------- |
| README.md        | Project overview                   |
| ARCHITECTURE.md  | Architecture and sequence diagrams |
| Deployment Notes | FIWARE DSC deployment              |
| Wiki             | Background and concepts            |