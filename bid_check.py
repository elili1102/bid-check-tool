#!/usr/bin/env python3
"""标书技术评分检查工具 - 命令行入口"""

import argparse
import json
import os
import platform
import sys
import time
import traceback
from pathlib import Path

# ── 终端颜色 ──────────────────────────────────────────────
IS_WINDOWS = platform.system() == 'Windows'

def _supports_color():
    """检测终端是否支持彩色输出"""
    if IS_WINDOWS:
        # Windows 10+ 支持 ANSI，尝试启用虚拟终端
        try:
            os.system('')  # 触发 Windows 启用 ANSI
            return True
        except Exception:
            return False
    return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

USE_COLOR = _supports_color()

class C:
    """ANSI 颜色常量"""
    RESET   = '\033[0m' if USE_COLOR else ''
    BOLD    = '\033[1m' if USE_COLOR else ''
    DIM     = '\033[2m' if USE_COLOR else ''
    RED     = '\033[91m' if USE_COLOR else ''
    GREEN   = '\033[92m' if USE_COLOR else ''
    YELLOW  = '\033[93m' if USE_COLOR else ''
    BLUE    = '\033[94m' if USE_COLOR else ''
    CYAN    = '\033[96m' if USE_COLOR else ''
    WHITE   = '\033[97m' if USE_COLOR else ''

def color(text, code):
    return f'{code}{text}{C.RESET}'

# ── 输出工具 ──────────────────────────────────────────────

def print_banner():
    line = f'{C.CYAN}{"═" * 43}{C.RESET}'
    print()
    print(line)
    print(f'{C.CYAN}{C.BOLD}  📋 标书技术评分检查报告{C.RESET}')
    print(line)

def print_summary(result):
    """打印终端彩色摘要"""
    print_banner()
    summary = result.get('summary', {})
    score = result.get('score_estimate', {})
    critical_issues = result.get('critical_issues', [])
    warnings = result.get('warnings', [])
    suggestions = result.get('suggestions', [])

    total_criteria = summary.get('total_criteria', 0)
    total_critical = summary.get('total_critical', len(critical_issues))
    total_warnings = summary.get('total_warnings', len(warnings))
    total_suggestions = summary.get('total_suggestions', len(suggestions))

    score_min = score.get('min', 0)
    score_max = score.get('max', 0)
    total_max = sum(d.get('max_score', 0) for d in score.get('details', []))
    if total_max == 0:
        total_max = score.get('total_max', 0)

    print()
    print(f'  {C.BLUE}📊{C.RESET} 评分要素：{C.BOLD}{total_criteria}{C.RESET} 项')
    print(f'  {C.RED}🚨{C.RESET} 硬伤问题：{C.BOLD}{C.RED}{total_critical}{C.RESET} 个')
    print(f'  {C.YELLOW}⚠️ {C.RESET} 扣分风险：{C.BOLD}{C.YELLOW}{total_warnings}{C.RESET} 个')
    print(f'  {C.CYAN}📝{C.RESET} 格式问题：{C.BOLD}{total_suggestions}{C.RESET} 个')
    if total_max > 0:
        print(f'  {C.BLUE}🔍{C.RESET} 预估得分：{C.BOLD}{score_min} ~ {score_max}{C.RESET} / {total_max}')

    sep = f'{C.DIM}{"─" * 43}{C.RESET}'

    # 硬伤问题
    if critical_issues:
        print()
        print(sep)
        print(f'  {C.RED}{C.BOLD}硬伤问题：{C.RESET}')
        print()
        for issue in critical_issues:
            tag = issue.get('type', '未知')
            detail = issue.get('detail', '')
            print(f'  {C.RED}❌{C.RESET} {C.BOLD}[{tag}]{C.RESET} {detail}')
    else:
        print()
        print(f'  {C.GREEN}✅ 未发现硬伤问题{C.RESET}')

    # 扣分风险
    if warnings:
        print()
        print(sep)
        print(f'  {C.YELLOW}{C.BOLD}扣分风险：{C.RESET}')
        print()
        show_count = min(len(warnings), 10)
        for w in warnings[:show_count]:
            tag = w.get('type', '未知')
            detail = w.get('detail', '')
            print(f'  {C.YELLOW}⚠️{C.RESET} {C.BOLD}[{tag}]{C.RESET} {detail}')
        if len(warnings) > show_count:
            print(f'  {C.DIM}  ... 还有 {len(warnings) - show_count} 项{C.RESET}')

    # 改进建议
    if suggestions:
        print()
        print(sep)
        print(f'  {C.CYAN}{C.BOLD}改进建议：{C.RESET}')
        print()
        show_count = min(len(suggestions), 5)
        for s in suggestions[:show_count]:
            tip = s.get('detail', s.get('suggestion', str(s)))
            print(f'  💡 {tip}')
        if len(suggestions) > show_count:
            print(f'  {C.DIM}  ... 还有 {len(suggestions) - show_count} 项{C.RESET}')

    print()
    print(sep)
    print()

