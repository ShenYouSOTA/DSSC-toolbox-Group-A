# Demo 架构与通信流程

本文档说明两个 Demo（Mock 和 Real Cluster）如何实现数据空间核心流程，以及 k3s 集群中的服务通信链路。

## 两种 Demo 对比

| 维度 | Mock Demo | Real Cluster Demo |
|------|-----------|-------------------|
| 运行环境 | 纯本地 Python | k3s 集群 (Docker) |
| Provider | FastAPI 进程 (:8000) | TMForum API + Scorpio |
| Consumer | DSSCConsumer 类 | Python httpx 客户端 |
| 认证 | 模拟 JWT 签发 | 真实 Keycloak OIDC |
| 数据来源 | 静态 JSON 文件 | Scorpio NGSI-LD |
| Contract Negotiation | Provider 内存状态机 | 本地 dataclass 模拟 |
| Transfer Process | Provider 内存状态机 | 本地 dataclass 模拟 |

---

## 数据组织：按 Scenario 分层

为了把 Mock Demo 从固定的学习资料目录解耦，并方便后续接入真实数据，演示数据现在统一放在 `demo/data/scenarios/<scenario-name>/` 下，通过 `config.py` 中的相对路径函数读取：

```
demo/data/scenarios/
└── DSSC_Minimal_Energy_Scenario/
    ├── data/
    │   └── building-energy-sample.json          # API payload
    ├── metadata/
    │   ├── data-product-valid.jsonld            # 默认 metadata
    │   └── data-product-invalid.jsonld          # validation 失败案例
    ├── mock-api/
    │   └── openapi.yaml                         # 合同模板
    ├── shapes/
    │   └── building-energy-shapes.ttl           # SHACL shapes
    └── gaia-x/
        ├── legal-participant.template.jsonld
        └── service-offering.template.jsonld
```

`config.py` 提供以下函数供代码使用：

```python
scenario_dir(name)          # demo/data/scenarios/<name>
scenario_data_dir(name)     # .../data
scenario_metadata_dir(name) # .../metadata
scenario_mock_api_dir(name) # .../mock-api
```

默认 scenario 由 `DEMO_SCENARIO` 环境变量控制（默认 `DSSC_Minimal_Energy_Scenario`），具体文件由 `DEMO_DATA_FILE`、`DEMO_METADATA_FILE`、`DEMO_OPENAPI_FILE` 控制。Provider 在加载 offering 和数据时会使用这些路径，从而在不修改代码的情况下切换到新的 scenario 或真实数据文件。

---

## 流程 1: Provider 发布 Data Offering，Consumer 看到 Metadata

### Mock Demo

```
Consumer                    Provider (FastAPI :8000)
   │                              │
   │  POST /auth/token            │
   │  {client_id, client_secret}  │
   │─────────────────────────────→│  验证凭证 → 签发 JWT
   │  ←── access_token ──────────│
   │                              │
   │  POST /api/catalog/offerings │
   │  Authorization: Bearer xxx   │
   │─────────────────────────────→│  加载 metadata/data-product-valid.jsonld
   │                              │  加载 mock-api/openapi.yaml
   │  ←── DataOffering ──────────│  组装 Offering 存入内存字典
   │                              │
   │  GET /api/catalog            │
   │─────────────────────────────→│  返回内存中所有 offerings
   │  ←── catalog list ──────────│
   │                              │
   │  GET /api/catalog/{id}       │
   │─────────────────────────────→│  返回 offering 详情
   │  ←── metadata + contract ───│  含 JSON-LD metadata + OpenAPI contract
```

**代码位置：**

- `provider_server.py:338-389` — `create_offering()` 从 scenario 的 `metadata/` 和 `mock-api/` 加载资源，组装成 `DataOffering` 存入内存
- `provider_server.py:398-428` — `get_catalog()` 和 `get_offering()` 返回内存中的 offerings
- `consumer_client.py:44-105` — `discover_catalog()` 和 `view_offering()` GET 端点获取数据

**数据源：**

- `demo/data/scenarios/DSSC_Minimal_Energy_Scenario/metadata/data-product-valid.jsonld` — JSON-LD 元数据（DCAT/DCTerms）
- `demo/data/scenarios/DSSC_Minimal_Energy_Scenario/mock-api/openapi.yaml` — OpenAPI 3.0 合同模板

