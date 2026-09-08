#!/usr/bin/env python3
"""文档解析模块 - 增强版，支持通用标书检测"""

import re
import os
from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from openpyxl import load_workbook
from datetime import datetime


# ============================================================
# XLSX 解析（评分标准）
# ============================================================

def parse_xlsx(filepath):
    """解析评分标准 xlsx 文件"""
    wb = load_workbook(filepath, data_only=True)
    result = {
        'sheets': [],
        'criteria_items': [],  # 评审要素列表
        'raw_data': {}
    }

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        sheet_data = []
        for row in ws.iter_rows(values_only=True):
            row_data = [str(cell) if cell is not None else '' for cell in row]
            sheet_data.append(row_data)

        result['sheets'].append({
            'name': sheet_name,
            'rows': sheet_data
        })
        result['raw_data'][sheet_name] = sheet_data

        # 尝试识别评分标准表格
        criteria = extract_criteria_from_sheet(sheet_data, sheet_name)
        result['criteria_items'].extend(criteria)

    return result


def extract_criteria_from_sheet(sheet_data, sheet_name):
    """从工作表中提取评分标准条目"""
    criteria = []

    # 寻找包含"评审要素"、"评分标准"等关键词的行作为表头
    header_row = -1
    col_map = {}

    for i, row in enumerate(sheet_data):
        row_text = '|'.join(row).lower()
        if any(kw in row_text for kw in ['评审要素', '评审因素', '评分标准', '评审内容', '评分内容']):
            header_row = i
            for j, cell in enumerate(row):
                cell_lower = str(cell).strip().lower()
                if '评审要素' in cell_lower or '评审因素' in cell_lower:
                    col_map['factor'] = j
                elif '分值' in cell_lower or '满分' in cell_lower:
                    col_map['max_score'] = j
                elif '评分标准' in cell_lower or '评分内容' in cell_lower or '评审内容' in cell_lower:
                    col_map['criteria'] = j
                elif '最低' in cell_lower or '基本分' in cell_lower:
                    col_map['min_score'] = j
            break

    if header_row < 0:
        return criteria

    # 读取评分条目
    current_criteria = None

    for i in range(header_row + 1, len(sheet_data)):
        row = sheet_data[i]
        if not row or all(str(cell).strip() == '' for cell in row):
            continue

        factor_name = ''
        max_score = 0
        min_score = 0
        criteria_text = ''

        if 'factor' in col_map and col_map['factor'] < len(row):
            factor_name = str(row[col_map['factor']]).strip()
        if 'max_score' in col_map and col_map['max_score'] < len(row):
            try:
                max_score = float(str(row[col_map['max_score']]).strip())
            except (ValueError, TypeError):
                max_score = 0
        if 'min_score' in col_map and col_map['min_score'] < len(row):
            try:
                min_score = float(str(row[col_map['min_score']]).strip())
            except (ValueError, TypeError):
                min_score = 0
        if 'criteria' in col_map and col_map['criteria'] < len(row):
            criteria_text = str(row[col_map['criteria']]).strip()

        # 尝试从评审要素名称中提取分值（如"1.对技术规范书的响应（10-6分）"）
        if factor_name and not max_score:
            score_match = re.search(r'[（(](\d+)[\-~](\d+)分[）)]', factor_name)
            if score_match:
                max_score = float(score_match.group(1))
                min_score = float(score_match.group(2))
                factor_name = re.sub(r'[（(]\d+[\-~]\d+分[）)]', '', factor_name).strip()

        # 如果是新的评审要素
        if factor_name and max_score > 0:
            if current_criteria:
                criteria.append(current_criteria)

            current_criteria = {
                'name': factor_name,
                'max_score': max_score,
                'min_score': min_score,
                'description': criteria_text,
                'source_sheet': sheet_name
            }
        elif current_criteria and criteria_text:
            # 这是当前条目的续行
            current_criteria['description'] += '\n' + criteria_text

    # 保存最后一个条目
    if current_criteria:
        criteria.append(current_criteria)

    return criteria


