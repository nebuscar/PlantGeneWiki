#!/usr/bin/env python3
import asyncio
import json
import os
import re
from playwright.async_api import async_playwright

BASE_URL = "https://www.bic.ac.cn"
TARGET_URL = f"{BASE_URL}/IMP/#/Download"
OUTPUT_DIR = "/home/nizhu/Projects/plantsdb/downloads/IMP"


async def crawl_species_list():
    species_data = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await (await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )).new_page()

        try:
            # navigate to base URL first, then hash route to avoid ERR_EMPTY_RESPONSE
            await page.goto(BASE_URL + "/IMP/", timeout=60000)
            await asyncio.sleep(3)
            await page.goto(TARGET_URL, timeout=60000)
            await page.wait_for_selector('.el-table', timeout=15000)
            await asyncio.sleep(3)
        except Exception as e:
            print(f"ERROR: page load failed: {e}")
            await browser.close()
            return []

        page_num = 1
        while True:
            await asyncio.sleep(2)
            rows = await page.query_selector_all('.el-table__body tr')

            for row in rows:
                try:
                    cells = await row.query_selector_all('td')
                    if not cells:
                        continue
                    full_name = re.sub(r'\s+', ' ', (await cells[0].inner_text()).strip())

                    # extract species code from igv download link
                    link = await row.query_selector('a[href*="/data/igv/"]')
                    if not link:
                        continue
                    href = await link.get_attribute('href')
                    m = re.search(r'/data/igv/([^/]+)', href)
                    if not m:
                        continue
                    code = m.group(1)

                    if not full_name or full_name.lower() in ('species', 'download', ''):
                        continue

                    dir_name = re.sub(r'[/\\:*?"<>|]', '_', full_name).replace(' ', '_')
                    species_data.append({'code': code, 'name': full_name, 'dir': dir_name})
                except Exception:
                    continue

            # advance to next page; stop when next button is disabled
            try:
                next_btn = await page.query_selector('button.btn-next')
                if not next_btn or await next_btn.get_attribute('disabled') is not None:
                    break
                await next_btn.click()
                page_num += 1
            except Exception:
                break

    await browser.close()

    # deduplicate by code, sort by name
    seen = set()
    unique = []
    for sp in species_data:
        if sp['code'] not in seen:
            seen.add(sp['code'])
            unique.append(sp)
    species_data = sorted(unique, key=lambda x: x['name'])

    # warn about entries where full name was not extracted
    incomplete = [sp for sp in species_data if sp['name'] == sp['code']]
    if incomplete:
        print(f"WARNING: {len(incomplete)} species missing full name (name==code), manual review needed:")
        for sp in incomplete:
            print(f"  {sp['code']}")

    print(f"crawled {len(species_data)} species ({len(incomplete)} incomplete)")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    manifest_file = f"{OUTPUT_DIR}/species_manifest.tsv"
    with open(manifest_file, 'w', encoding='utf-8') as f:
        f.write("Species_Code\tSpecies_Name\tDirectory_Name\n")
        for sp in species_data:
            f.write(f"{sp['code']}\t{sp['name']}\t{sp['dir']}\n")

    with open(f"{OUTPUT_DIR}/species_list.json", 'w', encoding='utf-8') as f:
        json.dump({'count': len(species_data), 'species': species_data}, f,
                  indent=2, ensure_ascii=False)

    print(f"saved: {manifest_file}")
    return species_data


if __name__ == "__main__":
    asyncio.run(crawl_species_list())
