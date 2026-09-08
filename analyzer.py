#!/usr/bin/env python3
"""通用标书分析引擎 - 支持多维度检查，不强制依赖评分标准"""

import re
from datetime import datetime
from collections import Counter


def analyze_bid(criteria=None, response=None, technical=None, file_names=None):
    """
    通用标书分析入口

    Args:
        criteria: 评分标准解析结果（可选，为None时只做通用检查）
        response: 应答文件解析结果（主要文件）
        technical: 技术文件解析结果（可选）
        file_names: 文件名映射

    Returns:
        分析结果字典
    """
    # 确保 response 存在
    if response is None:
        return _empty_result(file_names)

    result = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'file_names': file_names or {},
        'summary': {},
        'completeness_check': [],     # A. 结构完整性检查
        'content_quality': [],        # B. 内容质量检查
        'format_checks': [],          # C. 格式规范检查
        'basic_errors': [],           # D. 低级错误检查
        'cross_checks': [],           # E. 交叉一致性检查
        'criteria_analysis': [],      # F. 评分要素逐项分析（有评分标准时）
        'critical_issues': [],        # 硬伤/致命问题
        'warnings': [],               # 警告/扣分风险
        'suggestions': [],            # 改进建议
        'score_estimate': {           # 得分预估（有评分标准时）
            'min': 0, 'max': 0, 'total_max': 0, 'details': []
        },
        'has_criteria': criteria is not None and len(criteria.get('criteria_items', [])) > 0,
    }

    criteria_items = criteria.get('criteria_items', []) if criteria else []
    response_key_info = response.get('key_info', {})

    # ========== A. 标书结构完整性检查 ==========
    result['completeness_check'] = check_completeness(response, technical, criteria_items)

    # ========== B. 内容质量检查 ==========
    result['content_quality'] = check_content_quality(response, technical)

    # ========== C. 格式规范检查 ==========
    result['format_checks'] = check_format_compliance(response, technical)

    # ========== D. 低级错误检查 ==========
    result['basic_errors'] = check_basic_errors(response, technical)

    # ========== E. 交叉一致性检查（多文件时） ==========
    result['cross_checks'] = perform_cross_checks(response, technical)

    # ========== F. 评分要素分析（有评分标准时） ==========
    if criteria_items:
        for item in criteria_items:
            analysis = analyze_single_criteria(item, response, technical, response_key_info)
            result['criteria_analysis'].append(analysis)

        # 计算预估分数
        result['score_estimate'] = estimate_score(criteria_items, result['criteria_analysis'])

    # ========== 专项检查（汇总到硬伤和警告中） ==========

    # 业绩专项
    performance_checks = check_performance(response_key_info)
    result['critical_issues'].extend(performance_checks.get('critical', []))
    result['warnings'].extend(performance_checks.get('warnings', []))

    # 人员资质专项
    personnel_checks = check_personnel(response_key_info, criteria_items)
    result['critical_issues'].extend(personnel_checks.get('critical', []))
    result['warnings'].extend(personnel_checks.get('warnings', []))

    # 时间逻辑检查
    time_checks = check_time_logic(response)
    if technical:
        time_checks_tech = check_time_logic(technical)
        time_checks['critical'].extend(time_checks_tech.get('critical', []))
        time_checks['warnings'].extend(time_checks_tech.get('warnings', []))
    result['critical_issues'].extend(time_checks.get('critical', []))
    result['warnings'].extend(time_checks.get('warnings', []))

    # 认证资质检查
    cert_checks = check_certifications(response, technical, criteria_items)
    result['critical_issues'].extend(cert_checks.get('critical', []))
    result['warnings'].extend(cert_checks.get('warnings', []))

    # ========== 汇总 ==========
    total_issues = (len(result['critical_issues']) + len(result['warnings']) +
                    len(result['format_checks']) + len(result['basic_errors']))
    check_dimensions = 6 if criteria_items else 5  # 有评分标准时多一个维度

    result['summary'] = {
        'total_criteria': len(criteria_items),
        'total_critical': len(result['critical_issues']),
        'total_warnings': len(result['warnings']),
        'total_format_issues': len(result['format_checks']),
        'total_basic_errors': len(result['basic_errors']),
        'total_issues': total_issues,
        'check_dimensions': check_dimensions,
        'has_technical_doc': technical is not None,
        'has_criteria': len(criteria_items) > 0,
    }

    return result


def _empty_result(file_names):
    """返回空结果"""
    return {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'file_names': file_names or {},
        'summary': {}, 'completeness_check': [], 'content_quality': [],
        'format_checks': [], 'basic_errors': [], 'cross_checks': [],
        'criteria_analysis': [], 'critical_issues': [], 'warnings': [],
        'suggestions': [], 'score_estimate': {'min': 0, 'max': 0, 'total_max': 0, 'details': []},
        'has_criteria': False,
    }


# ============================================================
# A. 标书结构完整性检查
# ============================================================

