"""SKURGE browser app. Keeps the original Python services and SQLite schema."""
from __future__ import annotations
import os, sys, secrets, hashlib, uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from functools import wraps
from flask import Flask, flash, redirect, render_template, request, session, url_for, abort
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'frontend'))
from services.auth_service import AuthService
from services.business_service import BusinessService
from services.business_repository import DRAFT, REGISTRATION_IN_PROGRESS, REGISTERED_DECLARED, REGISTRATION_STATUS_CHOICES
from services.dashboard_service import DashboardService
from services.finance_service import FinanceService
from services.employee_service import EmployeeService
from services.database import get_connection
from services.permission_service import PermissionService
from services.employee_repository import ACTIVE, INACTIVE, ON_LEAVE, EMPLOYEE_ROLES

SECTIONS=[('dashboard','Dashboard','⌂'),('business','Business','▦'),('employees','Employees','♙'),('payroll','Payroll','＄'),('finance','Finance','↗'),('payments','Payments','⇄'),('orders','Orders','▤'),('inventory','Inventory','▧'),('suppliers','Suppliers','◇'),('customers','Customers','♧'),('tax','Tax','§'),('documents','Documents','▱'),('calendar','Calendar','▦'),('network','Business Network','◎'),('notifications','Notifications','♢'),('settings','Settings','⚙')]
DESCRIPTIONS={
'dashboard':'Your business at a glance: recorded income, expenses, cash movement and team status.',
'business':'Your business identity, registration details and profile information.',
'employees':'Manage employee records, employment status and secure join codes for team access.',
'payroll':'Organise payroll preparation and employee compensation records. No bank payments are sent from this workspace.',
'finance':'Record income and expenses, organise categories and review the transaction ledger.',
'payments':'Payment planning and records. External bank and PayShap execution is not connected.',
'orders':'Keep track of customer orders and their fulfilment status.',
'inventory':'Organise stock items, quantities, reorder levels and categories.',
'suppliers':'Maintain supplier contacts and purchasing relationships.',
'customers':'Keep customer contacts and relationship details in one place.',
'tax':'Organise tax-related notes and documents. SARS is not connected in this build.',
'documents':'A workspace for required company records and document tracking.',
'calendar':'Plan business tasks, reminders and important dates.',
'network':'A starting point for business-to-business relationships and supplier discovery.',
'notifications':'Review workspace notices and recent activity.',
'settings':'Control appearance, account details and business preferences.'}

