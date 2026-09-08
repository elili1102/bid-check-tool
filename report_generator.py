#!/usr/bin/env python3
"""HTML报告生成模块 - 通用标书检查报告"""

from datetime import datetime


def generate_html_report(result):
    """生成HTML格式的检查报告"""

    summary = result.get('summary', {})
    score = result.get('score_estimate', {})
    critical_issues = result.get('critical_issues', [])
    warnings = result.get('warnings', [])
    completeness = result.get('completeness_check', [])
    content_quality = result.get('content_quality', [])
    format_checks = result.get('format_checks', [])
    basic_errors = result.get('basic_errors', [])
    criteria_analysis = result.get('criteria_analysis', [])
    cross_checks = result.get('cross_checks', [])
    file_names = result.get('file_names', {})
    has_criteria = result.get('has_criteria', False)

    status_map = {
        'pass': ('✅ 基本满足', '#2e7d32', '#e8f5e9'),
        'risk': ('⚠️ 存在风险', '#e65100', '#fff3e0'),
        'fail': ('❌ 不满足', '#c62828', '#ffebee'),
        'unknown': ('❓ 待人工核查', '#5c6bc0', '#e8eaf6'),
    }

    # ===== 生成评分详情行 =====
    score_rows = ''
    for d in score.get('details', []):
        status_label, color, bg = status_map.get(d['status'], status_map['unknown'])
        score_rows += f'''
        <tr>
            <td>{d['name']}</td>
            <td style="text-align:center">{d['max_score']}</td>
            <td style="text-align:center">{d['estimated_min']} ~ {d['estimated_max']}</td>
            <td style="text-align:center"><span style="background:{bg};color:{color};padding:2px 10px;border-radius:12px;font-size:13px">{status_label}</span></td>
        </tr>'''

    # ===== 生成章节完整性 =====
    completeness_html = ''
    for item in completeness:
        in_resp = '✅' if item.get('in_response') else '❌'
        in_tech = '✅' if item.get('in_technical') else ('❌' if item.get('in_technical') is False else '—')
        overall = '✅' if (item.get('in_response') or item.get('in_technical')) else '❌'
        req_label = '必选' if item.get('required') else '建议'
        completeness_html += f'''
        <tr>
            <td>{item['section']}</td>
            <td style="text-align:center;font-size:12px;color:#888">{req_label}</td>
            <td style="text-align:center">{in_resp}</td>
            <td style="text-align:center">{in_tech}</td>
            <td style="text-align:center">{overall}</td>
        </tr>'''

    # ===== 生成内容质量检查 =====
    content_quality_html = ''
    cq_status_colors = {'pass': '#2e7d32', 'risk': '#e65100', 'fail': '#c62828'}
    cq_status_labels = {'pass': '✅ 充分', 'risk': '⚠️ 不足', 'fail': '❌ 缺失'}
    for item in content_quality:
        st = item.get('status', 'fail')
        color = cq_status_colors.get(st, '#999')
        label = cq_status_labels.get(st, '?')
        content_quality_html += f'''
        <tr>
            <td><strong>{item['dimension']}</strong></td>
            <td style="text-align:center"><span style="color:{color};font-weight:600">{label}</span></td>
            <td>{item['detail']}</td>
            <td style="font-size:13px;color:#666">{item['suggestion']}</td>
        </tr>'''

    # ===== 生成格式规范检查 =====
    format_checks_html = ''
    if format_checks:
        for i, fc in enumerate(format_checks, 1):
            format_checks_html += f'''
            <div class="issue-card warning">
                <div class="issue-header">
                    <span class="issue-badge warn">格式 #{i}</span>
                    <span class="issue-type">{fc['type']}</span>
                    <span style="font-size:12px;color:#888">[{fc.get('doc', '')}]</span>
                </div>
                <div class="issue-detail">{fc['detail']}</div>
                <div class="issue-suggestion">💡 建议：{fc['suggestion']}</div>
            </div>'''
    else:
        format_checks_html = '<div class="no-issue">格式规范检查通过 ✅</div>'

    # ===== 生成低级错误 =====
    basic_errors_html = ''
    if basic_errors:
        for i, err in enumerate(basic_errors, 1):
            basic_errors_html += f'''
            <div class="issue-card warning">
                <div class="issue-header">
                    <span class="issue-badge warn">错误 #{i}</span>
                    <span class="issue-type">{err['type']}</span>
                    <span style="font-size:12px;color:#888">[{err.get('doc', '')}]</span>
                </div>
                <div class="issue-detail">{err['detail']}</div>
                <div class="issue-suggestion">💡 建议：{err['suggestion']}</div>
            </div>'''
    else:
        basic_errors_html = '<div class="no-issue">未发现低级错误 ✅</div>'

    # ===== 生成交叉一致性检查 =====
    cross_checks_html = ''
    if cross_checks:
        for i, cc in enumerate(cross_checks, 1):
            severity = cc.get('severity', 'warning')
            card_class = 'critical' if severity == 'critical' else 'warning'
            badge_class = '' if severity == 'critical' else 'warn'
            cross_checks_html += f'''
            <div class="issue-card {card_class}">
                <div class="issue-header">
                    <span class="issue-badge {badge_class}">交叉 #{i}</span>
                    <span class="issue-type">{cc['type']}</span>
                </div>
                <div class="issue-detail">{cc['detail']}</div>
                <div class="issue-suggestion">💡 建议：{cc.get('suggestion', '请人工核查')}</div>
            </div>'''
    else:
        cross_checks_html = '<div class="no-issue">交叉一致性检查通过 ✅</div>'

    # ===== 生成硬伤问题 =====
    critical_html = ''
    if critical_issues:
        for i, issue in enumerate(critical_issues, 1):
            critical_html += f'''
            <div class="issue-card critical">
                <div class="issue-header">
                    <span class="issue-badge">硬伤 #{i}</span>
                    <span class="issue-type">{issue['type']}</span>
                </div>
                <div class="issue-detail">{issue['detail']}</div>
                <div class="issue-suggestion">💡 建议：{issue['suggestion']}</div>
            </div>'''
    else:
        critical_html = '<div class="no-issue">未发现硬伤问题 ✅</div>'

    # ===== 生成警告 =====
    warnings_html = ''
    if warnings:
        for i, w in enumerate(warnings, 1):
            warnings_html += f'''
            <div class="issue-card warning">
                <div class="issue-header">
                    <span class="issue-badge warn">风险 #{i}</span>
                    <span class="issue-type">{w['type']}</span>
                </div>
                <div class="issue-detail">{w['detail']}</div>
                <div class="issue-suggestion">💡 建议：{w['suggestion']}</div>
            </div>'''
    else:
        warnings_html = '<div class="no-issue">未发现明显风险 ✅</div>'

    # ===== 生成评分要素详细分析 =====
    criteria_html = ''
    for item in criteria_analysis:
        status_label, color, bg = status_map.get(item['status'], status_map['unknown'])
        issues_text = ''
        for issue in item.get('issues', []):
            issues_text += f'<li>{issue}</li>'
        findings_text = ''
        for finding in item.get('findings', []):
            findings_text += f'<li>{finding}</li>'

        criteria_html += f'''
        <div class="criteria-card" style="border-left:4px solid {color}">
            <div class="criteria-header">
                <strong>{item['name']}</strong>
                <span class="score-badge" style="background:{bg};color:{color}">{item['min_score']}~{item['max_score']}分</span>
                <span style="background:{bg};color:{color};padding:2px 10px;border-radius:12px;font-size:13px;margin-left:8px">{status_label}</span>
            </div>
            <div class="criteria-desc">{item['description'][:200]}{'...' if len(item.get('description',''))>200 else ''}</div>
            {f'<ul class="issues-list">{issues_text}</ul>' if issues_text else ''}
            {f'<ul class="findings-list">{findings_text}</ul>' if findings_text else ''}
        </div>'''

    # ===== 评分预估部分HTML =====
    score_section_html = ''
    if has_criteria:
        score_pct = score.get('max', 0) / max(score.get('total_max', 1), 1) * 100
        score_section_html = f'''
        <div class="score-section">
            <h2>📊 得分预估</h2>
            <div class="score-text">{score.get('min', 0)} ~ {score.get('max', 0)} 分</div>
            <div class="score-range">满分 {score.get('total_max', 100)} 分</div>
            <div class="score-bar">
                <div class="score-fill" style="width: {score_pct:.0f}%"></div>
            </div>
            <table>
                <thead>
                    <tr><th>评审要素</th><th>满分</th><th>预估区间</th><th>状态</th></tr>
                </thead>
                <tbody>{score_rows}</tbody>
            </table>
        </div>'''

    # ===== 交叉一致性section（仅多文件时显示） =====
    cross_section_html = ''
    if len([v for v in file_names.values() if v]) >= 2:
        cross_section_html = f'''
        <div class="section">
            <h2>🔗 交叉一致性检查</h2>
            {cross_checks_html}
        </div>'''

    # ===== 评分要素section（有评分标准时显示） =====
    criteria_section_html = ''
    if has_criteria:
        criteria_section_html = f'''
        <div class="section">
            <h2>📝 评分要素逐项分析</h2>
            {criteria_html}
        </div>'''

    # ===== 检查维度数 =====
    check_dims = summary.get('check_dimensions', 5)

    # ===== 文件标签 =====
    file_tags = "".join(f'<span class="file-tag">{v}</span>' for v in file_names.values() if v)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>通用标书检查报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; background: #f5f7fa; color: #333; line-height: 1.6; }}
        .container {{ max-width: 1000px; margin: 0 auto; padding: 20px; }}

        .header {{ background: linear-gradient(135deg, #006B54, #00896A); color: white; padding: 30px; border-radius: 12px; margin-bottom: 24px; }}
        .header h1 {{ font-size: 24px; margin-bottom: 8px; }}
        .header .meta {{ opacity: 0.85; font-size: 14px; }}

        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .summary-card {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); text-align: center; }}
        .summary-card .number {{ font-size: 36px; font-weight: 700; }}
        .summary-card .label {{ font-size: 13px; color: #888; margin-top: 4px; }}
        .summary-card.danger .number {{ color: #c62828; }}
        .summary-card.warn .number {{ color: #e65100; }}
        .summary-card.ok .number {{ color: #2e7d32; }}
        .summary-card.info .number {{ color: #1565c0; }}

        .score-section {{ background: white; border-radius: 10px; padding: 24px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
        .score-section h2 {{ font-size: 18px; margin-bottom: 16px; color: #006B54; border-bottom: 2px solid #e8f5e9; padding-bottom: 8px; }}
        .score-bar {{ background: #e0e0e0; border-radius: 20px; height: 24px; margin: 16px 0; position: relative; overflow: hidden; }}
        .score-fill {{ height: 100%; border-radius: 20px; background: linear-gradient(90deg, #c62828, #e65100, #2e7d32); transition: width 0.5s; }}
        .score-text {{ font-size: 28px; font-weight: 700; text-align: center; margin: 8px 0; }}
        .score-range {{ text-align: center; color: #666; font-size: 14px; }}

        table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
        th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; font-size: 14px; }}
        th {{ background: #f8f9fa; font-weight: 600; color: #555; }}
        tr:hover {{ background: #fafafa; }}

        .section {{ background: white; border-radius: 10px; padding: 24px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
        .section h2 {{ font-size: 18px; margin-bottom: 16px; color: #006B54; border-bottom: 2px solid #e8f5e9; padding-bottom: 8px; }}

        .issue-card {{ border-radius: 8px; padding: 16px; margin-bottom: 12px; border-left: 4px solid; }}
        .issue-card.critical {{ background: #ffebee; border-color: #c62828; }}
        .issue-card.warning {{ background: #fff3e0; border-color: #e65100; }}
        .issue-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }}
        .issue-badge {{ background: #c62828; color: white; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
        .issue-badge.warn {{ background: #e65100; }}
        .issue-type {{ font-weight: 600; font-size: 14px; }}
        .issue-detail {{ font-size: 14px; margin-bottom: 8px; color: #444; }}
        .issue-suggestion {{ font-size: 13px; color: #666; background: rgba(255,255,255,0.6); padding: 8px 12px; border-radius: 6px; }}

        .criteria-card {{ background: #fafafa; border-radius: 8px; padding: 16px; margin-bottom: 12px; }}
        .criteria-header {{ display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }}
        .score-badge {{ padding: 2px 10px; border-radius: 12px; font-size: 12px; }}
        .criteria-desc {{ font-size: 13px; color: #666; margin-bottom: 8px; }}
        .issues-list, .findings-list {{ font-size: 13px; padding-left: 20px; color: #555; }}
        .issues-list li {{ color: #c62828; }}
        .findings-list li {{ color: #555; }}

        .no-issue {{ text-align: center; padding: 20px; color: #2e7d32; font-size: 16px; }}

        .file-list {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }}
        .file-tag {{ background: #e8f5e9; color: #2e7d32; padding: 4px 12px; border-radius: 16px; font-size: 12px; }}

        .footer {{ text-align: center; color: #999; font-size: 12px; padding: 20px; }}

        @media (max-width: 600px) {{
            .container {{ padding: 12px; }}
            .summary-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .header h1 {{ font-size: 20px; }}
        }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>📋 通用标书检查报告</h1>
        <div class="meta">
            生成时间：{result.get('timestamp', '')}<br>
            分析文件：{len([v for v in file_names.values() if v])} 个 · 检查维度：{check_dims} 项
            <div class="file-list">
                {file_tags}
            </div>
        </div>
    </div>

    <!-- 概览卡片 -->
    <div class="summary-grid">
        <div class="summary-card {'danger' if summary.get('total_critical', 0) > 0 else 'ok'}">
            <div class="number">{summary.get('total_critical', 0)}</div>
            <div class="label">硬伤问题</div>
        </div>
        <div class="summary-card {'warn' if summary.get('total_warnings', 0) > 0 else 'ok'}">
            <div class="number">{summary.get('total_warnings', 0)}</div>
            <div class="label">扣分风险</div>
        </div>
        <div class="summary-card {'warn' if summary.get('total_format_issues', 0) > 0 else 'ok'}">
            <div class="number">{summary.get('total_format_issues', 0)}</div>
            <div class="label">格式问题</div>
        </div>
        <div class="summary-card {'warn' if summary.get('total_basic_errors', 0) > 0 else 'ok'}">
            <div class="number">{summary.get('total_basic_errors', 0)}</div>
            <div class="label">低级错误</div>
        </div>
        <div class="summary-card info">
            <div class="number">{check_dims}</div>
            <div class="label">检查维度</div>
        </div>
        {'<div class="summary-card ok"><div class="number">' + str(score.get('min', 0)) + '-' + str(score.get('max', 0)) + '</div><div class="label">预估得分/' + str(score.get('total_max', 100)) + '</div></div>' if has_criteria else ''}
    </div>

    <!-- 得分预估（有评分标准时） -->
    {score_section_html}

    <!-- 结构完整性检查 -->
    <div class="section">
        <h2>📑 结构完整性检查</h2>
        <table>
            <thead>
                <tr><th>标准章节</th><th style="text-align:center">要求</th><th style="text-align:center">应答文件</th><th style="text-align:center">技术文件</th><th style="text-align:center">综合</th></tr>
            </thead>
            <tbody>{completeness_html}</tbody>
        </table>
    </div>

    <!-- 内容质量检查 -->
    <div class="section">
        <h2>📝 内容质量检查</h2>
        <table>
            <thead>
                <tr><th>检查维度</th><th style="text-align:center">状态</th><th>发现</th><th>建议</th></tr>
            </thead>
            <tbody>{content_quality_html}</tbody>
        </table>
    </div>

    <!-- 格式规范检查 -->
    <div class="section">
        <h2>📐 格式规范检查</h2>
        {format_checks_html}
    </div>

    <!-- 低级错误 -->
    <div class="section">
        <h2>🔍 低级错误检查</h2>
        {basic_errors_html}
    </div>

    <!-- 交叉一致性检查（多文件时） -->
    {cross_section_html}

    <!-- 评分要素逐项分析（有评分标准时） -->
    {criteria_section_html}

    <!-- 硬伤问题汇总 -->
    <div class="section">
        <h2>🚨 硬伤问题（必须修正）</h2>
        {critical_html}
    </div>

    <!-- 扣分风险汇总 -->
    <div class="section">
        <h2>⚠️ 扣分风险</h2>
        {warnings_html}
    </div>

    <div class="footer">
        通用标书检查工具 v2.0 · 报告自动生成，关键项请人工复核
    </div>
</div>
</body>
</html>'''

    return html
