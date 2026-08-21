"""
FIWARE DSC Data Exchange Demo - Consumer Client

模拟数据消费方 (City Analytics Lab) 的完整数据空间流程：
1. 发现数据目录 (Catalog Discovery)
2. 查看 offering 详情 (含 metadata + contract policy)
3. 认证 (Authentication)
4. 发起合同协商 (Contract Negotiation)
5. 发起数据传输 (Transfer Process)
6. 获取数据 (Data Retrieval)
7. 验证数据 (Validation)
"""

from typing import Optional

import httpx
import jwt

from config import (
    CONSUMER_DID,
    DEFAULT_CLIENT_ID,
    DEFAULT_CLIENT_SECRET,
    JWT_ALGORITHM,
    JWT_SECRET,
    setup_logging,
)

log = setup_logging("consumer")


class DSSCConsumer:
    """FIWARE DSC Consumer 客户端 - 完整数据空间流程"""

    def __init__(self, provider_base_url: str = "http://localhost:8000"):
        self.provider_url = provider_base_url.rstrip("/")
        self.client = httpx.Client(timeout=30.0)
        self.token: Optional[str] = None
        self.client_id = DEFAULT_CLIENT_ID
        self.client_secret = DEFAULT_CLIENT_SECRET
        self.consumer_did = CONSUMER_DID
        self.current_offering: Optional[dict] = None
        self.current_negotiation: Optional[dict] = None
        self.current_transfer: Optional[dict] = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.client.close()

    # ================================================================
    # Step 1: Discover Catalog
    # ================================================================

    def discover_catalog(self) -> dict:
        """步骤1: 发现数据目录"""
        print("\n" + "=" * 60)
        print("📡 步骤1: 发现数据目录 (Catalog Discovery)")
        print("=" * 60)

        response = self.client.get(f"{self.provider_url}/api/catalog")
        response.raise_for_status()

        catalog = response.json()

        log.info("Catalog discovered: total=%d", catalog["total"])

        if catalog["total"] == 0:
            print("\n⚠️  目录为空，Provider 尚未发布任何 offering")
            return catalog

        print(f"\n✅ 发现 {catalog['total']} 个数据集:")
        for item in catalog["catalog"]:
            print(f"   - {item['title']}")
            print(f"     Offering ID: {item['offeringId']}")
            print(f"     Provider: {item['providerName']}")
            print(f"     Policy: {item['policy']['type']} - {item['policy']['description']}")

        return catalog

    # ================================================================
    # Step 2: View Offering Detail
    # ================================================================

    def view_offering(self, offering_id: str) -> dict:
        """步骤2: 查看 offering 详情 (含 metadata + contract template)"""
        print("\n" + "=" * 60)
        print("📋 步骤2: 查看 Offering 详情 (Metadata + Contract)")
        print("=" * 60)

        response = self.client.get(f"{self.provider_url}/api/catalog/{offering_id}")
        response.raise_for_status()

        offering = response.json()
        self.current_offering = offering

        print(f"\n✅ Offering 详情:")
        print(f"   标题: {offering['title']}")
        print(f"   数据集 ID: {offering['datasetId']}")
        print(f"   提供方: {offering['providerName']}")
        print(f"   端点: {offering['endpointUrl']}")
        print(f"   格式: {offering['format']}")
        print(f"   频率: {offering['frequency']}")
        print(f"   空间覆盖: {offering['spatialCoverage']}")
        print(f"   时间范围: {offering['temporalStart']} ~ {offering['temporalEnd']}")
        print(f"   许可证: {offering['policy']['license']}")

        print(f"\n   📜 合同政策:")
        print(f"      类型: {offering['policy']['type']}")
        print(f"      用途: {offering['policy'].get('purpose', 'N/A')}")
        if offering['policy'].get('constraints'):
            for c in offering['policy']['constraints']:
                print(f"      约束: {c}")

        print(f"\n   📄 Metadata (JSON-LD @type): {offering['metadata'].get('@type', 'N/A')}")
        print(f"   📄 Contract Template (OpenAPI): {list(offering['contractTemplate'].get('paths', {}).keys())}")

        return offering

    # ================================================================
    # Step 3: Authenticate
    # ================================================================

    def authenticate(self) -> str:
        """步骤3: 请求访问凭证 (模拟 OID4VP 认证)"""
        print("\n" + "=" * 60)
        print("🔐 步骤3: 认证 (Authentication)")
        print("=" * 60)
        print(f"\n   模拟 OID4VP 流程:")
        print(f"   1. Consumer 向 VCVerifier 发起认证请求")
        print(f"   2. 提供 Verifiable Credential")
        print(f"   3. VCVerifier 验证凭证")
        print(f"   4. 签发 JWT 访问令牌")

        response = self.client.post(
            f"{self.provider_url}/auth/token",
            json={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
        )
        response.raise_for_status()

        token_data = response.json()
        self.token = token_data["access_token"]

        payload = jwt.decode(self.token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        log.info("Authenticated: client=%s did=%s", self.client_id, self.consumer_did)

        print(f"\n✅ 认证成功!")
        print(f"   Subject: {payload.get('sub')}")
        print(f"   Name: {payload.get('name')}")
        print(f"   DID: {payload.get('did')}")
        print(f"   Role: {payload.get('role')}")
        print(f"   Scope: {payload.get('scope')}")
        print(f"   Expires in: {token_data['expires_in']} seconds")

        return self.token

    # ================================================================
    # Step 4: Contract Negotiation
    # ================================================================

    def negotiate_contract(self, offering_id: str) -> dict:
        """步骤4: 发起合同协商"""
        print("\n" + "=" * 60)
        print("📝 步骤4: 合同协商 (Contract Negotiation)")
        print("=" * 60)

        if not self.token:
            raise ValueError("请先调用 authenticate() 获取 token")

        print(f"\n   Offering ID: {offering_id}")
        print(f"   Consumer DID: {self.consumer_did}")
        print(f"\n   状态机流转: REQUESTED → CONFIRMED → AGREED")

        response = self.client.post(
            f"{self.provider_url}/api/contract-negotiations",
            json={
                "offeringId": offering_id,
                "consumerDID": self.consumer_did,
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response.raise_for_status()

        negotiation = response.json()
        self.current_negotiation = negotiation

        log.info("Negotiation completed: id=%s state=%s contract=%s",
                 negotiation["negotiationId"], negotiation["state"], negotiation.get("contractId"))

        print(f"\n✅ 协商完成!")
        print(f"   Negotiation ID: {negotiation['negotiationId']}")
        print(f"   Contract ID: {negotiation.get('contractId', 'N/A')}")
        print(f"   最终状态: {negotiation['state']}")

        print(f"\n   📊 状态历史:")
        for entry in negotiation['stateHistory']:
            print(f"      [{entry['state']}] {entry['timestamp']}")
            print(f"         {entry['detail']}")

        return negotiation

    # ================================================================
    # Step 5: Transfer Process
    # ================================================================

    def start_transfer(self, negotiation_id: str) -> dict:
        """步骤5: 发起数据传输"""
        print("\n" + "=" * 60)
        print("🔄 步骤5: 数据传输 (Transfer Process)")
        print("=" * 60)

        if not self.token:
            raise ValueError("请先调用 authenticate() 获取 token")

        print(f"\n   Negotiation ID: {negotiation_id}")
        print(f"\n   状态机流转: REQUESTED → STARTED → COMPLETED")

        response = self.client.post(
            f"{self.provider_url}/api/transfer-processes",
            json={
                "negotiationId": negotiation_id,
                "dataAddress": {
                    "type": "HttpData",
                    "baseUrl": "http://localhost:9000/consumer/sink",
                },
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response.raise_for_status()

        transfer = response.json()
        self.current_transfer = transfer

        log.info("Transfer completed: id=%s state=%s", transfer["transferId"], transfer["state"])

        print(f"\n✅ 传输完成!")
        print(f"   Transfer ID: {transfer['transferId']}")
        print(f"   最终状态: {transfer['state']}")

        if transfer.get('resourceAddress'):
            ra = transfer['resourceAddress']
            print(f"\n   📦 数据源地址:")
            print(f"      类型: {ra.get('type')}")
            print(f"      URL: {ra.get('baseUrl')}")

        print(f"\n   📊 状态历史:")
        for entry in transfer['stateHistory']:
            print(f"      [{entry['state']}] {entry['timestamp']}")
            print(f"         {entry['detail']}")

        return transfer

    # ================================================================
    # Step 6: Retrieve Data
    # ================================================================

    def retrieve_data(
        self,
        building_id: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> dict:
        """步骤6: 获取数据"""
        print("\n" + "=" * 60)
        print("📊 步骤6: 获取数据 (Data Retrieval)")
        print("=" * 60)

        if not self.token:
            raise ValueError("请先调用 authenticate() 获取 token")

        if not self.current_transfer or self.current_transfer['state'] != 'COMPLETED':
            raise ValueError("请先完成 Transfer (transfer 状态必须为 COMPLETED)")

        params = {}
        if building_id:
            params["buildingId"] = building_id
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        print(f"\n   请求参数: {params or '无 (获取全部数据)'}")
        print(f"   Transfer ID: {self.current_transfer['transferId']}")
        print(f"   使用 Bearer Token 认证")

        response = self.client.get(
            f"{self.provider_url}/api/energy/buildings/hourly",
            params=params,
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response.raise_for_status()

        data = response.json()

        log.info("Data retrieved: records=%d dataset=%s", len(data["records"]), data["datasetId"])

        print(f"\n✅ 数据获取成功!")
        print(f"   Dataset ID: {data['datasetId']}")
        print(f"   Provider: {data['providerName']}")
        print(f"   License: {data['license']}")
        print(f"   Records: {len(data['records'])} 条")

        return data

    # ================================================================
    # Step 7: Validate Data
    # ================================================================

    def validate_data(self, data: dict) -> bool:
        """步骤7: 验证数据格式"""
        print("\n" + "=" * 60)
        print("✅ 步骤7: 验证数据格式 (Validation)")
        print("=" * 60)

        errors = []

        required_fields = ["datasetId", "providerName", "records"]
        for field in required_fields:
            if field not in data:
                errors.append(f"缺少必填字段: {field}")

        if "records" in data:
            for i, record in enumerate(data["records"]):
                record_required = ["buildingId", "meterId", "timestamp", "energyKWh", "unit"]
                for field in record_required:
                    if field not in record:
                        errors.append(f"Record {i}: 缺少必填字段 {field}")
                if record.get("unit") != "kWh":
                    errors.append(f"Record {i}: unit 应该是 kWh，实际是 {record.get('unit')}")

        if errors:
            print(f"\n❌ 验证失败:")
            for error in errors:
                print(f"   - {error}")
            return False

        print(f"\n✅ 数据格式验证通过!")
        print(f"   - 所有必填字段存在")
        print(f"   - 数据类型正确")
        print(f"   - 单位符合规范 (kWh)")

        return True

    # ================================================================
    # Full Flow
    # ================================================================

    def run_full_flow(self) -> dict:
        """执行完整的数据空间流程"""
        print("\n" + "🚀" * 30)
        print("\n  FIWARE DSC 数据空间完整流程演示")
        print("  Data Publishing → Discovery → Negotiation → Transfer → Data Access")
        print("\n" + "🚀" * 30)

        results = {"steps": [], "success": False}

        # Step 1: Discover catalog
        try:
            catalog = self.discover_catalog()
            results["catalog"] = catalog
            if catalog["total"] == 0:
                results["steps"].append({"step": 1, "name": "目录发现", "status": "fail", "detail": "目录为空"})
                self._print_summary(results)
                return results
            results["steps"].append({"step": 1, "name": "目录发现", "status": "ok", "detail": f"{catalog['total']} 个 offering"})
        except Exception as e:
            results["steps"].append({"step": 1, "name": "目录发现", "status": "fail", "detail": str(e)})
            self._print_summary(results)
            return results

        # Step 2: View offering detail
        try:
            offering_id = catalog["catalog"][0]["offeringId"]
            offering = self.view_offering(offering_id)
            results["offering"] = offering
            results["steps"].append({"step": 2, "name": "Offering 详情", "status": "ok", "detail": offering["title"]})
        except Exception as e:
            results["steps"].append({"step": 2, "name": "Offering 详情", "status": "fail", "detail": str(e)})
            self._print_summary(results)
            return results

        # Step 3: Authenticate
        try:
            token = self.authenticate()
            results["token"] = token
            results["steps"].append({"step": 3, "name": "身份认证", "status": "ok", "detail": "JWT token 获取成功"})
        except Exception as e:
            results["steps"].append({"step": 3, "name": "身份认证", "status": "fail", "detail": str(e)})
            self._print_summary(results)
            return results

        # Step 4: Contract Negotiation
        try:
            negotiation = self.negotiate_contract(offering_id)
            results["negotiation"] = negotiation
            results["steps"].append({
                "step": 4, "name": "合同协商", "status": "ok",
                "detail": f"{negotiation['state']} | Contract: {negotiation.get('contractId', 'N/A')}"
            })
        except Exception as e:
            results["steps"].append({"step": 4, "name": "合同协商", "status": "fail", "detail": str(e)})
            self._print_summary(results)
            return results

        # Step 5: Transfer Process
        try:
            transfer = self.start_transfer(negotiation["negotiationId"])
            results["transfer"] = transfer
            results["steps"].append({
                "step": 5, "name": "数据传输", "status": "ok",
                "detail": f"{transfer['state']} | Transfer: {transfer['transferId']}"
            })
        except Exception as e:
            results["steps"].append({"step": 5, "name": "数据传输", "status": "fail", "detail": str(e)})
            self._print_summary(results)
            return results

        # Step 6: Retrieve Data
        try:
            data = self.retrieve_data()
            results["data"] = data
            results["steps"].append({"step": 6, "name": "数据获取", "status": "ok", "detail": f"{len(data['records'])} 条记录"})
        except Exception as e:
            results["steps"].append({"step": 6, "name": "数据获取", "status": "fail", "detail": str(e)})
            self._print_summary(results)
            return results

        # Step 7: Validate
        try:
            valid = self.validate_data(results["data"])
            results["valid"] = valid
            results["steps"].append({"step": 7, "name": "数据验证", "status": "ok" if valid else "fail", "detail": "格式正确" if valid else "格式错误"})
        except Exception as e:
            results["steps"].append({"step": 7, "name": "数据验证", "status": "fail", "detail": str(e)})

        results["success"] = all(s["status"] == "ok" for s in results["steps"])
        self._print_summary(results)
        return results

    def _print_summary(self, results: dict):
        """打印流程总结"""
        print("\n" + "=" * 60)
        print("📊 流程总结")
        print("=" * 60)

        for step in results["steps"]:
            icon = "✅" if step["status"] == "ok" else "❌"
            print(f"  {icon} 步骤{step['step']}: {step['name']} - {step['detail']}")

        print("-" * 60)
        if results["success"]:
            print("✅ 数据空间完整流程全部完成!")
        else:
            failed = [s for s in results["steps"] if s["status"] == "fail"]
            print(f"❌ 流程在以下步骤失败: {', '.join(s['name'] for s in failed)}")


# ============================================================
# CLI Entry Point
# ============================================================

def main():
    """CLI 入口"""
    import argparse

    parser = argparse.ArgumentParser(description="FIWARE DSC Consumer Client")
    parser.add_argument("--provider-url", default="http://localhost:8000", help="Provider API base URL")
    parser.add_argument("--building-id", help="Filter by building ID")
    parser.add_argument("--from-date", help="Start time (ISO format)")
    parser.add_argument("--to-date", help="End time (ISO format)")
    parser.add_argument(
        "--step",
        choices=["catalog", "detail", "auth", "negotiate", "transfer", "data", "all"],
        default="all",
        help="Run specific step or all",
    )

    args = parser.parse_args()

    with DSSCConsumer(args.provider_url) as consumer:
        if args.step == "all":
            consumer.run_full_flow()
        elif args.step == "catalog":
            consumer.discover_catalog()
        elif args.step == "detail":
            catalog = consumer.discover_catalog()
            if catalog["total"] > 0:
                consumer.view_offering(catalog["catalog"][0]["offeringId"])
        elif args.step == "auth":
            consumer.authenticate()
        elif args.step == "negotiate":
            consumer.authenticate()
            catalog = consumer.discover_catalog()
            if catalog["total"] > 0:
                consumer.negotiate_contract(catalog["catalog"][0]["offeringId"])
        elif args.step == "transfer":
            consumer.authenticate()
            catalog = consumer.discover_catalog()
            if catalog["total"] > 0:
                neg = consumer.negotiate_contract(catalog["catalog"][0]["offeringId"])
                consumer.start_transfer(neg["negotiationId"])
        elif args.step == "data":
            consumer.authenticate()
            catalog = consumer.discover_catalog()
            if catalog["total"] > 0:
                neg = consumer.negotiate_contract(catalog["catalog"][0]["offeringId"])
                consumer.start_transfer(neg["negotiationId"])
                consumer.retrieve_data(args.building_id, args.from_date, args.to_date)


if __name__ == "__main__":
    main()
