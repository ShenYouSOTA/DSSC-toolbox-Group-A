#!/usr/bin/env python3
"""
FIWARE DSC Data Exchange Demo - 一键演示脚本

完整流程: Provider 发布 offering → Consumer 发现 → 协商 → 传输 → 获取数据

使用方法:
    uv run python run_demo.py          # 完整演示
    uv run python run_demo.py server   # 仅启动 Provider 服务器
    uv run python run_demo.py client   # 仅运行 Consumer 客户端
"""

import argparse
import sys
import threading
import time

import httpx

from config import MOCK_HOST, MOCK_PORT, setup_logging

log = setup_logging("demo")


def wait_for_server(url: str, timeout: int = 30) -> bool:
    """等待服务器启动"""
    print(f"⏳ 等待服务器启动: {url}")
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = httpx.get(url, timeout=2.0)
            if response.status_code == 200:
                print(f"✅ 服务器已就绪")
                return True
        except (httpx.ConnectError, httpx.ReadTimeout):
            pass
        time.sleep(0.5)
    print(f"❌ 服务器启动超时")
    return False


def provider_publish_offering(provider_url: str) -> str:
    """Provider 发布 data offering (模拟数据发布步骤)"""
    print("\n" + "=" * 60)
    print("🏢 Provider: 发布 Data Offering (数据发布)")
    print("=" * 60)

    client = httpx.Client(timeout=30.0)

    # 1. Provider 先认证
    print("\n   1. Provider 认证...")
    token_resp = client.post(
        f"{provider_url}/auth/token",
        json={
            "client_id": "city-analytics-lab",
            "client_secret": "consumer-secret-123",
            "grant_type": "client_credentials",
        },
    )
    token_resp.raise_for_status()
    token = token_resp.json()["access_token"]
    print(f"   ✅ Token 获取成功")

    # 2. 创建 offering
    print("\n   2. 创建 Data Offering...")
    offering_resp = client.post(
        f"{provider_url}/api/catalog/offerings",
        headers={"Authorization": f"Bearer {token}"},
    )
    offering_resp.raise_for_status()
    offering = offering_resp.json()

    print(f"\n   ✅ Offering 已发布!")
    print(f"      Offering ID: {offering['offeringId']}")
    print(f"      标题: {offering['title']}")
    print(f"      提供方: {offering['providerName']}")
    print(f"      端点: {offering['endpointUrl']}")
    print(f"      政策: {offering['policy']['type']}")
    print(f"      许可证: {offering['policy']['license']}")
    print(f"      Metadata @type: {offering['metadata'].get('@type', 'N/A')}")
    print(f"      Contract paths: {list(offering['contractTemplate'].get('paths', {}).keys())}")

    client.close()
    return offering['offeringId']


def run_consumer_flow(provider_url: str):
    """运行 Consumer 完整流程"""
    from consumer_client import DSSCConsumer

    try:
        with DSSCConsumer(provider_url) as consumer:
            consumer.run_full_flow()
    except httpx.ConnectError:
        print(f"\n❌ 无法连接到服务器: {provider_url}")
        print("请确保 Provider 服务器已启动: uv run python run_demo.py server")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_server():
    """启动 Provider 服务器"""
    import uvicorn
    from provider_server import app

    print("\n" + "=" * 60)
    print("🏢 Energy Data Provider Ltd. - Mock API Server")
    print("=" * 60)
    print("\n🚀 启动服务器: http://{MOCK_HOST}:{MOCK_PORT}")
    print(f"\n📖 API文档: http://{MOCK_HOST}:{MOCK_PORT}/docs")
    print("\n按 Ctrl+C 停止服务器\n")

    uvicorn.run(app, host=MOCK_HOST, port=MOCK_PORT)


def run_full_demo():
    """完整演示: 启动服务器 → Provider 发布 → Consumer 流程"""
    import uvicorn
    from provider_server import app

    print("\n" + "🌟" * 30)
    print("\n  FIWARE DSC 数据空间完整流程演示")
    print("  Publishing → Discovery → Negotiation → Transfer → Data Access")
    print("\n" + "🌟" * 30)

    # Step 0: Start server
    print("\n📡 步骤0: 启动 Provider 服务器...")
    server_thread = threading.Thread(
        target=uvicorn.run,
        args=(app,),
        kwargs={"host": MOCK_HOST, "port": MOCK_PORT, "log_level": "warning"},
        daemon=True,
    )
    server_thread.start()

    base_url = f"http://localhost:{MOCK_PORT}"
    if not wait_for_server(f"{base_url}/health"):
        print("❌ 无法启动服务器")
        sys.exit(1)

    # Step 1: Provider publishes offering
    provider_publish_offering(base_url)

    # Step 2: Consumer full flow
    print("\n\n" + "=" * 60)
    print("👤 Consumer: 执行完整数据空间流程")
    print("=" * 60)

    run_consumer_flow(base_url)

    print("\n" + "=" * 60)
    print("✅ 完整演示完成!")
    print("=" * 60)
    print("\n流程总结:")
    print("  Provider: 创建 Data Offering (含 metadata + contract policy)")
    print("  Consumer: 发现 → 查看详情 → 认证 → 协商 → 传输 → 获取数据 → 验证")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="FIWARE DSC 数据空间完整流程演示",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  uv run python run_demo.py                    # 完整演示 (自动启动服务器)
  uv run python run_demo.py server             # 仅启动 Provider 服务器
  uv run python run_demo.py client             # 仅运行 Consumer 客户端
  uv run python run_demo.py client --building-id BLD-001  # 查询特定建筑

完整流程:
  1. Provider 发布 Data Offering (含 metadata JSON-LD + OpenAPI contract)
  2. Consumer 发现 Catalog
  3. Consumer 查看 Offering 详情
  4. Consumer 认证 (模拟 OID4VP)
  5. Consumer 发起 Contract Negotiation (REQUESTED → CONFIRMED → AGREED)
  6. Consumer 发起 Transfer Process (REQUESTED → STARTED → COMPLETED)
  7. Consumer 获取数据
  8. 验证数据格式
        """,
    )

    parser.add_argument(
        "mode",
        choices=["full", "server", "client"],
        default="full",
        nargs="?",
        help="运行模式: full=完整演示, server=仅服务器, client=仅客户端",
    )
    parser.add_argument("--provider-url", default=f"http://localhost:{MOCK_PORT}", help="Provider API URL")
    parser.add_argument("--building-id", help="按建筑ID过滤数据")
    parser.add_argument("--from-date", help="开始时间 (ISO格式)")
    parser.add_argument("--to-date", help="结束时间 (ISO格式)")

    args = parser.parse_args()

    if args.mode == "full":
        run_full_demo()
    elif args.mode == "server":
        run_server()
    elif args.mode == "client":
        if not wait_for_server(f"{args.provider_url}/health"):
            print(f"❌ 无法连接到服务器: {args.provider_url}")
            print("请先启动服务器: uv run python run_demo.py server")
            sys.exit(1)

        if args.building_id or args.from_date or args.to_date:
            from consumer_client import DSSCConsumer

            with DSSCConsumer(args.provider_url) as consumer:
                consumer.authenticate()
                catalog = consumer.discover_catalog()
                if catalog["total"] > 0:
                    neg = consumer.negotiate_contract(catalog["catalog"][0]["offeringId"])
                    transfer = consumer.start_transfer(neg["negotiationId"])
                    consumer.retrieve_data(args.building_id, args.from_date, args.to_date)
        else:
            run_consumer_flow(args.provider_url)


if __name__ == "__main__":
    main()