# ── 安全导入 ──────────────────────────────────────────────

def _safe_import(module_name, func_names):
    """安全导入模块函数，失败时给出友好提示"""
    try:
        mod = __import__(module_name, fromlist=func_names)
        funcs = tuple(getattr(mod, name) for name in func_names)
        return funcs if len(func_names) > 1 else funcs[0]
    except ImportError as e:
        print(f'{C.RED}❌ 导入 {module_name} 失败：{e}{C.RESET}', file=sys.stderr)
        print(f'{C.YELLOW}提示：请确保已安装依赖并检查模块文件是否完整。{C.RESET}', file=sys.stderr)
        print(f'{C.DIM}  安装依赖：pip install python-docx openpyxl{C.RESET}', file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f'{C.RED}❌ 加载 {module_name} 时出错：{e}{C.RESET}', file=sys.stderr)
        if '--verbose' in sys.argv or '-v' in sys.argv:
            traceback.print_exc()
        sys.exit(1)

# ── Web 模式 ──────────────────────────────────────────────

def run_web(port):
    """启动 Web 界面"""
    try:
        from app import main as app_main
    except ImportError:
        print(f'{C.RED}❌ 无法导入 app 模块，请检查 app.py 是否存在。{C.RESET}', file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f'{C.RED}❌ 加载 app 模块时出错：{e}{C.RESET}', file=sys.stderr)
        if '--verbose' in sys.argv or '-v' in sys.argv:
            traceback.print_exc()
        sys.exit(1)

    print()
    print(f'{C.CYAN}{C.BOLD}  🌐 标书技术评分检查工具 - Web 界面{C.RESET}')
    print(f'{C.DIM}{"─" * 43}{C.RESET}')
    print(f'  正在启动服务... 端口 {C.BOLD}{port}{C.RESET}')
    print(f'  请在浏览器打开：{C.GREEN}{C.BOLD}http://localhost:{port}{C.RESET}')
    print(f'{C.DIM}  按 Ctrl+C 停止服务{C.RESET}')
    print()

    try:
        app_main(port=port)
    except KeyboardInterrupt:
        print(f'\n{C.DIM}  服务已停止。{C.RESET}\n')
    except TypeError:
        # 兼容 app.main() 不接受 port 参数的情况
        try:
            app_main()
        except KeyboardInterrupt:
            print(f'\n{C.DIM}  服务已停止。{C.RESET}\n')

# ── CLI 模式 ──────────────────────────────────────────────