Mock Provider 启动时通过 `config.py` 中的 scenario 路径函数定位这些文件；默认 scenario 为 `DSSC_Minimal_Energy_Scenario`，可通过环境变量 `DEMO_SCENARIO` 切换。

### Real Cluster Demo

```
Python Client               k3s 集群 (via nginx-ingress)
   │                              │
   │  POST /ngsi-ld/v1/entities   │
   │  Host: scorpio-provider      │
   │─────────────────────────────→│  Scorpio (NGSI-LD Context Broker)
   │  ←── 201 Created ───────────│  存储 Building 实体
   │                              │
   │  POST /tmf-api/.../productSpecification
   │  Host: tm-forum-api          │
   │─────────────────────────────→│  TMForum API (Product Catalog)
   │  ←── spec_id ───────────────│  创建 ProductSpecification
   │                              │
   │  POST /tmf-api/.../productOffering
   │  Host: tm-forum-api          │
   │─────────────────────────────→│  TMForum API
   │  ←── offering_id ───────────│  创建 ProductOffering (引用 spec)
   │                              │
   │  GET /tmf-api/.../productOffering
   │─────────────────────────────→│  TMForum API
   │  ←── offerings list ────────│  Consumer 发现所有 Offerings
```

**代码位置：**

- `demo_real_cluster.py:120-170` — `step_create_offering()` 先在 Scorpio 创建 NGSI-LD 实体，再在 TMForum API 创建 ProductSpecification 和 ProductOffering
- `demo_real_cluster.py:175-195` — `step_consumer_discover()` GET TMForum API 的 productOffering 端点

**数据流：**

```
demo/data/scenarios/DSSC_Minimal_Energy_Scenario/data/building-energy-sample.json
        ↓ (demo 读取)
Python Client → Scorpio: 创建 urn:ngsi-ld:Building:BLD-001 实体
Python Client → TMForum: 创建 ProductSpecification (Energy Data Specification)
Python Client → TMForum: 创建 ProductOffering (Building Energy Consumption Data)
        ↓
Consumer → TMForum: GET /productOffering → 发现 5 个 Offerings
```

---

## 流程 2: Consumer 发起访问请求，产生 Negotiation / Transfer 状态

### Mock Demo

```
Consumer                    Provider (FastAPI :8000)
   │                              │
   │  POST /contract-negotiations │
   │  {offeringId, consumerDID}   │
   │─────────────────────────────→│
   │                              │  内存状态机自动流转:
   │                              │    REQUESTED → CONFIRMED → AGREED
   │  ←── negotiation ───────────│  生成 contractId
   │      state: AGREED           │
   │      contractId: contract-xx │
   │      stateHistory: [...]     │
   │                              │
   │  POST /transfer-processes    │
   │  {negotiationId}             │
   │─────────────────────────────→│
   │                              │  前置检查: negotiation.state == AGREED
   │                              │  内存状态机自动流转:
   │                              │    REQUESTED → STARTED → COMPLETED
   │  ←── transfer ──────────────│  生成 resourceAddress
   │      state: COMPLETED        │
   │      resourceAddress: {      │
   │        type: HttpData        │
   │        baseUrl: /api/energy  │
   │      }                       │
```

**状态机设计：**

```
Contract Negotiation:
  REQUESTED  ──→  CONFIRMED  ──→  AGREED
       │              │
       └──→ DECLINED  └──→ ERROR

Transfer Process:
  REQUESTED  ──→  STARTED  ──→  COMPLETED
       │              │
       └──→ TERMINATED └──→ SUSPENDED
```

**代码位置：**

- `provider_server.py:447-490` — `start_negotiation()` 创建 negotiation 后立即自动推进到 AGREED
- `provider_server.py:522-577` — `start_transfer()` 检查 negotiation 必须是 AGREED，然后自动推进到 COMPLETED
- `consumer_client.py:152-237` — `negotiate_contract()` 和 `start_transfer()` 发起请求并打印状态历史

### Real Cluster Demo

集群中没有真实的 Contract Negotiation API（contract-management 返回 404），因此状态流转在本地模拟：

