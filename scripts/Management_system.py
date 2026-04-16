#!/usr/bin/env python3
from flask import Flask, render_template_string, request, jsonify
import os
import argparse

# ====================== 命令行参数解析 ======================
parser = argparse.ArgumentParser(
    description="🧬 物种同源比对管理系统 - 基因组文件检索工具"
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
# 蛋白序列后缀
PROT_EXT = [".faa"]

# 关键词匹配
CDS_KEY = ["cds"]
GENOME_KEY = ["genome"]

# 序列文件后缀
SEQ_EXTS = [".faa", ".fna", ".fa"]

# 注释文件后缀
ANN_EXTS = [".gff", ".gbff"]

# ====================== 前端页面模板 ======================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧬 物种同源比对管理系统</title>
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
            max-width: 1300px;
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

        /* 双列布局 */
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
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

        .col-ready {
            border-top: 5px solid #10b981;
        }

        .col-empty {
            border-top: 5px solid #9ca3af;
        }

        .col-title {
            font-size: 20px;
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

        /* 物种名称颜色（已加深） */
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

        .tag-cds {
            background: #dbeafe;
            color: #1e40af;
        }

        .tag-genome {
            background: #fff7ed;
            color: #c2410c;
        }

        .tag-gff {
            background: #f3f4f6;
            color: #374151;
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
        <h1 class="title">🧬 物种同源比对管理系统</h1>
        <p class="desc">左侧：可同源比对（FAA/CDS/Genome）｜右侧：空文件</p>
        <input id="search" placeholder="输入属名快速搜索..." oninput="searchData()">
    </div>

    <div class="grid">
        <div class="col col-ready">
            <h3 class="col-title">✅ 可同源比对物种</h3>
            <div id="listOk" class="empty-tip">请输入属名开始搜索</div>
        </div>

        <div class="col col-empty">
            <h3 class="col-title">📄 空文件 </h3>
            <div id="listEmpty" class="empty-tip">请输入属名开始搜索</div>
        </div>
    </div>
</div>

<script>
async function searchData(){
    let q = document.getElementById("search").value.trim();
    if(!q){
        document.getElementById("listOk").innerHTML = "请输入属名开始搜索";
        document.getElementById("listEmpty").innerHTML = "请输入属名开始搜索";
        return;
    }
    let res = await fetch("/search?g="+encodeURIComponent(q));
    let data = await res.json();
    render(data);
}

function render(data){
    let okHtml = "";
    let emptyHtml = "";
    const listOk = document.getElementById("listOk");
    const listEmpty = document.getElementById("listEmpty");

    for(let sp in data){
        let info = data[sp];
        let tags = info.tags;
        let hasSeq = info.hasSeq;

        let line = `
            <div class="item">
                <span>${sp.replace(/_/g," ")}</span>
                <div class="tags">${tags}</div>
            </div>
        `;
        if(hasSeq){
            okHtml += line;
        }else{
            emptyHtml += line;
        }
    }

    listOk.innerHTML = okHtml || "<span class='empty-tip'>无匹配数据</span>";
    listEmpty.innerHTML = emptyHtml || "<span class='empty-tip'>无匹配数据</span>";
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
    """搜索接口：根据属名筛选物种并返回分类信息"""
    q = request.args.get("g", "").lower()
    result = {}

    # 遍历数据目录下的所有物种文件夹
    for dir_name in os.listdir(DATA_FOLDER):
        dir_path = os.path.join(DATA_FOLDER, dir_name)

        # 只处理文件夹
        if not os.path.isdir(dir_path):
            continue

        # 匹配属名（取文件夹名第一个下划线前的部分）
        genus = dir_name.split("_")[0].lower()
        if q not in genus:
            continue

        # 初始化文件类型标记
        has_faa = False
        has_cds = False
        has_genome = False
        has_gff = False
        has_gbff = False

        # 遍历当前物种文件夹内的所有文件
        for file_name in os.listdir(dir_path):
            file_lower = file_name.lower()
            file_ext = os.path.splitext(file_lower)[1]

            # 识别序列文件
            if file_ext in PROT_EXT:
                has_faa = True
            if any(key in file_lower for key in CDS_KEY) and file_ext in SEQ_EXTS:
                has_cds = True
            if any(key in file_lower for key in GENOME_KEY) and file_ext in SEQ_EXTS:
                has_genome = True

            # 识别注释文件
            if file_ext == ".gff":
                has_gff = True
            if file_ext == ".gbff":
                has_gbff = True

        # 生成前端标签 HTML
        tag_list = []
        if has_faa:
            tag_list.append('<span class="tag tag-faa">FAA</span>')
        if has_cds:
            tag_list.append('<span class="tag tag-cds">CDS</span>')
        if has_genome:
            tag_list.append('<span class="tag tag-genome">Genome</span>')
        if has_gff:
            tag_list.append('<span class="tag tag-gff">GFF</span>')
        if has_gbff:
            tag_list.append('<span class="tag tag-gbff">GBFF</span>')

        # 判断是否可比对：存在任意序列文件即可
        has_sequence = has_faa or has_cds or has_genome

        # 存入结果
        result[dir_name] = {"tags": "".join(tag_list), "hasSeq": has_sequence}

    return jsonify(result)


# ====================== 启动服务 ======================
if __name__ == "__main__":
    print(f"✅ 启动服务，数据目录：{DATA_FOLDER}")
    print(f"✅ 访问地址：http://127.0.0.1:8080")
    app.run(host="0.0.0.0", port=8080, debug=False, threaded=True)