# ============================================================
# DOCX 解析（通用标书文件）
# ============================================================

def parse_docx(filepath):
    """解析 docx 文件，提取结构化内容（增强版）"""
    doc = Document(filepath)
    result = {
        'paragraphs': [],        # 所有段落
        'tables': [],            # 所有表格（含分类信息）
        'sections': [],          # 识别的章节结构
        'numbering_info': [],    # 编号结构信息
        'images': [],            # 图片信息
        'key_info': {},          # 关键信息提取
        'full_text': '',         # 纯文本
        'file_size': 0,
        'file_path': filepath
    }

    result['file_size'] = os.path.getsize(filepath)

    # 1. 提取段落（含标题级别识别）
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            style_name = para.style.name if para.style else ''
            level = get_heading_level(style_name, text)
            result['paragraphs'].append({
                'text': text,
                'style': style_name,
                'level': level,
                'is_heading': level >= 0
            })

    # 2. 提取表格（增强分类）
    for t_idx, table in enumerate(doc.tables):
        table_data = []
        for row in table.rows:
            row_data = [cell.text.strip() for cell in row.cells]
            table_data.append(row_data)

        # 分类表格
        table_info = {
            'index': t_idx,
            'rows': table_data,
            'row_count': len(table_data),
            'col_count': len(table_data[0]) if table_data else 0,
            'category': classify_table(table_data),
            'has_header': check_table_header(table_data),
            'empty_rows': count_empty_rows(table_data)
        }
        result['tables'].append(table_info)

    # 3. 识别章节结构（增强版）
    result['sections'] = identify_sections_enhanced(result['paragraphs'])

    # 4. 提取编号结构
    result['numbering_info'] = extract_numbering_info(result['paragraphs'])

    # 5. 检测图片
    result['images'] = detect_images(doc)

    # 6. 提取关键信息
    result['key_info'] = extract_key_info(result)

    # 7. 纯文本
    result['full_text'] = '\n'.join(p['text'] for p in result['paragraphs'])

    return result


# ============================================================
# 标题级别识别（增强版）
# ============================================================

def get_heading_level(style_name, text=''):
    """
    从样式名称和文本内容综合判断标题级别
    支持：Word样式标题、数字编号标题、中文编号标题
    返回 -1 表示非标题
    """
    level = -1

    # 方法1: 通过Word样式判断
    if style_name:
        style_lower = style_name.lower()
        if 'heading' in style_lower or '标题' in style_lower:
            match = re.search(r'(\d+)', style_lower)
            if match:
                level = int(match.group(1))
            else:
                level = 0

    # 方法2: 通过文本内容的编号模式判断（辅助识别）
    if level < 0 and text:
        text_stripped = text.strip()

        # "第一章"、"第一节" 等
        if re.match(r'^第[一二三四五六七八九十百\d]+[章节条部分]', text_stripped):
            level = 0

        # "1." "1.1" "1.1.1" 等数字编号
        elif re.match(r'^(\d+)\.\s', text_stripped):
            nums = re.match(r'^(\d+(?:\.\d+)*)', text_stripped)
            if nums:
                parts = nums.group(1).split('.')
                level = len(parts) - 1

        # "一、" "（一）" 等中文编号
        elif re.match(r'^[一二三四五六七八九十]+[、．.]', text_stripped):
            level = 0
        elif re.match(r'^[（(][一二三四五六七八九十]+[）)]', text_stripped):
            level = 1

        # "A." "a)" 等字母编号
        elif re.match(r'^[A-Z][\.、．]\s', text_stripped):
            level = 1
        elif re.match(r'^[a-z][\)）]\s', text_stripped):
            level = 2

    return level


# ============================================================
# 章节结构识别（增强版）
# ============================================================

