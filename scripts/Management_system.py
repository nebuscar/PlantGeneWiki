#!/usr/bin/env python3
from flask import Flask, render_template_string, request, jsonify
import os
import argparse

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

# 数据目录配置（从命令行参数获取）
DATA_FOLDER = args.input

# ====================== 文件分类规则 ======================
# 核心文件后缀定义
PROT_EXT = [".faa"]  # 蛋白序列
NUC_EXT = [".fna"]  # 核酸序列
ANN_EXT_GFF = [".gff"]  # 注释文件
ANN_EXT_GBFF = [".gbff"]  # 注释文件
SEQ_EXTS = [".faa", ".fna", ".fa"]

# ====================== 前端页面模板 ======================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🐧 物种同源比对管理系统</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #f0f4f8 0%, #e2eafc 100%);
            min-height: 100vh;
            padding: 30px 20px;
            color: #2d3748;
        }

        .container {
            max-width: 1600px;
            margin: 0 auto;
        }

        /* 顶部卡片 */
        .card {
            background: #ffffff;
            padding: 32px;
            border-radius: 16px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06);
            margin-bottom: 28px;
            text-align: center;
            animation: fadeIn 0.4s ease;
        }

        .title {
            font-size: 30px;
            font-weight: 700;
            color: #1a202c;
            margin-bottom: 10px;
        }

        .desc {
            font-size: 15px;
            color: #718096;
            margin-bottom: 24px;
        }

        /* 搜索框 */
        #search {
            width: 100%;
            max-width: 600px;
            padding: 14px 20px;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            font-size: 16px;
            transition: all 0.25s ease;
            box-shadow: 0 2px 6px rgba(0,0,0,0.04);
        }

        #search:focus {
            outline: none;
            border-color: #3182ce;
            box-shadow: 0 0 0 4px rgba(49, 130, 206, 0.15);
        }

        /* 统计面板 */
        .stats-panel {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        .stat-item {
            background: #f8fafc;
            padding: 12px 16px;
            border-radius: 10px;
            min-width: 130px;
        }
        .stat-label {
            font-size: 13px;
            color: #64748b;
            margin-bottom: 4px;
        }
        .stat-number {
            font-size: 22px;
            font-weight: 700;
            color: #2d3748;
        }

        /* 三列布局 */
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 20px;
        }

        /* 列卡片 */
        .col {
            background: #fff;
            border-radius: 16px;
            padding: 28px;
            min-height: 550px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06);
            display: flex;
            flex-direction: column;
            animation: fadeIn 0.5s ease;
        }

        .col-align {
            border-top: 5px solid #10b981;
        }

        .col-manual {
            border-top: 5px solid #f59e0b;
        }

        .col-empty {
            border-top: 5px solid #9ca3af;
        }

        .col-title {
            font-size: 18px;
            font-weight: 600;
            padding-bottom: 14px;
            margin-bottom: 20px;
            border-bottom: 1px solid #f1f5f9;
            color: #1e293b;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* 列表内容 */
        .item {
            padding: 12px 16px;
            margin-bottom: 8px;
            background: #f8fafc;
            border-radius: 10px;
            font-size: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: background 0.2s;
        }

        .item:hover {
            background: #f1f5f9;
        }

        .item > span:first-child {
            color: #1e293b; 
            font-weight: 500;
        }

        .tags {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }

        .tag {
            font-size: 12px;
            font-weight: 600;
            padding: 4px 8px;
            border-radius: 6px;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }

        .tag-faa {
            background: #d1fae5;
            color: #065f46;
        }

        .tag-fna {
            background: #dbeafe;
            color: #1e40af;
        }

        .tag-gff {
            background: #fff7ed;
            color: #c2410c;
        }

        .tag-gbff {
            background: #f3f4f6;
            color: #374151;
        }

        .empty-tip {
            color: #9ca3af;
            font-size: 15px;
            text-align: center;
            padding: 40px 20px;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* 响应式 */
        @media (max-width: 1024px) {
            .grid {
                grid-template-columns: 1fr 1fr;
            }
        }
        @media (max-width: 768px) {
            .grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>

<body>
<div class="container">
    <div class="card">
        <h1 class="title">🐧 物种同源比对管理系统</h1>
        <p class="desc">✅可比对(faa+gff) | 📝需人工注释(fna+gbff) | 📄空文件</p>
        <input id="search" placeholder="输入属名快速搜索..." oninput="searchData()">
        
        <!-- 统计数据展示 -->
        <div class="stats-panel">
            <div class="stat-item">
                <div class="stat-label">总物种数</div>
                <div class="stat-number" id="totalSpecies">0</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">总属数</div>
                <div class="stat-number" id="totalGenus">0</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">可比对物种</div>
                <div class="stat-number" id="totalAlign">0</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">需人工注释物种</div>
                <div class="stat-number" id="totalManual">0</div>
            </div>
            <!-- 新增：空文件统计 -->
            <div class="stat-item">
                <div class="stat-label">空文件物种</div>
                <div class="stat-number" id="totalEmpty">0</div>
            </div>
        </div>
    </div>

    <div class="grid">
        <!-- 可同源比对 -->
        <div class="col col-align">
            <h3 class="col-title">✅ 可同源比对物种</h3>
            <div id="listAlign" class="empty-tip">请输入属名开始搜索</div>
        </div>

        <!-- 需人工注释 -->
        <div class="col col-manual">
            <h3 class="col-title">📝 需人工注释物种</h3>
            <div id="listManual" class="empty-tip">请输入属名开始搜索</div>
        </div>

        <!-- 空文件 -->
        <div class="col col-empty">
            <h3 class="col-title">📄 空文件</h3>
            <div id="listEmpty" class="empty-tip">请输入属名开始搜索</div>
        </div>
    </div>
</div>

<script>
async function searchData(){
    let q = document.getElementById("search").value.trim();
    let res = await fetch("/search?g="+encodeURIComponent(q));
    let data = await res.json();
    render(data);
}

function render(data){
    let alignHtml = "", manualHtml = "", emptyHtml = "";
    const listAlign = document.getElementById("listAlign");
    const listManual = document.getElementById("listManual");
    const listEmpty = document.getElementById("listEmpty");

    // 统计数据初始化
    let totalSpecies = Object.keys(data).length;
    let genusSet = new Set();
    let totalAlign = 0, totalManual = 0, totalEmpty = 0;

    for(let sp in data){
        let info = data[sp];
        let type = info.type;
        let tags = info.tags;

        // 统计属名
        let genus = sp.split("_")[0];
        genusSet.add(genus);

        // 统计数量
        if(type === "alignable") totalAlign++;
        if(type === "manual") totalManual++;
        if(type === "empty") totalEmpty++;

        // 生成列表项
        let line = `
            <div class="item">
                <span>${sp.replace(/_/g," ")}</span>
                <div class="tags">${tags}</div>
            </div>
        `;

        // 分类渲染
        if(type === "alignable") alignHtml += line;
        else if(type === "manual") manualHtml += line;
        else emptyHtml += line;
    }

    // 更新统计面板
    document.getElementById("totalSpecies").textContent = totalSpecies;
    document.getElementById("totalGenus").textContent = genusSet.size;
    document.getElementById("totalAlign").textContent = totalAlign;
    document.getElementById("totalManual").textContent = totalManual;
    document.getElementById("totalEmpty").textContent = totalEmpty;

    // 渲染列表
    listAlign.innerHTML = alignHtml || "<span class='empty-tip'>无匹配数据</span>";
    listManual.innerHTML = manualHtml || "<span class='empty-tip'>无匹配数据</span>";
    listEmpty.innerHTML = emptyHtml || "<span class='empty-tip'>无匹配数据</span>";
}

// 页面加载自动搜索
window.onload = function(){
    searchData();
}
</script>
</body>
</html>
"""


# ====================== 路由 ======================
@app.route("/")
def index():
    """首页路由，返回前端页面"""
    return render_template_string(HTML_TEMPLATE)


@app.route("/search")
def search():
    """搜索接口：根据属名筛选物种，按新规则分类"""
    q = request.args.get("g", "").lower()
    result = {}

    # 遍历数据目录
    for dir_name in os.listdir(DATA_FOLDER):
        dir_path = os.path.join(DATA_FOLDER, dir_name)
        if not os.path.isdir(dir_path):
            continue

        # 属名匹配筛选
        genus = dir_name.split("_")[0].lower()
        if q not in genus:
            continue

        # 初始化文件标记
        has_faa = False
        has_fna = False
        has_gff = False
        has_gbff = False

        # 遍历文件判断类型
        for file_name in os.listdir(dir_path):
            file_lower = file_name.lower()
            file_ext = os.path.splitext(file_lower)[1]

            if file_ext in PROT_EXT:
                has_faa = True
            if file_ext in NUC_EXT:
                has_fna = True
            if file_ext in ANN_EXT_GFF:
                has_gff = True
            if file_ext in ANN_EXT_GBFF:
                has_gbff = True

        # 生成标签
        tag_list = []
        if has_faa:
            tag_list.append('<span class="tag tag-faa">FAA</span>')
        if has_fna:
            tag_list.append('<span class="tag tag-fna">FNA</span>')
        if has_gff:
            tag_list.append('<span class="tag tag-gff">GFF</span>')
        if has_gbff:
            tag_list.append('<span class="tag tag-gbff">GBFF</span>')
        tags_html = "".join(tag_list)

        # ====================== 核心分类逻辑 ======================
        # 1. 可同源比对：必须同时有 faa + gff
        if has_faa and has_gff:
            species_type = "alignable"
        # 2. 需人工注释：必须同时有 fna + gbff
        elif has_fna and has_gbff:
            species_type = "manual"
        # 3. 空文件：无有效组合
        else:
            species_type = "empty"

        # 存入结果
        result[dir_name] = {"tags": tags_html, "type": species_type}

    return jsonify(result)


# ====================== 启动服务 ======================
if __name__ == "__main__":
    print(f"✅ 启动服务，数据目录：{DATA_FOLDER}")
    print(f"✅ 访问地址：http://127.0.0.1:8080")
    app.run(host="0.0.0.0", port=8080, debug=False, threaded=True)
