import json
import os
import time
import requests
import asyncio
from typing import Any, Dict
from pathlib import Path
from .tool_base import Tool, ToolOutput, ToolCategory 

class PaperCrawlTool(Tool):
    """学术论文摘要爬取工具 - 从 OpenReview 接口爬取指定会议的论文数据并保存为 Markdown 文件"""
    
    # 爬取的文件将保存到 Agent 的临时目录
    DEFAULT_PAPERS_DIR = Path(os.getenv("AGENT_TMP_DIR", "/tmp"))
    
    def _get_name(self) -> str:
        return "crawl_paper_abstracts"
    
    def _get_description(self) -> str:
        return "从 OpenReview 接口爬取指定会议/提交组的论文摘要、标题等数据，并将结果保存为单个 Markdown 文件。适用于批量获取会议论文列表。文件内容将嵌入元数据标记，方便后续RAG溯源。"
    
    def _get_category(self) -> ToolCategory:
        return ToolCategory.WEB_SCRAPING
    
    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "venue_id": {
                    "type": "string",
                    "description": "会议的 OpenReview ID，例如：'ICLR.cc/2026/Conference/Submission'"
                },
                "output_filename": {
                    "type": "string",
                    "description": "输出文件名，例如：'iclr_2026_submissions.md'。文件将保存在 Agent 的临时目录 (/tmp) 中。"
                },
                "limit": {
                    "type": "integer",
                    "description": "最大爬取数量（默认1000）。爬取数量过多可能会消耗较多时间。",
                    "default": 1000
                }
            },
            "required": ["venue_id", "output_filename"]
        }
    
    def _fetch_submissions(self, venue_id, offset=0, limit=100):
        """同步的 API 请求"""
        url = "https://api2.openreview.net/notes"
        params = {
            "content.venueid": venue_id,
            "details": "replyCount,invitation",
            "limit": limit,
            "offset": offset,
            "sort": "number:desc"
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, params=params, headers=headers, timeout=20.0)
        response.raise_for_status()
        return response.json()

    def _crawl_and_save(self, venue_id: str, output_filename: str, max_limit: int) -> Dict[str, Any]:
        """爬取核心逻辑，在单独线程中执行"""
        all_papers = []
        offset = 0
        limit = 100 
        output_file_path = self.DEFAULT_PAPERS_DIR / output_filename
        
        output_file_path.parent.mkdir(parents=True, exist_ok=True) 

        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(f"# 论文摘要爬取报告 - {venue_id}\n\n")
            total_fetched = 0
            
            while total_fetched < max_limit:
                current_limit = min(limit, max_limit - total_fetched)
                if current_limit <= 0:
                    break
                    
                data = self._fetch_submissions(venue_id, offset, current_limit)
                notes = data.get("notes", [])
                
                if not notes:
                    break
                
                for note in notes:
                    if total_fetched >= max_limit:
                        break
                    
                    paper = {
                        "number": note.get("number"),
                        "title": note.get("content", {}).get("title", {}).get("value", ""),
                        "authors": ", ".join(note.get("content", {}).get("authors", {}).get("value", [])),
                        "abstract": note.get("content", {}).get("abstract", {}).get("value", ""),
                        "forum_url": f"https://openreview.net/forum?id={note.get('id')}"
                    }
                    
                    # === 关键：嵌入 JSON 元数据标记，供 DocumentService 解析和溯源 ===
                    metadata_json = json.dumps({
                        "original_title": paper['title'],
                        "original_url": paper['forum_url'],
                        "document_type": "OpenReview_Paper",
                        "authors": paper['authors']
                    }, ensure_ascii=False)
                    
                    md_content = f"""<metadata_json_start>{metadata_json}<metadata_json_end>
## {paper['title']}
- **编号**: {paper['number']}
- **作者**: {paper['authors']}
- **链接**: <{paper['forum_url']}>

### 摘要
{paper['abstract']}

---\n"""
                    f.write(md_content)
                    all_papers.append(paper)
                    total_fetched += 1

                if len(notes) < current_limit:
                    break
                    
                offset += current_limit
                time.sleep(0.5) # 速率限制

        return {"total_papers": total_fetched, "file_path": str(output_file_path), "venue_id": venue_id}

    async def _execute(self, venue_id: str, output_filename: str, limit: int = 1000) -> ToolOutput:
        """异步执行爬取任务"""
        try:
            results = await asyncio.to_thread(self._crawl_and_save, venue_id, output_filename, limit)
            
            if results["total_papers"] == 0:
                 return ToolOutput(success=False, result=None, error=f"未爬取到任何论文。请检查 venue_id: {venue_id} 是否正确，或该会议数据是否已公开。")

            return ToolOutput(
                success=True,
                result=f"成功爬取 {results['total_papers']} 篇论文，并保存到文件 {results['file_path']}。此文件可用于后续知识库上传。",
                metadata=results
            )
        except Exception as e:
            return ToolOutput(success=False, result=None, error=f"论文爬取失败: {str(e)}")