def check_completeness(response, technical, criteria_items):
    """检查标书章节完整性（基于标准标书框架）"""
    checks = []

    # 标准标书应包含的章节（扩展版）
    required_sections = [
        {
            'name': '技术偏差表/偏离表',
            'keywords': ['偏差', '偏离', '偏离表', '偏差表'],
            'required': True,
            'category': 'structure'
        },
        {
            'name': '点对点应答/技术规格响应',
            'keywords': ['应答', '响应', '逐条', '点对点', '规格响应'],
            'required': True,
            'category': 'structure'
        },
        {
            'name': '业绩材料/项目案例',
            'keywords': ['业绩', '案例', '项目经验', '类似项目', '工程业绩'],
            'required': True,
            'category': 'structure'
        },
        {
            'name': '项目团队/人员配置',
            'keywords': ['团队', '人员', '组织', '项目组', '人员配置', '团队配置'],
            'required': True,
            'category': 'structure'
        },
        {
            'name': '对项目的理解/需求分析',
            'keywords': ['理解', '现状', '需求分析', '项目背景', '项目概述'],
            'required': True,
            'category': 'structure'
        },
        {
            'name': '工作规划/技术方案/服务方案',
            'keywords': ['规划', '方案', '计划', '技术方案', '服务方案', '实施方案'],
            'required': True,
            'category': 'structure'
        },
        {
            'name': '履约能力/质量保证措施',
            'keywords': ['质量', '保障', '质控', '履约', '质量保证', '质量保障'],
            'required': True,
            'category': 'structure'
        },
        {
            'name': '服务承诺/售后服务',
            'keywords': ['承诺', '服务', '售后', '服务承诺', '质保期'],
            'required': True,
            'category': 'structure'
        },
        {
            'name': '资质证明/附件清单',
            'keywords': ['资质', '附件', '证明', '证书', '资格'],
            'required': False,
            'category': 'structure'
        },
    ]

    # 收集所有章节标题和全文
    all_text = response.get('full_text', '').lower()
    if technical:
        all_text += '\n' + technical.get('full_text', '').lower()

    sections = response.get('sections', [])
    section_titles = [s.get('title', '').lower() for s in sections]

    tech_sections = []
    tech_titles = []
    if technical:
        tech_sections = technical.get('sections', [])
        tech_titles = [s.get('title', '').lower() for s in tech_sections]

    for item in required_sections:
        found_in_resp = _check_keywords_in_list(section_titles, item['keywords'])
        if not found_in_resp:
            found_in_resp = _check_keywords_in_text(response.get('full_text', '').lower(), item['keywords'])

        found_in_tech = None
        if technical:
            found_in_tech = _check_keywords_in_list(tech_titles, item['keywords'])
            if not found_in_tech:
                found_in_tech = _check_keywords_in_text(technical.get('full_text', '').lower(), item['keywords'])

        checks.append({
            'section': item['name'],
            'in_response': found_in_resp,
            'in_technical': found_in_tech,
            'required': item['required'],
            'category': item['category']
        })

    return checks


def _check_keywords_in_list(title_list, keywords):
    """在标题列表中查找关键词"""
    for title in title_list:
        if any(kw in title for kw in keywords):
            return True
    return False


def _check_keywords_in_text(text, keywords):
    """在全文中查找关键词（要求至少一个关键词出现在合理上下文中）"""
    for kw in keywords:
        if kw in text:
            return True
    return False


# ============================================================
# B. 内容质量检查
# ============================================================