def identify_sections_enhanced(paragraphs):
    """识别文档的章节结构（增强版，支持多级标题）"""
    sections = []
    current_section = None
    heading_stack = []  # 标题层级栈

    for para in paragraphs:
        level = para['level']
        text = para['text']

        if level >= 0:  # 是标题
            # 关闭之前的同级或更低级标题
            while heading_stack and heading_stack[-1]['level'] >= level:
                heading_stack.pop()

            if current_section:
                sections.append(current_section)

            current_section = {
                'title': text,
                'level': level,
                'content': [],
                'subsections': [],
                'has_content': False,
                'content_length': 0
            }
            heading_stack.append({'title': text, 'level': level})
        elif current_section:
            current_section['content'].append(text)
            current_section['has_content'] = True
            current_section['content_length'] += len(text)

    if current_section:
        sections.append(current_section)

    # 建立父子关系
    build_section_hierarchy(sections)

    return sections


def build_section_hierarchy(sections):
    """建立章节的层级关系"""
    for i, section in enumerate(sections):
        section['parent'] = None
        section['children'] = []

        # 向前查找父节点
        for j in range(i - 1, -1, -1):
            if sections[j]['level'] < section['level']:
                section['parent'] = j
                sections[j]['children'].append(i)
                break


# ============================================================
# 编号结构提取
# ============================================================

def extract_numbering_info(paragraphs):
    """提取文档中的编号结构，用于检测编号连续性"""
    numbering_patterns = []

    for para in paragraphs:
        if not para.get('is_heading'):
            continue

        text = para['text'].strip()

        # 提取数字编号（如 1.1, 1.2.3 等）
        num_match = re.match(r'^(\d+(?:\.\d+)*)[\.\s、．]', text)
        if num_match:
            numbering_patterns.append({
                'number': num_match.group(1),
                'text': text,
                'level': para['level'],
                'parts': [int(x) for x in num_match.group(1).split('.')]
            })

        # 提取中文编号
        cn_match = re.match(r'^第([一二三四五六七八九十百\d]+)[章节条部分]', text)
        if cn_match:
            numbering_patterns.append({
                'number': cn_match.group(1),
                'text': text,
                'level': para['level'],
                'parts': [],
                'type': 'chinese'
            })

    return numbering_patterns


# ============================================================
# 图片检测
# ============================================================

def detect_images(doc):
    """检测文档中是否包含图片"""
    images = []
    try:
        # 通过 relationships 检测图片
        for rel in doc.part.rels.values():
            if "image" in rel.reltype:
                images.append({
                    'rel_id': rel.rId,
                    'target': rel.target_ref if hasattr(rel, 'target_ref') else str(rel.target_partname)
                })
    except Exception:
        pass

    # 也统计内联图片数量（通过XML）
    inline_count = 0
    try:
        from docx.oxml.ns import qn
        for para in doc.paragraphs:
            for run in para.runs:
                if run._element.findall(qn('w:drawing')):
                    inline_count += 1
    except Exception:
        pass

    return {
        'count': max(len(images), inline_count),
        'rels': images,
        'has_images': len(images) > 0 or inline_count > 0
    }


# ============================================================
# 表格分类
# ============================================================

def classify_table(table_data):
    """
    根据表头和内容对表格进行分类
    返回: 'performance'(业绩表), 'personnel'(人员表), 'equipment'(设备表),
          'pricing'(报价表), 'deviation'(偏差表), 'other'(其他)
    """
    if not table_data or len(table_data) < 1:
        return 'other'

    header = '|'.join(str(c) for c in table_data[0]).lower()

    # 业绩表
    if any(kw in header for kw in ['项目名称', '工程名', '合同名', '业绩']):
        if any(kw in header for kw in ['金额', '合同额', '甲方', '时间']):
            return 'performance'

    # 人员表
    if any(kw in header for kw in ['姓名', '职称', '学历', '岗位', '职务']):
        if any(kw in header for kw in ['年龄', '经验', '年限', '专业']):
            return 'personnel'
        return 'personnel'

    # 设备表
    if any(kw in header for kw in ['设备名', '型号', '规格', '数量', '台套']):
        return 'equipment'

    # 报价表
    if any(kw in header for kw in ['单价', '合价', '总价', '报价', '费用明细']):
        return 'pricing'

    # 偏差表
    if any(kw in header for kw in ['偏差', '偏离', '响应', '应答']):
        return 'deviation'

    # 进度表
    if any(kw in header for kw in ['里程碑', '进度', '阶段', '工期', '起止时间']):
        return 'schedule'

    return 'other'


