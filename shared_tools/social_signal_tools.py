"""
Social Signal Tools for Multi-Agent Workflow
Tools for signal ingestion, clustering, insight analysis, and report generation.
"""
import json
import os
from datetime import datetime
from typing import Any, Dict, List
from pathlib import Path


def ingest_signals(
    hot_api_list_path: str,
    output_dir: str,
    time_window_hours: int = 24
) -> Dict[str, Any]:
    """
    Ingest signals from multiple platforms and save to structured format.
    
    Args:
        hot_api_list_path: Path to hot_api_list.json config file
        output_dir: Directory to save signal outputs
        time_window_hours: Time window for signal collection
        
    Returns:
        Dict with status and output paths
    """
    try:
        # Create output directories
        os.makedirs(output_dir, exist_ok=True)
        signals_dir = os.path.join(output_dir, "signals")
        os.makedirs(signals_dir, exist_ok=True)
        
        # Load API configuration
        if os.path.exists(hot_api_list_path):
            with open(hot_api_list_path, 'r', encoding='utf-8') as f:
                api_config = json.load(f)
        else:
            # Create mock config if not exists
            api_config = {
                "platforms": [
                    {"name": "weibo", "endpoint": "mock", "enabled": True},
                    {"name": "douyin", "endpoint": "mock", "enabled": True},
                    {"name": "zhihu", "endpoint": "mock", "enabled": True}
                ]
            }
        
        # Mock signal generation (in production, this would call actual APIs)
        all_signals = []
        fetched_at = datetime.utcnow().isoformat()
        
        for idx, platform_config in enumerate(api_config.get("platforms", [])):
            if not platform_config.get("enabled", True):
                continue
                
            platform_name = platform_config["name"]
            
            # Generate mock signals for demonstration
            platform_signals = []
            for rank in range(1, 6):  # Top 5 signals per platform
                signal = {
                    "signal_id": f"{platform_name}_{rank}",
                    "platform": platform_name,
                    "rank": rank,
                    "title": f"热点话题 {rank} from {platform_name}",
                    "metrics": {
                        "views": 1000000 - (rank * 100000),
                        "engagements": 50000 - (rank * 5000)
                    },
                    "url": f"https://{platform_name}.com/topic/{rank}",
                    "fetched_at": fetched_at
                }
                platform_signals.append(signal)
                all_signals.append(signal)
            
            # Save platform-specific signals
            platform_file = os.path.join(signals_dir, f"{platform_name}.json")
            with open(platform_file, 'w', encoding='utf-8') as f:
                json.dump(platform_signals, f, ensure_ascii=False, indent=2)
        
        # Save combined raw signals
        raw_signals_path = os.path.join(output_dir, "raw_signals.json")
        with open(raw_signals_path, 'w', encoding='utf-8') as f:
            json.dump({
                "fetched_at": fetched_at,
                "time_window_hours": time_window_hours,
                "total_signals": len(all_signals),
                "signals": all_signals
            }, f, ensure_ascii=False, indent=2)
        
        return {
            "status": "success",
            "raw_signals_path": raw_signals_path,
            "signals_dir": signals_dir,
            "total_signals": len(all_signals),
            "platforms": [p["name"] for p in api_config.get("platforms", [])]
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def cluster_signals_fallback(
    raw_signals_path: str,
    output_dir: str,
    top_k: int = 5
) -> Dict[str, Any]:
    """
    Fallback clustering when LLM fails - simple keyword-based grouping.
    
    Args:
        raw_signals_path: Path to raw_signals.json
        output_dir: Directory to save cluster outputs
        top_k: Maximum number of hotspots to return
        
    Returns:
        Dict with status and hotspots
    """
    try:
        # Load raw signals
        with open(raw_signals_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        signals = data.get("signals", [])
        
        # Simple fallback: group by platform, take top signals
        clusters_dir = os.path.join(output_dir, "clusters")
        os.makedirs(clusters_dir, exist_ok=True)
        
        # Group signals by platform
        platform_groups = {}
        for signal in signals:
            platform = signal["platform"]
            if platform not in platform_groups:
                platform_groups[platform] = []
            platform_groups[platform].append(signal)
        
        # Create hotspots (one per platform for fallback)
        hotspots = []
        for idx, (platform, platform_signals) in enumerate(platform_groups.items()):
            if idx >= top_k:
                break
            
            # Sort by views and take top signal
            platform_signals.sort(key=lambda x: x["metrics"].get("views", 0), reverse=True)
            top_signal = platform_signals[0]
            
            hotspot = {
                "hotspot_id": f"H{idx + 1}",
                "title": f"{platform}平台热点: {top_signal['title']}",
                "summary": f"来自{platform}的高热度话题",
                "signals": [s["signal_id"] for s in platform_signals[:3]],
                "platforms": [platform],
                "heat_score": min(0.9, 0.5 + (0.1 * (len(platform_signals) - idx))),
                "should_chase": True,
                "clustering_method": "fallback"
            }
            hotspots.append(hotspot)
        
        # Save hotspots
        hotspots_path = os.path.join(clusters_dir, "hotspots.json")
        with open(hotspots_path, 'w', encoding='utf-8') as f:
            json.dump({
                "clustered_at": datetime.utcnow().isoformat(),
                "method": "fallback",
                "total_hotspots": len(hotspots),
                "hotspots": hotspots
            }, f, ensure_ascii=False, indent=2)
        
        return {
            "status": "success",
            "hotspots_path": hotspots_path,
            "total_hotspots": len(hotspots),
            "hotspots": hotspots
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def insight_analysis_fallback(
    hotspots_path: str,
    output_dir: str
) -> Dict[str, Any]:
    """
    Fallback insight generation when LLM fails - basic template-based insights.
    
    Args:
        hotspots_path: Path to hotspots.json
        output_dir: Directory to save insight outputs
        
    Returns:
        Dict with status and insights
    """
    try:
        # Load hotspots
        with open(hotspots_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        hotspots = data.get("hotspots", [])
        
        # Create insights directory
        insights_dir = os.path.join(output_dir, "insights")
        os.makedirs(insights_dir, exist_ok=True)
        
        # Generate basic insights for each hotspot
        insights = []
        for hotspot in hotspots:
            insight = {
                "hotspot_id": hotspot["hotspot_id"],
                "why_now": "该话题因时事热点或社会事件引发关注",
                "core_audience": ["年轻用户群体", "活跃网民"],
                "emotion_structure": {
                    "dominant": "好奇",
                    "secondary": ["关注", "讨论"]
                },
                "content_nature": ["热点跟随", "信息传播"],
                "risk_notes": ["需注意平台内容政策", "避免争议性表达"],
                "generation_method": "fallback"
            }
            insights.append(insight)
        
        # Save insights
        insights_path = os.path.join(insights_dir, "insights.json")
        with open(insights_path, 'w', encoding='utf-8') as f:
            json.dump({
                "analyzed_at": datetime.utcnow().isoformat(),
                "method": "fallback",
                "total_insights": len(insights),
                "insights": insights
            }, f, ensure_ascii=False, indent=2)
        
        return {
            "status": "success",
            "insights_path": insights_path,
            "total_insights": len(insights),
            "insights": insights
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def render_strategy_report_fallback(
    hotspots_path: str,
    insights_path: str,
    output_dir: str
) -> Dict[str, Any]:
    """
    Fallback report rendering when LLM fails - template-based report.
    
    Args:
        hotspots_path: Path to hotspots.json
        insights_path: Path to insights.json
        output_dir: Directory to save report
        
    Returns:
        Dict with status and report path
    """
    try:
        # Load data
        with open(hotspots_path, 'r', encoding='utf-8') as f:
            hotspots_data = json.load(f)
        with open(insights_path, 'r', encoding='utf-8') as f:
            insights_data = json.load(f)
        
        hotspots = hotspots_data.get("hotspots", [])
        insights = insights_data.get("insights", [])
        
        # Create insight lookup
        insight_map = {i["hotspot_id"]: i for i in insights}
        
        # Generate markdown report
        report_lines = [
            "# 社会洞察分析报告",
            "",
            f"生成时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
            "",
            "## 当前核心热点列表",
            ""
        ]
        
        for hotspot in hotspots:
            heat_label = "🔥" * min(3, int(hotspot["heat_score"] * 3))
            chase_label = "✅ 建议追踪" if hotspot.get("should_chase") else "⚠️ 谨慎评估"
            report_lines.append(
                f"- **{hotspot['hotspot_id']}** | {hotspot['title']} | 热度: {heat_label} | {chase_label}"
            )
        
        report_lines.extend([
            "",
            "## 平台级投放建议",
            "",
            "### 短视频平台（抖音/快手）",
            ""
        ])
        
        video_hotspots = [h for h in hotspots if "douyin" in h.get("platforms", [])]
        if video_hotspots:
            for h in video_hotspots[:2]:
                insight = insight_map.get(h["hotspot_id"], {})
                report_lines.extend([
                    f"**适配热点**: {h['hotspot_id']} - {h['title']}",
                    "",
                    f"- **建议角度**: {insight.get('why_now', '跟随热点趋势')}",
                    f"- **目标受众**: {', '.join(insight.get('core_audience', ['通用用户']))}",
                    f"- **风险提示**: {'; '.join(insight.get('risk_notes', ['注意内容合规']))}",
                    ""
                ])
        else:
            report_lines.append("暂无适配短视频平台的热点")
            report_lines.append("")
        
        report_lines.extend([
            "### 社交平台（微博/知乎）",
            ""
        ])
        
        social_hotspots = [h for h in hotspots if any(p in h.get("platforms", []) for p in ["weibo", "zhihu"])]
        if social_hotspots:
            for h in social_hotspots[:2]:
                insight = insight_map.get(h["hotspot_id"], {})
                report_lines.extend([
                    f"**适配热点**: {h['hotspot_id']} - {h['title']}",
                    "",
                    f"- **建议角度**: {insight.get('why_now', '跟随热点趋势')}",
                    f"- **情绪主导**: {insight.get('emotion_structure', {}).get('dominant', '关注')}",
                    f"- **风险提示**: {'; '.join(insight.get('risk_notes', ['注意内容合规']))}",
                    ""
                ])
        else:
            report_lines.append("暂无适配社交平台的热点")
            report_lines.append("")
        
        report_lines.extend([
            "## 不建议追的热点说明",
            ""
        ])
        
        not_chase = [h for h in hotspots if not h.get("should_chase")]
        if not_chase:
            for h in not_chase:
                report_lines.append(f"- **{h['hotspot_id']}**: 热度或受众匹配度较低")
        else:
            report_lines.append("当前所有热点均建议追踪")
        
        report_lines.extend([
            "",
            "---",
            "",
            "_本报告由社会洞察多Agent工作流自动生成_"
        ])
        
        # Save report
        report_path = os.path.join(output_dir, "report.md")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        return {
            "status": "success",
            "report_path": report_path,
            "report_preview": '\n'.join(report_lines[:20])
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def register_tools(registry: object) -> None:
    """Register all social signal tools with the shared tools registry."""
    register = getattr(registry, "register_tool", None)
    if not callable(register):
        return
    
    register("social.ingest_signals", ingest_signals)
    register("social.cluster_signals_fallback", cluster_signals_fallback)
    register("social.insight_analysis_fallback", insight_analysis_fallback)
    register("social.render_strategy_report_fallback", render_strategy_report_fallback)
