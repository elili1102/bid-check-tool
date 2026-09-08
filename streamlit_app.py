#!/usr/bin/env python3
"""标书检测工具 - Streamlit 版本"""

import os
import sys
import json
import time
import tempfile
import traceback
from pathlib import Path

import streamlit as st

# 确保当前目录在 sys.path 中
BASE_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(BASE_DIR))

from parsers import parse_docx, parse_xlsx
from analyzer import analyze_bid
from report_generator import generate_html_report

# ============================================================
# 页面配置
# ============================================================

PRIMARY_COLOR = "#006B54"

st.set_page_config(
    page_title="标书检测工具",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 注入自定义 CSS
st.markdown(f"""
<style>
    /* 主题色变量 */
    :root {{
        --primary: {PRIMARY_COLOR};
    }}
    /* 顶部标题栏 */
    .main-header {{
        background: linear-gradient(135deg, {PRIMARY_COLOR}, #00896A);
        color: white;
        padding: 24px 30px;
        border-radius: 12px;
        margin-bottom: 20px;
    }}
    .main-header h1 {{
        font-size: 26px;
        margin: 0 0 6px 0;
    }}
    .main-header p {{
        font-size: 14px;
        opacity: 0.85;
        margin: 0;
    }}
    /* 概览卡片 */
    .metric-card {{
        background: white;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        border: 1px solid #eee;
    }}
    .metric-card .number {{
        font-size: 36px;
        font-weight: 700;
        line-height: 1.2;
    }}
    .metric-card .label {{
        font-size: 13px;
        color: #888;
        margin-top: 4px;
    }}
    .metric-red .number {{ color: #c62828; }}
    .metric-orange .number {{ color: #e65100; }}
    .metric-blue .number {{ color: #1565c0; }}
    .metric-green .number {{ color: #2e7d32; }}

    /* 得分预估 */
    .score-display {{
        font-size: 32px;
        font-weight: 700;
        text-align: center;
        color: {PRIMARY_COLOR};
        margin: 12px 0;
    }}
    .score-sub {{
        font-size: 14px;
        text-align: center;
        color: #666;
    }}
</style>
""", unsafe_allow_html=True)

# ============================================================
# Session State 初始化
# ============================================================

if "result" not in st.session_state:
    st.session_state.result = None
if "file_names" not in st.session_state:
    st.session_state.file_names = {}
if "temp_files" not in st.session_state:
    st.session_state.temp_files = []


def cleanup_temp_files():
    """清理临时文件"""
    for fp in st.session_state.temp_files:
        try:
            if os.path.exists(fp):
                os.remove(fp)
        except Exception:
            pass
    st.session_state.temp_files = []


def save_uploaded_file(uploaded_file) -> str:
    """将上传文件保存到临时目录，返回文件路径"""
    suffix = Path(uploaded_file.name).suffix.lower()
    fd, tmp_path = tempfile.mkstemp(suffix=suffix, prefix="bid_")
    os.close(fd)
    with open(tmp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.session_state.temp_files.append(tmp_path)
    return tmp_path


# ============================================================
# 页面标题
# ============================================================

st.markdown("""
<div class="main-header">
    <h1>📋 通用标书检测工具</h1>
    <p>上传评分标准与标书文件，自动检测硬伤、扣分风险，预估得分区间</p>
</div>
""", unsafe_allow_html=True)

# ============================================================
# 第一步：文件上传
# ============================================================

st.subheader("📂 上传文件")

col1, col2, col3 = st.columns(3)

with col1:
    criteria_files = st.file_uploader(
        "评分标准（xlsx）⭐ 推荐上传",
        type=["xlsx"],
        key="criteria_uploader",
    )

with col2:
    response_files = st.file_uploader(
        "应答文件（docx）🔴 必选",
        type=["docx"],
        key="response_uploader",
    )

with col3:
    technical_files = st.file_uploader(
        "技术文件（docx）🟢 可选",
        type=["docx"],
        key="technical_uploader",
    )

# ============================================================
# 第二步：开始检查
# ============================================================

check_clicked = st.button(
    "🔍 开始检查",
    type="primary",
    use_container_width=True,
    disabled=(response_files is None),
)

if response_files is None:
    st.info("请先上传**应答文件（docx）**后点击检查。")
    st.stop()

if not check_clicked:
    # 如果尚未点击检查，且之前也没有结果 → 停止
    if st.session_state.result is None:
        st.stop()
    # 如果已有之前的结果，继续往下展示
else:
    # ========== 执行检查 ==========
    st.session_state.result = None

    progress_bar = st.progress(0, text="正在准备文件…")

    try:
        # 保存上传文件到临时目录
        progress_bar.progress(10, text="正在保存上传文件…")

        resp_path = save_uploaded_file(response_files)

        criteria_path = None
        if criteria_files:
            criteria_path = save_uploaded_file(criteria_files)

        tech_path = None
        if technical_files:
            tech_path = save_uploaded_file(technical_files)

        # 文件名映射
        file_name_map = {
            "bid_response": response_files.name,
        }
        if criteria_files:
            file_name_map["scoring_criteria"] = criteria_files.name
        if technical_files:
            file_name_map["technical_doc"] = technical_files.name

        # 解析
        progress_bar.progress(25, text="正在解析应答文件…")
        response_data = parse_docx(resp_path)

        criteria_data = None
        if criteria_path:
            progress_bar.progress(40, text="正在解析评分标准…")
            criteria_data = parse_xlsx(criteria_path)

        technical_data = None
        if tech_path:
            progress_bar.progress(55, text="正在解析技术文件…")
            technical_data = parse_docx(tech_path)

        # 分析
        progress_bar.progress(70, text="正在执行多维度分析…")
        result = analyze_bid(
            criteria=criteria_data,
            response=response_data,
            technical=technical_data,
            file_names=file_name_map,
        )

        progress_bar.progress(95, text="正在整理结果…")
        result["uploaded_files"] = [
            f.name
            for f in [response_files, criteria_files, technical_files]
            if f is not None
        ]
        st.session_state.result = result
        st.session_state.file_names = file_name_map

        progress_bar.progress(100, text="✅ 检查完成！")
        time.sleep(0.3)
        progress_bar.empty()

    except Exception as e:
        progress_bar.empty()
        st.error(f"分析过程出错：{e}")
        with st.expander("查看详细错误信息"):
            st.code(traceback.format_exc())
        cleanup_temp_files()
        st.stop()

# ============================================================
# 第三步：展示结果
# ============================================================

result = st.session_state.result
if result is None:
    st.stop()

summary = result.get("summary", {})
score = result.get("score_estimate", {})
critical_issues = result.get("critical_issues", [])
warnings = result.get("warnings", [])
completeness = result.get("completeness_check", [])
content_quality = result.get("content_quality", [])
format_checks = result.get("format_checks", [])
basic_errors = result.get("basic_errors", [])
criteria_analysis = result.get("criteria_analysis", [])
cross_checks = result.get("cross_checks", [])
has_criteria = result.get("has_criteria", False)
suggestions = result.get("suggestions", [])

# ── a) 概览卡片 ──────────────────────────────────────────

st.markdown("---")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="metric-card metric-red">
        <div class="number">{len(critical_issues)}</div>
        <div class="label">硬伤数</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="metric-card metric-orange">
        <div class="number">{len(warnings)}</div>
        <div class="label">扣分风险数</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    total_criteria = summary.get("total_criteria", len(criteria_analysis))
    st.markdown(f"""
    <div class="metric-card metric-blue">
        <div class="number">{total_criteria}</div>
        <div class="label">评分要素数</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    score_text = f"{score.get('min', 0)}~{score.get('max', 0)}" if has_criteria else "N/A"
    st.markdown(f"""
    <div class="metric-card metric-green">
        <div class="number">{score_text}</div>
        <div class="label">预估得分{('/' + str(score.get('total_max', 0))) if has_criteria else ''}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("")

# ── b) 评分要素逐项分析 ──────────────────────────────────

if criteria_analysis:
    st.subheader("📝 评分要素逐项分析")

    # 按状态排序: fail → risk → unknown → pass
    status_order = {"fail": 0, "risk": 1, "unknown": 2, "pass": 3}
    status_emoji = {
        "fail": "❌",
        "risk": "⚠️",
        "unknown": "❓",
        "pass": "✅",
    }
    sorted_criteria = sorted(
        criteria_analysis,
        key=lambda x: status_order.get(x.get("status", "unknown"), 9),
    )

    for item in sorted_criteria:
        name = item.get("name", "未知要素")
        max_s = item.get("max_score", 0)
        min_s = item.get("min_score", 0)
        status = item.get("status", "unknown")
        emoji = status_emoji.get(status, "❓")
        desc = item.get("description", "")
        issues = item.get("issues", [])
        findings = item.get("findings", [])

        header = f"{emoji} {name} （{min_s}~{max_s}分）"

        with st.expander(header, expanded=(status in ("fail", "risk"))):
            if desc:
                st.markdown(f"**评分标准：**")
                st.markdown(desc[:500] + ("..." if len(desc) > 500 else ""))

            if issues:
                st.markdown("**发现的问题：**")
                for iss in issues:
                    st.markdown(f"- {iss}")

            if findings:
                st.markdown("**修改建议：**")
                for f_item in findings:
                    st.markdown(f"- {f_item}")

            if not issues and not findings:
                st.info("未发现明显问题，建议人工复核。")

# ── c) 得分预估 ──────────────────────────────────────────

if has_criteria:
    st.markdown("---")
    st.subheader("📊 得分预估")

    s_min = score.get("min", 0)
    s_max = score.get("max", 0)
    s_total = score.get("total_max", 100)

    st.markdown(f"""
    <div class="score-display">{s_min} ~ {s_max} 分</div>
    <div class="score-sub">满分 {s_total} 分</div>
    """, unsafe_allow_html=True)

    pct = min(s_max / max(s_total, 1), 1.0)
    st.progress(pct, text=f"预估最高得分率 {pct*100:.0f}%")

    # 分项得分表
    details = score.get("details", [])
    if details:
        import pandas as pd

        df_data = []
        for d in details:
            df_data.append({
                "评审要素": d.get("name", ""),
                "满分": d.get("max_score", 0),
                "预估最低": d.get("estimated_min", 0),
                "预估最高": d.get("estimated_max", 0),
                "状态": status_emoji.get(d.get("status", "unknown"), "❓"),
            })
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

# ── d) 硬伤问题 ──────────────────────────────────────────

if critical_issues:
    st.markdown("---")
    st.subheader("🚨 硬伤问题（必须修正）")
    for i, issue in enumerate(critical_issues, 1):
        tag = issue.get("type", "未知")
        detail = issue.get("detail", "")
        suggestion = issue.get("suggestion", "")
        st.error(f"**[{tag}]** {detail}\n\n💡 建议：{suggestion}")

# ── e) 扣分风险 ──────────────────────────────────────────

if warnings:
    st.markdown("---")
    st.subheader("⚠️ 扣分风险")
    for i, w in enumerate(warnings, 1):
        tag = w.get("type", "未知")
        detail = w.get("detail", "")
        suggestion = w.get("suggestion", "")
        st.warning(f"**[{tag}]** {detail}\n\n💡 建议：{suggestion}")

# ── f) 章节完整性 ────────────────────────────────────────

if completeness:
    st.markdown("---")
    st.subheader("📑 章节完整性检查")
    import pandas as pd

    comp_data = []
    for item in completeness:
        in_resp = "✅" if item.get("in_response") else "❌"
        in_tech = "✅" if item.get("in_technical") else ("❌" if item.get("in_technical") is False else "—")
        overall = "✅" if (item.get("in_response") or item.get("in_technical")) else "❌"
        req_label = "必选" if item.get("required") else "建议"
        comp_data.append({
            "标准章节": item.get("section", ""),
            "要求": req_label,
            "应答文件": in_resp,
            "技术文件": in_tech,
            "综合": overall,
        })
    df_comp = pd.DataFrame(comp_data)
    st.dataframe(df_comp, use_container_width=True, hide_index=True)

# ── g) 修改建议汇总 ──────────────────────────────────────

# 收集所有修改建议，按优先级分组
urgent_suggestions = []      # 🔴 紧急 - 来自硬伤
important_suggestions = []   # 🟡 重要 - 来自风险
normal_suggestions = []      # 🟢 建议 - 来自格式/质量检查

for issue in critical_issues:
    urgent_suggestions.append({
        "source": issue.get("type", "硬伤"),
        "detail": issue.get("detail", ""),
        "suggestion": issue.get("suggestion", ""),
    })

for w in warnings:
    important_suggestions.append({
        "source": w.get("type", "风险"),
        "detail": w.get("detail", ""),
        "suggestion": w.get("suggestion", ""),
    })

for fc in format_checks:
    normal_suggestions.append({
        "source": fc.get("type", "格式"),
        "detail": fc.get("detail", ""),
        "suggestion": fc.get("suggestion", ""),
    })

for be in basic_errors:
    normal_suggestions.append({
        "source": be.get("type", "错误"),
        "detail": be.get("detail", ""),
        "suggestion": be.get("suggestion", ""),
    })

for cq in content_quality:
    if cq.get("status") != "pass":
        normal_suggestions.append({
            "source": cq.get("dimension", "质量"),
            "detail": cq.get("detail", ""),
            "suggestion": cq.get("suggestion", ""),
        })

st.markdown("---")
st.subheader("💡 修改建议汇总")

col_ug, col_im, col_ns = st.columns(3)

with col_ug:
    label = f"🔴 紧急（{len(urgent_suggestions)}）"
    with st.expander(label, expanded=bool(urgent_suggestions)):
        if urgent_suggestions:
            for s in urgent_suggestions:
                st.markdown(f"**[{s['source']}]** {s['detail']}")
                st.markdown(f"  💡 {s['suggestion']}")
                st.markdown("---")
        else:
            st.success("暂无紧急修改项 ✅")

with col_im:
    label = f"🟡 重要（{len(important_suggestions)}）"
    with st.expander(label, expanded=bool(important_suggestions)):
        if important_suggestions:
            for s in important_suggestions:
                st.markdown(f"**[{s['source']}]** {s['detail']}")
                st.markdown(f"  💡 {s['suggestion']}")
                st.markdown("---")
        else:
            st.success("暂无重要修改项 ✅")

with col_ns:
    label = f"🟢 建议（{len(normal_suggestions)}）"
    with st.expander(label):
        if normal_suggestions:
            for s in normal_suggestions:
                st.markdown(f"**[{s['source']}]** {s['detail']}")
                st.markdown(f"  💡 {s['suggestion']}")
                st.markdown("---")
        else:
            st.success("暂无建议修改项 ✅")

# ── h) 底部操作：导出报告 ────────────────────────────────

st.markdown("---")
st.subheader("📥 导出报告")

exp_col1, exp_col2 = st.columns(2)

with exp_col1:
    # 导出 HTML 报告
    try:
        html_content = generate_html_report(result)
        st.download_button(
            label="📄 导出 HTML 报告",
            data=html_content.encode("utf-8"),
            file_name=f"标书检查报告_{int(time.time())}.html",
            mime="text/html",
            use_container_width=True,
        )
    except Exception as e:
        st.error(f"生成 HTML 报告失败：{e}")

with exp_col2:
    # 导出 JSON
    try:
        json_bytes = json.dumps(result, ensure_ascii=False, indent=2, default=str).encode("utf-8")
        st.download_button(
            label="📋 导出 JSON 数据",
            data=json_bytes,
            file_name=f"标书检查结果_{int(time.time())}.json",
            mime="application/json",
            use_container_width=True,
        )
    except Exception as e:
        st.error(f"生成 JSON 数据失败：{e}")

# 页面底部信息
st.markdown("")
st.caption("通用标书检测工具 v2.0 · Streamlit 版 · 报告自动生成，关键项请人工复核")