def check_content_quality(response, technical):
    """检查内容质量（架构图、流程图、功能设计、关键技术、进度计划、人员分工）"""
    checks = []
    combined = response.get('full_text', '')
    if technical:
        combined += '\n' + technical.get('full_text', '')

    # B1. 架构图检查
    arch_keywords = ['总体架构', '应用架构', '数据架构', '技术架构', '部署架构',
                     '系统架构', '网络架构', '逻辑架构', '物理架构']
    arch_found = [kw for kw in arch_keywords if kw in combined]
    checks.append({
        'dimension': '架构图描述',
        'status': 'pass' if len(arch_found) >= 3 else ('risk' if len(arch_found) >= 1 else 'fail'),
        'found_items': arch_found,
        'expected_items': arch_keywords,
        'detail': f'发现{len(arch_found)}类架构描述：{", ".join(arch_found)}' if arch_found else '未发现架构描述相关内容',
        'suggestion': '建议包含总体架构、应用架构、数据架构、技术架构、部署架构等描述'
    })

    # B2. 流程图检查
    flow_keywords = ['工作流程', '业务流程', '流程图', '处理流程', '实施流程',
                     '操作步骤', '作业流程', '服务流程']
    flow_found = [kw for kw in flow_keywords if kw in combined]
    checks.append({
        'dimension': '流程描述',
        'status': 'pass' if len(flow_found) >= 2 else ('risk' if len(flow_found) >= 1 else 'fail'),
        'found_items': flow_found,
        'expected_items': flow_keywords,
        'detail': f'发现{len(flow_found)}类流程描述：{", ".join(flow_found)}' if flow_found else '未发现流程描述相关内容',
        'suggestion': '建议包含工作流程或业务流程的详细描述'
    })

    # B3. 功能设计检查
    func_keywords = ['功能模块', '功能清单', '功能描述', '功能设计', '功能说明',
                     '系统功能', '模块功能', '功能列表']
    func_found = [kw for kw in func_keywords if kw in combined]
    checks.append({
        'dimension': '功能设计',
        'status': 'pass' if len(func_found) >= 2 else ('risk' if len(func_found) >= 1 else 'fail'),
        'found_items': func_found,
        'expected_items': func_keywords,
        'detail': f'发现{len(func_found)}类功能设计描述：{", ".join(func_found)}' if func_found else '未发现功能设计相关内容',
        'suggestion': '建议包含功能模块清单和详细功能描述'
    })

    # B4. 关键技术检查
    tech_keywords = ['关键技术', '核心技术', '技术路线', '技术方案', '技术选型',
                     '先进技术', '技术创新', '技术方案']
    tech_found = [kw for kw in tech_keywords if kw in combined]
    checks.append({
        'dimension': '关键技术',
        'status': 'pass' if len(tech_found) >= 2 else ('risk' if len(tech_found) >= 1 else 'fail'),
        'found_items': tech_found,
        'expected_items': tech_keywords,
        'detail': f'发现{len(tech_found)}类关键技术描述：{", ".join(tech_found)}' if tech_found else '未发现关键技术相关内容',
        'suggestion': '建议明确描述采用的关键技术和技术路线'
    })

    # B5. 进度计划检查
    schedule_keywords = ['进度计划', '里程碑', '时间安排', '项目进度', '实施进度',
                         '工期安排', '进度表', '甘特图', '时间节点']
    schedule_found = [kw for kw in schedule_keywords if kw in combined]
    checks.append({
        'dimension': '进度计划',
        'status': 'pass' if len(schedule_found) >= 2 else ('risk' if len(schedule_found) >= 1 else 'fail'),
        'found_items': schedule_found,
        'expected_items': schedule_keywords,
        'detail': f'发现{len(schedule_found)}类进度描述：{", ".join(schedule_found)}' if schedule_found else '未发现进度计划相关内容',
        'suggestion': '建议包含项目进度安排、里程碑计划和详细时间节点'
    })

    # B6. 人员配置检查
    personnel_keywords = ['人员分工', '人员配置', '组织架构', '团队分工', '人员安排',
                         '岗位职责', '角色分工', '团队结构']
    personnel_found = [kw for kw in personnel_keywords if kw in combined]
    # 也检查是否有人员表格
    has_person_table = False
    for table in response.get('tables', []):
        if table.get('category') == 'personnel':
            has_person_table = True
            break
    if technical:
        for table in technical.get('tables', []):
            if table.get('category') == 'personnel':
                has_person_table = True
                break

    checks.append({
        'dimension': '人员配置',
        'status': 'pass' if (len(personnel_found) >= 1 and has_person_table) else
                  ('risk' if (len(personnel_found) >= 1 or has_person_table) else 'fail'),
        'found_items': personnel_found + (['人员表格'] if has_person_table else []),
        'expected_items': personnel_keywords,
        'detail': (f'发现{len(personnel_found)}类人员配置描述' +
                  ('，且有人员分工表格' if has_person_table else '')),
        'suggestion': '建议包含明确的人员分工表和组织架构描述'
    })

    return checks


# ============================================================
# C. 格式规范检查
# ============================================================

def check_format_compliance(response, technical):
    """检查格式规范（编号连续性、标题层级、空章节、表格完整性）"""
    issues = []

    for doc_name, parsed_doc in [('应答文件', response)] + (
        [('技术文件', technical)] if technical else []):

        if not parsed_doc:
            continue

        paragraphs = parsed_doc.get('paragraphs', [])
        sections = parsed_doc.get('sections', [])
        numbering_info = parsed_doc.get('numbering_info', [])
        tables = parsed_doc.get('tables', [])

        # C1. 编号连续性检查
        issues.extend(check_numbering_continuity(numbering_info, doc_name))

        # C2. 标题层级一致性检查
        issues.extend(check_heading_levels(sections, doc_name))

        # C3. 空章节检查
        issues.extend(check_empty_sections(sections, doc_name))

        # C4. 表格完整性检查
        issues.extend(check_table_completeness(tables, doc_name))

    return issues