def run_cli(args):
    """命令行检查模式"""
    verbose = args.verbose

    # 导入核心模块
    parse_docx, parse_xlsx = _safe_import('parsers', ['parse_docx', 'parse_xlsx'])
    analyze_bid = _safe_import('analyzer', ['analyze_bid'])
    generate_html_report = _safe_import('report_generator', ['generate_html_report'])

    # 校验文件存在
    response_path = Path(args.response)
    if not response_path.exists():
        print(f'{C.RED}❌ 应答文件不存在：{response_path}{C.RESET}', file=sys.stderr)
        sys.exit(1)

    criteria_path = Path(args.criteria) if args.criteria else None
    if criteria_path and not criteria_path.exists():
        print(f'{C.RED}❌ 评分标准文件不存在：{criteria_path}{C.RESET}', file=sys.stderr)
        sys.exit(1)

    technical_path = Path(args.technical) if args.technical else None
    if technical_path and not technical_path.exists():
        print(f'{C.RED}❌ 技术文件不存在：{technical_path}{C.RESET}', file=sys.stderr)
        sys.exit(1)

    # ── 解析文件 ──
    if verbose:
        print(f'\n{C.DIM}📂 正在解析文件...{C.RESET}')
        print(f'  应答文件：{response_path.name}')

    start_time = time.time()

    response_data = parse_docx(str(response_path))

    criteria_data = None
    if criteria_path:
        if verbose:
            print(f'  评分标准：{criteria_path.name}')
        criteria_data = parse_xlsx(str(criteria_path))

    technical_data = None
    if technical_path:
        if verbose:
            print(f'  技术文件：{technical_path.name}')
        technical_data = parse_docx(str(technical_path))

    # 构建文件名映射
    file_names = {'response': response_path.name}
    if criteria_path:
        file_names['criteria'] = criteria_path.name
    if technical_path:
        file_names['technical'] = technical_path.name

    if verbose:
        print(f'  解析完成，耗时 {time.time() - start_time:.1f}s')
        print(f'\n{C.DIM}🔍 正在分析...{C.RESET}')

    # ── 分析 ──
    result = analyze_bid(criteria_data, response_data, technical_data, file_names)

    if verbose:
        print(f'  分析完成，耗时 {time.time() - start_time:.1f}s')

    # ── 输出 ──
    fmt = args.format
    timestamp = int(time.time())
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)

    # JSON 输出
    if fmt in ('json', 'both'):
        json_path = args.output
        if json_path and fmt == 'json':
            json_path = str(Path(json_path).with_suffix('.json'))
        elif json_path and fmt == 'both':
            json_path = str(Path(json_path).with_suffix('.json'))
        else:
            json_path = str(output_dir / f'report_{timestamp}.json')

        # 构建可序列化的结果
        json_result = dict(result)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_result, f, ensure_ascii=False, indent=2, default=str)

        if verbose or fmt == 'json':
            print(f'  📄 JSON 结果已保存：{C.GREEN}{json_path}{C.RESET}')

    # HTML 输出
    if fmt in ('html', 'both'):
        html_path = args.output
        if html_path and fmt == 'both':
            html_path = str(Path(html_path).with_suffix('.html'))
        elif not html_path:
            html_path = str(output_dir / f'report_{timestamp}.html')

        html_content = generate_html_report(result)
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

    # 终端摘要（json 模式不打印摘要）
    if fmt != 'json':
        print_summary(result)

        if fmt in ('html', 'both'):
            html_display = args.output if args.output else str(output_dir / f'report_{timestamp}.html')
            print(f'  {C.GREEN}✅ 报告已生成：{C.BOLD}{html_display}{C.RESET}')
            print()
    else:
        # JSON 模式只输出 JSON 路径
        json_display = json_path if 'json_path' in dir() else '(see above)'
        print(f'  {C.GREEN}✅ JSON 结果已生成：{C.BOLD}{json_display}{C.RESET}')
        print()

# ── 参数解析 ──────────────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(
        prog='bid_check',
        description='📋 标书技术评分检查工具 — 自动解析评分标准与应答文件，输出检查报告',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  %(prog)s --response response.docx
  %(prog)s --criteria scoring.xlsx --response response.docx --technical tech.docx
  %(prog)s --response response.docx --format json --output result.json
  %(prog)s --web --port 5000
        ''',
    )

    parser.add_argument('-c', '--criteria', metavar='FILE',
                        help='评分标准文件（xlsx 格式）')
    parser.add_argument('-r', '--response', metavar='FILE',
                        help='应答文件（docx 格式）')
    parser.add_argument('-t', '--technical', metavar='FILE',
                        help='技术文件（docx 格式，可选）')
    parser.add_argument('-o', '--output', metavar='PATH',
                        help='输出文件路径（默认 output/report_<timestamp>.html）')
    parser.add_argument('-f', '--format', choices=['html', 'json', 'both'],
                        default='html',
                        help='输出格式：html（默认）、json、both')
    parser.add_argument('--web', action='store_true',
                        help='启动 Web 界面模式')
    parser.add_argument('--port', type=int, default=5000,
                        help='Web 服务端口（默认 5000）')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='显示详细检查过程')
    parser.add_argument('--no-color', action='store_true',
                        help='禁用彩色终端输出')

    return parser

def main():
    parser = build_parser()
    args = parser.parse_args()

    # 禁用颜色
    global USE_COLOR
    if args.no_color:
        USE_COLOR = False
        # 重置颜色常量
        for attr in ('RESET', 'BOLD', 'DIM', 'RED', 'GREEN', 'YELLOW',
                      'BLUE', 'CYAN', 'WHITE'):
            setattr(C, attr, '')

    # Web 模式
    if args.web:
        run_web(args.port)
        return

    # CLI 模式必须提供应答文件
    if not args.response:
        parser.error('请指定应答文件：--response FILE，或使用 --web 启动界面模式')

    run_cli(args)

if __name__ == '__main__':
    main()