def check_table_header(table_data):
    """检查表格是否有表头"""
    if not table_data or len(table_data) < 1:
        return False
    # 检查第一行是否全部为空
    first_row = table_data[0]
    return any(str(cell).strip() for cell in first_row)


def count_empty_rows(table_data):
    """统计表格中的空行数"""
    if not table_data:
        return 0
    empty = 0
    for row in table_data[1:]:  # 跳过表头
        if not row or all(str(cell).strip() == '' for cell in row):
            empty += 1
    return empty


# ============================================================
# 关键信息提取
# ============================================================

def extract_key_info(parsed):
    """从解析结果中提取关键信息"""
    info = {
        'company_name': '',
        'company_names': [],       # 文档中出现的所有公司名称写法
        'project_name': '',
        'project_manager': {},
        'technical_lead': {},
        'team_members': [],
        'performance_items': [],   # 业绩列表
        'certifications': [],      # 资质认证
        'service_commitments': [], # 服务承诺
        'dates': [],               # 提取的日期
        'date_formats': [],        # 使用的日期格式
        'amounts': [],             # 提取的金额
        'amount_units': [],        # 金额单位（万元/元）
        'contact_info': [],        # 联系方式
    }

    full_text = parsed.get('full_text', '')

    # 提取公司名称（所有出现形式）
    info['company_names'] = extract_company_names(full_text)
    if info['company_names']:
        info['company_name'] = info['company_names'][0]

    # 提取项目名称
    project_patterns = [
        r'项目名称[：:]\s*(.+?)(?:\n|$)',
        r'工程名称[：:]\s*(.+?)(?:\n|$)',
    ]
    for pattern in project_patterns:
        match = re.search(pattern, full_text)
        if match:
            info['project_name'] = match.group(1).strip()
            break

    # 提取项目负责人
    info['project_manager'] = extract_person_info(full_text, ['项目负责人', '项目经理', '项目总监'])
    info['technical_lead'] = extract_person_info(full_text, ['技术负责人', '技术总监'])

    # 提取团队成员
    tables_data = [t.get('rows', []) for t in parsed.get('tables', [])]
    info['team_members'] = extract_team_members(parsed.get('tables', []))

    # 提取业绩列表
    info['performance_items'] = extract_performance_items(parsed.get('tables', []))

    # 提取日期及格式
    info['dates'], info['date_formats'] = extract_dates_and_formats(full_text)

    # 提取金额及单位
    info['amounts'], info['amount_units'] = extract_amounts_and_units(full_text)

    # 提取联系方式
    info['contact_info'] = extract_contact_info(full_text)

    # 提取认证信息
    info['certifications'] = extract_certifications(full_text)

    return info


