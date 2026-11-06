import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { Activity, ArrowLeft, ArrowRight, Bus, Building2, ChevronDown, Eye, EyeOff, FileText, GraduationCap, LayoutDashboard, LockKeyhole, LogOut, Mail, Menu, Search, Settings, ShieldCheck, Users, Wallet, Wrench, BookOpen, Bell, Plus, RefreshCw, X, Upload, Download } from 'lucide-react'

const API = (import.meta as any).env?.VITE_API_URL || ''
type User = { id:number; name:string; email:string; role:string; school_id?:number|null }
type ModuleDef = { key:string; label:string; icon:any; endpoint?:string; fields?:{key:string;label:string;type?:string;required?:boolean}[]; description:string }
const modules: ModuleDef[] = [
 {key:'dashboard',label:'Dashboard',icon:LayoutDashboard,description:'School overview and operational alerts'},
 {key:'parent-portal',label:'Parent Portal',icon:Users,description:'Family view of linked students and fee balances'},
 {key:'chatbot',label:'Help Assistant',icon:Activity,description:'School FAQ and guided help'},
 {key:'approvals',label:'Staff Approvals',icon:Users,description:'Review verified staff account requests'},
 {key:'schools',label:'Schools',icon:Building2,endpoint:'/api/schools',description:'Register schools and assign school-owner accounts',fields:[{key:'name',label:'School name',required:true},{key:'code',label:'School code',required:true}]},
 {key:'students',label:'Students',icon:GraduationCap,endpoint:'/api/students',description:'Profiles, admissions, guardians and student services',fields:[{key:'admission_no',label:'Admission number',required:true},{key:'full_name',label:'Full name',required:true},{key:'class_name',label:'Class'},{key:'section',label:'Section'},{key:'guardian_name',label:'Guardian name'},{key:'guardian_phone',label:'Guardian phone'},{key:'email',label:'Email',type:'email'},{key:'address',label:'Address'},{key:'date_of_birth',label:'Date of birth',type:'date'},{key:'transport_required',label:'Transport required',type:'checkbox'},{key:'hostel_required',label:'Hostel required',type:'checkbox'}]},
 {key:'staff',label:'Staff & HR',icon:Users,endpoint:'/api/staff',description:'Employee profiles, validated HR details and optional staff login accounts',fields:[{key:'employee_no',label:'Employee number (4 uppercase letters + 4 digits)',required:true},{key:'full_name',label:'Full name',required:true},{key:'designation',label:'Designation',type:'designation'},{key:'department',label:'Department (max 32 characters)'},{key:'phone',label:'Phone (+91)',type:'tel',required:true},{key:'email',label:'Gmail address / login username',type:'email',required:true},{key:'salary',label:'Monthly salary (e.g. 25000.00)',type:'text',required:true},{key:'status',label:'Employment status'},{key:'school_id',label:'School',type:'school-select',required:true}]},
 {key:'classes',label:'Classes',icon:BookOpen,endpoint:'/api/classes',description:'Grades, sections, capacity and class teachers',fields:[{key:'name',label:'Class / grade',required:true},{key:'section',label:'Section'},{key:'academic_year',label:'Academic year'},{key:'class_teacher',label:'Class teacher'},{key:'capacity',label:'Capacity',type:'number'}]},
 {key:'vehicles',label:'Transport',icon:Bus,endpoint:'/api/vehicles',description:'Vehicles, routes, drivers and service reminders',fields:[{key:'registration_no',label:'Registration number',required:true},{key:'vehicle_type',label:'Vehicle type'},{key:'route_name',label:'Route'},{key:'capacity',label:'Capacity',type:'number'},{key:'driver_name',label:'Driver name'},{key:'driver_phone',label:'Driver phone'},{key:'insurance_expiry',label:'Insurance expiry',type:'date'},{key:'next_service_date',label:'Next service date',type:'date'}]},
 {key:'hostels',label:'Hostel',icon:Building2,endpoint:'/api/hostels',description:'Hostels, rooms, occupancy and wardens',fields:[{key:'name',label:'Hostel name',required:true},{key:'building',label:'Building'},{key:'room_no',label:'Room number'},{key:'capacity',label:'Capacity',type:'number'},{key:'occupied',label:'Occupied beds',type:'number'},{key:'warden_name',label:'Warden'},{key:'status',label:'Status'}]},
 {key:'documents',label:'Documents',icon:FileText,endpoint:'/api/documents',description:'Document register and verification metadata',fields:[{key:'owner_type',label:'Owner type',required:true},{key:'owner_id',label:'Owner record ID',type:'number',required:true},{key:'category',label:'Category',required:true},{key:'file_name',label:'File name',required:true},{key:'storage_key',label:'Private storage key',required:true},{key:'status',label:'Status'},{key:'expiry_date',label:'Expiry date',type:'date'}]},
 {key:'maintenance',label:'Maintenance',icon:Wrench,endpoint:'/api/maintenance',description:'Requests, work orders and repair tracking',fields:[{key:'title',label:'Request title',required:true},{key:'category',label:'Category'},{key:'location',label:'Location'},{key:'description',label:'Description'},{key:'priority',label:'Priority'},{key:'status',label:'Status'},{key:'assigned_to',label:'Assigned to'},{key:'estimated_cost',label:'Estimated cost',type:'number'}]},
 {
  key: 'fee-structures',
  label: 'Fee Structures',
  icon: Wallet,
  endpoint: '/api/fee-structures',
  description: 'Configure school fees',
  fields: [
    { key: 'name', label: 'Fee name', required: true },
    { key: 'category', label: 'Fee type (tuition, admission, examination, transport, hostel, books, miscellaneous)', required: true },
    { key: 'amount', label: 'Amount (₹)', type: 'number', required: true },
    { key: 'term', label: 'Frequency / term (annual, monthly, quarterly, term-1, term-2)', required: true },
    { key: 'academic_year', label: 'Academic year', required: true },
    { key: 'description', label: 'Description' },
  ],
 },
 {
  key: 'student-fees',
  label: 'Student Fees',
  icon: GraduationCap,
  endpoint: '/api/student-fees',
  description: 'Assign fees and track outstanding balances',
  fields: [
    { key: 'total_amount', label: 'Fee Amount (₹)', type: 'number', required: true },
  ],
 },
 {
  key: 'payments',
  label: 'Fee Payments',
  icon: Wallet,
  description: 'Record payments and access receipts',
 },
 {
  key: 'fee-reports',
  label: 'Fee Reports',
  icon: FileText,
  description: 'View collections, outstanding balances and overdue fees',
 },
]

const roleLabels:Record<string,string> = {
 super_admin:'Developer', user:'Principal', admin:'Principal', principal:'Principal',
 vice_principal:'Vice Principal', teacher:'Teacher', account:'Accounts', accountant:'Accounts',
 clerk:'Clerk', office_assistant:'Office Assistant', librarian:'Librarian',
 lab_assistant:'Lab Assistant', it_administrator:'IT Administrator',
 transport_manager:'Transport Manager', hostel_warden:'Hostel Warden',
 security_guard:'Security Guard', others:'Others', parent:'Parent'
}
const roleDescriptions:Record<string,string> = {
 super_admin:'Platform-wide administration, school onboarding and user management.',
 user:'School leadership workspace for academic and day-to-day operations.',
 admin:'School leadership workspace for academic and day-to-day operations.',
 principal:'School leadership workspace for academic and day-to-day operations.',
 vice_principal:'Academic coordination, student services and staff oversight.',
 teacher:'Classroom-focused access to students, classes and learning records.',
 account:'Finance workspace for fee setup, collections and outstanding balances.',
 accountant:'Finance workspace for fee setup, collections and outstanding balances.',
 clerk:'Front-office student records, fee desk and document handling.',
 office_assistant:'Office administration, staff coordination and student records.',
 librarian:'Student lookup and library-related document support.',
 lab_assistant:'Laboratory support, maintenance requests and documents.',
 it_administrator:'IT operations, staff account support and maintenance.',
 transport_manager:'Transport routes, vehicles and student transport details.',
 hostel_warden:'Hostel occupancy, resident information and maintenance.',
 security_guard:'Front-desk student lookup and essential school information.',
 others:'A focused workspace with school help and shared information.',
 parent:'Family portal for linked students only.'
}
const roleModuleAccess:Record<string,string[]> = {
 super_admin:modules.map(m=>m.key),
 user:['dashboard','chatbot','approvals','students','staff','classes','vehicles','hostels','documents','maintenance','fee-structures','student-fees','payments','fee-reports'],
 admin:['dashboard','chatbot','approvals','students','staff','classes','vehicles','hostels','documents','maintenance','fee-structures','student-fees','payments','fee-reports'],
 principal:['dashboard','chatbot','approvals','students','staff','classes','vehicles','hostels','documents','maintenance','fee-structures','student-fees','payments','fee-reports'],
 vice_principal:['dashboard','chatbot','students','staff','classes','documents','maintenance','fee-reports'],
 teacher:['dashboard','chatbot','students','classes','documents'],
 account:['dashboard','chatbot','students','fee-structures','student-fees','payments','fee-reports'],
 accountant:['dashboard','chatbot','students','fee-structures','student-fees','payments','fee-reports'],
 clerk:['dashboard','chatbot','students','student-fees','payments','documents'],
 office_assistant:['dashboard','chatbot','students','staff','documents','approvals'],
 librarian:['dashboard','chatbot','students','documents'],
 lab_assistant:['dashboard','chatbot','documents','maintenance'],
 it_administrator:['dashboard','chatbot','staff','documents','maintenance','approvals'],
 transport_manager:['dashboard','chatbot','students','vehicles','documents','maintenance'],
 hostel_warden:['dashboard','chatbot','students','hostels','documents','maintenance'],
 security_guard:['dashboard','chatbot','students'],
 others:['dashboard','chatbot'],
 parent:['parent-portal','chatbot']
}
const roleAccent:Record<string,string> = {
 super_admin:'#6654c7', user:'#0f766e', admin:'#0f766e', principal:'#0f766e',
 vice_principal:'#2563a6', teacher:'#39845d', account:'#a66a18', accountant:'#a66a18',
 clerk:'#0d8792', office_assistant:'#4975a8', librarian:'#7354a6',
 lab_assistant:'#357c8b', it_administrator:'#5968b5',
 transport_manager:'#b36b24', hostel_warden:'#9a5c86',
 security_guard:'#64748b', others:'#64748b', parent:'#267d9b'
}
const roleCatalog = Object.entries(roleLabels).filter(([key])=>key!=='user'&&key!=='admin'&&key!=='accountant').map(([key,label])=>({
 role:label, roleKey:key,
 scope:roleDescriptions[key],
 level:key==='super_admin'?'Platform access':key==='parent'?'Linked-student access':'Role workspace'
}))