def check_numbering_continuity(numbering_info, doc_name):
    """检查编号连续性"""
    issues = []

    # 按层级分组检查
    by_level = {}
    for item in numbering_info:
        if 'parts' not in item or not item['parts']:
            continue
        level = len(item['parts'])
        if level not in by_level:
            by_level[level] = []
        by_level[level].append(item)

    for level, items in by_level.items():
        if len(items) < 2:
            continue

        # 检查同级编号是否连续
        for i in range(1, len(items)):
            prev_parts = items[i-1]['parts']
            curr_parts = items[i]['parts']

            # 只比较同级（前缀相同）
            if level == 1:
                # 一级编号：1, 2, 3...
                if curr_parts[0] != prev_parts[0] + 1:
                    # 检查是否跳过了编号
                    if curr_parts[0] > prev_parts[0] + 1:
                        issues.append({
                            'type': '编号不连续',
                            'doc': doc_name,
                            'detail': f'一级编号从 {prev_parts[0]} 跳到 {curr_parts[0]}，'
                                      f'缺少 {", ".join(str(x) for x in range(prev_parts[0]+1, curr_parts[0]))}',
                            'context': f'"{items[i-1]["text"][:30]}" → "{items[i]["text"][:30]}"',
                            'suggestion': '检查是否遗漏了中间章节'
                        })
            elif level >= 2:
                # 检查子编号的父编号是否相同
                prefix_match = all(curr_parts[j] == prev_parts[j] for j in range(level - 1))
                if prefix_match:
                    if curr_parts[-1] != prev_parts[-1] + 1 and curr_parts[-1] > prev_parts[-1] + 1:
                        parent = '.'.join(str(x) for x in prev_parts[:-1])
                        issues.append({
                            'type': '子编号不连续',
                            'doc': doc_name,
                            'detail': f'{parent} 下的子编号从 {prev_parts[-1]} 跳到 {curr_parts[-1]}',
                            'context': f'"{items[i-1]["text"][:30]}" → "{items[i]["text"][:30]}"',
                            'suggestion': '检查是否遗漏了子章节'
                        })

    return issues


def check_heading_levels(sections, doc_name):
    """检查标题层级一致性（是否有跳级）"""
    issues = []

    for i in range(1, len(sections)):
        prev_level = sections[i-1]['level']
        curr_level = sections[i]['level']

        # 检查是否跳级（如从1级直接到3级）
        if curr_level > prev_level + 1:
            issues.append({
                'type': '标题层级跳级',
                'doc': doc_name,
                'detail': f'标题从"{sections[i-1]["title"][:30]}"(第{prev_level+1}级) '
                          f'跳到"{sections[i]["title"][:30]}"(第{curr_level+1}级)，跳过了第{prev_level+2}级',
                'context': '',
                'suggestion': '检查标题层级是否正确，避免从第1级直接到第3级'
            })

    return issues


def check_empty_sections(sections, doc_name):
    """检查空章节（标题下无内容）"""
    issues = []

    for section in sections:
        if not section.get('has_content', False) and section.get('content_length', 0) == 0:
            # 检查是否有子章节（有子章节不算空）
            children = section.get('children', [])
            if not children:
                issues.append({
                    'type': '空章节',
                    'doc': doc_name,
                    'detail': f'章节"{section["title"][:50]}"下没有任何内容',
                    'context': '',
                    'suggestion': '补充该章节内容，或将其删除'
                })

    return issues


def check_table_completeness(tables, doc_name):
    """检查表格完整性"""
    issues = []

    for table in tables:
        # 检查是否有表头
        if not table.get('has_header', True):
            issues.append({
                'type': '表格缺少表头',
                'doc': doc_name,
                'detail': f'第{table["index"]+1}个表格缺少表头行',
                'context': '',
                'suggestion': '为表格添加表头行以说明各列含义'
            })

        # 检查空行
        empty_rows = table.get('empty_rows', 0)
        if empty_rows > 0:
            issues.append({
                'type': '表格含空行',
                'doc': doc_name,
                'detail': f'第{table["index"]+1}个表格包含{empty_rows}个空行',
                'context': '',
                'suggestion': '删除表格中的空行或补充数据'
            })

    return issues


# ============================================================
# D. 低级错误检查
# ============================================================

def check_basic_errors(response, technical):
    """检查低级错误"""
    errors = []

    all_docs = [('应答文件', response)]
    if technical:
        all_docs.append(('技术文件', technical))

    for doc_name, parsed_doc in all_docs:
        if not parsed_doc:
            continue

        full_text = parsed_doc.get('full_text', '')

        # D1. 中英文标点混用
        errors.extend(check_mixed_punctuation(full_text, doc_name))

        # D2. 日期格式不一致
        errors.extend(check_date_format_consistency(parsed_doc, doc_name))

        # D3. 金额表述不一致
        errors.extend(check_amount_consistency(parsed_doc, doc_name))

        # D4. 公司名称不一致
        errors.extend(check_company_name_consistency(parsed_doc, doc_name))

    return errors


