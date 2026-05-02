#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
醫師門診管理系統 - CLI 管理工具
用於查詢審計日誌、產生回溯 SQL、執行資料復原

用法:
    python cli.py logs [--table TABLE] [--limit N] [--action ACTION]
    python cli.py log LOG_ID
    python cli.py revert LOG_ID [--dry-run|--execute]
    python cli.py interactive
"""

import argparse
import sys
import os
import json
from datetime import datetime

# 添加父目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_connection, get_audit_logs, get_audit_log_by_id, logger

# 顏色定義
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def color_text(text, color):
    """為文字加上顏色"""
    return f"{color}{text}{Colors.ENDC}"


def format_json(data):
    """格式化 JSON 輸出"""
    if data is None:
        return color_text("無資料", Colors.YELLOW)
    try:
        return json.dumps(json.loads(data), indent=2, ensure_ascii=False)
    except:
        return data


def print_log(log):
    """格式化列印單筆記錄"""
    print(color_text("=" * 70, Colors.CYAN))
    print(f"{Colors.BOLD}#{log['id']}{Colors.ENDC} | {color_text(log['action'], get_action_color(log['action']))} | {log['table_name']}")
    print(color_text("-" * 70, Colors.CYAN))
    print(f"時間: {log['created_at']}")
    print(f"操作者: {log['operator']} | IP: {log['ip_address'] or 'N/A'}")
    print(f"記錄 ID: {log['record_id']}")
    print()
    print(f"{Colors.BOLD}原始 SQL:{Colors.ENDC}")
    print(f"  {log['sql_statement'] or 'N/A'}")
    print()
    print(f"{Colors.BOLD}反向 SQL (用於復原):{Colors.ENDC}")
    print(color_text(f"  {log['reverse_sql'] or '無法復原', Colors.YELLOW}"))
    print()
    print(f"{Colors.BOLD}變更前資料:{Colors.ENDC}")
    print(format_json(log['old_data']))
    print()
    print(f"{Colors.BOLD}變更後資料:{Colors.ENDC}")
    print(format_json(log['new_data']))


def get_action_color(action):
    """根據操作類型回傳顏色"""
    colors = {
        "INSERT": Colors.GREEN,
        "UPDATE": Colors.YELLOW,
        "DELETE": Colors.RED
    }
    return colors.get(action, Colors.ENDC)


def cmd_logs(args):
    """查詢日誌列表"""
    conn = get_connection()
    cursor = conn.cursor()
    
    logs = get_audit_logs(
        cursor,
        table_name=args.table,
        record_id=args.record_id,
        action=args.action,
        limit=args.limit,
        offset=args.offset
    )
    
    conn.close()
    
    if not logs:
        print(color_text("找不到符合條件的日誌", Colors.YELLOW))
        return
    
    print(color_text(f"\n找到 {len(logs)} 筆記錄\n", Colors.GREEN))
    
    for log in logs:
        action_color = get_action_color(log['action'])
        date_str = log['created_at'][:19] if log['created_at'] else 'N/A'
        print(f"[{log['id']:4}] {date_str} | {color_text(log['action'], action_color):6} | {log['table_name']:30} | ID:{log['record_id']}")
    
    print()


def cmd_log_detail(args):
    """顯示單筆日誌詳情"""
    conn = get_connection()
    cursor = conn.cursor()
    
    log = get_audit_log_by_id(cursor, args.log_id)
    conn.close()
    
    if not log:
        print(color_text(f"找不到 ID={args.log_id} 的日誌", Colors.RED))
        sys.exit(1)
    
    print_log(dict(log))


def cmd_revert(args):
    """執行回溯操作"""
    conn = get_connection()
    cursor = conn.cursor()
    
    log = get_audit_log_by_id(cursor, args.log_id)
    conn.close()
    
    if not log:
        print(color_text(f"找不到 ID={args.log_id} 的日誌", Colors.RED))
        sys.exit(1)
    
    log = dict(log)
    
    print(color_text("\n" + "=" * 70, Colors.RED))
    print(color_text("警告！即將執行復原操作", Colors.RED + Colors.BOLD))
    print(color_text("=" * 70, Colors.RED))
    print()
    print_log(log)
    print()
    
    reverse_sql = log['reverse_sql']
    if not reverse_sql:
        print(color_text("錯誤：此筆記錄無法復原（缺少 reverse_sql）", Colors.RED))
        sys.exit(1)
    
    if args.dry_run:
        print(color_text("【DRY-RUN 模式】以下 SQL 將會執行：", Colors.YELLOW))
        print()
        print(color_text(reverse_sql, Colors.CYAN))
        print()
        print(color_text("（使用 --execute 選項執行）", Colors.YELLOW))
    elif args.execute:
        print(color_text("【執行模式】正在執行復原...", Colors.YELLOW))
        print()
        
        # 確認
        confirm = input("確定要執行此操作？輸入 YES 確認: ")
        if confirm != "YES":
            print(color_text("已取消操作", Colors.YELLOW))
            return
        
        # 執行 SQL
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(reverse_sql)
            conn.commit()
            
            # 記錄復原操作本身
            from database import log_db_action
            log_db_action(
                cursor,
                action="REVERT",
                table_name=log['table_name'],
                record_id=log['record_id'],
                old_data=None,
                new_data=None,
                sql_statement=reverse_sql,
                operator="cli_tool"
            )
            conn.commit()
            conn.close()
            
            print(color_text("復原成功！", Colors.GREEN))
            logger.info(f"復原操作成功: log_id={args.log_id}, sql={reverse_sql}")
        except Exception as e:
            print(color_text(f"復原失敗: {e}", Colors.RED))
            logger.error(f"復原操作失敗: log_id={args.log_id}, error={e}")
            sys.exit(1)
    else:
        print(color_text("請指定操作模式：--dry-run 或 --execute", Colors.YELLOW))
        print()
        print(color_text("反向 SQL：", Colors.CYAN))
        print(reverse_sql)


def cmd_interactive(args):
    """互動模式"""
    print(color_text("\n" + "=" * 50, Colors.CYAN))
    print(color_text("審計日誌互動模式", Colors.BOLD + Colors.CYAN))
    print(color_text("=" * 50, Colors.CYAN))
    print()
    print("可用指令:")
    print("  log <id>    - 檢視指定 ID 的日誌詳情")
    print("  revert <id> - 產生指定 ID 的回溯 SQL")
    print("  tables     - 列出所有資料表")
    print("  exit       - 離開")
    print()
    
    while True:
        try:
            user_input = input(color_text("audit> ", Colors.GREEN)).strip()
            
            if not user_input:
                continue
            
            parts = user_input.split()
            cmd = parts[0].lower()
            
            if cmd == "exit":
                print(color_text("再見！", Colors.CYAN))
                break
            
            elif cmd == "log" and len(parts) > 1:
                try:
                    log_id = int(parts[1])
                    conn = get_connection()
                    cursor = conn.cursor()
                    log = get_audit_log_by_id(cursor, log_id)
                    conn.close()
                    
                    if log:
                        print()
                        print_log(dict(log))
                    else:
                        print(color_text(f"找不到 ID={log_id} 的日誌", Colors.YELLOW))
                except ValueError:
                    print(color_text("請輸入有效的 ID", Colors.YELLOW))
            
            elif cmd == "revert" and len(parts) > 1:
                try:
                    log_id = int(parts[1])
                    conn = get_connection()
                    cursor = conn.cursor()
                    log = get_audit_log_by_id(cursor, log_id)
                    conn.close()
                    
                    if log:
                        log = dict(log)
                        if log['reverse_sql']:
                            print()
                            print(color_text("反向 SQL：", Colors.CYAN))
                            print(log['reverse_sql'])
                            print()
                            
                            confirm = input("要執行此 SQL 嗎？輸入 YES 執行: ")
                            if confirm == "YES":
                                conn = get_connection()
                                cursor = conn.cursor()
                                cursor.execute(log['reverse_sql'])
                                conn.commit()
                                conn.close()
                                print(color_text("執行成功！", Colors.GREEN))
                        else:
                            print(color_text("此記錄無法復原", Colors.YELLOW))
                    else:
                        print(color_text(f"找不到 ID={log_id} 的日誌", Colors.YELLOW))
                except ValueError:
                    print(color_text("請輸入有效的 ID", Colors.YELLOW))
            
            elif cmd == "tables":
                print()
                print("可用的資料表：")
                print("  - patients")
                print("  - doctors")
                print("  - diseases")
                print("  - traditional_medicines")
                print("  - traditional_medicine_record")
                print("  - biological_medicines")
                print("  - biological_medicine_record")
                print("  - examinations")
                print("  - examination_record")
                print()
            
            else:
                print(color_text("未知指令，請使用 log <id>, revert <id>, tables, exit", Colors.YELLOW))
        
        except KeyboardInterrupt:
            print()
            print(color_text("再見！", Colors.CYAN))
            break
        except EOFError:
            break


def main():
    """主程式"""
    parser = argparse.ArgumentParser(
        description="醫師門診管理系統 - CLI 管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  python cli.py logs --table patients --limit 20
  python cli.py log 123
  python cli.py revert 123 --dry-run
  python cli.py revert 123 --execute
  python cli.py interactive
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='子指令')
    
    # logs 指令
    parser_logs = subparsers.add_parser('logs', help='查詢日誌列表')
    parser_logs.add_argument('--table', '-t', help='依資料表篩選')
    parser_logs.add_argument('--record-id', '-r', type=int, help='依記錄 ID 篩選')
    parser_logs.add_argument('--action', '-a', choices=['INSERT', 'UPDATE', 'DELETE'], help='依操作類型篩選')
    parser_logs.add_argument('--limit', '-l', type=int, default=50, help='限制筆數 (預設: 50)')
    parser_logs.add_argument('--offset', '-o', type=int, default=0, help='偏移量 (預設: 0)')
    
    # log 指令
    parser_log = subparsers.add_parser('log', help='顯示單筆日誌詳情')
    parser_log.add_argument('log_id', type=int, help='日誌 ID')
    
    # revert 指令
    parser_revert = subparsers.add_parser('revert', help='執行回溯操作')
    parser_revert.add_argument('log_id', type=int, help='日誌 ID')
    parser_revert.add_argument('--dry-run', action='store_true', help='僅顯示要執行的 SQL')
    parser_revert.add_argument('--execute', action='store_true', help='執行復原')
    
    # interactive 指令
    subparsers.add_parser('interactive', help='互動模式')
    
    args = parser.parse_args()
    
    if args.command == 'logs':
        cmd_logs(args)
    elif args.command == 'log':
        cmd_log_detail(args)
    elif args.command == 'revert':
        cmd_revert(args)
    elif args.command == 'interactive':
        cmd_interactive(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