```
Python Client               (本地 dataclass)
   │                              │
   │  NegotiationState            │
   │  state_history.append(...)   │
   │  REQUESTED → CONFIRMED → AGREED
   │  生成 negotiation_id, contract_id
   │                              │
   │  TransferState               │
   │  state_history.append(...)   │
   │  REQUESTED → STARTED → COMPLETED
   │  生成 transfer_id
```

**代码位置：**

- `demo_real_cluster.py:200-240` — `step_contract_negotiation()` 用 `NegotiationState` dataclass 记录状态流转
- `demo_real_cluster.py:245-270` — `step_transfer_process()` 用 `TransferState` dataclass 记录状态流转

---

## 流程 3: 数据访问

### Mock Demo

```
Consumer                    Provider (FastAPI :8000)
   │                              │
   │  GET /api/energy/buildings/hourly
   │  Authorization: Bearer xxx   │
   │  ?buildingId=BLD-001         │
   │─────────────────────────────→│  1. 验证 JWT (verify_token)
   │                              │  2. 加载 data/building-energy-sample.json
   │                              │  3. 按 buildingId/from/to 过滤
   │  ←── EnergyDataset ─────────│  4. 返回 {datasetId, records: [...]}
```

**静态数据文件：**

```json
// demo/data/scenarios/DSSC_Minimal_Energy_Scenario/data/building-energy-sample.json
{
  "datasetId": "building-energy-hourly-v1",
  "providerName": "Energy Data Provider Ltd.",
  "license": "CC-BY-4.0",
  "records": [
    {"buildingId": "BLD-001", "meterId": "MTR-001", "timestamp": "2026-05-01T00:00:00+08:00", "energyKWh": 12.4, "unit": "kWh", "location": {"city": "Shenzhen", "district": "Nanshan"}},
    {"buildingId": "BLD-001", "meterId": "MTR-001", "timestamp": "2026-05-01T01:00:00+08:00", "energyKWh": 11.8, "unit": "kWh", "location": {"city": "Shenzhen", "district": "Nanshan"}},
    {"buildingId": "BLD-002", "meterId": "MTR-002", "timestamp": "2026-05-01T00:00:00+08:00", "energyKWh": 8.7, "unit": "kWh", "location": {"city": "Shenzhen", "district": "Futian"}}
  ]
}
```

**代码位置：**

- `provider_server.py:604-635` — `get_energy_data()` 验证 token 后从当前 scenario 加载数据文件，按参数过滤返回
- `consumer_client.py:243-287` — `retrieve_data()` 带 token 请求数据端点

### Real Cluster Demo

```
Python Client               k3s 集群 (via nginx-ingress)
   │                              │
   │  GET /ngsi-ld/v1/entities/urn:ngsi-ld:Building:BLD-001
   │  Host: scorpio-provider      │
   │  Accept: application/ld+json │
   │─────────────────────────────→│  Scorpio (NGSI-LD Context Broker)
   │  ←── entity JSON-LD ────────│  返回步骤 2 创建的 Building 实体
```

**代码位置：**

- `demo_real_cluster.py:275-300` — `step_retrieve_data()` 从 Scorpio 读取之前创建的实体

---

## k3s 集群服务通信流程

### 整体架构