const DEMO_USERS = [
 {label:'Developer',email:'demo.developer@jovoo.in',schoolCode:''},
 {label:'Principal',email:'demo.principal@jovoo.in',schoolCode:'DEMO-SCHOOL'},
 {label:'Vice Principal',email:'demo.viceprincipal@jovoo.in',schoolCode:'DEMO-SCHOOL'},
 {label:'Teacher',email:'demo.teacher@jovoo.in',schoolCode:'DEMO-SCHOOL'},
 {label:'Accounts',email:'demo.accounts@jovoo.in',schoolCode:'DEMO-SCHOOL'},
 {label:'Clerk',email:'demo.clerk@jovoo.in',schoolCode:'DEMO-SCHOOL'},
 {label:'Office Assistant',email:'demo.officeassistant@jovoo.in',schoolCode:'DEMO-SCHOOL'},
 {label:'Librarian',email:'demo.librarian@jovoo.in',schoolCode:'DEMO-SCHOOL'},
 {label:'Lab Assistant',email:'demo.labassistant@jovoo.in',schoolCode:'DEMO-SCHOOL'},
 {label:'IT Administrator',email:'demo.itadmin@jovoo.in',schoolCode:'DEMO-SCHOOL'},
 {label:'Transport Manager',email:'demo.transport@jovoo.in',schoolCode:'DEMO-SCHOOL'},
 {label:'Hostel Warden',email:'demo.warden@jovoo.in',schoolCode:'DEMO-SCHOOL'},
 {label:'Security Guard',email:'demo.security@jovoo.in',schoolCode:'DEMO-SCHOOL'},
 {label:'Others',email:'demo.others@jovoo.in',schoolCode:'DEMO-SCHOOL'},
 {label:'Parent',email:'demo.parent@jovoo.in',schoolCode:'DEMO-SCHOOL'},
]
const DEMO_MODE = (import.meta as any).env?.VITE_ENABLE_DEMO_MODE === 'true'

const money = (n:number) => new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(n || 0)