def check_mixed_punctuation(text, doc_name):
    """检查中英文标点混用"""
    issues = []

    # 统计中文段落中英文标点出现次数
    # 中文段落特征：包含连续中文字符
    cn_para_pattern = re.compile(r'[\u4e00-\u9fa5]{5,}')

    # 在中文段落中查找英文逗号（后面不跟数字的情况，排除金额等）
    en_comma_in_cn = re.findall(r'[\u4e00-\u9fa5],[\u4e00-\u9fa5]', text)
    # 在中文段落中查找英文句号
    en_period_in_cn = re.findall(r'[\u4e00-\u9fa5]\.[\u4e00-\u9fa5]', text)
    # 在中文段落中查找英文分号
    en_semi_in_cn = re.findall(r'[\u4e00-\u9fa5];[\u4e00-\u9fa5]', text)
    # 在中文段落中查找英文括号
    en_paren_in_cn = re.findall(r'[\u4e00-\u9fa5]\([\u4e00-\u9fa5]', text)

    total_mixed = len(en_comma_in_cn) + len(en_period_in_cn) + len(en_semi_in_cn) + len(en_paren_in_cn)

    if total_mixed > 3:  # 超过3处才报警
        details = []
        if en_comma_in_cn:
            details.append(f'英文逗号{len(en_comma_in_cn)}处')
        if en_period_in_cn:
            details.append(f'英文句号{len(en_period_in_cn)}处')
        if en_semi_in_cn:
            details.append(f'英文分号{len(en_semi_in_cn)}处')
        if en_paren_in_cn:
            details.append(f'英文括号{len(en_paren_in_cn)}处')

        issues.append({
            'type': '中英文标点混用',
            'doc': doc_name,
            'detail': f'发现{total_mixed}处中英文标点混用：{", ".join(details)}',
            'suggestion': '统一使用中文标点符号（，。；（））'
        })

    return issues


def check_date_format_consistency(parsed_doc, doc_name):
    """检查日期格式一致性"""
    issues = []
    date_formats = parsed_doc.get('key_info', {}).get('date_formats', [])

    if len(date_formats) >= 2:
        issues.append({
            'type': '日期格式不一致',
            'doc': doc_name,
            'detail': f'文档中使用了{len(date_formats)}种日期格式：{", ".join(date_formats)}',
            'suggestion': '统一日期格式，建议全部使用"YYYY年MM月DD日"或"YYYY-MM-DD"'
        })

    return issues


def check_amount_consistency(parsed_doc, doc_name):
    """检查金额表述一致性"""
    issues = []
    amount_units = parsed_doc.get('key_info', {}).get('amount_units', [])

    if len(amount_units) >= 2 and '万元' in amount_units and '元' in amount_units:
        issues.append({
            'type': '金额单位混用',
            'doc': doc_name,
            'detail': f'文档中同时使用了"万元"和"元"两种金额单位，可能造成混淆',
            'suggestion': '统一金额单位，或在首次出现时注明换算关系'
        })

    return issues


def check_company_name_consistency(parsed_doc, doc_name):
    """检查公司名称是否在同一文档中出现不同写法"""
    issues = []
    company_names = parsed_doc.get('key_info', {}).get('company_names', [])

    if len(company_names) >= 2:
        # 检查是否有不同写法（简单判断：去掉常见前缀后是否相同）
        unique_names = set()
        for name in company_names:
            # 去掉括号内容
            clean = re.sub(r'[（(][^）)]*[）)]', '', name).strip()
            unique_names.add(clean)

        if len(unique_names) >= 2:
            issues.append({
                'type': '公司名称写法不一致',
                'doc': doc_name,
                'detail': f'文档中出现{len(unique_names)}种公司名称写法：{", ".join(list(unique_names)[:5])}',
                'suggestion': '统一公司名称写法，确保全文一致'
            })

    return issues


# ============================================================
# E. 交叉一致性检查
# ============================================================

