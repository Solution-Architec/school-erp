import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { Activity, Bus, Building2, ChevronDown, FileText, GraduationCap, LayoutDashboard, LogOut, Menu, Search, Settings, Users, Wallet, Wrench, BookOpen, Bell, Plus, RefreshCw, X } from 'lucide-react'

const API = (import.meta as any).env?.VITE_API_URL || ''
type User = { id:number; name:string; email:string; role:string }
type ModuleDef = { key:string; label:string; icon:any; endpoint?:string; fields?:{key:string;label:string;type?:string;required?:boolean}[]; description:string }
const modules: ModuleDef[] = [
 {key:'dashboard',label:'Dashboard',icon:LayoutDashboard,description:'School overview and operational alerts'},
 {key:'students',label:'Students',icon:GraduationCap,endpoint:'/api/students',description:'Profiles, admissions, guardians and student services',fields:[{key:'admission_no',label:'Admission number',required:true},{key:'full_name',label:'Full name',required:true},{key:'class_name',label:'Class'},{key:'section',label:'Section'},{key:'guardian_name',label:'Guardian name'},{key:'guardian_phone',label:'Guardian phone'},{key:'email',label:'Email',type:'email'},{key:'address',label:'Address'},{key:'date_of_birth',label:'Date of birth',type:'date'},{key:'transport_required',label:'Transport required',type:'checkbox'},{key:'hostel_required',label:'Hostel required',type:'checkbox'}]},
 {key:'staff',label:'Staff & HR',icon:Users,endpoint:'/api/staff',description:'Employee profiles and HR records',fields:[{key:'employee_no',label:'Employee number',required:true},{key:'full_name',label:'Full name',required:true},{key:'designation',label:'Designation'},{key:'department',label:'Department'},{key:'phone',label:'Phone'},{key:'email',label:'Email',type:'email'},{key:'salary',label:'Monthly salary',type:'number'},{key:'status',label:'Status'}]},
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
    { key: 'fee_type', label: 'Fee type', required: true },
    { key: 'amount', label: 'Amount (₹)', type: 'number', required: true },
    { key: 'frequency', label: 'Frequency', required: true },
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
    { key: 'student_id', label: 'Student ID', type: 'number', required: true },
    { key: 'fee_structure_id', label: 'Fee structure ID', type: 'number' },
    { key: 'title', label: 'Fee title', required: true },
    { key: 'total_amount', label: 'Total amount (₹)', type: 'number', required: true },
    { key: 'due_date', label: 'Due date', type: 'date', required: true },
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
const money = (n:number) => new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(n || 0)

function Login({onLogin}:{onLogin:(token:string,user:User)=>void}) {
 const [email,setEmail]=useState('admin@example.com'), [password,setPassword]=useState('ChangeMe123!'), [error,setError]=useState(''), [busy,setBusy]=useState(false)
 async function submit(e: FormEvent<HTMLFormElement>) {e.preventDefault();setBusy(true);setError('');try{const form=new URLSearchParams({username:email,password});const r=await fetch(`${API}/api/auth/login`,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:form});const d=await r.json().catch(()=>null);if(!r.ok)throw new Error(d?.detail||`Login failed (${r.status})`);if(!d?.access_token||!d?.user)throw new Error('The server returned an empty or invalid login response');onLogin(d.access_token,d.user)}catch(err:any){setError(err.message||'Unable to connect to the ERP API')}finally{setBusy(false)}}
 return <div className="login-wrap"><form className="login-card" onSubmit={submit}><div className="brand-mark"><GraduationCap size={30}/></div><p className="eyebrow">SCHOOL MANAGEMENT PLATFORM</p><h1>Welcome back</h1><p className="muted">Sign in to your school workspace.</p><label>Email address<input type="email" value={email} onChange={e=>setEmail(e.target.value)} required/></label><label>Password<input type="password" value={password} onChange={e=>setPassword(e.target.value)} required/></label>{error&&<div className="error">{error}</div>}<button className="primary full" disabled={busy}>{busy?'Signing in…':'Sign in'}</button><p className="small muted">Change the bootstrap password before deployment.</p></form></div>
}