def extract_company_names(text):
    """提取文档中所有公司名称写法"""
    companies = []
    patterns = [
        r'投标人[：:]\s*(\S+(?:公司|集团|企业|有限))',
        r'投标人名称[：:]\s*(\S+(?:公司|集团|企业|有限))',
        r'(\S+(?:公司|集团|企业)[^\s,，。；;、]{0,20}(?:有限|股份|责任))',
        r'([\u4e00-\u9fa5]{2,15}(?:有限公司|股份有限公司|集团有限公司))',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for m in matches:
            m = m.strip()
            if len(m) >= 4 and m not in companies:
                companies.append(m)
    return companies


def extract_person_info(text, keywords):
    """提取人员信息"""
    person = {}
    for kw in keywords:
        # 查找该人员相关信息块
        pattern = rf'{kw}[：:]\s*(\S+)'
        match = re.search(pattern, text)
        if match:
            person['name'] = match.group(1).strip()

        # 提取性别
        gender_pattern = rf'{person.get("name", "")}.*?(?:性别[：:]?\s*([男女]))'
        gender_match = re.search(gender_pattern, text)
        if gender_match:
            person['gender'] = gender_match.group(1)

        # 提取年龄
        age_pattern = rf'{person.get("name", "")}.*?(?:年龄[：:]?\s*(\d+))'
        age_match = re.search(age_pattern, text)
        if age_match:
            person['age'] = int(age_match.group(1))

        # 提取学历
        edu_pattern = rf'{person.get("name", "")}.*?(?:学历[：:]?\s*([^\s,，、]+))'
        edu_match = re.search(edu_pattern, text)
        if edu_match:
            person['education'] = edu_match.group(1)

        # 提取工作年限
        exp_pattern = rf'{person.get("name", "")}.*?(?:工作年限?[：:]?\s*(\d+))'
        exp_match = re.search(exp_pattern, text)
        if exp_match:
            person['experience_years'] = int(exp_match.group(1))

        # 提取职称
        title_pattern = rf'{person.get("name", "")}.*?(?:职称[：:]?\s*([^\s,，、]+))'
        title_match = re.search(title_pattern, text)
        if title_match:
            person['title'] = title_match.group(1)

    return person


def extract_team_members(tables):
    """从表格中提取团队成员信息"""
    members = []
    for table in tables:
        rows = table.get('rows', [])
        if not rows:
            continue

        # 检查表头是否包含人员相关信息
        header = '|'.join(rows[0]).lower() if rows else ''
        if not any(kw in header for kw in ['姓名', '角色', '岗位', '职务', '职称', '学历', '经验']):
            continue

        # 识别列
        col_names = rows[0] if rows else []
        name_col = -1
        for j, col in enumerate(col_names):
            if '姓名' in str(col):
                name_col = j
                break

        if name_col < 0:
            continue

        for row in rows[1:]:
            if len(row) > name_col and row[name_col].strip():
                member = {'name': row[name_col].strip()}
                for j, col in enumerate(col_names):
                    if j < len(row):
                        col_lower = str(col).lower()
                        if '学历' in col_lower:
                            member['education'] = row[j].strip()
                        elif '职称' in col_lower:
                            member['title'] = row[j].strip()
                        elif '年限' in col_lower or '经验' in col_lower:
                            member['experience'] = row[j].strip()
                        elif '角色' in col_lower or '岗位' in col_lower:
                            member['role'] = row[j].strip()
                members.append(member)

    return members


def extract_performance_items(tables):
    """从表格中提取业绩列表"""
    items = []
    for t_idx, table in enumerate(tables):
        rows = table.get('rows', [])
        if not rows or len(rows) < 2:
            continue

        header = '|'.join(str(c) for c in rows[0]).lower()

        # 识别业绩表格的特征列
        has_name = any(kw in header for kw in ['项目名', '工程名', '合同名', '项目名称', '工程'])
        has_amount = any(kw in header for kw in ['金额', '合同额', '费用', '总价', '合同价'])
        has_date = any(kw in header for kw in ['时间', '期间', '起止', '合同期', '签订'])

        if not (has_name and (has_amount or has_date)):
            continue

        # 识别列索引
        col_names = [str(c).strip() for c in rows[0]]
        col_indices = {}

        for j, col in enumerate(col_names):
            col_lower = col.lower()
            if any(kw in col_lower for kw in ['项目名', '工程名', '合同名', '项目名称']):
                col_indices['name'] = j
            if any(kw in col_lower for kw in ['金额', '合同额', '费用']):
                col_indices['amount'] = j
            if any(kw in col_lower for kw in ['时间', '期间', '起止']):
                col_indices['period'] = j
            if any(kw in col_lower for kw in ['甲方', '业主', '发包方']):
                col_indices['client'] = j
            if any(kw in col_lower for kw in ['联系人', '联系方式']):
                col_indices['contact'] = j

        if 'name' not in col_indices:
            continue

        for r_idx, row in enumerate(rows[1:], 1):
            if len(row) <= col_indices['name']:
                continue
            name = row[col_indices['name']].strip()
            if not name:
                continue

            item = {
                'table_index': t_idx,
                'row_index': r_idx,
                'name': name,
            }
            if 'amount' in col_indices and col_indices['amount'] < len(row):
                item['amount'] = row[col_indices['amount']].strip()
            if 'period' in col_indices and col_indices['period'] < len(row):
                item['period'] = row[col_indices['period']].strip()
            if 'client' in col_indices and col_indices['client'] < len(row):
                item['client'] = row[col_indices['client']].strip()
            if 'contact' in col_indices and col_indices['contact'] < len(row):
                item['contact'] = row[col_indices['contact']].strip()

            items.append(item)

    return items


def extract_dates_and_formats(text):
    """提取日期及日期格式"""
    dates = []
    formats = set()

    # 各种日期格式
    # "2024年1月15日"
    if re.search(r'\d{4}年\d{1,2}月\d{1,2}日', text):
        formats.add('YYYY年MM月DD日')
    # "2024.01.15"
    if re.search(r'\d{4}\.\d{1,2}\.\d{1,2}', text):
        formats.add('YYYY.MM.DD')
    # "2024-01-15"
    if re.search(r'\d{4}-\d{2}-\d{2}', text):
        formats.add('YYYY-MM-DD')
    # "2024/01/15"
    if re.search(r'\d{4}/\d{2}/\d{2}', text):
        formats.add('YYYY/MM/DD')
    # "2024年1月" (无日)
    if re.search(r'\d{4}年\d{1,2}月(?!\d)', text):
        formats.add('YYYY年MM月')
    # "2024.01" (无日)
    if re.search(r'\d{4}\.\d{1,2}(?!\.\d)', text):
        formats.add('YYYY.MM')

    # 提取所有日期字符串
    date_pattern = r'(\d{4}[\.年/-]\d{1,2}[\.月/-]\d{0,2}[日号]?)'
    dates = re.findall(date_pattern, text)

    return dates, list(formats)


def extract_amounts_and_units(text):
    """提取金额及单位"""
    amounts = []
    units = set()

    # 提取金额
    amount_pattern = r'([\d,.]+)\s*(万元|元|亿)'
    matches = re.findall(amount_pattern, text)
    for amount, unit in matches:
        amounts.append(f'{amount}{unit}')
        units.add(unit)

    return amounts, list(units)


def extract_contact_info(text):
    """提取联系方式"""
    contacts = []

    # 电话
    phones = re.findall(r'(?:电话|联系电话|手机|Tel|TEL)[：:]\s*([\d\-\s]+)', text)
    for p in phones:
        contacts.append({'type': 'phone', 'value': p.strip()})

    # 邮箱
    emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
    for e in emails:
        contacts.append({'type': 'email', 'value': e.strip()})

    # 地址
    addresses = re.findall(r'(?:地址|联系地址|通讯地址)[：:]\s*(.+?)(?:\n|$)', text)
    for a in addresses:
        contacts.append({'type': 'address', 'value': a.strip()})

    return contacts


def extract_certifications(text):
    """提取认证资质信息"""
    certs = []
    cert_patterns = {
        'ISO 9001': r'ISO\s*9001',
        'ISO 27001': r'ISO\s*27001',
        'ISO 20000': r'ISO\s*20000',
        'CMMI': r'CMMI',
        'ITSS': r'ITSS',
        '信息系统集成': r'信息系统集成[资质]',
    }
    for name, pattern in cert_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            certs.append(name)
    return certs