def perform_cross_checks(response, technical):
    """交叉一致性检查 - 检查多份文件之间的数据一致性"""
    checks = []

    if not technical:
        return checks

    response_text = response.get('full_text', '')
    tech_text = technical.get('full_text', '')
    combined = response_text + '\n' + tech_text

    response_info = response.get('key_info', {})
    tech_info = technical.get('key_info', {})

    # 1. 检查公司名称一致性
    resp_company = response_info.get('company_name', '')
    tech_company = tech_info.get('company_name', '')
    if resp_company and tech_company and resp_company != tech_company:
        checks.append({
            'type': '公司名称不一致',
            'detail': f'应答文件中公司名称为"{resp_company}"，技术文件中为"{tech_company}"',
            'severity': 'critical',
            'suggestion': '统一两份文件中的公司名称'
        })

    # 2. 检查项目负责人一致性
    resp_pm = response_info.get('project_manager', {}).get('name', '')
    tech_pm = tech_info.get('project_manager', {}).get('name', '')
    if resp_pm and tech_pm and resp_pm != tech_pm:
        checks.append({
            'type': '项目负责人不一致',
            'detail': f'应答文件中项目负责人为"{resp_pm}"，技术文件中为"{tech_pm}"',
            'severity': 'warning',
            'suggestion': '确认并统一项目负责人信息'
        })

    # 3. 检查业绩数量一致性
    resp_perf_count = len(response_info.get('performance_items', []))
    tech_perf_count = len(tech_info.get('performance_items', []))
    if resp_perf_count > 0 and tech_perf_count > 0 and resp_perf_count != tech_perf_count:
        checks.append({
            'type': '业绩数量不一致',
            'detail': f'应答文件中列出{resp_perf_count}项业绩，技术文件中列出{tech_perf_count}项',
            'severity': 'warning',
            'suggestion': '统一两份文件中的业绩清单'
        })

    # 4. 检查是否有"详见技术文件"等推诿性应答
    dodge_patterns = ['详见技术', '见技术文件', '详见商务', '见商务文件']
    for pattern in dodge_patterns:
        if pattern in response_text:
            checks.append({
                'type': '应答不够具体',
                'detail': f'应答文件中存在"{pattern}"等推诿性表述，建议直接给出具体内容',
                'severity': 'warning',
                'suggestion': '将推诿性表述替换为具体的应答内容'
            })
            break

    # 5. 检查日期逻辑
    date_pattern = r'(\d{4})[年\.\-/](\d{1,2})[月\.\-/](\d{1,2})[日号]?'
    all_dates = re.findall(date_pattern, combined)
    for y, m, d in all_dates:
        try:
            dt = datetime(int(y), int(m), int(d))
            if dt.year < 2010 or dt.year > 2030:
                checks.append({
                    'type': '日期异常',
                    'detail': f'发现异常日期: {y}年{m}月{d}日，请确认是否正确',
                    'severity': 'warning',
                    'suggestion': '核实该日期是否准确'
                })
        except ValueError:
            pass

    return checks


# ============================================================
# F. 评分要素逐项分析
# ============================================================

def analyze_single_criteria(criteria_item, response, technical, key_info):
    """分析单个评分要素的满足情况"""
    name = criteria_item['name']
    description = criteria_item.get('description', '')
    max_score = criteria_item['max_score']
    min_score = criteria_item.get('min_score', 0)

    analysis = {
        'name': name,
        'max_score': max_score,
        'min_score': min_score,
        'description': description,
        'status': 'unknown',
        'score_range': [min_score, max_score],
        'issues': [],
        'findings': [],
        'confidence': 'medium'
    }

    # 合并响应文件和技术文件的全文
    combined_text = response.get('full_text', '')
    if technical:
        combined_text += '\n' + technical.get('full_text', '')

    name_lower = name.lower()

    # 技术规范响应
    if '规范' in name_lower or '响应' in name_lower or '偏离' in name_lower:
        analysis['status'] = check_technical_response(response, technical, description)

    # 服务方案
    elif '方案' in name_lower or '规划' in name_lower:
        analysis['status'] = check_service_plan(response, technical, description)

    # 业绩
    elif '业绩' in name_lower:
        analysis['status'] = check_performance_criteria(key_info, description)

    # 人员
    elif '人员' in name_lower or '团队' in name_lower or '素质' in name_lower:
        analysis['status'] = check_personnel_criteria(key_info, description)

    # 质量保证
    elif '质量' in name_lower or '认证' in name_lower or '体系' in name_lower:
        analysis['status'] = check_quality_criteria(response, technical, description)

    # 绩效评价
    elif '绩效' in name_lower or '评价' in name_lower:
        analysis['status'] = 'unknown'
        analysis['issues'].append('绩效评价取决于甲方对历史服务的评价，无法从标书内容自动判断')
        analysis['confidence'] = 'low'

    else:
        # 通用检查：根据描述中的关键词在文档中搜索
        analysis['status'] = generic_criteria_check(combined_text, description, name)

    return analysis


def generic_criteria_check(combined_text, description, name):
    """通用评分要素检查 - 通过关键词匹配判断"""
    if not description:
        return 'unknown'

    # 提取描述中的关键词
    desc_keywords = set()
    # 中文2字及以上词组
    words = re.findall(r'[\u4e00-\u9fa5]{2,6}', description)
    desc_keywords.update(words)

    if not desc_keywords:
        return 'unknown'

    # 统计匹配数
    match_count = sum(1 for kw in desc_keywords if kw in combined_text)
    match_ratio = match_count / len(desc_keywords) if desc_keywords else 0

    if match_ratio >= 0.3:
        return 'pass'
    elif match_ratio >= 0.1:
        return 'risk'
    else:
        return 'fail'


def check_technical_response(response, technical, description):
    """检查技术规范响应情况"""
    if technical:
        tech_text = technical.get('full_text', '')
        if len(tech_text) > 500:
            return 'pass'
        return 'risk'
    return 'unknown'