function Login({onLogin}:{onLogin:(token:string,user:User)=>void}) {
 const [mode,setMode]=useState<'signin'|'school'|'staff'|'verify'|'forgot'|'reset'|'mfa'>('signin')
 const [values,setValues]=useState({name:'',email:'',password:'',school_name:'',school_code:'',role:'principal',code:''})
 const [mfaToken,setMfaToken]=useState('')
 const [error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false),[showPassword,setShowPassword]=useState(false)
 const set=(key:string,value:string)=>setValues(old=>({...old,[key]:value}))
 async function call(path:string,body:Record<string,string>){const r=await fetch(`${API}${path}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const d=await r.json().catch(()=>null);if(!r.ok)throw new Error(d?.detail||d?.message||`Request failed (${r.status})`);return d}
 async function submit(e:FormEvent<HTMLFormElement>){e.preventDefault();setBusy(true);setError('');setNotice('');try{
   if(mode==='signin'){const loginPayload:Record<string,string>={email:values.email,password:values.password};if(values.school_code.trim())loginPayload.school_code=values.school_code.trim().toUpperCase();const d=await call('/api/auth/login',loginPayload);if(d.mfa_required){setMfaToken(d.mfa_token);setNotice(d.message);setMode('mfa');return}if(!d?.access_token||!d?.user)throw new Error('Invalid login response');onLogin(d.access_token,d.user);return}
   if(mode==='mfa'){const d=await call('/api/auth/verify-mfa',{mfa_token:mfaToken,code:values.code});if(!d?.access_token||!d?.user)throw new Error('Invalid MFA response');onLogin(d.access_token,d.user);return}
  if(mode==='school'){const d=await call('/api/auth/register-school',values);setNotice(d.message);setMode('verify')}
  else if(mode==='staff'){const d=await call('/api/auth/register-staff',values);setNotice(d.message);setMode('verify')}
  else if(mode==='verify'){const d=await call('/api/auth/verify-email',{email:values.email,code:values.code});setNotice(d.message);setMode('signin')}
  else if(mode==='forgot'){const d=await call('/api/auth/forgot-password',{email:values.email});setNotice(d.message);setMode('reset')}
  else if(mode==='reset'){const d=await call('/api/auth/reset-password',{email:values.email,code:values.code,password:values.password});setNotice(d.message);setMode('signin')}
 }catch(err:any){setError(err.message||'Unable to complete request')}finally{setBusy(false)}}
 const titles={signin:'Welcome back',mfa:'Verify your sign-in',school:'Register your school',staff:'Join your school',verify:'Verify your email',forgot:'Recover password',reset:'Create a new password'}
 const descriptions={signin:'Enter your email and password. School users must also enter their school code.',mfa:'Enter the six-digit security code sent to your email address.',school:'Create your school and its first Principal account.',staff:'Register under an existing school. Approval by a school user is required.',verify:'Enter the six-digit code sent to your email.',forgot:'Enter your registered email to request a reset code.',reset:'Verify the code and choose a new password.'}
 const isPasswordMode=['signin','school','staff','reset'].includes(mode)
 const passwordLabel=mode==='reset'?'New password':'Password'
 const submitLabel=mode==='signin'?'Continue securely':mode==='mfa'?'Verify and sign in':mode==='school'?'Create school account':mode==='staff'?'Request staff account':mode==='verify'?'Verify email':mode==='forgot'?'Send reset code':'Reset password'
 return <div className="auth-page">
  <aside className="auth-showcase">
   <div className="auth-showcase-inner">
    <div className="auth-brand"><div className="auth-brand-icon"><GraduationCap size={25}/></div><span>SchoolOS</span></div>
    <div className="auth-showcase-copy">
     <span className="auth-kicker">SCHOOL MANAGEMENT PLATFORM</span>
     <h2>Everything your school needs.<br/><em>All in one place.</em></h2>
     <p>Bring your school community, daily operations and financial workflows together in one secure workspace.</p>
    </div>
    <div className="auth-visual" aria-hidden="true">
     <div className="auth-orbit orbit-one"/><div className="auth-orbit orbit-two"/>
     <div className="auth-campus-card"><div className="campus-sun"/><div className="campus-building"><div className="campus-roof"/><div className="campus-columns"><i/><i/><i/><i/></div><div className="campus-door"/></div><div className="campus-ground"/></div>
     <div className="auth-float-card float-students"><Users size={17}/><span><strong>One school community</strong><small>Students · Staff · Families</small></span></div>
     <div className="auth-float-card float-secure"><ShieldCheck size={19}/><span><strong>Secure workspace</strong><small>Role-based access</small></span></div>
    </div>
    <div className="auth-showcase-foot"><span><ShieldCheck size={14}/> Built for modern school teams</span><span>Learn · Manage · Grow</span></div>
   </div>
  </aside>
  <main className="auth-main">
   <div className="auth-mobile-brand"><div className="auth-brand-icon"><GraduationCap size={22}/></div><strong>SchoolOS</strong></div>
   <section className="auth-form-shell">
    <form className="auth-form-card" onSubmit={submit}>
     <div className="auth-form-top"><span className="auth-step-icon">{mode==='school'?<Building2 size={20}/>:mode==='staff'?<Users size={20}/>:mode==='verify'?<ShieldCheck size={20}/>:<GraduationCap size={20}/>}</span><span className="auth-form-context">{mode==='school'?'SCHOOL SETUP':mode==='staff'?'STAFF REGISTRATION':mode==='signin'?'YOUR SCHOOL WORKSPACE':'ACCOUNT ACCESS'}</span></div>
     <p className="eyebrow">SCHOOL MANAGEMENT PLATFORM</p>
     <h1>{titles[mode]}</h1>
     <p className="auth-intro">{descriptions[mode]}</p>
     {mode==='school'&&<>
      <div className="auth-section-label"><span>01</span><div><strong>First user account</strong><small>Your first standard school user</small></div></div>
      <div className="auth-field"><label htmlFor="admin-name">Full name</label><input id="admin-name" value={values.name} onChange={e=>set('name',e.target.value)} placeholder="Enter the user's full name" autoComplete="name" required/></div>
      <div className="auth-section-label auth-section-admin"><span>02</span><div><strong>School information</strong><small>Tell us about your institution</small></div></div>
      <div className="auth-field"><label htmlFor="school-name">School name</label><input id="school-name" value={values.school_name} onChange={e=>set('school_name',e.target.value)} placeholder="e.g. Green Valley School" autoComplete="organization" required/></div>
      <div className="auth-field"><label htmlFor="school-code">School code</label><input id="school-code" value={values.school_code} onChange={e=>set('school_code',e.target.value.toUpperCase())} placeholder="Create a unique school code" required/><small>This code will identify your school for staff registration.</small></div>
     </>}
     {mode==='staff'&&<>
      <div className="auth-field"><label htmlFor="staff-name">Full name</label><input id="staff-name" value={values.name} onChange={e=>set('name',e.target.value)} placeholder="Enter your full name" autoComplete="name" required/></div>
      <div className="auth-field"><label htmlFor="staff-school-code">School code</label><input id="staff-school-code" value={values.school_code} onChange={e=>set('school_code',e.target.value.toUpperCase())} placeholder="Enter your school's code" required/></div>
      <div className="auth-field"><label htmlFor="staff-role">Account type</label><select id="staff-role" value={values.role} onChange={e=>set('role',e.target.value)}>{Object.entries(roleLabels).filter(([key])=>key!=='super_admin'&&key!=='parent'&&key!=='user'&&key!=='admin'&&key!=='accountant').map(([key,label])=><option key={key} value={key}>{label}</option>)}<option value="parent">Parent (linked students only)</option></select></div>
     </>}
     {mode==='signin'&&<div className="auth-field"><label htmlFor="login-school-code">School code <span className="muted">(school accounts only)</span></label><input id="login-school-code" value={values.school_code} onChange={e=>set('school_code',e.target.value.toUpperCase())} placeholder="Leave blank for Developer" autoCapitalize="characters"/><small>Leave this blank to sign in as Developer. All school users must enter their school's code.</small></div>}
      {['signin','school','staff','verify','forgot','reset'].includes(mode)&&<div className="auth-field"><label htmlFor="auth-email">Email address</label><div className="auth-input-wrap"><Mail size={17}/><input id="auth-email" type="email" value={values.email} onChange={e=>set('email',e.target.value)} placeholder="you@school.com" required autoComplete="email"/></div></div>}
     {isPasswordMode&&<div className="auth-field"><label htmlFor="auth-password">{passwordLabel}</label><div className="auth-input-wrap"><LockKeyhole size={17}/><input id="auth-password" type={showPassword?'text':'password'} value={values.password} onChange={e=>set('password',e.target.value)} placeholder={mode==='signin'?'Enter your password':'Create a strong password'} minLength={mode==='signin'?undefined:12} required autoComplete={mode==='signin'?'current-password':'new-password'}/><button className="auth-password-toggle" type="button" onClick={()=>setShowPassword(v=>!v)} aria-label={showPassword?'Hide password':'Show password'}>{showPassword?<EyeOff size={17}/>:<Eye size={17}/>}</button></div>{mode!=='signin'&&<small className="auth-help">Use at least 12 characters.</small>}</div>}
     {['verify','reset','mfa'].includes(mode)&&<div className="auth-field"><label htmlFor="auth-code">{mode==='mfa'?'Sign-in security code':'Email verification / reset code'}</label><div className="auth-input-wrap"><ShieldCheck size={17}/><input id="auth-code" inputMode="numeric" pattern="[0-9]{6}" maxLength={6} value={values.code} onChange={e=>set('code',e.target.value.replace(/\D/g,'').slice(0,6))} placeholder="6-digit code" required/></div></div>}
     {error&&<div className="error auth-message" role="alert">{error}</div>}{notice&&<div className="success auth-message" role="status">{notice}</div>}
     <button className="auth-submit" disabled={busy}>{busy?'Please wait…':<>{submitLabel}<ArrowRight size={17}/></>}</button>
     <div className="auth-links">{mode==='signin'?<><button type="button" onClick={()=>{setMode('school');setError('');setNotice('')}}>Register a school</button><button type="button" onClick={()=>{setMode('staff');setError('');setNotice('')}}>Register as staff</button><button type="button" onClick={()=>{setMode('forgot');setError('');setNotice('')}}>Forgot password?</button></>:<><button type="button" onClick={()=>{setMode('signin');setError('');setNotice('')}}><ArrowLeft size={14}/> Back to sign in</button>{mode==='mfa'&&<button type="button" onClick={()=>{setMode('signin');setMfaToken('');set('code','');setError('');setNotice('')}}>Start over</button>}{mode==='verify'&&<button type="button" onClick={async()=>{try{const d=await call('/api/auth/resend-verification',{email:values.email});setNotice(d.message);setError('')}catch(e:any){setError(e.message)}}}>Resend code</button>}</>}</div>
    </form>
    <p className="auth-copyright">© {new Date().getFullYear()} SchoolOS · School operations platform</p>
   </section>
  </main>
 </div>
}

function ParentPortal({request}:{request:(url:string,options?:RequestInit)=>Promise<any>}) {
 const [children,setChildren]=useState<any[]>([]),[childId,setChildId]=useState(''),[fees,setFees]=useState<any[]>([]),[error,setError]=useState('');
 useEffect(()=>{request('/api/parent/children').then((data:any[])=>{setChildren(data);if(data.length)setChildId(String(data[0].id))}).catch((e:any)=>setError(e.message))},[]);
 useEffect(()=>{if(childId)request('/api/parent/children/'+childId+'/fees').then(setFees).catch((e:any)=>setError(e.message));else setFees([])},[childId]);
 return <div className="panel"><div className="panel-heading"><div><h3>Family Portal</h3><p>View information for students linked to your parent account.</p></div><Users size={20}/></div>{error&&<div className="error">{error}</div>}{children.length===0?<div className="empty-state"><strong>No student profiles linked</strong><p>Ask your school administrator to link your parent account to your child.</p></div>:<><label className="parent-child-select">Student<select value={childId} onChange={e=>setChildId(e.target.value)}>{children.map(c=><option key={c.id} value={c.id}>{c.full_name} · {c.admission_no} · {c.class_name} {c.section}</option>)}</select></label><div className="table-wrap"><table><thead><tr><th>Fee category</th><th>Academic year</th><th>Total</th><th>Paid</th><th>Balance</th><th>Status</th></tr></thead><tbody>{fees.map(f=><tr key={f.fee_id}><td>{f.category}</td><td>{f.academic_year}</td><td>{money(f.total)}</td><td>{money(f.paid)}</td><td><strong>{money(f.balance)}</strong></td><td><span className="status-badge">{f.status}</span></td></tr>)}{!fees.length&&<tr><td colSpan={6}>No fee records found.</td></tr>}</tbody></table></div></>}</div>
}
function HelpAssistant({request}:{request:(url:string,options?:RequestInit)=>Promise<any>}) {
 const [question,setQuestion]=useState(''),[messages,setMessages]=useState<{q:string,a:string}[]>([]),[busy,setBusy]=useState(false),[error,setError]=useState('');
 async function ask(e:FormEvent<HTMLFormElement>){e.preventDefault();if(!question.trim()||busy)return;const q=question.trim();setQuestion('');setBusy(true);setError('');try{const result=await request('/api/chatbot/faq',{method:'POST',body:JSON.stringify({question:q})});setMessages(old=>[...old,{q,a:result.answer}])}catch(err:any){setError(err.message)}finally{setBusy(false)}}
 return <div className="panel"><div className="panel-heading"><div><h3>SchoolOS Help Assistant</h3><p>Ask common questions about school workflows. Answers are from approved FAQ content.</p></div><Activity size={20}/></div><div className="chat-faq-list">{messages.map((m,i)=><div className="chat-faq-item" key={i}><div className="chat-user-question">{m.q}</div><div className="chat-assistant-answer">{m.a}</div></div>)}{!messages.length&&<div className="empty-state"><strong>How can I help?</strong><p>Try “How do I pay fees?”, “How do I reset my password?”, or “Where is transport information?”</p></div>}</div>{error&&<div className="error">{error}</div>}<form className="chat-faq-form" onSubmit={ask}><input value={question} maxLength={500} onChange={e=>setQuestion(e.target.value)} placeholder="Ask SchoolOS…" /><button className="primary" disabled={busy||!question.trim()}>{busy?'Thinking…':'Ask'}</button></form></div>
}
function App(){
 const [token,setToken]=useState(localStorage.getItem('erp_token')||'')
 const [user,setUser]=useState<User|null>(null)
 const [demoTestingActive,setDemoTestingActive]=useState(sessionStorage.getItem('demo_testing_active')==='true')
 const [demoTargetEmail,setDemoTargetEmail]=useState('')
 const [demoSwitchPassword,setDemoSwitchPassword]=useState('')
 const [demoSwitchBusy,setDemoSwitchBusy]=useState(false)
 const [demoSwitchError,setDemoSwitchError]=useState('')
 const [active,setActive]=useState('dashboard')
 const [mobileNav,setMobileNav]=useState(false)
 const [showWorkspaceFlow,setShowWorkspaceFlow]=useState(false)
 const [rows,setRows]=useState<any[]>([])
 const [stats,setStats]=useState<any>({})
 const [loading,setLoading]=useState(false)
 const [error,setError]=useState('')
 const [query,setQuery]=useState('')
 const [showForm,setShowForm]=useState(false)
 const [form,setForm]=useState<Record<string,any>>({})
 const [editingRecordId,setEditingRecordId]=useState<number|null>(null)
 const [notice,setNotice]=useState('')
 const [importing,setImporting]=useState(false)
 const [importSchoolId,setImportSchoolId]=useState('')
 const [studentSearch,setStudentSearch]=useState('')
 const [studentResults,setStudentResults]=useState<any[]>([])
 const [selectedStudent,setSelectedStudent]=useState<any|null>(null)
 const [reportData,setReportData]=useState<any>({collected:0,outstanding:0,chart:[],recent_payments:[]})
 const [reportMonth,setReportMonth]=useState('')
 const [reportYear,setReportYear]=useState(String(new Date().getFullYear()))
 const [reportSchool,setReportSchool]=useState('')
 const [schools,setSchools]=useState<any[]>([])
 const [ownerUsers,setOwnerUsers]=useState<any[]>([])
 const [ownerUserId,setOwnerUserId]=useState('')
 const [ownerSchoolId,setOwnerSchoolId]=useState('')
 const [feeDues,setFeeDues]=useState<any[]>([])
 const [paymentFeeId,setPaymentFeeId]=useState('')
 const [paymentAmount,setPaymentAmount]=useState('')
 const [paymentMethod,setPaymentMethod]=useState('cash')
 const allowedModuleKeys=roleModuleAccess[user?.role||'user']||roleModuleAccess.user
 const availableModules=modules.filter(m=>allowedModuleKeys.includes(m.key))
 const selected=modules.find(m=>m.key===active)||modules[0]
 const roleLabel=roleLabels[user?.role||'user']||'School User'
 const hasModule=(key:string)=>allowedModuleKeys.includes(key)
 const authHeaders=useMemo(()=>({'Authorization':`Bearer ${token}`,'Content-Type':'application/json'}),[token])
 useEffect(()=>{if(user){const first=roleModuleAccess[user.role]?.[0]||'dashboard';if(!roleModuleAccess[user.role]?.includes(active))setActive(first)}},[user])
 useEffect(()=>{if(!token)return;fetch(`${API}/api/auth/me`,{headers:authHeaders}).then(r=>r.ok?r.json():Promise.reject()).then(setUser).catch(()=>{localStorage.removeItem('erp_token');setToken('');setUser(null)})},[token,authHeaders])
 async function request(url:string,options:RequestInit={}){const r=await fetch(`${API}${url}`,{...options,headers:{...authHeaders,...options.headers}});if(r.status===401){logout();throw new Error('Session expired. Please sign in again.')}const raw=await r.text();let data:any={};try{data=raw?JSON.parse(raw):{}}catch{data={}}if(!r.ok){const detail=data.detail||data.message||raw.slice(0,240);throw new Error((detail||'API request failed')+` (HTTP ${r.status}: ${options.method||'GET'} ${url})`)}return data}
 function logout(){localStorage.removeItem('erp_token');setToken('');setUser(null);setRows([]);setDemoTestingActive(false);setDemoTargetEmail('');setDemoSwitchPassword('');setDemoSwitchError('');sessionStorage.removeItem('demo_testing_active')}
 function handleLogin(t:string,u:User){localStorage.setItem('erp_token',t);setToken(t);setUser(u);const canTest=DEMO_MODE&&u.role==='super_admin'&&u.email==='demo.developer@jovoo.in';setDemoTestingActive(canTest);if(canTest)sessionStorage.setItem('demo_testing_active','true');else sessionStorage.removeItem('demo_testing_active');setActive('dashboard')}
 async function switchDemoAccount(email:string,passwordOverride?:string){
  const demo=DEMO_USERS.find(item=>item.email===email)
  const password=passwordOverride||demoSwitchPassword
  if(!demo||!password){setDemoSwitchError('Choose a demo role and enter the shared demo password.');return}
  setDemoSwitchBusy(true);setDemoSwitchError('')
  try{
   const response=await fetch(API+'/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:demo.email,password:password,...(demo.schoolCode?{school_code:demo.schoolCode}:{})})})
   const data=await response.json().catch(()=>null)
   if(!response.ok||!data?.access_token||!data?.user)throw new Error(data?.detail||'Unable to open that demo role.')
   localStorage.setItem('erp_token',data.access_token);setToken(data.access_token);setUser(data.user);setActive('dashboard');setDemoTargetEmail('');setDemoSwitchPassword('');setDemoSwitchError('')
  }catch(err:any){setDemoSwitchError(err.message||'Unable to switch demo role.')}finally{setDemoSwitchBusy(false)}
 }
 async function recordFeePayment(){if(!paymentFeeId||!paymentAmount)return;try{await request('/api/student-fees/'+paymentFeeId+'/payments',{method:'POST',body:JSON.stringify({amount:Number(paymentAmount),payment_method:paymentMethod})});setNotice('Fee payment recorded successfully');setPaymentAmount('');await load()}catch(e:any){setError(e.message)}}
 async function assignSchoolOwner(){if(!ownerUserId||!ownerSchoolId)return;try{await request('/api/users/'+ownerUserId+'/school',{method:'PATCH',body:JSON.stringify({school_id:Number(ownerSchoolId)})});setNotice('School owner assigned successfully');setOwnerUsers(await request('/api/users'))}catch(e:any){setError(e.message)}}

 function downloadStudentTemplate(){const csv="admission_no,full_name,class_name,section,guardian_name,guardian_phone,email,address,date_of_birth,transport_required,hostel_required,status\nADM001,Student Name,Class 1,A,Parent Name,9876543210,student@example.com,Hyderabad,2015-04-20,false,false,active\n";const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8;'}));const link=document.createElement('a');link.href=url;link.download='campusflow-student-template.csv';link.click();URL.revokeObjectURL(url)}
 async function importStudents(e:any){const file=e.target.files?.[0] as File|undefined;e.target.value='';if(!file)return;setImporting(true);setError('');setNotice('');try{const body=new FormData();body.append('file',file);if(user?.role==='super_admin'){if(!importSchoolId){setError('Select a school before importing students.');setImporting(false);return}body.append('school_id',importSchoolId)}const response=await fetch(API+'/api/students/import',{method:'POST',headers:{Authorization:'Bearer '+token},body});const data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(data.detail||'Import failed ('+response.status+')');setNotice('Import complete: '+data.created+' students added, '+data.skipped+' skipped.'+(data.errors?.length?' First issue: row '+data.errors[0].row+' — '+data.errors[0].error:''));await load()}catch(err:any){setError(err.message||'Student import failed')}finally{setImporting(false)}}
 async function importModule(e:any){const file=e.target.files?.[0] as File|undefined;e.target.value='';if(!file)return;if(user?.role==='super_admin'&&!importSchoolId){setError('Select a school before importing records.');return}setImporting(true);setError('');setNotice('');try{const body=new FormData();body.append('file',file);if(user?.role==='super_admin')body.append('school_id',importSchoolId);const response=await fetch(API+'/api/'+active+'/import',{method:'POST',headers:{Authorization:'Bearer '+token},body});const data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(data.detail||'Import failed ('+response.status+')');setNotice('Import complete: '+data.created+' '+selected.label.toLowerCase()+' added, '+data.skipped+' skipped.'+(data.errors?.length?' First issue: row '+data.errors[0].row+' — '+data.errors[0].error:''));await load()}catch(err:any){setError(err.message||'Import failed')}finally{setImporting(false)}}
 async function load(){if(!user)return;setLoading(true);setError('');try{if(active==='dashboard'){
      setStats(await request('/api/dashboard'));setRows([]);
      if(hasModule('fee-reports')){
       const year=String(new Date().getFullYear());
       const results=await Promise.allSettled([request('/api/fee-reports?year='+year),request('/api/fee-dues')]);
       if(results[0].status==='fulfilled')setReportData(results[0].value);
       if(results[1].status==='fulfilled')setFeeDues(results[1].value);
      }
     }else if(active==='parent-portal'||active==='chatbot'){setRows([])}else if(active==='approvals'){setRows(await request('/api/auth/pending-users'))}else if(active==='payments'){setFeeDues(await request('/api/fee-dues'));setRows([])}else if(active==='fee-reports'){const params=new URLSearchParams({year:reportYear});if(reportMonth)params.set('month',reportMonth);if(user.role==='super_admin'&&reportSchool)params.set('school_id',reportSchool);setReportData(await request('/api/fee-reports?'+params.toString()));setRows([])}else if(selected.endpoint){setRows(await request(selected.endpoint+'?q='+encodeURIComponent(query)))}}catch(e:any){setError(e.message)}finally{setLoading(false)}}
 useEffect(()=>{if(user&&active!=='fee-reports')load()},[active,user,query])
 useEffect(()=>{if(user&&active==='fee-reports')load()},[active,user,reportMonth,reportYear,reportSchool])
 useEffect(()=>{if(user)request('/api/schools').then(setSchools).catch(()=>setSchools([]))},[user,token])
 useEffect(()=>{if(user?.role==='super_admin'&&active==='schools')request('/api/users').then(setOwnerUsers).catch(()=>setOwnerUsers([]))},[user,active,token])
 useEffect(()=>{let cancelled=false;const timer=setTimeout(async()=>{if(!user||studentSearch.trim().length<2){setStudentResults([]);return}try{const found=await request('/api/students?q='+encodeURIComponent(studentSearch.trim()));if(!cancelled)setStudentResults(found)}catch{if(!cancelled)setStudentResults([])}},250);return()=>{cancelled=true;clearTimeout(timer)}},[studentSearch,user,token])
 function chooseStudent(student:any){setSelectedStudent(student);setStudentSearch('');setStudentResults([]);if(active==='student-fees'){setForm({total_amount:''});setShowForm(true)}if(active==='documents'){setForm(current=>({...current,owner_type:'student',owner_id:student.id}));setShowForm(true)}}
 async function save(e: FormEvent<HTMLFormElement>) {e.preventDefault();try{const payload={...form};for(const f of selected.fields||[]){if((f.type==='number'||f.type==='school-select')&&payload[f.key]!==''&&payload[f.key]!=null)payload[f.key]=Number(payload[f.key]);if(f.type==='checkbox')payload[f.key]=Boolean(payload[f.key]);if(payload[f.key]==='')delete payload[f.key]}if(active==='student-fees'){if(!selectedStudent)throw new Error('Search and select a student before adding a fee.');payload.student_id=selectedStudent.id;payload.category='tuition';payload.academic_year=`${new Date().getFullYear()}-${String(new Date().getFullYear()+1).slice(-2)}`;payload.term='annual';payload.discount=0;payload.description='Tuition fee'}const created=await request(selected.endpoint!+(editingRecordId?'/'+editingRecordId:''),{method:editingRecordId?'PUT':'POST',body:JSON.stringify(payload)});if(active==='students')setSelectedStudent(created);setShowForm(false);setForm({});setEditingRecordId(null);setNotice(editingRecordId?'Record updated successfully':(active==='staff'&&payload.create_account?'Staff record and login account created successfully':'Record created successfully'));if(active==='schools')setSchools(await request('/api/schools'));await load()}catch(e:any){setError(e.message)}}
 async function deleteStaff(row:any){if(!window.confirm('Delete staff record '+row.employee_no+' — '+row.full_name+'? This cannot be undone.'))return;try{await request('/api/staff/'+row.id,{method:'DELETE'});setNotice('Staff record deleted successfully');await load()}catch(e:any){setError(e.message)}}
 if(!token||!user)return <Login onLogin={handleLogin}/>
 const Icon=selected.icon
 return <div className="app-shell role-themed" style={{'--role-accent':roleAccent[user.role]||'#0f766e'} as any}>
  <aside className={`sidebar ${mobileNav?'open':''}`}><div className="brand"><div className="brand-mark"><GraduationCap/></div><div><strong>SchoolOS</strong><span>SCHOOL MANAGEMENT PLATFORM</span></div><button className="icon-button mobile-close" onClick={()=>setMobileNav(false)}><X/></button></div><div className="school-switch school-identity"><div className="school-avatar"><GraduationCap size={19}/></div><div className="school-switch-copy"><span className="school-switch-kicker">ACTIVE SCHOOL</span><strong>{schools.find(sc=>sc.id===user.school_id)?.name||"My School"}</strong><span className="school-switch-action">School workspace</span></div></div><div className="workspace-nav-heading"><div><span className="nav-label">WORKSPACE</span><small>Modules for your role</small></div><span className="workspace-module-count">{availableModules.length}</span></div><nav>{availableModules.map(m=>{const I=m.icon;return <button key={m.key} className={`nav-item ${active===m.key?'selected':''}`} onClick={()=>{setActive(m.key);setMobileNav(false);setShowForm(false)}}><I size={18}/><span>{m.label}</span></button>})}</nav><div className="sidebar-bottom"><div className="user-mini"><div className="avatar">{user.name.slice(0,1).toUpperCase()}</div><div><strong>{user.name}</strong><span>{roleLabel}</span></div><button className="icon-button" title="Sign out" onClick={logout}><LogOut size={17}/></button></div></div></aside>
  <main className="main"><header className="topbar"><button className="icon-button mobile-menu" onClick={()=>setMobileNav(true)}><Menu/></button><div className="crumb">Workspace <span>/</span> <strong>{selected.label}</strong></div><span className="role-chip">{roleLabel}</span>{DEMO_MODE&&demoTestingActive&&user.role!=="super_admin"&&<button className="secondary" onClick={()=>{const password=window.prompt("Enter the shared demo password to return to Developer");if(password)switchDemoAccount("demo.developer@jovoo.in",password)}}>Return to Developer</button>}<div className="top-actions">{user.role!=='parent'&&<div className="student-global-search"><Search size={16}/><input aria-label="Find student across modules" placeholder="Find student by name / admission no." value={studentSearch} onChange={e=>setStudentSearch(e.target.value)}/>{studentResults.length>0&&<div className="student-search-results">{studentResults.map(s=><button type="button" key={s.id} onClick={()=>chooseStudent(s)}><strong>{s.full_name}</strong><span>{s.admission_no} · {s.class_name||'Class not set'} {s.section||''}</span></button>)}</div>}</div>}<div className="online-pill"><span/> System online</div><button className="icon-button" title="Notifications"><Bell size={19}/></button><div className="avatar">{user.name.slice(0,1).toUpperCase()}</div></div></header>
  <div className="content">{selectedStudent&&<div className="selected-student-context"><div><strong>Selected student: {selectedStudent.full_name}</strong><span>{selectedStudent.admission_no} · {selectedStudent.class_name||'Class not set'} {selectedStudent.section||''} · Guardian: {selectedStudent.guardian_name||'—'} · Phone: {selectedStudent.guardian_phone||'—'}</span></div><button type="button" className="secondary" onClick={()=>setSelectedStudent(null)}>Clear student</button></div>}<div className="page-heading"><div><p className="eyebrow">SCHOOL ERP / {selected.key.toUpperCase()}</p><h1>{selected.label}</h1><p className="muted">{selected.description}</p></div><div className="heading-actions"><button className="secondary" onClick={load}><RefreshCw size={16}/> Refresh</button>{active==='students'&&user.role!=='parent'&&<>{user.role==='super_admin'&&<select aria-label="Import school" value={importSchoolId} onChange={e=>setImportSchoolId(e.target.value)}><option value="">Select school</option>{schools.map(sc=><option key={sc.id} value={sc.id}>{sc.name}</option>)}</select>}<button className="secondary" onClick={downloadStudentTemplate}><Download size={16}/> Template</button><input id="student-bulk-file" type="file" accept=".csv,.xlsx" style={{display:"none"}} onChange={importStudents}/><button className="secondary" disabled={importing||(user.role==='super_admin'&&!importSchoolId)} onClick={()=>document.getElementById('student-bulk-file')?.click()}><Upload size={16}/> {importing?'Uploading…':'Bulk upload'}</button></>}{['staff','classes','vehicles','hostels','maintenance','fee-structures'].includes(active)&&user.role!=='parent'&&<>{user.role==='super_admin'&&<select aria-label="Import school" value={importSchoolId} onChange={e=>setImportSchoolId(e.target.value)}><option value="">Select school</option>{schools.map(sc=><option key={sc.id} value={sc.id}>{sc.name}</option>)}</select>}<input id="module-bulk-file" type="file" accept=".csv,.xlsx" style={{display:"none"}} onChange={importModule}/><button className="secondary" disabled={importing||(user.role==='super_admin'&&!importSchoolId)} onClick={()=>document.getElementById('module-bulk-file')?.click()}><Upload size={16}/> {importing?'Importing…':'Import CSV / Excel'}</button></>}{selected.endpoint&&(user.role!=='super_admin'||active==='schools'||active==='staff')&&<button className="primary" onClick={()=>{setEditingRecordId(null);setForm(active==='student-fees'&&selectedStudent?{student_id:selectedStudent.id,term:'annual',discount:0}:{});setShowForm(true)}}><Plus size={17}/> Add record</button>}</div></div>
  {error&&<div className="error banner"><span>{error}</span><button onClick={()=>setError('')}><X size={16}/></button></div>}{notice&&<div className="success banner">{notice}<button onClick={()=>setNotice('')}><X size={16}/></button></div>}
  {active==='parent-portal'?<ParentPortal request={request}/>:active==='chatbot'?<HelpAssistant request={request}/>:active==='dashboard'?<>
    {DEMO_MODE&&demoTestingActive&&user.role==='super_admin'&&<div className="panel demo-role-testing-panel"><div className="panel-heading"><div><h3>Role testing workspace</h3><p>Open a real demo account to verify its dashboard and navigation. This does not change normal user access.</p></div><ShieldCheck size={20}/></div><div className="quick-grid"><label className="auth-field">Demo role<select value={demoTargetEmail} onChange={e=>setDemoTargetEmail(e.target.value)}><option value="">Choose a role to test…</option>{DEMO_USERS.filter(demo=>demo.email!=='demo.developer@jovoo.in').map(demo=><option key={demo.email} value={demo.email}>{demo.label}</option>)}</select></label><label className="auth-field">Shared demo password<input type="password" autoComplete="off" value={demoSwitchPassword} onChange={e=>setDemoSwitchPassword(e.target.value)} placeholder="Enter the password printed by the seeder"/></label><div><button className="primary" disabled={demoSwitchBusy||!demoTargetEmail||!demoSwitchPassword} onClick={()=>switchDemoAccount(demoTargetEmail)}>{demoSwitchBusy?'Opening workspace…':'Open selected role'}</button></div></div>{demoSwitchError&&<div className="error auth-message" role="alert">{demoSwitchError}</div>}</div>}
    <div className="welcome-panel"><div><span className="welcome-tag">{roleLabel.toUpperCase()} WORKSPACE</span><h2>Good to see you, {user.name.split(' ')[0]}</h2><p>{roleDescriptions[user.role]||'Your school workspace and assigned daily tasks.'} Use the options on the left to get started.</p></div><div className="welcome-icon"><GraduationCap size={44}/></div></div>
    <div className="stat-grid">{[{label:'Total students',key:'students',target:'students',icon:GraduationCap,tone:'teal'},{label:'Staff members',key:'staff',target:'staff',icon:Users,tone:'blue'},{label:'Classes & sections',key:'classes',target:'classes',icon:BookOpen,tone:'purple'},{label:'Transport vehicles',key:'vehicles',target:'vehicles',icon:Bus,tone:'orange'},{label:'Hostel rooms',key:'hostel_rooms',target:'hostels',icon:Building2,tone:'pink'},{label:'Open maintenance',key:'open_maintenance',target:'maintenance',icon:Wrench,tone:'red'}].filter(s=>hasModule(s.target)).map(s=>{const I=s.icon;return <div className="stat-card dashboard-link-card" key={s.key} role="link" tabIndex={0} onClick={()=>setActive(s.target)} onKeyDown={e=>{if(e.key==='Enter'){setActive(s.target)}}}><div className={`stat-icon ${s.tone}`}><I size={20}/></div><p>{s.label}</p><strong>{stats[s.key]??'—'}</strong><span className="stat-foot">Current records · Click to open</span></div>})}</div>
    {hasModule('fee-reports')&&<>
     <div className="dashboard-section-heading"><div><h3>Finance overview</h3><p>Collections and outstanding balances · {new Date().getFullYear()}</p></div><button className="secondary" onClick={()=>setActive('fee-reports')}>Full fee reports <FileText size={15}/></button></div>
     <div className="fee-report-stats dashboard-finance-stats">
      <div className="stat-card dashboard-link-card" role="link" tabIndex={0} onClick={()=>setActive("fee-reports")}><div className="stat-icon teal"><Wallet size={19}/></div><p>Collected this year</p><strong>{money(reportData.collected||0)}</strong><span className="stat-foot">Payments received in {new Date().getFullYear()}</span></div>
      <div className="stat-card dashboard-link-card" role="link" tabIndex={0} onClick={()=>setActive("fee-reports")}><div className="stat-icon orange"><Activity size={19}/></div><p>Outstanding balance</p><strong>{money(reportData.outstanding||0)}</strong><span className="stat-foot">Balance on fees assigned this year</span></div>
      <div className="stat-card dashboard-link-card" role="link" tabIndex={0} onClick={()=>setActive("payments")}><div className="stat-icon purple"><Bell size={19}/></div><p>Fees with open balance</p><strong>{feeDues.length}</strong><span className="stat-foot">Student fee records needing follow-up</span></div>
     </div>
     <div className="dashboard-finance-grid">
      <div className="panel dashboard-chart-panel"><div className="panel-heading"><div><h3>Monthly fee collections</h3><p>Payment totals by month for {new Date().getFullYear()}</p></div></div>
       {reportData.chart?.length?<div className="fee-chart">{reportData.chart.map((point:any)=>{const max=Math.max(...reportData.chart.map((p:any)=>Number(p.amount)),1);return <div className="fee-chart-column" key={point.period}><strong>{money(Number(point.amount))}</strong><div className="fee-chart-track"><div className="fee-chart-bar" style={{height:(Number(point.amount)/max*100)+'%'}}/></div><span>{new Date(point.period+'-01T00:00:00').toLocaleString('en-IN',{month:'short'})}</span></div>})}</div>:<div className="empty-state compact-empty"><strong>No collections recorded this year</strong><p>Monthly totals will appear after payments are entered.</p></div>}
      </div>
      <div className="panel dashboard-actions-panel"><div className="panel-heading"><div><h3>Quick actions</h3><p>Jump to common school workflows</p></div><Plus size={19}/></div>
       <div className="quick-grid">
        {hasModule('students')&&<button className="quick-item" onClick={()=>setActive('students')}><GraduationCap size={17}/> Add / find student <span className="quick-arrow">→</span></button>}
        {hasModule('payments')&&<button className="quick-item" onClick={()=>setActive('payments')}><Wallet size={17}/> Record fee payment <span className="quick-arrow">→</span></button>}
        {hasModule('staff')&&<button className="quick-item" onClick={()=>setActive('staff')}><Users size={17}/> Manage staff <span className="quick-arrow">→</span></button>}
        {hasModule('fee-reports')&&<button className="quick-item" onClick={()=>setActive('fee-reports')}><FileText size={17}/> View fee reports <span className="quick-arrow">→</span></button>}
       </div>
       <div className="dashboard-alert"><Bell size={17}/><div><strong>{feeDues.length?feeDues.length+' fee records have outstanding balances':'No outstanding fee records'}</strong><span>{feeDues.length?'Review open balances and follow up with families.':'There are no unpaid fee balances in the current fee register.'}</span></div></div>
      </div>
     </div>
     <div className="panel dashboard-recent-panel"><div className="panel-heading"><div><h3>Recent fee payments</h3><p>Latest payment activity for this school</p></div><button className="secondary" onClick={()=>setActive('fee-reports')}>View all <span>→</span></button></div>
      <div className="table-wrap"><table><thead><tr><th>Date</th><th>Receipt</th><th>Student</th><th>Admission no.</th><th>Method</th><th>Amount</th></tr></thead><tbody>{(reportData.recent_payments||[]).slice(0,6).map((p:any)=><tr key={p.id}><td>{new Date(p.payment_date).toLocaleDateString('en-IN')}</td><td>{p.receipt_no}</td><td>{p.student_name}</td><td>{p.admission_no}</td><td>{p.payment_method}</td><td><strong>{money(p.amount)}</strong></td></tr>)}{!reportData.recent_payments?.length&&<tr><td colSpan={6}><div className="empty-state compact-empty"><strong>No recent payments</strong><p>Recorded student fee payments will appear here.</p></div></td></tr>}</tbody></table></div>
     </div>
    </>}
    {user.role==='super_admin'&&<>
    <div className="panel dashboard-roles-panel"><div className="panel-heading"><div><h3>Roles &amp; Authentication</h3><p>Application roles and their authenticated access scope</p></div><Users size={19}/></div><div className="table-wrap"><table><thead><tr><th>Role</th><th>Authentication / access scope</th><th>Access level</th><th>Current user</th></tr></thead><tbody>{roleCatalog.map(r=><tr key={r.roleKey}><td><strong>{r.role}</strong></td><td>{r.scope}</td><td><span className="status-badge active">{r.level}</span></td><td>{user.role===r.roleKey?<span className="status-badge active">Signed in</span>:'—'}</td></tr>)}</tbody></table></div><div className="status-note">Each school role receives a focused workspace and matching navigation. Developer has platform-wide access. Parent accounts use explicit guardian-to-student links and can access linked students only. API-level permissions should be enforced separately for production.</div></div>
    </>}
    {user.role==='super_admin'&&<DeveloperModulePermissionPanel moduleList={modules} roles={roleCatalog}/>}
    {user.role==='super_admin'&&<>
    <div className="panel dashboard-modules-panel"><div className="panel-heading"><div><h3>Entire School ERP Project</h3><p>Complete list of modules available in this application</p></div><GraduationCap size={19}/></div><div className="table-wrap"><table><thead><tr><th>Module</th><th>Project area</th><th>Description</th><th>Action</th></tr></thead><tbody>{availableModules.map(m=><tr key={m.key}><td><strong>{m.label}</strong></td><td>{m.key==='dashboard'?'Overview':m.key.startsWith('fee')||m.key==='payments'||m.key==='student-fees'?'Finance':m.key==='students'||m.key==='classes'?'Academics':m.key==='staff'?'HR':m.key==='vehicles'?'Transport':m.key==='hostels'?'Accommodation':m.key==='documents'?'Administration':'Operations'}</td><td>{m.description}</td><td><button className="secondary" onClick={()=>setActive(m.key)}>Open</button></td></tr>)}</tbody></table></div><div className="table-footer">Available modules: {availableModules.length}<span>SchoolOS · Project overview</span></div></div>
    </>}

    </>:active==='approvals'?<div className="panel data-panel"><div className="panel-heading"><div><h3>Verified staff requests</h3><p>Approve only people who should access this school's workspace.</p></div><span className="record-count">{rows.length} pending</span></div><div className="table-wrap"><table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Requested</th><th>Decision</th></tr></thead><tbody>{rows.map((r:any)=><tr key={r.id}><td><strong>{r.name}</strong></td><td>{r.email}</td><td>{r.role.replaceAll('_',' ')}</td><td>{new Date(r.created_at).toLocaleDateString('en-IN')}</td><td><div className="approval-actions"><button className="primary" onClick={async()=>{try{await request('/api/auth/users/'+r.id+'/approval',{method:'POST',body:JSON.stringify({decision:'approve'})});setNotice('Staff account approved');await load()}catch(e:any){setError(e.message)}}}>Approve</button><button className="secondary" onClick={async()=>{try{await request('/api/auth/users/'+r.id+'/approval',{method:'POST',body:JSON.stringify({decision:'reject'})});setNotice('Staff account rejected');await load()}catch(e:any){setError(e.message)}}}>Reject</button></div></td></tr>)}{!rows.length&&<tr><td colSpan={5}><div className="empty-state"><strong>No pending staff requests</strong><p>Verified staff registrations will appear here for review.</p></div></td></tr>}</tbody></table></div></div>:active==='payments'?<div className="panel payment-entry-panel">
   <div className="panel-heading"><div><h3>Record student fee payment</h3><p>Select a fee with an outstanding balance and record the amount received.</p></div><Wallet size={20}/></div>
   <div className="payment-entry-form">
    <label>Student fee<select value={paymentFeeId} onChange={e=>setPaymentFeeId(e.target.value)}><option value="">Select student fee</option>{feeDues.map(f=><option key={f.fee_id} value={f.fee_id}>{f.student_name} · {f.admission_no} · Balance {money(f.balance)}</option>)}</select></label>
    <label>Payment amount (₹)<input type="number" min="1" step="0.01" value={paymentAmount} onChange={e=>setPaymentAmount(e.target.value)} placeholder="Enter amount"/></label>
    <label>Payment method<select value={paymentMethod} onChange={e=>setPaymentMethod(e.target.value)}><option value="cash">Cash</option><option value="upi">UPI</option><option value="bank_transfer">Bank transfer</option><option value="card">Card</option><option value="cheque">Cheque</option></select></label>
    <button className="primary" disabled={!paymentFeeId||!paymentAmount||Number(paymentAmount)<=0} onClick={recordFeePayment}><Wallet size={16}/> Record payment</button>
   </div>
   <div className="table-wrap"><table><thead><tr><th>Student</th><th>Admission no.</th><th>Total fee</th><th>Paid</th><th>Balance</th></tr></thead><tbody>{feeDues.map(f=><tr key={f.fee_id}><td>{f.student_name}</td><td>{f.admission_no}</td><td>{money(f.total_amount)}</td><td>{money(f.paid_amount)}</td><td><strong>{money(f.balance)}</strong></td></tr>)}{!feeDues.length&&<tr><td colSpan={5}><div className="empty-state"><strong>No outstanding fees</strong><p>Outstanding student fees will appear here.</p></div></td></tr>}</tbody></table></div>
  </div>:active==='fee-reports'?<div className="fee-report-wrap">
   <div className="fee-report-filters">
    {user.role==='super_admin'&&<label>School<select value={reportSchool} onChange={e=>setReportSchool(e.target.value)}><option value="">All schools</option>{schools.map(sc=><option key={sc.id} value={sc.id}>{sc.name}</option>)}</select></label>}
    <label>Year<select value={reportYear} onChange={e=>setReportYear(e.target.value)}>{Array.from({length:7},(_,i)=>String(new Date().getFullYear()-i)).map(y=><option key={y} value={y}>{y}</option>)}</select></label>
    <label>Month<select value={reportMonth} onChange={e=>setReportMonth(e.target.value)}><option value="">All months</option>{Array.from({length:12},(_,i)=>i+1).map(m=><option key={m} value={m}>{new Date(2000,m-1,1).toLocaleString('en-IN',{month:'long'})}</option>)}</select></label>
    <button className="secondary" onClick={load}><RefreshCw size={15}/> Apply filters</button>
   </div>
   <div className="fee-report-stats">
    <div className="stat-card"><p>Total collected</p><strong>{money(reportData.collected)}</strong><span className="stat-foot">Payments received for selected period</span></div>
    <div className="stat-card"><p>Outstanding balance</p><strong>{money(reportData.outstanding)}</strong><span className="stat-foot">Unpaid student fee balance</span></div>
   </div>
   <div className="panel fee-chart-panel"><div className="panel-heading"><div><h3>Monthly collection trend</h3><p>Fee payments received during {reportYear}</p></div></div>
    {reportData.chart?.length?<div className="fee-chart">{reportData.chart.map((point:any)=>{const max=Math.max(...reportData.chart.map((p:any)=>Number(p.amount)),1);return <div className="fee-chart-column" key={point.period}><strong>{money(Number(point.amount))}</strong><div className="fee-chart-track"><div className="fee-chart-bar" style={{height:(Number(point.amount)/max*100)+'%'}}/></div><span>{new Date(point.period+'-01T00:00:00').toLocaleString('en-IN',{month:'short'})}</span></div>})}</div>:<div className="empty-state"><strong>No payment data for this year</strong><p>Monthly collections will appear here after fee payments are recorded.</p></div>}
   </div>
   <div className="panel fee-recent-panel"><div className="panel-heading"><div><h3>Recent payment history</h3><p>Latest 100 payments matching the selected filters</p></div><span className="record-count">{reportData.recent_payments?.length||0} payments</span></div>
    <div className="table-wrap"><table><thead><tr>{user.role==='super_admin'&&!reportSchool&&<th>School</th>}<th>Date</th><th>Receipt</th><th>Student</th><th>Admission no.</th><th>Method</th><th>Amount</th></tr></thead><tbody>{reportData.recent_payments?.map((p:any)=><tr key={p.id}>{user.role==='super_admin'&&!reportSchool&&<td>{p.school_name}</td>}<td>{new Date(p.payment_date).toLocaleDateString('en-IN')}</td><td>{p.receipt_no}</td><td>{p.student_name}</td><td>{p.admission_no}</td><td>{p.payment_method}</td><td><strong>{money(p.amount)}</strong></td></tr>)}{!reportData.recent_payments?.length&&<tr><td colSpan={user.role==='super_admin'&&!reportSchool?7:6}><div className="empty-state"><strong>No payments found</strong><p>Payment records will appear here once payments are entered.</p></div></td></tr>}</tbody></table></div>
   </div>
  </div>:<div className="panel data-panel"><div className="panel-heading"><div><h3>{selected.label} records</h3><p>Manage records and keep your school information up to date.</p></div><span className="record-count">{rows.length} records</span></div><div className="table-tools"><div className="search-box"><Search size={17}/><input placeholder={`Search ${selected.label.toLowerCase()}…`} value={query} onChange={e=>setQuery(e.target.value)}/></div><span className="muted small">{loading?'Loading records…':'Latest records first'}</span></div>{active==='schools'&&user.role==='super_admin'&&<div className="school-owner-assign"><div><strong>Assign existing school owner</strong><p>Link an existing standard user login to one school. The user will only see that school's records.</p></div><label>Standard user account<select value={ownerUserId} onChange={e=>setOwnerUserId(e.target.value)}><option value="">Select standard user account</option>{ownerUsers.filter(u=>u.role!=='super_admin'&&u.role!=='parent').map(u=><option key={u.id} value={u.id}>{u.name} · {u.email}{u.school_id?' (already assigned)':''}</option>)}</select></label><label>School<select value={ownerSchoolId} onChange={e=>setOwnerSchoolId(e.target.value)}><option value="">Select school</option>{schools.map(sc=><option key={sc.id} value={sc.id}>{sc.name}</option>)}</select></label><button className="primary" disabled={!ownerUserId||!ownerSchoolId} onClick={assignSchoolOwner}>Assign owner</button></div>}{showForm&&<form className={`record-form ${active==='staff'?'staff-record-form':''}`} onSubmit={save}><div className="form-heading"><h3>{editingRecordId?'Edit':'Add'} {selected.label.toLowerCase()} record</h3><button type="button" className="icon-button" onClick={()=>setShowForm(false)}><X size={18}/></button></div>{active==='student-fees'&&<>{selectedStudent?<div className="student-fee-details"><h4>Student details</h4><div className="student-fee-detail-grid">{[['Admission number',selectedStudent.admission_no],['Student name',selectedStudent.full_name],['Class',selectedStudent.class_name],['Section',selectedStudent.section],['Guardian name',selectedStudent.guardian_name],['Guardian phone',selectedStudent.guardian_phone],['Email',selectedStudent.email],['Date of birth',selectedStudent.date_of_birth],['Address',selectedStudent.address],['Transport required',selectedStudent.transport_required?'Yes':'No'],['Hostel required',selectedStudent.hostel_required?'Yes':'No'],['Student status',selectedStudent.status]].map(([label,value])=><div key={label}><span>{label}</span><strong>{value||'—'}</strong></div>)}</div></div>:<p className="muted">Search and select a student above before entering a fee amount.</p>}</> }<div className="form-grid">{selected.fields?.filter(f=>f.key!=='school_id'||user.role==='super_admin').map(f=><label key={f.key}>{f.type==='school-select'?<>{f.label}<select value={form[f.key]??''} required={f.required} onChange={e=>setForm({...form,[f.key]:e.target.value})}><option value="">Select school</option>{schools.map(sc=><option key={sc.id} value={sc.id}>{sc.name}</option>)}</select></>:active==='staff'&&f.key==='designation'?<>{f.label}<select value={form.designation??'Teacher'} required onChange={e=>setForm({...form,designation:e.target.value})}><option value="">Select designation</option><option>Principal</option><option>Vice Principal</option><option>Teacher</option><option>Accountant</option><option>Clerk</option><option>Office Assistant</option><option>Librarian</option><option>Lab Assistant</option><option>IT Administrator</option><option>Transport Manager</option><option>Hostel Warden</option><option>Security Guard</option><option>Other</option></select></>:active==='staff'&&f.key==='phone'?<><span className="staff-phone-label">{f.label}</span><div className="staff-phone-inputs"><span className="staff-phone-prefix">+91</span><input className="staff-phone-part" aria-label="First five phone digits" type="tel" inputMode="numeric" pattern="[0-9]{5}" maxLength={5} placeholder="98765" value={String(form.phone??'').replace(/^\+91\s*/,'').replace(/\D/g,'').slice(0,5)} required onChange={e=>{const digits=String(form.phone??'').replace(/^\+91\s*/,'').replace(/\D/g,'').slice(0,10);const first=e.target.value.replace(/\D/g,'').slice(0,5);const rest=digits.slice(5,10);setForm({...form,phone:'+91 '+first+rest})}}/><input className="staff-phone-part" aria-label="Last five phone digits" type="tel" inputMode="numeric" pattern="[0-9]{5}" maxLength={5} placeholder="43210" value={String(form.phone??'').replace(/^\+91\s*/,'').replace(/\D/g,'').slice(5,10)} required onChange={e=>{const digits=String(form.phone??'').replace(/^\+91\s*/,'').replace(/\D/g,'').slice(0,10);const first=digits.slice(0,5);const rest=e.target.value.replace(/\D/g,'').slice(0,5);setForm({...form,phone:'+91 '+first+rest})}}/></div><small className="staff-field-help">India +91 · Enter exactly 10 digits in two groups of five</small></>:active==='staff'&&f.key==='salary'?<>{f.label}<input className="staff-salary-input" type="text" inputMode="decimal" value={form.salary??''} required maxLength={10} pattern="[0-9]{1,7}\.[0-9]{2}" placeholder="25000.00" title="Maximum 7 digits before decimal and exactly 2 digits after decimal; maximum ₹150,000.00" onChange={e=>{let v=e.target.value.replace(/[^0-9.]/g,'');const dot=v.indexOf('.');if(dot>=0){v=v.slice(0,dot+1)+v.slice(dot+1).replace(/\./g,'').slice(0,2);v=v.slice(0,dot).slice(0,7)+v.slice(dot)}else{v=v.slice(0,7)}if(v&&Number(v)>150000.00)return;setForm({...form,salary:v})}}/><small className="staff-field-help">Up to 7 whole-number digits · exactly 2 decimal digits · maximum ₹150,000.00</small></>:active==='staff'&&f.key==='status'?<>{f.label}<select value={form.status??'active'} onChange={e=>setForm({...form,status:e.target.value})}><option value="active">Active</option><option value="absent">Absent</option><option value="suspended">Suspended</option><option value="terminated">Terminated</option><option value="sick">Sick</option><option value="leave">Leave</option></select></>:<>{f.label}<input type={f.type||'text'} value={form[f.key]??''} required={f.required} min={f.type==='number'?0:undefined} max={f.key==='salary'?150000:undefined} step={f.key==='salary'?0.01:undefined} maxLength={active==='staff'?({employee_no:8,full_name:100,department:32,email:40}[f.key] as number|undefined):undefined} pattern={active==='staff'?({employee_no:'[A-Z]{4}[0-9]{4}',full_name:"[A-Za-z][A-Za-z .'-]*",department:'[A-Za-z ]{0,32}',email:'[A-Za-z0-9._%+-]+@gmail\\.com'} as Record<string,string>)[f.key]:undefined} title={active==='staff'&&f.key==='employee_no'?'Enter exactly 4 letters followed by 4 digits':active==='staff'&&f.key==='email'?'Use a Gmail address (maximum 40 characters)':undefined} placeholder={active==='staff'&&f.key==='employee_no'?'e.g. SPVB0001':undefined} onChange={e=>setForm({...form,[f.key]:f.key==='employee_no'?(()=>{const raw=e.target.value.toUpperCase().replace(/[^A-Z0-9]/g,'');const letters=raw.replace(/[^A-Z]/g,'').slice(0,4);const digits=raw.replace(/[^0-9]/g,'').slice(0,4);return letters+digits})():e.target.value})}/></>}</label>)}</div>{active==='staff'&&user.role==='super_admin'&&!editingRecordId&&<div className="staff-account-options"><label className="checkbox-field"><input type="checkbox" checked={Boolean(form.create_account)} onChange={e=>setForm({...form,create_account:e.target.checked})}/> Create login account for this staff member</label>{form.create_account&&<div className="form-grid"><label>Permission / role<select value={form.account_role??'principal'} onChange={e=>setForm({...form,account_role:e.target.value})}>{Object.entries(roleLabels).filter(([key])=>key!=='super_admin'&&key!=='parent'&&key!=='user'&&key!=='admin'&&key!=='accountant').map(([key,label])=><option key={key} value={key}>{label}</option>)}<option value="parent">Parent</option></select></label><label>Temporary login password (minimum 12 characters)<input type="password" minLength={12} required value={form.account_password??''} onChange={e=>setForm({...form,account_password:e.target.value})}/></label><p className="muted">The Gmail address above is the login username. Staff sign in with this email, the password, and the selected school's code. All standard school users share the same SchoolOS module access. School code: {schools.find(sc=>String(sc.id)===String(form.school_id))?.code||'Select a school first'}</p></div>}</div>}<div className="form-actions"><button type="button" className="secondary" onClick={()=>setShowForm(false)}>Cancel</button><button className="primary"><Plus size={16}/> {editingRecordId?'Update record':'Save record'}</button></div></form>}<div className="table-wrap"><table><thead><tr><th>ID</th>{active==='staff'&&user.role==='super_admin'&&<th>School</th>}{(selected.fields||[]).slice(0,5).map(f=><th key={f.key}>{f.label}</th>)}<th>Status</th>{active==='staff'&&<th>Actions</th>}</tr></thead><tbody>{rows.map(r=><tr key={r.id}><td className="id-cell">#{r.id}</td>{active==='staff'&&user.role==='super_admin'&&<td>{schools.find(sc=>sc.id===r.school_id)?.name||'—'}</td>}{(selected.fields||[]).slice(0,5).map(f=><td key={f.key}>{f.type==='checkbox'?(r[f.key]?'Yes':'No'):(r[f.key]??'—')}</td>)}<td><span className={`status-badge ${String(r.status||'active').toLowerCase()}`}>{r.status||(r.is_active?'active':'inactive')}</span></td>{active==='staff'&&<td><div className="row-actions"><button type="button" className="secondary" onClick={()=>{setEditingRecordId(r.id);setForm({...r,phone:r.phone?('+91 '+String(r.phone).replace(/^\\+91\\s*/,'').trim()):'+91 ',salary:Number(r.salary??0).toFixed(2)});setShowForm(true)}}>Edit</button><button type="button" className="secondary" onClick={()=>deleteStaff(r)}>Delete</button></div></td>}</tr>)}{!rows.length&&<tr><td colSpan={(selected.fields?.slice(0,5).length||0)+2+(active==='staff'&&user.role==='super_admin'?1:0)+(active==='staff'?1:0)}><div className="empty-state"><div className="empty-icon"><Icon size={25}/></div><strong>{loading?'Loading records…':'No records found'}</strong><p>{loading?'Please wait.':'Create your first record to get started.'}</p>{!loading&&(user.role!=='super_admin'||active==='schools'||active==='staff')&&<button className="primary" onClick={()=>setShowForm(true)}><Plus size={16}/> Add first record</button>}</div></td></tr>}</tbody></table></div><div className="table-footer">Showing {rows.length} record(s) <span>SchoolOS · Secure workspace</span></div></div>}
  <footer className="footer"><span>© {new Date().getFullYear()} SchoolOS</span><span>School operations platform</span></footer></div></main>
 </div>
 }

function DeveloperModulePermissionPanel({moduleList,roles}:{moduleList:ModuleDef[];roles:{role:string;roleKey:string;scope:string;level:string}[]}) {
 const [role,setRole]=useState('teacher');
 const [permissions,setPermissions]=useState<Record<string,Record<string,boolean>>>({});
 const actions=['View','Create','Edit','Delete','Approve','Export'];
 const current=permissions[role]||{};
 const enabledCount=moduleList.filter(m=>current[m.key+':View']).length;
 function toggle(key:string,action:string,value:boolean){setPermissions(old=>({...old,[role]:{...(old[role]||{}),[key+':'+action]:value}}))}
 function setAll(value:boolean){setPermissions(old=>({...old,[role]:Object.fromEntries(moduleList.flatMap(m=>actions.map(a=>[m.key+':'+a,value])))}))}
 function copyDraft(){const value=JSON.stringify({role,permissions:current},null,2);if(typeof navigator!=='undefined'&&navigator.clipboard?.writeText)void navigator.clipboard.writeText(value)}
 return <div className="panel developer-permissions-panel">
  <div className="panel-heading"><div><h3>Module permissions</h3><p>Select a role and configure permissions module by module.</p></div><ShieldCheck size={20}/></div>
  <div className="permission-toolbar">
   <label className="auth-field">Select role<select value={role} onChange={e=>setRole(e.target.value)}>{roles.filter(r=>r.roleKey!=='super_admin').map(r=><option key={r.roleKey} value={r.roleKey}>{r.role}</option>)}</select></label>
   <div className="permission-summary"><strong>{enabledCount} / {moduleList.length}</strong><span>modules with View enabled</span></div>
   <div className="permission-bulk-actions"><button type="button" className="secondary" onClick={()=>setAll(true)}>Select all</button><button type="button" className="secondary" onClick={()=>setAll(false)}>Clear all</button></div>
  </div>
  <div className="table-wrap permission-table-wrap"><table className="permission-table"><thead><tr><th>Module</th>{actions.map(a=><th key={a}>{a}</th>)}</tr></thead><tbody>{moduleList.map(m=><tr key={m.key}><td><strong>{m.label}</strong><small>{m.description}</small></td>{actions.map(a=><td key={a}><input aria-label={m.label+' '+a+' permission'} type="checkbox" checked={Boolean(current[m.key+':'+a])} onChange={e=>toggle(m.key,a,e.target.checked)}/></td>)}</tr>)}</tbody></table></div>
  <div className="permission-footer"><span>{role.replaceAll('_',' ')} · {Object.values(current).filter(Boolean).length} permissions selected</span><button type="button" className="secondary" onClick={copyDraft}>Copy permission draft</button></div>
  <p className="status-note">Draft only: selections are local to this page and are not saved to the server or enforced by APIs. Backend authorization is required before these settings can control real access.</p>
 </div>
}

export default App