def create_app(test_config=None):
 app=Flask(__name__,template_folder='templates',static_folder='static')
 production=os.getenv('RENDER','').lower()=='true' or os.getenv('FLASK_ENV')=='production'
 secret=os.getenv('SKURGE_SECRET_KEY')
 if production and not secret: raise RuntimeError('Set SKURGE_SECRET_KEY in the Render environment.')
 app.config.update(SECRET_KEY=secret or 'local-development-only-change-me',SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=production,MAX_CONTENT_LENGTH=2*1024*1024)
 if test_config: app.config.update(test_config)
 CSRFProtect(app); Limiter(get_remote_address,app=app,default_limits=['200 per day','50 per hour'])
 @app.after_request
 def headers(resp):
  resp.headers.setdefault('X-Content-Type-Options','nosniff'); resp.headers.setdefault('X-Frame-Options','DENY'); resp.headers.setdefault('Referrer-Policy','strict-origin-when-cross-origin'); return resp
 @app.get('/healthz')
 def healthz(): return {'status':'ok','service':'skurge-web'},200
 def login_required(fn):
  @wraps(fn)
  def inner(*a,**kw):
   if not session.get('user'): flash('Please sign in to continue.','info'); return redirect(url_for('login'))
   return fn(*a,**kw)
  return inner
 def current_user(): return session.get('user')
 def current_business():
  u=current_user()
  if not u: return None
  owned=BusinessService.get_business_for_user(u['id'])
  if owned: return owned
  conn=get_connection()
  row=conn.execute('SELECT b.id,b.owner_user_id,b.name,b.business_type,b.industry,b.registration_status,b.province,b.cipc_number,b.city,b.phone,b.email,b.primary_contact_name,b.tax_status,b.created_at,b.updated_at FROM businesses b JOIN business_memberships m ON m.business_id=b.id WHERE m.user_id=? ORDER BY m.created_at DESC LIMIT 1',(u['id'],)).fetchone()
  conn.close()
  if row:
   from services.business_repository import Business
   return Business(*row)
  return None
 def require_owner(biz):
  u=current_user()
  if not biz or not u or biz.owner_user_id != u['id']:
   abort(403)
 def require_manager(biz):
  u=current_user()
  if not biz or not u or not PermissionService.has_permission(biz.id,u['id'],'manage_employees'):
   abort(403)
 def fmt(cents): return f"R {cents/100:,.2f}"
 @app.context_processor
 def globals_ctx(): return {'sections':SECTIONS,'current_year':date.today().year,'today_iso':date.today().isoformat()}
 @app.get('/')
 def index(): return redirect(url_for('splash'))
 @app.get('/splash')
 def splash(): return render_template('splash.html',next_url=url_for('welcome'))
 @app.get('/welcome')
 def welcome(): return render_template('welcome.html')
 @app.route('/register',methods=['GET','POST'])
 def register():
  invite=request.args.get('code','').strip().upper() or request.form.get('referral_code','').strip().upper()
  if request.method=='POST':
   name=request.form.get('full_name','').strip(); email=request.form.get('email','').strip(); password=request.form.get('password','')
   if len(password)<10: flash('Use a password with at least 10 characters.','error')
   else:
    if invite:
     try:
      conn=get_connection(); conn.execute('CREATE TABLE IF NOT EXISTS web_employee_invites (id TEXT PRIMARY KEY,business_id TEXT NOT NULL,employee_id TEXT NOT NULL,code_hash TEXT NOT NULL UNIQUE,expires_at TEXT NOT NULL,created_by TEXT NOT NULL,created_at TEXT NOT NULL,used_at TEXT,used_by TEXT)'); conn.commit(); check=conn.execute('SELECT expires_at,used_at FROM web_employee_invites WHERE code_hash=?',(hashlib.sha256(invite.encode()).hexdigest(),)).fetchone(); conn.close()
      if not check: raise ValueError('That employee referral code is invalid.')
      if check[1] or datetime.fromisoformat(check[0]) < datetime.now(): raise ValueError('That employee referral code has expired or has already been used.')
     except ValueError as e:
      flash(str(e),'error'); return render_template('auth.html',mode='register',referral_code=invite)
    try:
     user=AuthService.register(name,email,password)
     session.clear(); session['user']={'id':user.id,'full_name':user.full_name,'email':user.email}
     if invite:
      try:
       conn=get_connection(); row=conn.execute('SELECT id,business_id,employee_id,code_hash,expires_at,used_at FROM web_employee_invites WHERE code_hash=?',(hashlib.sha256(invite.encode()).hexdigest(),)).fetchone()
       if not row: raise ValueError('That employee referral code is invalid.')
       iid,bid,eid,ch,expires,used=row
       if used or datetime.fromisoformat(expires)<datetime.now(): raise ValueError('That employee referral code has expired or has already been used.')
       conn.execute('INSERT OR IGNORE INTO business_memberships(id,business_id,user_id,role,created_at) VALUES(?,?,?,?,?)',(str(uuid.uuid4()),bid,user.id,'employee',datetime.utcnow().isoformat()))
       conn.execute('UPDATE web_employee_invites SET used_at=?,used_by=? WHERE id=?',(datetime.utcnow().isoformat(),user.id,iid)); conn.commit(); conn.close()
       session['employee_business_id']=bid; flash('Account created and linked to your employer’s SKURGE workspace.','success'); return redirect(url_for('module_page',section='dashboard'))
      except Exception as e:
       flash(f'Your account was created, but the referral could not be applied: {e}','error')
     flash('Account created. Now set up your business.','success'); return redirect(url_for('business_setup'))
    except ValueError as e: flash(str(e),'error')
  return render_template('auth.html',mode='register',referral_code=invite)
 @app.route('/login',methods=['GET','POST'])
 def login():
  if request.method=='POST':
   try:
    user=AuthService.login(request.form.get('email',''),request.form.get('password',''))
    session.clear(); session['user']={'id':user.id,'full_name':user.full_name,'email':user.email}
    flash('Welcome back.','success'); conn=get_connection(); member=conn.execute('SELECT 1 FROM business_memberships WHERE user_id=? LIMIT 1',(user.id,)).fetchone(); conn.close()
    return redirect(url_for('module_page',section='dashboard') if (BusinessService.get_business_for_user(user.id) or member) else url_for('business_setup'))
   except ValueError as e: flash(str(e),'error')
  return render_template('auth.html',mode='login',referral_code='')
 @app.post('/logout')
 def logout(): session.clear(); flash('You have been signed out.','success'); return redirect(url_for('welcome'))
 @app.route('/business/setup',methods=['GET','POST'])
 @login_required
 def business_setup():
  u=current_user(); existing=BusinessService.get_business_for_user(u['id'])
  if request.method=='POST':
   f={'name':request.form.get('name','').strip(),'business_type':request.form.get('business_type','').strip(),'industry':request.form.get('industry','').strip(),'registration_status':request.form.get('registration_status',DRAFT),'province':request.form.get('province','').strip(),'cipc_number':request.form.get('cipc_number','').strip(),'city':request.form.get('city','').strip(),'phone':request.form.get('phone','').strip(),'email':request.form.get('business_email','').strip(),'primary_contact_name':u['full_name'],'tax_status':''}
   if f['registration_status'] not in {DRAFT,REGISTRATION_IN_PROGRESS,REGISTERED_DECLARED}: f['registration_status']=DRAFT
   if not all(f[k] for k in ('name','business_type','industry','province')): flash('Business name, type, industry and province are required.','error')
   else:
    try: BusinessService.create_business(owner_user_id=u['id'],**f); flash('Business profile created.','success'); return redirect(url_for('module_page',section='dashboard'))
    except ValueError as e: flash(str(e),'error')
  return render_template('business_setup.html',user=u,existing=existing,statuses=REGISTRATION_STATUS_CHOICES)
 @app.get('/dashboard')
 @login_required
 def dashboard(): return redirect(url_for('module_page',section='dashboard'))
 @app.route('/app/<section>',methods=['GET','POST'])
 @login_required
 def module_page(section):
  valid={x[0] for x in SECTIONS}
  if section not in valid: return redirect(url_for('module_page',section='dashboard'))
  u=current_user(); biz=current_business()
  if session.get('employee_business_id') and not biz:
   conn=get_connection(); row=conn.execute('SELECT id,owner_user_id,name,business_type,industry,registration_status,province,cipc_number,city,phone,email,primary_contact_name,tax_status,created_at,updated_at FROM businesses WHERE id=?',(session['employee_business_id'],)).fetchone(); conn.close()
   if row:
    from services.business_repository import Business
    biz=Business(*row)
  if section!='settings' and not biz and section not in ('business',): flash('Create or join a business to unlock your workspace.','info')
  if biz and section=='finance' and not PermissionService.has_permission(biz.id,u['id'],'view_finance'): abort(403)
  if biz and section=='employees' and not PermissionService.has_permission(biz.id,u['id'],'manage_employees'): abort(403)
  data={'label':dict((k,n) for k,n,s in SECTIONS)[section],'symbol':dict((k,n) for k,n,s in SECTIONS)[section],'description':DESCRIPTIONS[section],'active':section,'user':u,'business':biz,'sections':SECTIONS,'today':date.today().isoformat(),'module_data':{},'totals':{'income_cents':0,'expense_cents':0,'net_cents':0},'employees':[],'counts':{'active':0,'inactive':0,'on_leave':0},'transactions':[],'invites':[]}
  if section=='dashboard' and biz:
   data['dashboard_data']=DashboardService.get_dashboard_data(biz)
  if section=='finance' and biz:
   data['totals']=FinanceService.get_totals(biz.id); data['transactions']=FinanceService.list_transactions(biz.id)
   if request.method=='POST':
    if not PermissionService.has_permission(biz.id,u['id'],'record_transactions'): abort(403)
    try:
     typ=request.form.get('transaction_type','expense'); desc=request.form.get('description','').strip(); category=request.form.get('category','').strip(); amount=float(request.form.get('amount','0')); txdate=request.form.get('transaction_date','')
     if amount<=0 or amount>100000000: raise ValueError('Enter a valid amount greater than zero.')
     cents=round(amount*100)
     if typ=='income': FinanceService.record_income(biz.id,desc,cents,category,txdate,request.form.get('notes',''))
     else: FinanceService.record_expense(biz.id,desc,cents,category,txdate,request.form.get('notes',''))
     flash('Transaction recorded.','success'); return redirect(url_for('module_page',section='finance'))
    except (ValueError,TypeError) as e: flash(str(e),'error')
  if section=='employees' and biz:
   data['employees']=EmployeeService.list_employees(biz.id); data['counts']=EmployeeService.get_counts(biz.id)
   conn=get_connection(); conn.execute('CREATE TABLE IF NOT EXISTS web_employee_invites (id TEXT PRIMARY KEY,business_id TEXT NOT NULL,employee_id TEXT NOT NULL,code_hash TEXT NOT NULL UNIQUE,expires_at TEXT NOT NULL,created_by TEXT NOT NULL,created_at TEXT NOT NULL,used_at TEXT,used_by TEXT)'); conn.commit()
   data['invites']=conn.execute('SELECT i.id,i.employee_id,i.expires_at,i.used_at,e.full_name,e.email FROM web_employee_invites i JOIN employees e ON e.id=i.employee_id WHERE i.business_id=? ORDER BY i.created_at DESC',(biz.id,)).fetchall(); conn.close()
   if request.method=='POST':
    require_manager(biz); action=request.form.get('action','add')
    try:
     if action=='add':
      emp=EmployeeService.add_employee(acting_user_id=u['id'],business_id=biz.id,full_name=request.form.get('full_name','').strip(),job_title=request.form.get('job_title','').strip(),role=request.form.get('role','employee'),employment_status=request.form.get('employment_status','active'),start_date=request.form.get('start_date',''),email=request.form.get('email','').strip(),phone=request.form.get('phone','').strip())
      flash('Employee record added. Generate a referral code from the employee row when they need access.','success')
     elif action=='status':
      EmployeeService.set_employment_status(acting_user_id=u['id'],business_id=biz.id,employee_id=request.form.get('employee_id',''),employment_status=request.form.get('employment_status','inactive')); flash('Employee status updated.','success')
     elif action=='invite':
      eid=request.form.get('employee_id',''); emp=EmployeeService.get_employee(eid)
      if not emp or emp.business_id!=biz.id: raise ValueError('Employee record not found in this business.')
      code=secrets.token_urlsafe(7).replace('-','').replace('_','').upper()[:10]
      conn=get_connection(); conn.execute('CREATE TABLE IF NOT EXISTS web_employee_invites (id TEXT PRIMARY KEY,business_id TEXT NOT NULL,employee_id TEXT NOT NULL,code_hash TEXT NOT NULL UNIQUE,expires_at TEXT NOT NULL,created_by TEXT NOT NULL,created_at TEXT NOT NULL,used_at TEXT,used_by TEXT)')
      conn.execute('INSERT INTO web_employee_invites(id,business_id,employee_id,code_hash,expires_at,created_by,created_at) VALUES(?,?,?,?,?,?,?)',(str(uuid.uuid4()),biz.id,eid,hashlib.sha256(code.encode()).hexdigest(),(datetime.now()+timedelta(days=7)).isoformat(),u['id'],datetime.utcnow().isoformat())); conn.commit(); conn.close()
      session['new_referral_code']=code; session['new_referral_employee']=emp.full_name; flash('Referral code generated. Copy it now; the full code is shown once. It expires in 7 days.','success')
     return redirect(url_for('module_page',section='employees'))
    except (ValueError,PermissionError) as e: flash(str(e),'error')
  # Generic persisted records give the remaining original navigation modules usable
  # create/list workflows without pretending external integrations exist.
  generic_sections={'payroll','payments','orders','inventory','suppliers','customers','tax','documents','calendar','network','notifications'}
  if section in generic_sections and biz:
   conn=get_connection(); conn.execute('''CREATE TABLE IF NOT EXISTS web_workspace_records (id TEXT PRIMARY KEY,business_id TEXT NOT NULL,module TEXT NOT NULL,title TEXT NOT NULL,category TEXT NOT NULL,status TEXT NOT NULL,due_date TEXT,notes TEXT,created_by TEXT NOT NULL,created_at TEXT NOT NULL)'''); conn.commit()
   if request.method=='POST':
    require_owner(biz)
    title=request.form.get('title','').strip(); category=request.form.get('category','General').strip() or 'General'; status=request.form.get('status','Open').strip() or 'Open'; due_date=request.form.get('due_date','').strip(); notes=request.form.get('notes','').strip()
    if not title: flash('A title is required for this record.','error')
    else:
     conn.execute('INSERT INTO web_workspace_records(id,business_id,module,title,category,status,due_date,notes,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),biz.id,section,title,category,status,due_date,notes,u['id'],datetime.utcnow().isoformat())); conn.commit(); conn.close(); flash(f'{data["label"]} record saved.','success'); return redirect(url_for('module_page',section=section))
   data['module_records']=conn.execute('SELECT title,category,status,due_date,notes,created_at FROM web_workspace_records WHERE business_id=? AND module=? ORDER BY created_at DESC',(biz.id,section)).fetchall(); conn.close()
  if section=='settings' and request.method=='POST':
   action=request.form.get('action')
   if action=='switch_business' and biz:
    try: BusinessService.set_active_business(u['id'],request.form.get('business_id','')); flash('Active business switched.','success')
    except ValueError as e: flash(str(e),'error')
   elif action=='profile': flash('Account profile is shown here; password changes require a dedicated reset flow.','info')
   return redirect(url_for('module_page',section='settings'))
  if section=='business' and request.method=='POST' and biz:
   require_owner(biz)
   fields={k:request.form.get(k,'').strip() for k in ['name','business_type','industry','province','city','phone','email','cipc_number']}
   try: BusinessService.update_business(biz.id,**fields); flash('Business profile updated.','success'); return redirect(url_for('module_page',section='business'))
   except ValueError as e: flash(str(e),'error')
  new_code=session.pop('new_referral_code',None) if section=='employees' else None
  new_employee=session.pop('new_referral_employee',None) if section=='employees' else None
  data.update(new_referral_code=new_code,new_referral_employee=new_employee,all_businesses=BusinessService.get_businesses_for_user(u['id']))
  return render_template('module.html',**data)
 return app
app=create_app()
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')),debug=False)