def check_service_plan(response, technical, description):
    """检查服务方案"""
    combined = ''
    if technical:
        combined += technical.get('full_text', '')
    combined += response.get('full_text', '')

    plan_keywords = ['工作流程', '工作方案', '实施计划', '进度安排', '里程碑',
                     '工作基础', '架构', '技术路线']
    found_keywords = [kw for kw in plan_keywords if kw in combined]

    if len(found_keywords) >= 4:
        return 'pass'
    elif len(found_keywords) >= 2:
        return 'risk'
    else:
        return 'fail'


def check_performance_criteria(key_info, description):
    """检查业绩是否满足评分要求"""
    performance_items = key_info.get('performance_items', [])

    if not performance_items:
        return 'fail'

    # 检查是否有重复项
    names = [item['name'] for item in performance_items]
    duplicates = [name for name, count in Counter(names).items() if count > 1]
    if duplicates:
        return 'risk'

    if len(performance_items) >= 5:
        return 'pass'
    elif len(performance_items) >= 3:
        return 'risk'
    else:
        return 'fail'


def check_personnel_criteria(key_info, description):
    """检查人员资质"""
    pm = key_info.get('project_manager', {})
    tl = key_info.get('technical_lead', {})

    issues = []

    if pm:
        edu = pm.get('education', '')
        exp = pm.get('experience_years', 0)
        title = pm.get('title', '')

        if not title:
            issues.append('项目负责人未明确标注职称')
        elif '副高' not in title and '高级' not in title:
            issues.append(f'项目负责人职称为"{title}"，需确认是否满足副高及以上要求')

        if edu and '本科' in edu and exp < 5:
            issues.append(f'项目负责人学历为{edu}但工作年限仅{exp}年，需满足5年以上')

    if tl:
        exp = tl.get('experience_years', 0)
        title = tl.get('title', '')
        if not title:
            issues.append('技术负责人未明确标注职称')

    if issues:
        return 'risk'
    return 'pass'


def check_quality_criteria(response, technical, description):
    """检查质量保证"""
    combined = ''
    if technical:
        combined += technical.get('full_text', '')
    combined += response.get('full_text', '')

    cert_keywords = ['ISO', 'iso', '质量管理', '体系认证', 'CMMI', 'ITSS',
                     '质量保证体系', '质量认证', '9001']
    found_certs = [kw for kw in cert_keywords if kw in combined]

    if found_certs:
        return 'pass'
    else:
        return 'risk'


# ============================================================
# 专项检查
# ============================================================

def check_performance(key_info):
    """业绩专项检查"""
    result = {'critical': [], 'warnings': []}
    items = key_info.get('performance_items', [])

    if not items:
        result['warnings'].append({
            'type': '业绩缺失',
            'detail': '未能在表格中识别到业绩列表',
            'suggestion': '请手动确认业绩章节是否包含完整的业绩清单表格'
        })
        return result

    # 检查重复项
    name_count = Counter([item['name'] for item in items])
    duplicates = {name: count for name, count in name_count.items() if count > 1}
    for name, count in duplicates.items():
        result['critical'].append({
            'type': '业绩重复',
            'detail': f'项目"{name}"出现{count}次，疑似重复列入',
            'suggestion': '删除重复条目，或将不同合同拆分为独立条目并标注差异'
        })

    # 检查金额为空
    for item in items:
        if not item.get('amount'):
            result['warnings'].append({
                'type': '业绩信息不完整',
                'detail': f'项目"{item["name"]}"缺少合同金额信息',
                'suggestion': '补充合同金额，评分标准可能按金额分级计分'
            })

    # 检查时间格式
    for item in items:
        period = item.get('period', '')
        if period:
            time_check = validate_time_period(period)
            if time_check:
                result['critical'].append({
                    'type': '时间逻辑错误',
                    'detail': f'项目"{item["name"]}"的时间"{period}"存在错误：{time_check}',
                    'suggestion': '修正时间段，确保结束时间晚于开始时间'
                })

    return result


def check_personnel(key_info, criteria_items):
    """人员资质专项分析"""
    result = {'critical': [], 'warnings': []}
    pm = key_info.get('project_manager', {})

    if not pm:
        result['warnings'].append({
            'type': '项目负责人信息缺失',
            'detail': '未能自动提取项目负责人信息',
            'suggestion': '请确认标书中是否明确列出项目负责人及其资质'
        })
        return result

    title = pm.get('title', '')
    if not title:
        result['warnings'].append({
            'type': '职称信息缺失',
            'detail': f'项目负责人{pm.get("name", "")}未标注职称',
            'suggestion': '补充职称信息。评分要求副高及以上职称，或满足学历+年限组合条件'
        })

    edu = pm.get('education', '')
    exp = pm.get('experience_years', 0)

    if edu and exp:
        meets = False
        if '副高' in title or '高级' in title:
            meets = True
        elif '博士' in edu and exp >= 2:
            meets = True
        elif '硕士' in edu and exp >= 3:
            meets = True
        elif '本科' in edu and exp >= 5:
            meets = True

        if not meets:
            result['warnings'].append({
                'type': '人员资质可能不达标',
                'detail': f'项目负责人{pm.get("name", "")}：{edu}学历，{exp}年经验，职称"{title}"',
                'suggestion': '需确认是否满足以下任一条件：副高职称；本科+5年；硕士+3年；博士+2年'
            })

    return result


