#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行催化裂化装置碳排放统计分析系统的脚本
"""

import os
import sys
import subprocess
import time

# 检查Python是否安装
try:
    import pip
except ImportError:
    print("错误：未找到Python，请先安装Python 3.7或更高版本")
    input("按回车键退出...")
    sys.exit(1)

# 安装依赖项
def install_dependencies():
    print("正在安装依赖项...")
    requirements = [
        "Flask",
        "Flask-SQLAlchemy",
        "Flask-Login",
        "WTForms",
        "pandas",
        "openpyxl"
    ]
    
    for package in requirements:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✓ 安装 {package} 成功")
        except subprocess.CalledProcessError:
            print(f"✗ 安装 {package} 失败")

# 运行应用
def run_app():
    print("\n正在启动催化裂化装置碳排放统计分析系统...")
    print("=" * 60)
    print("系统启动中，请稍候...")
    print("=" * 60)
    
    # 运行Flask应用
    try:
        # 保存当前目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 切换到脚本所在目录
        os.chdir(current_dir)
        
        # 启动应用
        print("\n系统已启动，登录地址：")
        print("http://127.0.0.1:5002")
        print("\n请在浏览器中打开上述地址进行登录")
        print("默认用户名：admin")
        print("默认密码：admin")
        print("\n按 Ctrl+C 停止服务")
        
        # 运行app.py
        subprocess.run([sys.executable, "app.py"])
        
    except KeyboardInterrupt:
        print("\n系统已停止")
    except Exception as e:
        print(f"错误：{e}")
        input("按回车键退出...")

if __name__ == "__main__":
    print("催化裂化装置碳排放统计分析系统启动脚本")
    print("=" * 60)
    
    # 安装依赖项
    install_dependencies()
    
    # 运行应用
    run_app()
