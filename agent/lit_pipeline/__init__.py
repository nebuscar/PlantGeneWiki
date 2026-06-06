from lit_pipeline.processor import upload_paper, process_paper, list_papers, delete_paper
from lit_pipeline.classifier import classify_paper, classify_all_pending, get_paper_tags, update_tags
from lit_pipeline.summarizer import pregenerate_summaries


def ingest_paper(pdf_path, **meta) -> dict:
    """
    完整文献接入流水线：上传 → 处理 → 分类 → 预生成摘要。
    返回各步骤状态。
    """
    paper_id = upload_paper(pdf_path, **meta)

    proc_result = process_paper(paper_id)
    if not proc_result["success"]:
        return {"paper_id": paper_id, "success": False, **proc_result}

    tags = classify_paper(paper_id)

    return {
        "paper_id":    paper_id,
        "success":     True,
        "chunk_count": proc_result["chunk_count"],
        "tags":        tags,
    }
