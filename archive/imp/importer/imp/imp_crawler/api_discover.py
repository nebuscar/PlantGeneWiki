#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IMP API 发现脚本 - 使用 Playwright
自动访问IMP网站，捕获网络请求，发现API端点
"""

import asyncio
import json
import time
from playwright.async_api import async_playwright

BASE_URL = "https://www.bic.ac.cn"
TARGET_URL = f"{BASE_URL}/IMP/#/Download"
OUTPUT_DIR = "/home/nizhu/Projects/PlantGeneWiki/data/meta/imp"


async def capture_network_requests():
    """使用Playwright捕获网络请求"""
    print("=" * 60)
    print("IMP API 发现工具 (Playwright版)")
    print("=" * 60)
    print(f"目标URL: {TARGET_URL}")
    print("-" * 60)

    api_endpoints = []
    json_files = []
    all_requests = []  # 记录所有请求用于调试

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # 设置请求监听器 - 捕获所有请求
        def handle_request(request):
            url = request.url
            # 记录所有来自bic.ac.cn的请求
            if 'bic.ac.cn' in url:
                all_requests.append({
                    'url': url,
                    'method': request.method
                })
                # 只打印我们感兴趣的
                if any(pattern in url.lower() for pattern in ['api', 'data', 'json', 'download', 'genome', 'species', 'file']):
                    print(f"📡 {request.method}: {url[:120]}")

        page.on("request", handle_request)

        # 设置响应监听器
        def handle_response(response):
            url = response.url
            status = response.status
            if 'bic.ac.cn' in url and status == 200:
                content_type = response.headers.get('content-type', '')
                if 'json' in content_type or '.json' in url:
                    print(f"✅ JSON响应 [{status}]: {url[:100]}")

        page.on("response", handle_response)

        print("\n正在访问IMP下载页面...")

        try:
            await page.goto(TARGET_URL, timeout=60000)

            # 等待初始加载
            print("等待页面渲染...")
            await asyncio.sleep(5)

            # 获取初始URL和已加载的请求
            initial_requests = len(all_requests)
            print(f"当前请求数: {initial_requests}")

            # 尝试页面交互
            print("\n尝试与页面交互...")

            # 1. 滚动页面
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(2)

            # 2. 尝试点击表格行（如果有的话）
            try:
                # 查找el-table元素
                table_rows = await page.query_selector_all('.el-table__row, .el-table tr')
                print(f"  发现 {len(table_rows)} 个表格行")
                if table_rows:
                    await table_rows[0].click()
                    await asyncio.sleep(2)
            except Exception as e:
                print(f"  点击表格行: {e}")

            # 3. 查找所有按钮并点击
            try:
                buttons = await page.query_selector_all('button')
                print(f"  发现 {len(buttons)} 个按钮")
                for i, btn in enumerate(buttons[:5]):
                    try:
                        txt = await btn.inner_text()
                        if txt:
                            print(f"    点击按钮[{i}]: {txt[:30]}")
                            await btn.click()
                            await asyncio.sleep(1)
                    except:
                        pass
            except Exception as e:
                print(f"  点击按钮: {e}")

            # 4. 再次滚动
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(2)

            # 5. 尝试查找搜索框并输入
            try:
                search_inputs = await page.query_selector_all('input')
                print(f"  发现 {len(search_inputs)} 个输入框")
                for inp in search_inputs[:3]:
                    try:
                        await inp.fill('Arabidopsis')
                        await asyncio.sleep(1)
                        await inp.fill('')
                    except:
                        pass
            except Exception as e:
                print(f"  搜索框交互: {e}")

            # 最终等待让所有请求完成
            print("\n等待最终请求完成...")
            await asyncio.sleep(5)

            print("\n页面交互完成")

        except Exception as e:
            print(f"页面加载异常: {e}")

        # 获取页面内容
        html = await page.content()
        html_file = f"{OUTPUT_DIR}/imp_download_page_full.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"完整页面已保存: {html_file} ({len(html)} bytes)")

        await browser.close()

    # 输出结果统计
    print("\n" + "=" * 60)
    print("请求统计")
    print("=" * 60)
    print(f"总请求数: {len(all_requests)}")

    # 分析请求模式
    domains = {}
    for req in all_requests:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(req['url'])
            domain = parsed.netloc
            if domain not in domains:
                domains[domain] = []
            domains[domain].append(req['url'].split('?')[0])  # 去重用
        except:
            pass

    print("\n请求来源域名:")
    for domain, urls in domains.items():
        unique_urls = list(set(urls))
        print(f"  {domain}: {len(unique_urls)} 个唯一URL")

    # 特别关注 bic.ac.cn 的请求
    print("\n来自 bic.ac.cn 的请求:")
    bic_requests = [r for r in all_requests if 'bic.ac.cn' in r.get('url', '')]
    for req in bic_requests:
        print(f"  {req['method']} {req['url'][:100]}")

    # 提取可能的API端点
    print("\n" + "=" * 60)
    print("可能的API端点")
    print("=" * 60)

    api_candidates = set()
    for req in all_requests:
        url = req['url']
        if any(x in url.lower() for x in ['/api/', 'data/', 'file/', 'download', 'genome', 'species']):
            if 'statistics' not in url and 'analytics' not in url:
                # 提取基础路径
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(url)
                path = parsed.path
                query = parse_qs(parsed.query)
                if path:
                    api_candidates.add(path)

    if api_candidates:
        print("发现的可能端点:")
        for path in sorted(api_candidates):
            print(f"  {path}")
    else:
        print("❌ 未发现明显API端点")
        print("\n提示：请手动打开浏览器开发者工具(F12) -> Network标签")
        print("      访问IMP网站，查看是否有XHR/Fetch请求")

    # 保存完整请求日志
    log_file = f"{OUTPUT_DIR}/all_requests.json"
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump({
            'all_requests': all_requests,
            'api_candidates': list(api_candidates)
        }, f, indent=2)
    print(f"\n请求日志已保存: {log_file}")

    return api_candidates


async def main():
    candidates = await capture_network_requests()

    print("\n" + "=" * 60)
    print("API发现完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