function App(){
 const [token,setToken]=useState(localStorage.getItem('erp_token')||'')
 const [user,setUser]=useState<User|null>(null)
 const [active,setActive]=useState('dashboard')
 const [mobileNav,setMobileNav]=useState(false)
 const [rows,setRows]=useState<any[]>([])
 const [stats,setStats]=useState<any>({})
 const [loading,setLoading]=useState(false)
 const [error,setError]=useState('')
 const [query,setQuery]=useState('')
 const [showForm,setShowForm]=useState(false)
 const [form,setForm]=useState<Record<string,any>>({})
 const [notice,setNotice]=useState('')
 const selected=modules.find(m=>m.key===active)||modules[0]
 const authHeaders=useMemo(()=>({'Authorization':`Bearer ${token}`,'Content-Type':'application/json'}),[token])
 useEffect(()=>{if(!token)return;fetch(`${API}/api/auth/me`,{headers:authHeaders}).then(r=>r.ok?r.json():Promise.reject()).then(setUser).catch(()=>{localStorage.removeItem('erp_token');setToken('');setUser(null)})},[token,authHeaders])
 async function request(url:string,options:RequestInit={}){const r=await fetch(`${API}${url}`,{...options,headers:{...authHeaders,...options.headers}});if(r.status===401){logout();throw new Error('Session expired. Please sign in again.')}const data=await r.json().catch(()=>({}));if(!r.ok)throw new Error(data.detail||'Request failed');return data}
 function logout(){localStorage.removeItem('erp_token');setToken('');setUser(null);setRows([])}
 function handleLogin(t:string,u:User){localStorage.setItem('erp_token',t);setToken(t);setUser(u)}
 async function load(){if(!user)return;setLoading(true);setError('');try{if(active==='dashboard'){setStats(await request('/api/dashboard'));setRows([])}else if(selected.endpoint){setRows(await request(`${selected.endpoint}?q=${encodeURIComponent(query)}`))}}catch(e:any){setError(e.message)}finally{setLoading(false)}}
 useEffect(()=>{if(user)load()},[active,user,query])
 async function save(e: FormEvent<HTMLFormElement>) {e.preventDefault();try{const payload={...form};for(const f of selected.fields||[]){if(f.type==='number'&&payload[f.key]!==''&&payload[f.key]!=null)payload[f.key]=Number(payload[f.key]);if(f.type==='checkbox')payload[f.key]=Boolean(payload[f.key]);if(payload[f.key]==='')delete payload[f.key]}await request(selected.endpoint!,{method:'POST',body:JSON.stringify(payload)});setShowForm(false);setForm({});setNotice('Record created successfully');await load()}catch(e:any){setError(e.message)}}
 if(!token||!user)return <Login onLogin={handleLogin}/>
 const Icon=selected.icon
 return <div className="app-shell">
  <aside className={`sidebar ${mobileNav?'open':''}`}><div className="brand"><div className="brand-mark"><GraduationCap/></div><div><strong>CampusFlow</strong><span>ERP MANAGEMENT</span></div><button className="icon-button mobile-close" onClick={()=>setMobileNav(false)}><X/></button></div><div className="school-switch"><div className="school-avatar">S</div><div><strong>My School</strong><span>Academic workspace</span></div><ChevronDown size={16}/></div><p className="nav-label">WORKSPACE</p><nav>{modules.map(m=>{const I=m.icon;return <button key={m.key} className={`nav-item ${active===m.key?'selected':''}`} onClick={()=>{setActive(m.key);setMobileNav(false);setShowForm(false)}}><I size={18}/><span>{m.label}</span></button>})}</nav><div className="sidebar-bottom"><div className="user-mini"><div className="avatar">{user.name.slice(0,1).toUpperCase()}</div><div><strong>{user.name}</strong><span>{user.role.replace('_',' ')}</span></div><button className="icon-button" title="Sign out" onClick={logout}><LogOut size={17}/></button></div></div></aside>
  <main className="main"><header className="topbar"><button className="icon-button mobile-menu" onClick={()=>setMobileNav(true)}><Menu/></button><div className="crumb">Workspace <span>/</span> <strong>{selected.label}</strong></div><div className="top-actions"><div className="online-pill"><span/> System online</div><button className="icon-button" title="Notifications"><Bell size={19}/></button><div className="avatar">{user.name.slice(0,1).toUpperCase()}</div></div></header>
  <div className="content"><div className="page-heading"><div><p className="eyebrow">SCHOOL ERP / {selected.key.toUpperCase()}</p><h1>{selected.label}</h1><p className="muted">{selected.description}</p></div><div className="heading-actions"><button className="secondary" onClick={load}><RefreshCw size={16}/> Refresh</button>{selected.endpoint&&<button className="primary" onClick={()=>{setForm({});setShowForm(true)}}><Plus size={17}/> Add record</button>}</div></div>
  {error&&<div className="error banner"><span>{error}</span><button onClick={()=>setError('')}><X size={16}/></button></div>}{notice&&<div className="success banner">{notice}<button onClick={()=>setNotice('')}><X size={16}/></button></div>}
  {active==='dashboard'?<><div className="welcome-panel"><div><span className="welcome-tag">OVERVIEW</span><h2>Good to see you, {user.name.split(' ')[0]}</h2><p>Your school operations at a glance. Use the navigation to manage records.</p></div><div className="welcome-icon"><GraduationCap size={44}/></div></div><div className="stat-grid">{[{label:'Total students',key:'students',icon:GraduationCap,tone:'teal'},{label:'Staff members',key:'staff',icon:Users,tone:'blue'},{label:'Classes & sections',key:'classes',icon:BookOpen,tone:'purple'},{label:'Transport vehicles',key:'vehicles',icon:Bus,tone:'orange'},{label:'Hostel rooms',key:'hostel_rooms',icon:Building2,tone:'pink'},{label:'Open maintenance',key:'open_maintenance',icon:Wrench,tone:'red'}].map(s=>{const I=s.icon;return <div className="stat-card" key={s.key}><div className={`stat-icon ${s.tone}`}><I size={20}/></div><p>{s.label}</p><strong>{stats[s.key]??'—'}</strong><span className="stat-foot">Current records</span></div>})}</div><div className="bottom-grid"><div className="panel"><div className="panel-heading"><div><h3>Quick access</h3><p>Common school operations</p></div><Activity size={19}/></div><div className="quick-grid">{modules.filter(m=>m.endpoint).slice(0,6).map(m=>{const I=m.icon;return <button key={m.key} className="quick-item" onClick={()=>setActive(m.key)}><I size={19}/><span>{m.label}</span><span className="quick-arrow">↗</span></button>})}</div></div><div className="panel"><div className="panel-heading"><div><h3>System status</h3><p>Application services</p></div><Settings size={19}/></div><div className="status-row"><span className="status-dot"/><div><strong>ERP API</strong><small>Connected to authenticated session</small></div><span className="status-text">Active</span></div><div className="status-row"><span className="status-dot"/><div><strong>Workspace access</strong><small>Role: {user.role.replaceAll('_',' ')}</small></div><span className="status-text">Active</span></div><div className="status-note">More academic, finance and communication modules can be added using the same module pattern.</div></div></div></>:<div className="panel data-panel"><div className="panel-heading"><div><h3>{selected.label} records</h3><p>Manage records and keep your school information up to date.</p></div><span className="record-count">{rows.length} records</span></div><div className="table-tools"><div className="search-box"><Search size={17}/><input placeholder={`Search ${selected.label.toLowerCase()}…`} value={query} onChange={e=>setQuery(e.target.value)}/></div><span className="muted small">{loading?'Loading records…':'Latest records first'}</span></div>{showForm&&<form className="record-form" onSubmit={save}><div className="form-heading"><h3>Add {selected.label.toLowerCase()} record</h3><button type="button" className="icon-button" onClick={()=>setShowForm(false)}><X size={18}/></button></div><div className="form-grid">{selected.fields?.map(f=><label key={f.key} className={f.type==='checkbox'?'checkbox-field':''}>{f.type==='checkbox'?<><input type="checkbox" checked={Boolean(form[f.key])} onChange={e=>setForm({...form,[f.key]:e.target.checked})}/>{f.label}</>:<>{f.label}<input type={f.type||'text'} value={form[f.key]??''} required={f.required} min={f.type==='number'?0:undefined} onChange={e=>setForm({...form,[f.key]:e.target.value})}/></>}</label>)}</div><div className="form-actions"><button type="button" className="secondary" onClick={()=>setShowForm(false)}>Cancel</button><button className="primary"><Plus size={16}/> Save record</button></div></form>}<div className="table-wrap"><table><thead><tr><th>ID</th>{(selected.fields||[]).slice(0,5).map(f=><th key={f.key}>{f.label}</th>)}<th>Status</th></tr></thead><tbody>{rows.map(r=><tr key={r.id}><td className="id-cell">#{r.id}</td>{(selected.fields||[]).slice(0,5).map(f=><td key={f.key}>{f.type==='checkbox'?(r[f.key]?'Yes':'No'):(r[f.key]??'—')}</td>)}<td><span className={`status-badge ${String(r.status||'active').toLowerCase()}`}>{r.status||'active'}</span></td></tr>)}{!rows.length&&<tr><td colSpan={(selected.fields?.slice(0,5).length||0)+2}><div className="empty-state"><div className="empty-icon"><Icon size={25}/></div><strong>{loading?'Loading records…':'No records found'}</strong><p>{loading?'Please wait.':'Create your first record to get started.'}</p>{!loading&&<button className="primary" onClick={()=>setShowForm(true)}><Plus size={16}/> Add first record</button>}</div></td></tr>}</tbody></table></div><div className="table-footer">Showing {rows.length} record(s) <span>School ERP · Secure workspace</span></div></div>}
  <footer className="footer"><span>© {new Date().getFullYear()} CampusFlow ERP</span><span>School operations platform</span></footer></div></main>
 </div>
 }
export default App
