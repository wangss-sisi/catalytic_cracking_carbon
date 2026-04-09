#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统诊断脚本
"""

import os
import sys
import socket
import urllib.request
import json

# 检查系统环境
def check_environment():
    print("===== 系统环境检查 =====")
    print(f"Python版本: {sys.version}")
    print(f"当前目录: {os.getcwd()}")
    print(f"可执行文件路径: {os.path.abspath(__file__)}")
    print()

# 检查网络连接
def check_network():
    print("===== 网络连接检查 =====")
    try:
        # 检查本地服务器是否运行
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 5002))
        if result == 0:
            print("✓ 本地服务器正在运行")
        else:
            print("✗ 本地服务器未运行")
        sock.close()
    except Exception as e:
        print(f"✗ 网络检查失败: {e}")
    print()

# 检查页面访问
def check_page_access():
    print("===== 页面访问检查 =====")
    try:
        # 访问登录页面
        login_url = "http://127.0.0.1:5002/login"
        response = urllib.request.urlopen(login_url, timeout=5)
        status_code = response.getcode()
        print(f"✓ 登录页面访问成功，状态码: {status_code}")
        
        # 读取页面内容
        content = response.read().decode('utf-8')
        if "用户登录" in content:
            print("✓ 登录页面内容正确")
        else:
            print("✗ 登录页面内容异常")
            print(f"页面内容片段: {content[:200]}...")
    except Exception as e:
        print(f"✗ 页面访问失败: {e}")
    print()

# 检查文件结构
def check_file_structure():
    print("===== 文件结构检查 =====")
    # 检查可执行文件是否存在
    exe_path = "dist\催化裂化装置碳排放统计分析系统.exe"
    if os.path.exists(exe_path):
        print(f"✓ 可执行文件存在: {exe_path}")
    else:
        print(f"✗ 可执行文件不存在: {exe_path}")
    
    # 检查模板文件是否存在
    templates_dir = "templates"
    if os.path.exists(templates_dir):
        print(f"✓ 模板目录存在: {templates_dir}")
        # 检查关键模板文件
        key_templates = ["login.html", "base.html", "dashboard.html"]
        for template in key_templates:
            template_path = os.path.join(templates_dir, template)
            if os.path.exists(template_path):
                print(f"✓ 模板文件存在: {template}")
            else:
                print(f"✗ 模板文件不存在: {template}")
    else:
        print(f"✗ 模板目录不存在: {templates_dir}")
    print()

if __name__ == "__main__":
    print("催化裂化装置碳排放统计分析系统诊断工具")
    print("=" * 60)
    
    check_environment()
    check_network()
    check_page_access()
    check_file_structure()
    
    print("诊断完成！")
    print("=" * 60)
    print("如果服务器未运行，请先运行 'run_system.bat' 启动系统")
    print("然后再运行此诊断工具")
    input("按回车键退出...")
