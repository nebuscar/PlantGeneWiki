#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IMP 物种列表爬虫
获取IMP网站上的植物物种列表（物种代码 + 物种全称）
"""

import asyncio
import json
import re
from playwright.async_api import async_playwright

BASE_URL = "https://www.bic.ac.cn"
TARGET_URL = f"{BASE_URL}/IMP/#/Download"
OUTPUT_DIR = "/home/nizhu/Projects/plantsdb/downloads/IMP"


async def crawl_species_list():
    """从IMP页面爬取物种列表（支持翻页）"""
    print("=" * 60)
    print("IMP 物种列表爬虫（全量版）")
    print("=" * 60)

    species_data = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        print("\n正在访问IMP下载页面...")

        try:
            await page.goto(TARGET_URL, timeout=60000)
            await asyncio.sleep(5)

            print("等待页面完全加载...")

            try:
                await page.wait_for_selector('.el-table', timeout=10000)
                print("✅ 表格已加载")
            except:
                print("⚠️ 未发现表格")

            # 等待第一页数据加载完成
            await asyncio.sleep(3)

            # 翻页爬取
            page_num = 1
            total_pages = 54  # 已知总页数

            print(f"\n开始爬取... 预计 {total_pages} 页")

            while True:
                print(f"\n--- 第 {page_num}/{total_pages} 页 ---")

                # 滚动加载当前页
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(2)

                # 获取当前页的下载链接
                download_links = await page.query_selector_all('a[href*="/data/igv/"]')
                print(f"  发现 {len(download_links)} 个下载链接")

                for link in download_links:
                    href = await link.get_attribute('href')
                    if not href:
                        continue

                    # 从URL提取短码
                    match = re.search(r'/data/igv/([^/]+)', href)
                    if not match:
                        continue

                    short_code = match.group(1)

                    # 获取同一行的物种名称
                    try:
                        row_html = await page.evaluate('''
                            (link) => {
                                const tr = link.closest('tr');
                                if (tr) {
                                    const firstTd = tr.querySelector('td');
                                    return firstTd ? firstTd.textContent.trim() : null;
                                }
                                return null;
                            }
                        ''', link)

                        if row_html:
                            full_name = row_html.strip()
                            full_name = re.sub(r'\s+', ' ', full_name)

                            if full_name and not any(x in full_name.lower() for x in ['species', 'download', 'fasta']):
                                dir_name = re.sub(r'[/\\:*?"<>|]', '_', full_name)
                                dir_name = dir_name.replace(' ', '_')

                                species_data.append({
                                    'code': short_code,
                                    'name': full_name,
                                    'dir': dir_name
                                })
                    except:
                        pass

                print(f"  当前已获取: {len(species_data)} 个物种")

                # 检查是否还有下一页
                if page_num >= total_pages:
                    break

                # 尝试点击"下一页"按钮
                try:
                    # 查找分页组件中的下一页按钮
                    next_btn = await page.query_selector('.el-pager .btn-next, .el-pagination .btn-next, button:has-text("下一页"), .el-icon-arrow-right')

                    if next_btn:
                        # 检查是否禁用
                        is_disabled = await next_btn.get_attribute('disabled') or await next_btn.get_attribute('aria-disabled')
                        if is_disabled:
                            print("  已到最后一页")
                            break

                        # 点击下一页
                        await next_btn.click()
                        await asyncio.sleep(3)  # 等待加载
                        page_num += 1
                    else:
                        # 尝试查找页码按钮
                        pager = await page.query_selector('.el-pager')
                        if pager:
                            # 查找下一页按钮（通常是最后一个按钮或带箭头类名）
                            buttons = await pager.query_selector_all('li:not(.is-disabled)')
                            if len(buttons) > 1:
                                # 点击最后一个可点击的按钮（通常是下一页）
                                await buttons[-1].click()
                                await asyncio.sleep(3)
                                page_num += 1
                            else:
                                break
                        else:
                            break
                except Exception as e:
                    print(f"  点击下一页失败: {e}")
                    break

            # 去重（按短码）
            seen_codes = set()
            unique_species = []
            for sp in species_data:
                if sp['code'] not in seen_codes:
                    seen_codes.add(sp['code'])
                    unique_species.append(sp)

            species_data = unique_species
            species_data.sort(key=lambda x: x['code'])

            print(f"\n========== 爬取完成 ==========")
            print(f"总计获取: {len(species_data)} 个物种")

            # 保存结果
            manifest_file = f"{OUTPUT_DIR}/species_manifest.tsv"
            with open(manifest_file, 'w', encoding='utf-8') as f:
                f.write("Species_Code\tSpecies_Name\tDirectory_Name\n")
                for sp in species_data:
                    f.write(f"{sp['code']}\t{sp['name']}\t{sp['dir']}\n")

            print(f"✅ 物种清单已保存: {manifest_file}")

            json_file = f"{OUTPUT_DIR}/species_list.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'count': len(species_data),
                    'species': species_data
                }, f, indent=2, ensure_ascii=False)
            print(f"✅ JSON已保存: {json_file}")

        except Exception as e:
            print(f"页面加载异常: {e}")

        await browser.close()

    print("\n" + "=" * 60)
    print(f"物种列表获取完成: {len(species_data)} 个物种")
    print("=" * 60)

    return species_data


async def main():
    species = await crawl_species_list()
    return species


if __name__ == "__main__":
    asyncio.run(main())
