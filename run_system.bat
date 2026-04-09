@echo off

rem 催化裂化装置碳排放统计分析系统启动脚本

cls
echo 催化裂化装置碳排放统计分析系统
echo ================================
echo 正在启动系统...
echo ================================

echo 系统将在后台启动，启动后请在浏览器中访问：
echo http://127.0.0.1:5002
echo 
echo 登录信息：
echo 用户名：admin
echo 密码：admin
echo 
echo 按任意键启动系统...
pause > nul

rem 启动可执行文件
start "催化裂化装置碳排放统计分析系统" "dist\催化裂化装置碳排放统计分析系统.exe"

echo 系统已启动，请在浏览器中打开上述地址进行登录
echo 
echo 按任意键退出...
pause > nul