```
                         ┌─────────────────────────────────────────────┐
                         │            k3s 集群 (Docker 容器)            │
                         │                                             │
  Python Client          │   ┌──────────────┐    ┌───────────────┐    │
  (demo_real_cluster.py) │   │ nginx-ingress│    │  APISIX       │    │
         │               │   │ controller   │    │  (API Gateway)│    │
         │ HTTPS         │   └──────┬───────┘    └───────┬───────┘    │
         │ (ingress)     │          │                    │            │
         ▼               │          ▼                    ▼            │
  ┌──────────────────────────────────────────────────────────────┐   │
  │                     Ingress 路由                              │   │
  │  tm-forum-api.127.0.0.1.nip.io    → tm-forum-api-svc:8080   │   │
  │  scorpio-provider.127.0.0.1.nip.io → data-service-scorpio:9090│  │
  │  keycloak-consumer.127.0.0.1.nip.io → consumer-keycloak:8080 │   │
  │  keycloak-provider.127.0.0.1.nip.io → provider-keycloak:8080 │   │
  │  tir.127.0.0.1.nip.io              → tir:8080                │   │
  │  til-provider.127.0.0.1.nip.io     → trusted-issuers-list:8080│  │
  │  mp-data-service.127.0.0.1.nip.io  → provider-apisix:9080    │   │
  │  dashboard-provider.127.0.0.1.nip.io → provider-fdsc-dashboard│  │
  └──────────────────────────────────────────────────────────────┘   │
         │                                                            │
         ▼                                                            │
  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │
  │ TMForum API │  │  Scorpio    │  │  Keycloak   │  │  TIR/TIL  │  │
  │ (Catalog)   │  │ (NGSI-LD)  │  │ (Auth)      │  │ (DID)     │  │
  │      │      │  │      │      │  │      │      │  │           │  │
  │      ▼      │  │      ▼      │  │      ▼      │  │           │  │
  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │  │           │  │
  │ │PostgreSQL│ │  │ │ MongoDB │ │  │ │PostgreSQL│ │  │           │  │
  │ └─────────┘ │  │ └─────────┘ │  │ └─────────┘ │  │           │  │
  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │
                         │                                             │
                         └─────────────────────────────────────────────┘
```

### 请求链路

| 步骤 | 源 | 目标 | Host 路由 | 说明 |
|------|-----|------|-----------|------|
| 健康检查 | Python | nginx-ingress → 各服务 | 多个 Host | 7 个端点并行检查 |
| 创建 Entity | Python | nginx-ingress → Scorpio | scorpio-provider | NGSI-LD POST，存入 MongoDB |
| 创建 Spec | Python | nginx-ingress → TMForum API | tm-forum-api | REST POST，存入 PostgreSQL |
| 创建 Offering | Python | nginx-ingress → TMForum API | tm-forum-api | REST POST，引用 Spec |
| 发现 Catalog | Python | nginx-ingress → TMForum API | tm-forum-api | REST GET |
| 认证 | Python | nginx-ingress → Consumer Keycloak | keycloak-consumer | OIDC password grant |
| 验证 DID | Python | nginx-ingress → TIR | tir | GET /v4/issuers |
| 读取数据 | Python | nginx-ingress → Scorpio | scorpio-provider | NGSI-LD GET，从 MongoDB 读取 |

### nginx-ingress 路由机制

nginx-ingress 根据 HTTP 请求的 `Host` 头匹配 Ingress 资源的 `spec.rules.host` 字段，将请求路由到对应的 Kubernetes Service：

```yaml
# 示例: provider-keycloak Ingress
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: provider-keycloak
  namespace: provider
spec:
  ingressClassName: nginx
  rules:
    - host: keycloak-provider.127.0.0.1.nip.io
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: provider-keycloak
                port:
                  number: 8080
```

请求链路：

```
Python Client
  ↓ HTTPS (Host: keycloak-provider.127.0.0.1.nip.io)
nginx-ingress-controller (pod in ingress-nginx namespace)
  ↓ 匹配 Ingress 规则
  ↓ 转发到 provider-keycloak:8080
provider-keycloak-0 (pod in provider namespace)
```

### 数据库依赖

| 服务 | 数据库 | 用途 |
|------|--------|------|
| TMForum API | PostgreSQL | Catalog、ProductSpecification、ProductOffering |
| Keycloak | PostgreSQL | Realm、User、Client、Token |
| Scorpio | MongoDB | NGSI-LD 实体存储 |
| Contract Management | PostgreSQL | 合同记录（当前未完全配置） |
| Verifier | PostgreSQL | 凭证配置 |

---

## 附录: 关键代码文件

| 文件 | 行数 | 职责 |
|------|------|------|
| `config.py` | 150+ | 集中配置：路径、JWT、端口、凭证、logging、scenario 选择 |
| `provider_server.py` | 700+ | FastAPI Mock Provider（auth/catalog/negotiate/transfer/data） |
| `consumer_client.py` | 496 | Consumer 客户端（7 步流程） |
| `run_demo.py` | 221 | Mock Demo 编排器 |
| `demo_real_cluster.py` | 330 | Real Cluster Demo（ingress + 完整数据交换） |
