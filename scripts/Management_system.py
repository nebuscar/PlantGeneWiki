#!/usr/bin/env python3
from flask import Flask, render_template_string, request, jsonify
import os
import argparse
import csv

# ====================== 命令行参数解析 ======================
parser = argparse.ArgumentParser(
    description="🐧 物种同源比对管理系统 - 基因组文件检索工具"
)
parser.add_argument(
    "-i",
    "--input",
    default="/DATA/data2/downloads/genomes",
    help="指定基因组数据目录路径，默认路径：/DATA/data2/downloads/genomes",
)
args = parser.parse_args()

# Flask 应用初始化
app = Flask(__name__)

# 数据目录配置
DATA_FOLDER = args.input
# ========== 直接写死你给的绝对路径 ==========
TAXONOMY_FILE = (
    "/home/nizhu/renjinran/plantsdb/data/meta/species_list_unique_with_taxid.txt"
)

# ====================== 加载物种分类映射表 ======================
species_taxonomy = {}  # key: 文件夹名(xxx_xxx)，value: genus/order/family


def load_taxonomy_mapping():
    global species_taxonomy
    try:
        # tab分隔读取你的物种列表
        with open(TAXONOMY_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                species_raw = row.get("Species", "").strip()
                if not species_raw:
                    continue
                # 物种名空格转下划线 = 文件夹名
                folder_name = species_raw.replace(" ", "_")
                # 提取分类 → 改用 Family
                order = row.get("Order", "").strip()
                family = row.get("Family", "").strip()
                genus = species_raw.split(" ")[0]

                species_taxonomy[folder_name] = {
                    "genus": genus,
                    "order": order,
                    "family": family,
                }
        print(f"✅ 分类文件加载成功：{TAXONOMY_FILE}")
        print(f"✅ 共载入分类物种：{len(species_taxonomy)} 个")
    except FileNotFoundError:
        print(f"❌ 错误：找不到文件 {TAXONOMY_FILE}")
    except Exception as e:
        print(f"❌ 分类表读取异常：{str(e)}")


# 程序启动自动加载
load_taxonomy_mapping()

# ====================== 文件后缀规则 ======================
PROT_EXT = [".faa"]
NUC_EXT = [".fna"]
ANN_EXT_GFF = [".gff"]
ANN_EXT_GBFF = [".gbff"]

# ====================== 前端页面模板 ======================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🐧 物种同源比对管理系统</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Roboto, sans-serif;
            background: #fff7ed;
            min-height: 100vh; padding: 20px;
            color: #2d3748;
        }
        .container {
            max-width: 1600px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 320px 1fr;
            gap: 24px;
            align-items: start;
        }
        .left-panel {
            display: flex; flex-direction: column; gap: 16px;
            background: #fff; padding: 24px; border-radius: 16px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.06);
        }
        .donut-chart-wrapper {
            position: relative; width: 100%; aspect-ratio: 1/1;
            display: flex; align-items: center; justify-content: center;
        }
        .donut-total {
            position: absolute; font-size: 36px; font-weight: 700; color: #1a202c;
        }
        .donut-label {
            position: absolute; bottom: 10px; font-size: 14px; color: #718096;
        }
        .mini-card {
            padding: 16px; border-radius: 12px; color: #333;
            display: flex; flex-direction: column; gap: 4px;
        }
        /* 自定义三色 */
        .mini-card.align { background: #f38181; }
        .mini-card.manual { background: #fce38a; }
        .mini-card.empty { background: #95e1d3; }
        .mini-card .label { font-size: 13px; opacity: 0.9; }
        .mini-card .value { font-size: 24px; font-weight: 700; }

        .right-panel { display: flex; flex-direction: column; gap: 20px; }
        .header-card {
            background: #fff; padding: 24px; border-radius: 16px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.06); text-align: center;
        }
        .title { font-size: 26px; font-weight: 700; margin-bottom: 8px; }
        .desc { font-size: 14px; color: #718096; margin-bottom: 16px; }
        #search {
            width: 100%; max-width: 500px; padding: 12px 18px;
            border: 1px solid #e2e8f0; border-radius: 10px; font-size: 15px;
        }
        #search:focus {
            outline: none; border-color: #3182ce;
            box-shadow: 0 0 0 4px rgba(49,130,206,0.15);
        }
        .grid {
            display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px;
        }
        .col {
            background: #fff; border-radius: 16px; padding: 20px;
            min-height: 500px; box-shadow: 0 8px 24px rgba(0,0,0,0.06);
        }
        /* 顶部边框配色同步 */
        .col-align { border-top: 5px solid #f38181; }
        .col-manual { border-top: 5px solid #fce38a; }
        .col-empty { border-top: 5px solid #95e1d3; }
        .col-title {
            font-size: 16px; font-weight: 600; padding-bottom: 12px;
            margin-bottom: 16px; border-bottom: 1px solid #f1f5f9;
        }
        .item {
            padding: 10px 14px; margin-bottom: 6px; background: #f8fafc;
            border-radius: 8px; font-size: 14px; display: flex;
            justify-content: space-between; align-items: center;
        }
        .tags { display: flex; gap: 4px; }
        .tag {
            font-size: 11px; padding: 3px 6px; border-radius: 4px;
            font-weight: 600; text-transform: uppercase;
        }
        .tag-faa { background: #d1fae5; color: #065f46; }
        .tag-fna { background: #dbeafe; color: #1e40af; }
        .tag-gff { background: #fff7ed; color: #c2410c; }
        .tag-gbff { background: #f3f4f6; color: #374151; }
        .empty-tip { color: #9ca3af; text-align: center; padding: 30px 15px; }

        .advanced-sidebar {
            position: fixed; top: 20px; right: -300px; width: 280px;
            background: white; padding: 20px; border-radius: 16px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.1); transition: right 0.3s;
            z-index: 100;
        }
        .advanced-sidebar.open { right: 20px; }
        .toggle-btn {
            position: fixed; top: 20px; right: 20px;
            background: #3182ce; color: white; border: none;
            padding: 10px 16px; border-radius: 8px; cursor: pointer; z-index: 101;
        }
        .sidebar-item { padding: 10px 0; border-bottom: 1px solid #f1f5f9; }
        .sidebar-label { font-size: 13px; color: #64748b; }
        .sidebar-value { font-size: 20px; font-weight: 700; }

        @media (max-width: 1200px) { .container { grid-template-columns: 1fr; } }
        @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
    </style>
</head>

<body>
<button class="toggle-btn" onclick="toggleSidebar()">📊 高级统计</button>
<div class="advanced-sidebar" id="advancedSidebar">
    <h3 style="margin-bottom:16px">分类层级统计</h3>
    <div class="sidebar-item"><div class="sidebar-label">科总数(Family)</div><div class="sidebar-value" id="sidebarFamily">0</div></div>
    <div class="sidebar-item"><div class="sidebar-label">目总数(Order)</div><div class="sidebar-value" id="sidebarOrder">0</div></div>
    <div class="sidebar-item"><div class="sidebar-label">总属数</div><div class="sidebar-value" id="sidebarGenus">0</div></div>
    <div class="sidebar-item"><div class="sidebar-label">可比对属数</div><div class="sidebar-value" id="sidebarAlignGenus">0</div></div>
</div>

<div class="container">
    <div class="left-panel">
        <div class="donut-chart-wrapper">
            <canvas id="donutChart"></canvas>
            <div class="donut-total" id="donutTotal">0</div>
            <div class="donut-label">总物种数</div>
        </div>
        <div class="mini-card align"><div class="label">✅ 可比对物种</div><div class="value" id="miniAlign">0</div></div>
        <div class="mini-card manual"><div class="label">📝 需人工注释物种</div><div class="value" id="miniManual">0</div></div>
        <div class="mini-card empty"><div class="label">📄 空文件物种</div><div class="value" id="miniEmpty">0</div></div>
    </div>

    <div class="right-panel">
        <div class="header-card">
            <h1 class="title">🐧 物种同源比对管理系统</h1>
            <p class="desc">✅可比对(faa+gff) | 📝需人工注释(fna+gbff) | 📄空文件</p>
            <input id="search" placeholder="输入属名快速搜索..." oninput="searchData()">
        </div>

        <div class="grid">
            <div class="col col-align"><h3 class="col-title">✅ 可同源比对物种</h3><div id="listAlign" class="empty-tip"></div></div>
            <div class="col col-manual"><h3 class="col-title">📝 需人工注释物种</h3><div id="listManual" class="empty-tip"></div></div>
            <div class="col col-empty"><h3 class="col-title">📄 空文件</h3><div id="listEmpty" class="empty-tip"></div></div>
        </div>
    </div>
</div>

<script>
let donutChart;
function initChart() {
    let ctx = document.getElementById("donutChart").getContext("2d");
    // 环形图配色同步新颜色
    donutChart = new Chart(ctx, {
        type: 'doughnut',
        data: { 
            datasets: [{ 
                data: [0,0,0], 
                backgroundColor: ['#f38181','#fce38a','#95e1d3'], 
                borderWidth:0, 
                cutout:'70%' 
            }] 
        },
        options: { plugins: { legend: { display: false } } }
    });
}
function toggleSidebar() {
    document.getElementById("advancedSidebar").classList.toggle("open");
}
async function searchData() {
    let q = document.getElementById("search").value.trim();
    let res = await fetch("/search?g="+encodeURIComponent(q));
    let data = await res.json();
    render(data);
}
function render(data) {
    let alignHtml = "", manualHtml = "", emptyHtml = "";
    let totalAlign=0, totalManual=0, totalEmpty=0;
    let genusSet = new Set(), familySet = new Set(), orderSet = new Set(), alignGenusSet = new Set();

    for(let sp in data.species) {
        let info = data.species[sp];
        if(info.type === "alignable") { totalAlign++; alignGenusSet.add(info.genus); }
        if(info.type === "manual") totalManual++;
        if(info.type === "empty") totalEmpty++;
        
        genusSet.add(info.genus);
        familySet.add(info.family);
        orderSet.add(info.order);

        let line = `<div class="item"><span>${sp.replace(/_/g," ")}</span><div class="tags">${info.tags}</div></div>`;
        if(info.type === "alignable") alignHtml += line;
        else if(info.type === "manual") manualHtml += line;
        else emptyHtml += line;
    }

    donutChart.data.datasets[0].data = [totalAlign, totalManual, totalEmpty];
    donutChart.update();
    document.getElementById("donutTotal").textContent = totalAlign+totalManual+totalEmpty;
    document.getElementById("miniAlign").textContent = totalAlign;
    document.getElementById("miniManual").textContent = totalManual;
    document.getElementById("miniEmpty").textContent = totalEmpty;

    document.getElementById("sidebarFamily").textContent = familySet.size;
    document.getElementById("sidebarOrder").textContent = orderSet.size;
    document.getElementById("sidebarGenus").textContent = genusSet.size;
    document.getElementById("sidebarAlignGenus").textContent = alignGenusSet.size;

    document.getElementById("listAlign").innerHTML = alignHtml || "<span class='empty-tip'>无匹配数据</span>";
    document.getElementById("listManual").innerHTML = manualHtml || "<span class='empty-tip'>无匹配数据</span>";
    document.getElementById("listEmpty").innerHTML = emptyHtml || "<span class='empty-tip'>无匹配数据</span>";
}
window.onload = () => { initChart(); searchData(); }
</script>
</body>
</html>
"""


# ====================== 路由 ======================
@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/search")
def search():
    q = request.args.get("g", "").lower()
    result = {}

    # 检查数据目录是否存在
    if not os.path.isdir(DATA_FOLDER):
        return jsonify({"error": f"数据目录不存在: {DATA_FOLDER}", "species": {}}), 404

    for dir_name in os.listdir(DATA_FOLDER):
        dir_path = os.path.join(DATA_FOLDER, dir_name)
        if not os.path.isdir(dir_path):
            continue

        taxon = species_taxonomy.get(
            dir_name, {"genus": "未知属", "order": "未知目", "family": "未知科"}
        )
        genus = taxon["genus"]

        if q and q not in genus.lower():
            continue

        has_faa = has_fna = has_gff = has_gbff = False
        try:
            file_list = os.listdir(dir_path)
        except PermissionError:
            continue
        for f in file_list:
            ext = os.path.splitext(f.lower())[1]
            if ext in PROT_EXT:
                has_faa = True
            if ext in NUC_EXT:
                has_fna = True
            if ext in ANN_EXT_GFF:
                has_gff = True
            if ext in ANN_EXT_GBFF:
                has_gbff = True

        tags = []
        if has_faa:
            tags.append('<span class="tag tag-faa">FAA</span>')
        if has_fna:
            tags.append('<span class="tag tag-fna">FNA</span>')
        if has_gff:
            tags.append('<span class="tag tag-gff">GFF</span>')
        if has_gbff:
            tags.append('<span class="tag tag-gbff">GBFF</span>')
        tags_html = "".join(tags)

        if has_faa and has_gff:
            st = "alignable"
        elif has_fna and has_gbff:
            st = "manual"
        else:
            st = "empty"

        result[dir_name] = {
            "tags": tags_html,
            "type": st,
            "genus": genus,
            "order": taxon["order"],
            "family": taxon["family"],
        }

    return jsonify({"species": result})


# ====================== 启动服务 ======================
if __name__ == "__main__":
    print(f"✅ 基因组目录：{DATA_FOLDER}")
    print(f"✅ 访问地址：http://0.0.0.0:8080")
    app.run(host="0.0.0.0", port=8080, debug=False)
