# -*- coding: utf-8 -*-.
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, FloatField, SelectField, DateField
from wtforms.validators import DataRequired, Length, NumberRange
from functools import wraps
from datetime import datetime
import math
import json
import pandas as pd
from io import BytesIO
from flask import send_file
import os

# 处理模板文件路径
basedir = os.path.abspath(os.path.dirname(__file__))
templates_dir = os.path.join(basedir, 'templates')

app = Flask(__name__, template_folder=templates_dir)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///carbon_emission.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='user')

class PlanExecution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    烧焦量 = db.Column(db.Float, nullable=False)
    加工量 = db.Column(db.Float, nullable=True)
    设备开工天数 = db.Column(db.Integer, nullable=True)
    平均日加工量 = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class FlueGas(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    O2 = db.Column(db.Float, nullable=False)
    CO2 = db.Column(db.Float, nullable=False)
    CO = db.Column(db.Float, nullable=True, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CarbonEmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    烧焦量 = db.Column(db.Float, nullable=False)
    焦层中含碳量 = db.Column(db.Float, nullable=False)
    碳氧化率 = db.Column(db.Float, nullable=False, default=98)
    CO2排放量 = db.Column(db.Float, nullable=False)
    环比变化原因 = db.Column(db.String(500), nullable=True)
    同比变化原因 = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('密码', validators=[DataRequired()])
    submit = SubmitField('登录')

class PlanExecutionForm(FlaskForm):
    year = IntegerField('年份', validators=[DataRequired(), NumberRange(min=2020, max=2030)])
    month = SelectField('月份', choices=[(str(i), str(i)) for i in range(1, 13)], validators=[DataRequired()])
    烧焦量 = FloatField('烧焦量(吨)', validators=[DataRequired(), NumberRange(min=0)])
    加工量 = FloatField('加工量(吨)', validators=[NumberRange(min=0)])
    设备开工天数 = IntegerField('设备开工天数', validators=[NumberRange(min=0, max=31)])
    平均日加工量 = FloatField('平均日加工量(吨)', validators=[NumberRange(min=0)])
    submit = SubmitField('提交')

class FlueGasForm(FlaskForm):
    year = IntegerField('年份', validators=[DataRequired(), NumberRange(min=2020, max=2030)])
    month = SelectField('月份', choices=[(str(i), str(i)) for i in range(1, 13)], validators=[DataRequired()])
    O2 = FloatField('O2(%)', validators=[DataRequired(), NumberRange(min=0, max=21)])
    CO2 = FloatField('CO2(%)', validators=[DataRequired(), NumberRange(min=0, max=100)])
    CO = FloatField('CO(%)', validators=[NumberRange(min=0, max=100)])
    submit = SubmitField('提交')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 权限检查装饰器
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('您没有权限执行此操作')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.password == form.password.data:
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('登录失败，请检查用户名和密码')
    return render_template('login.html', form=form)

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# 计算焦层中含碳量
def calculate_carbon_content(O2, CO2, CO=0):
    try:
        denominator = CO2 + CO
        if denominator == 0:
            return 0
        term = (8.93 - 0.425 * (CO2 + O2) - 0.257 * CO) / denominator
        carbon_ratio = 1 / (1 + term)
        return carbon_ratio * 100  # 转换为百分比
    except:
        return 0

# 计算CO2排放量
def calculate_co2_emission(烧焦量, 碳含量, 碳氧化率=98):
    try:
        # CO2排放量=烧焦量*焦层中含碳量*碳氧化率*44/12/1000
        # 根据需求，移除最后的/1000，直接返回吨为单位的数值
        emission = 烧焦量 * (碳含量 / 100) * (碳氧化率 / 100) * 44 / 12
        return emission
    except:
        return 0

# 计算环比变化
def calculate_month_over_month(current, previous):
    if previous == 0:
        return 0
    return ((current - previous) / previous) * 100

# 计算同比变化
def calculate_year_over_year(current, last_year):
    if last_year == 0:
        return 0
    return ((current - last_year) / last_year) * 100

@app.route('/dashboard')
@login_required
def dashboard():
    # 获取最新的碳排放数据
    latest_emissions = CarbonEmission.query.order_by(CarbonEmission.year.desc(), CarbonEmission.month.desc()).limit(12).all()
    return render_template('dashboard.html', emissions=latest_emissions)

@app.route('/plan_execution', methods=['GET', 'POST'])
@login_required
def plan_execution():
    form = PlanExecutionForm()
    
    # 处理查询和修改
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    
    # 如果有年月参数，尝试填充表单数据
    if year and month:
        existing = PlanExecution.query.filter_by(year=year, month=month).first()
        if existing:
            form.year.data = existing.year
            form.month.data = str(existing.month)
            form.烧焦量.data = existing.烧焦量
            form.加工量.data = existing.加工量
            form.设备开工天数.data = existing.设备开工天数
            form.平均日加工量.data = existing.平均日加工量
    
    if form.validate_on_submit() and current_user.role == 'admin':
        # 检查是否已存在相同年月的数据
        existing = PlanExecution.query.filter_by(year=form.year.data, month=int(form.month.data)).first()
        if existing:
            existing.烧焦量 = form.烧焦量.data
            existing.加工量 = form.加工量.data
            existing.设备开工天数 = form.设备开工天数.data
            existing.平均日加工量 = form.平均日加工量.data
            db.session.commit()
            flash('计划执行情况更新成功')
        else:
            new_plan = PlanExecution(
                year=form.year.data,
                month=int(form.month.data),
                烧焦量=form.烧焦量.data,
                加工量=form.加工量.data,
                设备开工天数=form.设备开工天数.data,
                平均日加工量=form.平均日加工量.data
            )
            db.session.add(new_plan)
            db.session.commit()
            flash('计划执行情况添加成功')
        return redirect(url_for('plan_execution'))
    
    # 构建查询
    query = PlanExecution.query
    if year and not request.method == 'POST':
        query = query.filter_by(year=year)
    if month and not request.method == 'POST':
        query = query.filter_by(month=month)
    
    # 获取计划执行数据
    plans = query.order_by(PlanExecution.year.desc(), PlanExecution.month.desc()).all()
    
    return render_template('plan_execution.html', form=form, plans=plans, year=year, month=month)

@app.route('/plan_execution/delete/<int:id>')
@login_required
@admin_required
def delete_plan(id):
    plan = PlanExecution.query.get(id)
    if plan:
        db.session.delete(plan)
        db.session.commit()
        flash('计划执行情况删除成功')
    return redirect(url_for('plan_execution'))

@app.route('/flue_gas', methods=['GET', 'POST'])
@login_required
def flue_gas():
    form = FlueGasForm()
    
    # 处理查询和修改
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    
    # 如果有年月参数，尝试填充表单数据
    if year and month:
        existing = FlueGas.query.filter_by(year=year, month=month).first()
        if existing:
            form.year.data = existing.year
            form.month.data = str(existing.month)
            form.O2.data = existing.O2
            form.CO2.data = existing.CO2
            form.CO.data = existing.CO
    
    if form.validate_on_submit() and current_user.role == 'admin':
        # 检查是否已存在相同年月的数据
        existing = FlueGas.query.filter_by(year=form.year.data, month=int(form.month.data)).first()
        if existing:
            existing.O2 = form.O2.data
            existing.CO2 = form.CO2.data
            existing.CO = form.CO.data or 0
            db.session.commit()
            flash('烟气成绩更新成功')
        else:
            new_flue_gas = FlueGas(
                year=form.year.data,
                month=int(form.month.data),
                O2=form.O2.data,
                CO2=form.CO2.data,
                CO=form.CO.data or 0
            )
            db.session.add(new_flue_gas)
            db.session.commit()
            flash('烟气成绩添加成功')
        return redirect(url_for('flue_gas'))
    
    # 构建查询
    query = FlueGas.query
    if year and not request.method == 'POST':
        query = query.filter_by(year=year)
    if month and not request.method == 'POST':
        query = query.filter_by(month=month)
    
    # 获取烟气成绩数据
    flue_gases = query.order_by(FlueGas.year.desc(), FlueGas.month.desc()).all()
    
    return render_template('flue_gas.html', form=form, flue_gases=flue_gases, year=year, month=month)

@app.route('/flue_gas/delete/<int:id>')
@login_required
@admin_required
def delete_flue_gas(id):
    flue_gas = FlueGas.query.get(id)
    if flue_gas:
        db.session.delete(flue_gas)
        db.session.commit()
        flash('烟气成绩删除成功')
    return redirect(url_for('flue_gas'))

@app.route('/calculate_emissions')
@login_required
@admin_required
def calculate_emissions():
    # 获取所有计划执行和烟气成绩数据
    plans = PlanExecution.query.all()
    flue_gases = FlueGas.query.all()
    
    # 创建年月到数据的映射
    plan_map = {(p.year, p.month): p for p in plans}
    flue_gas_map = {(f.year, f.month): f for f in flue_gases}
    
    # 计算碳排放数据
    for (year, month), plan in plan_map.items():
        if (year, month) in flue_gas_map:
            flue_gas = flue_gas_map[(year, month)]
            # 计算焦层中含碳量
            carbon_content = calculate_carbon_content(flue_gas.O2, flue_gas.CO2, flue_gas.CO)
            # 计算CO2排放量
            co2_emission = calculate_co2_emission(plan.烧焦量, carbon_content)
            
            # 检查是否已存在相同年月的碳排放数据
            existing = CarbonEmission.query.filter_by(year=year, month=month).first()
            if existing:
                existing.烧焦量 = plan.烧焦量
                existing.焦层中含碳量 = carbon_content
                existing.CO2排放量 = co2_emission
            else:
                new_emission = CarbonEmission(
                    year=year,
                    month=month,
                    烧焦量=plan.烧焦量,
                    焦层中含碳量=carbon_content,
                    CO2排放量=co2_emission
                )
                db.session.add(new_emission)
    
    db.session.commit()
    flash('碳排放数据计算成功')
    return redirect(url_for('carbon_emission'))

@app.route('/carbon_emission')
@login_required
def carbon_emission():
    # 处理查询
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    
    # 构建查询
    query = CarbonEmission.query
    if year:
        query = query.filter_by(year=year)
    if month:
        query = query.filter_by(month=month)
    
    # 获取碳排放数据
    emissions = query.order_by(CarbonEmission.year.desc(), CarbonEmission.month.desc()).all()
    
    # 计算环比和同比变化
    for i, emission in enumerate(emissions):
        # 计算环比
        if i < len(emissions) - 1:
            prev_emission = emissions[i + 1]
            if prev_emission.year == emission.year and prev_emission.month == emission.month - 1:
                mom_change = calculate_month_over_month(emission.CO2排放量, prev_emission.CO2排放量)
                # 分析环比变化原因
                reasons = []
                
                # 分析烧焦量变化
                if abs(emission.烧焦量 - prev_emission.烧焦量) / prev_emission.烧焦量 * 100 > 2:
                    if emission.烧焦量 > prev_emission.烧焦量:
                        reasons.append(f"本月烧焦量较上月增加{emission.烧焦量 - prev_emission.烧焦量:.0f}吨")
                    else:
                        reasons.append(f"本月烧焦量较上月减少{prev_emission.烧焦量 - emission.烧焦量:.0f}吨")
                
                # 分析焦层含碳量变化
                if abs(emission.焦层中含碳量 - prev_emission.焦层中含碳量) > 0.5:
                    if emission.焦层中含碳量 > prev_emission.焦层中含碳量:
                        reasons.append(f"焦层含碳量较上月增加{emission.焦层中含碳量 - prev_emission.焦层中含碳量:.2f}%")
                    else:
                        reasons.append(f"焦层含碳量较上月减少{prev_emission.焦层中含碳量 - emission.焦层中含碳量:.2f}%")
                
                # 生成环比变化原因
                if reasons:
                    reason_text = "；".join(reasons)
                    emission.环比变化原因 = f"{reason_text}，导致CO2排放量环比{'增加' if mom_change > 0 else '减少'}{abs(mom_change):.2f}%"
                elif abs(mom_change) > 3:
                    emission.环比变化原因 = f"本月CO2排放量环比变化{mom_change:.2f}%，超过3%"
        
        # 计算同比
        last_year_emission = CarbonEmission.query.filter_by(year=emission.year - 1, month=emission.month).first()
        if last_year_emission:
            yoy_change = calculate_year_over_year(emission.CO2排放量, last_year_emission.CO2排放量)
            # 分析同比变化原因
            yoy_reasons = []
            
            # 分析烧焦量变化
            if abs(emission.烧焦量 - last_year_emission.烧焦量) / last_year_emission.烧焦量 * 100 > 2:
                if emission.烧焦量 > last_year_emission.烧焦量:
                    yoy_reasons.append(f"本年烧焦量较去年同期增加{emission.烧焦量 - last_year_emission.烧焦量:.0f}吨")
                else:
                    yoy_reasons.append(f"本年烧焦量较去年同期减少{last_year_emission.烧焦量 - emission.烧焦量:.0f}吨")
            
            # 分析焦层含碳量变化
            if abs(emission.焦层中含碳量 - last_year_emission.焦层中含碳量) > 0.5:
                if emission.焦层中含碳量 > last_year_emission.焦层中含碳量:
                    yoy_reasons.append(f"焦层含碳量较去年同期增加{emission.焦层中含碳量 - last_year_emission.焦层中含碳量:.2f}%")
                else:
                    yoy_reasons.append(f"焦层含碳量较去年同期减少{last_year_emission.焦层中含碳量 - emission.焦层中含碳量:.2f}%")
            
            # 生成同比变化原因
            if yoy_reasons:
                yoy_reason_text = "；".join(yoy_reasons)
                emission.同比变化原因 = f"{yoy_reason_text}，导致CO2排放量同比{'增加' if yoy_change > 0 else '减少'}{abs(yoy_change):.2f}%"
            elif abs(yoy_change) > 3:
                emission.同比变化原因 = f"本月CO2排放量同比变化{yoy_change:.2f}%，超过3%"
    
    db.session.commit()
    return render_template('carbon_emission.html', emissions=emissions, year=year, month=month)

@app.route('/carbon_emission/delete/<int:id>')
@login_required
@admin_required
def delete_carbon_emission(id):
    emission = CarbonEmission.query.get(id)
    if emission:
        db.session.delete(emission)
        db.session.commit()
        flash('碳排放数据删除成功')
    return redirect(url_for('carbon_emission'))

@app.route('/analysis')
@login_required
def analysis():
    # 处理年份选择
    selected_year = request.args.get('year', type=int)
    
    # 构建查询
    query = CarbonEmission.query
    if selected_year:
        query = query.filter_by(year=selected_year)
    
    # 获取碳排放数据，按年月排序
    emissions = query.order_by(CarbonEmission.year.asc(), CarbonEmission.month.asc()).all()
    
    # 准备图表数据
    labels = [f"{e.year}-{e.month:02d}" for e in emissions]
    co2_data = [e.CO2排放量 for e in emissions]
    carbon_content_data = [e.焦层中含碳量 for e in emissions]
    coke_data = [e.烧焦量 for e in emissions]
    
    # 获取所有可用年份（从多个表中）
    # 从PlanExecution表获取年份
    plan_years = db.session.query(PlanExecution.year).distinct().all()
    plan_years = [year[0] for year in plan_years]
    
    # 从FlueGas表获取年份
    flue_gas_years = db.session.query(FlueGas.year).distinct().all()
    flue_gas_years = [year[0] for year in flue_gas_years]
    
    # 从CarbonEmission表获取年份
    emission_years = db.session.query(CarbonEmission.year).distinct().all()
    emission_years = [year[0] for year in emission_years]
    
    # 合并所有年份并去重，然后排序
    years = list(set(plan_years + flue_gas_years + emission_years))
    years.sort()
    
    return render_template('analysis.html', 
                         labels=json.dumps(labels),
                         co2_data=json.dumps(co2_data),
                         carbon_content_data=json.dumps(carbon_content_data),
                         烧焦量_data=json.dumps(coke_data),
                         selected_year=selected_year,
                         years=years)

# 导出计划执行情况数据
@app.route('/export/plan_execution')
@login_required
def export_plan_execution():
    plans = PlanExecution.query.order_by(PlanExecution.year, PlanExecution.month).all()
    data = []
    for plan in plans:
        data.append({
            '年份': plan.year,
            '月份': plan.month,
            '烧焦量(吨)': plan.烧焦量,
            '加工量(吨)': plan.加工量 or 0,
            '设备开工天数': plan.设备开工天数 or 0,
            '平均日加工量(吨)': plan.平均日加工量 or 0
        })
    
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='计划执行情况', index=False)
    output.seek(0)
    
    return send_file(output, as_attachment=True, download_name='计划执行情况.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# 导出烟气成绩数据
@app.route('/export/flue_gas')
@login_required
def export_flue_gas():
    flue_gases = FlueGas.query.order_by(FlueGas.year, FlueGas.month).all()
    data = []
    for gas in flue_gases:
        data.append({
            '年份': gas.year,
            '月份': gas.month,
            'O2(%)': gas.O2,
            'CO2(%)': gas.CO2,
            'CO(%)': gas.CO or 0
        })
    
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='烟气成绩', index=False)
    output.seek(0)
    
    return send_file(output, as_attachment=True, download_name='烟气成绩.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# 导出碳排放数据
@app.route('/export/carbon_emission')
@login_required
def export_carbon_emission():
    emissions = CarbonEmission.query.order_by(CarbonEmission.year, CarbonEmission.month).all()
    data = []
    for emission in emissions:
        data.append({
            '年份': emission.year,
            '月份': emission.month,
            '烧焦量(吨)': emission.烧焦量,
            '焦层中含碳量(%)': emission.焦层中含碳量,
            '碳氧化率(%)': emission.碳氧化率,
            'CO2排放量(吨)': emission.CO2排放量,
            '环比变化原因': emission.环比变化原因 or '-',
            '同比变化原因': emission.同比变化原因 or '-'
        })
    
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='碳排放数据', index=False)
    output.seek(0)
    
    return send_file(output, as_attachment=True, download_name='碳排放数据.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# 导入计划执行情况数据
@app.route('/import/plan_execution', methods=['POST'])
@login_required
@admin_required
def import_plan_execution():
    if 'file' not in request.files:
        flash('未上传文件')
        return redirect(url_for('plan_execution'))
    
    file = request.files['file']
    if file.filename == '':
        flash('未选择文件')
        return redirect(url_for('plan_execution'))
    
    try:
        df = pd.read_excel(file)
        for _, row in df.iterrows():
            year = int(row['年份'])
            month = int(row['月份'])
            existing = PlanExecution.query.filter_by(year=year, month=month).first()
            if existing:
                existing.烧焦量 = row['烧焦量(吨)']
                existing.加工量 = row.get('加工量(吨)', 0)
                existing.设备开工天数 = row.get('设备开工天数', 0)
                existing.平均日加工量 = row.get('平均日加工量(吨)', 0)
            else:
                new_plan = PlanExecution(
                    year=year,
                    month=month,
                    烧焦量=row['烧焦量(吨)'],
                    加工量=row.get('加工量(吨)', 0),
                    设备开工天数=row.get('设备开工天数', 0),
                    平均日加工量=row.get('平均日加工量(吨)', 0)
                )
                db.session.add(new_plan)
        db.session.commit()
        flash('计划执行情况导入成功')
    except Exception as e:
        flash(f'导入失败: {str(e)}')
    
    return redirect(url_for('plan_execution'))

# 导入烟气成绩数据
@app.route('/import/flue_gas', methods=['POST'])
@login_required
@admin_required
def import_flue_gas():
    if 'file' not in request.files:
        flash('未上传文件')
        return redirect(url_for('flue_gas'))
    
    file = request.files['file']
    if file.filename == '':
        flash('未选择文件')
        return redirect(url_for('flue_gas'))
    
    try:
        df = pd.read_excel(file)
        for _, row in df.iterrows():
            year = int(row['年份'])
            month = int(row['月份'])
            existing = FlueGas.query.filter_by(year=year, month=month).first()
            if existing:
                existing.O2 = row['O2(%)']
                existing.CO2 = row['CO2(%)']
                existing.CO = row.get('CO(%)', 0)
            else:
                new_flue_gas = FlueGas(
                    year=year,
                    month=month,
                    O2=row['O2(%)'],
                    CO2=row['CO2(%)'],
                    CO=row.get('CO(%)', 0)
                )
                db.session.add(new_flue_gas)
        db.session.commit()
        flash('烟气成绩导入成功')
    except Exception as e:
        flash(f'导入失败: {str(e)}')
    
    return redirect(url_for('flue_gas'))

with app.app_context():
    # 检查并更新数据库表结构
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    columns = [column['name'] for column in inspector.get_columns('user')]
    
    # 如果user表不存在role字段，添加它
    if 'role' not in columns:
        from sqlalchemy import text
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE user ADD COLUMN role VARCHAR(10) DEFAULT \'user\''))
            conn.commit()
    
    db.create_all()
    
    # 确保admin和user用户存在
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', password='admin', role='admin')
        db.session.add(admin)
    else:
        admin.role = 'admin'
    
    user = User.query.filter_by(username='user').first()
    if not user:
        user = User(username='user', password='user', role='user')
        db.session.add(user)
    else:
        user.role = 'user'
    
    db.session.commit()

if __name__ == '__main__':
    app.run(debug=True, port=5002)