def check_time_logic(parsed_doc):
    """时间逻辑检查"""
    result = {'critical': [], 'warnings': []}
    full_text = parsed_doc.get('full_text', '')

    period_patterns = [
        r'(\d{4}[\.\-年/]\d{1,2}[\.\-月])\s*[-~至到]\s*(\d{4}[\.\-年/]\d{1,2}[\.\-月/日号]?)',
    ]

    for pattern in period_patterns:
        matches = re.finditer(pattern, full_text)
        for match in matches:
            start_str = match.group(1)
            end_str = match.group(2)

            try:
                start_date = parse_date_flexible(start_str)
                end_date = parse_date_flexible(end_str)

                if start_date and end_date and end_date < start_date:
                    context = full_text[max(0, match.start()-30):match.end()+30]
                    result['critical'].append({
                        'type': '时间逻辑错误',
                        'detail': f'"{start_str} - {end_str}" 结束时间早于开始时间（上下文：{context.strip()}）',
                        'suggestion': '修正时间段，确保结束日期晚于开始日期'
                    })
            except Exception:
                pass

    return result


def check_certifications(response, technical=None, criteria_items=None):
    """认证资质检查"""
    result = {'critical': [], 'warnings': []}
    combined = response.get('full_text', '')
    if technical:
        combined += '\n' + technical.get('full_text', '')

    cert_patterns = {
        'ISO 9001': r'ISO\s*9001',
        'ISO 27001': r'ISO\s*27001',
        'ISO 20000': r'ISO\s*20000',
        'CMMI': r'CMMI',
        'ITSS': r'ITSS',
    }

    found_certs = []
    for cert_name, pattern in cert_patterns.items():
        if re.search(pattern, combined, re.IGNORECASE):
            found_certs.append(cert_name)

    if not found_certs:
        result['warnings'].append({
            'type': '认证信息不明确',
            'detail': '未在标书中发现明确的体系认证信息（如ISO 9001、CMMI等）',
            'suggestion': '如公司拥有相关认证，建议在质量保证章节明确列出并附证书编号'
        })

    return result


# ============================================================
# 辅助函数
# ============================================================

def validate_time_period(period_str):
    """验证时间段逻辑"""
    parts = re.split(r'[-~至到]', period_str)
    if len(parts) != 2:
        return None

    start = parse_date_flexible(parts[0].strip())
    end = parse_date_flexible(parts[1].strip())

    if start and end and end < start:
        return f'结束时间({parts[1].strip()})早于开始时间({parts[0].strip()})'
    return None


def parse_date_flexible(date_str):
    """灵活解析日期字符串"""
    date_str = date_str.strip()
    formats = [
        (r'(\d{4})[年\.\-/](\d{1,2})[月\.\-/](\d{1,2})', '%Y-%m-%d'),
        (r'(\d{4})[年\.\-/](\d{1,2})', '%Y-%m'),
    ]

    for pattern, fmt in formats:
        match = re.match(pattern, date_str)
        if match:
            try:
                parts = match.groups()
                if len(parts) == 3:
                    return datetime(int(parts[0]), int(parts[1]), int(parts[2]))
                elif len(parts) == 2:
                    return datetime(int(parts[0]), int(parts[1]), 1)
            except ValueError:
                pass
    return None


def estimate_score(criteria_items, analyses):
    """估算得分区间"""
    if not criteria_items:
        return {'min': 0, 'max': 0, 'total_max': 0, 'details': []}

    total_min = 0
    total_max = 0
    details = []

    for criteria, analysis in zip(criteria_items, analyses):
        max_score = criteria['max_score']
        min_score = criteria.get('min_score', 0)
        name = criteria['name']
        status = analysis.get('status', 'unknown')

        if status == 'pass':
            est_min = max_score * 0.85
            est_max = max_score
        elif status == 'risk':
            est_min = max_score * 0.5
            est_max = max_score * 0.85
        elif status == 'fail':
            est_min = min_score
            est_max = max_score * 0.5
        else:
            est_min = min_score
            est_max = max_score

        total_min += est_min
        total_max += est_max
        details.append({
            'name': name,
            'max_score': max_score,
            'estimated_min': round(est_min, 1),
            'estimated_max': round(est_max, 1),
            'status': status
        })

    return {
        'min': round(total_min, 1),
        'max': round(total_max, 1),
        'total_max': sum(c['max_score'] for c in criteria_items),
        'details': details
    }
