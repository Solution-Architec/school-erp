import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import DeveloperControlCentre from './DeveloperControlCentre'
import ParentNotifications from './ParentNotifications'
import NotificationManagementPanel from './NotificationManagementPanel'
import CertificateManagementPanel from './CertificateManagementPanel'
import { Activity, ArrowLeft, ArrowRight, Bus, Building2, ChevronDown, Eye, EyeOff, FileText, GraduationCap, LayoutDashboard, LockKeyhole, LogOut, Mail, Menu, Search, Settings, ShieldCheck, Users, Wallet, Wrench, BookOpen, Bell, Plus, RefreshCw, X, Upload, Download, CalendarCheck, CalendarDays, ClipboardList, Award, NotebookPen, MessageCircle, ClipboardCheck } from 'lucide-react'

const API = (import.meta as any).env?.VITE_API_URL || ''
type User = { id:number; name:string; email:string; role:string; school_id?:number|null; platform_workspace?:boolean }
type ModuleDef = { key:string; label:string; icon:any; endpoint?:string; fields?:{key:string;label:string;type?:string;required?:boolean;options?:string[]}[]; description:string }
const modules: ModuleDef[] = [
 {key:'dashboard',label:'Dashboard',icon:LayoutDashboard,description:'School overview and operational alerts'},
 {key:'parent-portal',label:'Parent Workspace',icon:Users,description:'One secure family workspace for all linked children and school services'},
 {key:'parent-relationships',label:'Parent Relationships',icon:Users,description:'Review and manage verified parent–student access for this school'},
 {key:'certificate-management',label:'Certificate Management',icon:Award,description:'Review parent certificate requests, issue certificates and download secure PDFs'},
 {key:'notifications',label:'Notification Centre',icon:Bell,description:'Publish school announcements and targeted parent alerts'},
 {key:'facility-requests',label:'Transport & Hostel Requests',icon:Bus,description:'Review parent transport and hostel allocation requests'},
 {key:'chatbot',label:'Help Assistant',icon:Activity,description:'School FAQ and guided help'},
 {key:'approvals',label:'Staff Approvals',icon:Users,description:'Review verified staff account requests'},
 {key:'schools',label:'Schools',icon:Building2,endpoint:'/api/schools',description:'Register schools and assign school-owner accounts',fields:[{key:'name',label:'School name',required:true},{key:'code',label:'School code',required:true}]},
 {key:'developer-control',label:'Developer Control Centre',icon:ShieldCheck,description:'Platform-wide client, subscription, collection, support and usage management'},
 {key:'students',label:'Students',icon:GraduationCap,endpoint:'/api/students',description:'Profiles, admissions, guardians and student services',fields:[{key:'admission_no',label:'Admission number',required:true},{key:'full_name',label:'Full name',required:true},{key:'class_name',label:'Class'},{key:'section',label:'Section'},{key:'guardian_name',label:'Guardian name'},{key:'guardian_phone',label:'Guardian phone'},{key:'email',label:'Email',type:'email'},{key:'address',label:'Address'},{key:'date_of_birth',label:'Date of birth',type:'date'},{key:'transport_required',label:'Transport required',type:'checkbox'},{key:'hostel_required',label:'Hostel required',type:'checkbox'}]},
 {key:'staff',label:'Staff & HR',icon:Users,endpoint:'/api/staff',description:'Employee profiles, validated HR details and optional staff login accounts',fields:[{key:'employee_no',label:'Employee number (4 uppercase letters + 4 digits)',required:true},{key:'full_name',label:'Full name',required:true},{key:'designation',label:'Designation',type:'designation'},{key:'department',label:'Department (max 32 characters)'},{key:'phone',label:'Phone (+91)',type:'tel',required:true},{key:'email',label:'Gmail address / login username',type:'email',required:true},{key:'salary',label:'Monthly salary (e.g. 25000.00)',type:'text',required:true},{key:'status',label:'Employment status'},{key:'school_id',label:'School',type:'school-select',required:true}]},
 {key:'classes',label:'Classes',icon:BookOpen,endpoint:'/api/classes',description:'Grades, sections, capacity and class teachers',fields:[{key:'name',label:'Class / grade',required:true},{key:'section',label:'Section'},{key:'academic_year',label:'Academic year'},{key:'class_teacher',label:'Class teacher'},{key:'capacity',label:'Capacity',type:'number'}]},
 {key:'attendance',label:'Attendance',icon:CalendarCheck,endpoint:'/api/attendance',description:'Daily student attendance with present, absent, late and leave tracking',fields:[{key:'school_id',label:'School',type:'school-select',required:true},{key:'student_id',label:'Student record ID',type:'number',required:true},{key:'attendance_date',label:'Attendance date',type:'date',required:true},{key:'status',label:'Attendance status',type:'select',required:true,options:['present','absent','late','leave']},{key:'remarks',label:'Remarks'}]},
 {key:'timetable',label:'Timetable',icon:CalendarDays,endpoint:'/api/timetable',description:'Weekly class periods, subjects, teachers and room assignments',fields:[{key:'school_id',label:'School',type:'school-select',required:true},{key:'class_name',label:'Class / grade',required:true},{key:'section',label:'Section'},{key:'day_of_week',label:'Day',type:'select',required:true,options:['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']},{key:'period',label:'Period number',type:'number',required:true},{key:'subject',label:'Subject',required:true},{key:'teacher_name',label:'Teacher'},{key:'room',label:'Room'},{key:'start_time',label:'Start time',type:'time',required:true},{key:'end_time',label:'End time',type:'time',required:true}]},
 {key:'exams',label:'Exams',icon:ClipboardList,endpoint:'/api/exams',description:'Exam schedules, subjects, maximum marks and pass marks',fields:[{key:'school_id',label:'School',type:'school-select',required:true},{key:'name',label:'Exam name',required:true},{key:'class_name',label:'Class / grade',required:true},{key:'section',label:'Section'},{key:'subject',label:'Subject',required:true},{key:'exam_date',label:'Exam date',type:'date',required:true},{key:'max_marks',label:'Maximum marks',type:'number',required:true},{key:'pass_marks',label:'Pass marks',type:'number',required:true},{key:'academic_year',label:'Academic year'}]},
 {key:'report-cards',label:'Report Cards',icon:Award,endpoint:'/api/report-cards',description:'Student-wise exam marks, remarks and academic result records',fields:[{key:'school_id',label:'School',type:'school-select',required:true},{key:'student_id',label:'Student record ID',type:'number',required:true},{key:'exam_id',label:'Exam record ID',type:'number',required:true},{key:'marks_obtained',label:'Marks obtained',type:'number',required:true},{key:'remarks',label:'Remarks'}]},
 {key:'homework',label:'Homework',icon:NotebookPen,endpoint:'/api/homework',description:'Assign and manage class homework with due dates and instructions',fields:[{key:'school_id',label:'School',type:'school-select',required:true},{key:'class_name',label:'Class / grade',required:true},{key:'section',label:'Section'},{key:'subject',label:'Subject',required:true},{key:'title',label:'Homework title',required:true},{key:'description',label:'Instructions',type:'textarea'},{key:'due_date',label:'Due date',type:'date',required:true},{key:'attachment_url',label:'Attachment URL'}]},
 {key:'student-leave',label:'Student Leave',icon:ClipboardCheck,endpoint:'/api/student-leave',description:'Review student leave applications and approve or reject requests',fields:[{key:'school_id',label:'School',type:'school-select'},{key:'student_id',label:'Student record ID',type:'number',required:true},{key:'start_date',label:'From date',type:'date',required:true},{key:'end_date',label:'To date',type:'date',required:true},{key:'reason',label:'Reason',type:'textarea',required:true}]},
 {key:'parent-messages',label:'Parent–Teacher Messages',icon:MessageCircle,endpoint:'/api/parent-messages',description:'Private school-scoped messages between linked parents and school staff',fields:[{key:'student_id',label:'Student record ID',type:'number',required:true},{key:'recipient_user_id',label:'Recipient user ID',type:'number',required:true},{key:'subject',label:'Subject'},{key:'body',label:'Message',type:'textarea',required:true}]},
 {key:'library-books',label:'Library Books',icon:BookOpen,endpoint:'/api/library-books',description:'School library catalog, ISBN, categories, shelf locations and copy availability',fields:[{key:'school_id',label:'School',type:'school-select',required:true},{key:'title',label:'Book title',required:true},{key:'author',label:'Author'},{key:'isbn',label:'ISBN'},{key:'publisher',label:'Publisher'},{key:'category',label:'Category'},{key:'total_copies',label:'Total copies',type:'number',required:true},{key:'shelf_location',label:'Shelf location'}]},
 {key:'library-loans',label:'Library Issue & Return',icon:ClipboardCheck,endpoint:'/api/library-loans',description:'Issue books to students, track due dates and record returns',fields:[{key:'school_id',label:'School',type:'school-select',required:true},{key:'book_id',label:'Book record ID',type:'number',required:true},{key:'student_id',label:'Student record ID',type:'number',required:true},{key:'due_date',label:'Due date',type:'date',required:true}]},
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
 super_admin:['developer-control'],
 user:['dashboard','chatbot','approvals','students','staff','classes','vehicles','hostels','documents','maintenance','fee-structures','student-fees','payments','fee-reports','attendance','timetable','exams','report-cards','homework','student-leave','parent-messages','library-books','library-loans'],
 admin:['dashboard','chatbot','approvals','students','staff','classes','vehicles','hostels','documents','maintenance','fee-structures','student-fees','payments','fee-reports','attendance','timetable','exams','report-cards','homework','student-leave','parent-messages','library-books','library-loans','facility-requests','parent-relationships','notifications','certificate-management'],
 principal:['dashboard','chatbot','approvals','students','staff','classes','vehicles','hostels','documents','maintenance','fee-structures','student-fees','payments','fee-reports','attendance','timetable','exams','report-cards','homework','student-leave','parent-messages','library-books','library-loans','facility-requests','notifications','certificate-management'],
 vice_principal:['dashboard','chatbot','students','staff','classes','documents','maintenance','fee-reports','attendance','timetable','exams','report-cards','homework','student-leave','parent-messages','library-books','library-loans','facility-requests','notifications'],
 teacher:['dashboard','chatbot','students','classes','documents','attendance','timetable','exams','report-cards','homework','student-leave','parent-messages'],
 account:['dashboard','chatbot','students','fee-structures','student-fees','payments','fee-reports'],
 accountant:['dashboard','chatbot','students','fee-structures','student-fees','payments','fee-reports'],
 clerk:['dashboard','chatbot','students','student-fees','payments','documents'],
 office_assistant:['dashboard','chatbot','students','staff','documents','approvals'],
 librarian:['dashboard','chatbot','students','documents','library-books','library-loans'],
 lab_assistant:['dashboard','chatbot','documents','maintenance'],
 it_administrator:['dashboard','chatbot','staff','documents','maintenance','approvals'],
 transport_manager:['dashboard','chatbot','students','vehicles','documents','maintenance','facility-requests'],
 hostel_warden:['dashboard','chatbot','students','hostels','documents','maintenance','facility-requests'],
 security_guard:['dashboard','chatbot','students'],
 others:['dashboard','chatbot'],
 parent:['parent-portal']
}
const roleAccent:Record<string,string> = {
 super_admin:'#6654c7', user:'#0f766e', admin:'#0f766e', principal:'#0f766e',
 vice_principal:'#2563a6', teacher:'#39845d', account:'#a66a18', accountant:'#a66a18',
 clerk:'#0d8792', office_assistant:'#4975a8', librarian:'#7354a6',
 lab_assistant:'#357c8b', it_administrator:'#5968b5',
 transport_manager:'#b36b24', hostel_warden:'#9a5c86',
 security_guard:'#64748b', others:'#64748b', parent:'#267d9b'
}
const roleCatalog = Object.entries(roleLabels).filter(([key])=>key!=='super_admin'&&key!=='user'&&key!=='admin'&&key!=='accountant').map(([key,label])=>({
 role:label, roleKey:key,
 scope:roleDescriptions[key],
 level:key==='super_admin'?'Platform access':key==='parent'?'Linked-student access':'Role workspace'
}))

const DEMO_USERS = [
 {label:'Principal',email:'demo.principal@jovoo.in',schoolCode:'DEMO-SCHOOL'},
 {label:'School Admin',email:'demo.admin@jovoo.in',schoolCode:'DEMO-SCHOOL'},
 {label:'Accountant',email:'demo.accountant@jovoo.in',schoolCode:'DEMO-SCHOOL'},
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
const DEMO_PASSWORD = (import.meta as any).env?.VITE_DEMO_PASSWORD || ''

const money = (n:number) => new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(n || 0)

function Login({onLogin}:{onLogin:(token:string,user:User)=>void}) {
 const [mode,setMode]=useState<'signin'|'school'|'staff'|'verify'|'forgot'|'reset'|'mfa'>('signin')
 const [values,setValues]=useState({name:'',position:'Principal',email:'',password:'',school_name:'',school_code:'',institution_type:'school',role:'principal',code:''})
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
 const titles={signin:'Welcome back',mfa:'Verify your sign-in',school:'Register your institution',staff:'Join your school',verify:'Verify your email',forgot:'Recover password',reset:'Create a new password'}
 const descriptions={signin:'Enter your email and password. School users must also enter their school code.',mfa:'Enter the six-digit security code sent to your email address.',school:'Submit your institution and authorized representative details for EduNexus platform review.',staff:'Register under an existing school. Approval by a school user is required.',verify:'Enter the six-digit code sent to your email.',forgot:'Enter your registered email to request a reset code.',reset:'Verify the code and choose a new password.'}
 const isPasswordMode=['signin','school','staff','reset'].includes(mode)
 const passwordLabel=mode==='reset'?'New password':'Password'
 const submitLabel=mode==='signin'?'Continue securely':mode==='mfa'?'Verify and sign in':mode==='school'?'Register institution':mode==='staff'?'Request staff account':mode==='verify'?'Verify email':mode==='forgot'?'Send reset code':'Reset password'
 return <div className="auth-page">
  <aside className="auth-showcase">
   <div className="auth-showcase-inner">
    <div className="auth-brand"><div className="auth-brand-icon"><GraduationCap size={25}/></div><span>EduNexus</span></div>
    <div className="auth-showcase-copy">
     <span className="auth-kicker">EDUCATION MANAGEMENT PLATFORM</span>
     <h2>Everything your institution needs.<br/><em>All in one place.</em></h2>
     <p>Bring your institution community, academic operations and financial workflows together in one secure workspace.</p>
    </div>
    <div className="auth-visual" aria-hidden="true">
     <div className="auth-orbit orbit-one"/><div className="auth-orbit orbit-two"/>
     <div className="auth-campus-card"><div className="campus-sun"/><div className="campus-building"><div className="campus-roof"/><div className="campus-columns"><i/><i/><i/><i/></div><div className="campus-door"/></div><div className="campus-ground"/></div>
     <div className="auth-float-card float-students"><Users size={17}/><span><strong>One school community</strong><small>Students · Staff · Families</small></span></div>
     <div className="auth-float-card float-secure"><ShieldCheck size={19}/><span><strong>Secure workspace</strong><small>Role-based access</small></span></div>
    </div>
    <div className="auth-showcase-foot"><span><ShieldCheck size={14}/> Built for education teams</span><span>Learn · Manage · Grow</span></div>
   </div>
  </aside>
  <main className="auth-main">
   <div className="auth-mobile-brand"><div className="auth-brand-icon"><GraduationCap size={22}/></div><strong>EduNexus</strong></div>
   <section className="auth-form-shell">
    <form className="auth-form-card" onSubmit={submit}>
     <div className="auth-form-top"><span className="auth-step-icon">{mode==='school'?<Building2 size={20}/>:mode==='staff'?<Users size={20}/>:mode==='verify'?<ShieldCheck size={20}/>:<GraduationCap size={20}/>}</span><span className="auth-form-context">{mode==='school'?'INSTITUTION SETUP':mode==='staff'?'STAFF REGISTRATION':mode==='signin'?'YOUR SCHOOL WORKSPACE':'ACCOUNT ACCESS'}</span></div>
     <p className="eyebrow">EDUCATION MANAGEMENT PLATFORM</p>
     <h1>{titles[mode]}</h1>
     <p className="auth-intro">{descriptions[mode]}</p>
     {mode==='signin'&&DEMO_MODE&&<div className="panel demo-login-panel">
      <div className="panel-heading"><div><h3>Practice with a demo role</h3><p>Select a sample account to fill in its login details.</p></div><ShieldCheck size={20}/></div>
      <div className="auth-field"><label htmlFor="demo-role-select">Choose demo role</label><select id="demo-role-select" defaultValue="" onChange={e=>{const demo=DEMO_USERS.find(item=>item.email===e.target.value);if(demo)setValues(old=>({...old,email:demo.email,school_code:demo.schoolCode,password:DEMO_PASSWORD||old.password}))}}>
       <option value="">Select a role…</option>{DEMO_USERS.map(demo=><option key={demo.email} value={demo.email}>{demo.label} — {demo.email}</option>)}
      </select></div>

     </div>}
     {mode==='school'&&<>
      <div className="auth-section-label"><span>01</span><div><strong>Authorized representative</strong><small>Primary contact and first school account</small></div></div>
      <div className="auth-field"><label htmlFor="admin-name">Full name</label><input id="admin-name" value={values.name} onChange={e=>set('name',e.target.value)} placeholder="Enter the authorized person's full name" autoComplete="name" required/></div>
      <div className="auth-field"><label htmlFor="admin-position">Position / Designation</label><select id="admin-position" value={values.position} onChange={e=>set('position',e.target.value)} required><option value="Principal">Principal</option><option value="Head of Institution">Head of Institution</option><option value="Dean">Dean</option><option value="Director">Director</option><option value="School Director">School Director</option><option value="Correspondent">Correspondent</option><option value="School Administrator">School Administrator</option><option value="Chairperson">Chairperson</option><option value="Other">Other</option></select><small>Select the position of the person submitting this institution registration.</small></div>
      <div className="auth-section-label auth-section-admin"><span>02</span><div><strong>Institution information</strong><small>Tell us about your organisation</small></div></div>
      <div className="auth-field"><label htmlFor="school-type">Institution type</label><select id="school-type" value={values.institution_type} onChange={e=>set('institution_type',e.target.value)} required><option value="school">School</option><option value="college">College</option><option value="university">University</option><option value="coaching_centre">Coaching centre</option><option value="training_institute">Training institute</option><option value="other">Other educational institution</option></select><small>Choose the type that best describes your organisation. Academic setup can be configured after onboarding.</small></div><div className="auth-field"><label htmlFor="school-name">Institution name</label><input id="school-name" value={values.school_name} onChange={e=>set('school_name',e.target.value)} placeholder="Enter your institution name" autoComplete="organization" required/></div>
      <div className="auth-field"><label htmlFor="school-code">Institution code</label><input id="school-code" value={values.school_code} onChange={e=>set('school_code',e.target.value.toUpperCase())} placeholder="Create a unique school code" required/><small>This code identifies your institution for staff and learner registration.</small></div>
      <div className="auth-section-label auth-section-admin"><span>03</span><div><strong>Account credentials</strong><small>Secure your EduNexus administrator account</small></div></div>
     </>}
     {mode==='staff'&&<>
      <div className="auth-field"><label htmlFor="staff-name">Full name</label><input id="staff-name" value={values.name} onChange={e=>set('name',e.target.value)} placeholder="Enter your full name" autoComplete="name" required/></div>
      <div className="auth-field"><label htmlFor="staff-school-code">School code</label><input id="staff-school-code" value={values.school_code} onChange={e=>set('school_code',e.target.value.toUpperCase())} placeholder="Enter your school's code" required/></div>
      <div className="auth-field"><label htmlFor="staff-role">Account type</label><select id="staff-role" value={values.role} onChange={e=>set('role',e.target.value)}>{Object.entries(roleLabels).filter(([key])=>key!=='super_admin'&&key!=='parent'&&key!=='user'&&key!=='admin'&&key!=='accountant').map(([key,label])=><option key={key} value={key}>{label}</option>)}<option value="parent">Parent (linked students only)</option></select></div>
     </>}
     {mode==='signin'&&<div className="auth-field"><label htmlFor="login-school-code">School code <span className="muted">(school accounts only)</span></label><input id="login-school-code" value={values.school_code} onChange={e=>set('school_code',e.target.value.toUpperCase())} placeholder="Authorized platform account only" autoCapitalize="characters"/><small>Only authorized platform accounts may sign in without an institution code. All institution users must enter their institution code.</small></div>}
      {['signin','school','staff','verify','forgot','reset'].includes(mode)&&<div className="auth-field"><label htmlFor="auth-email">Email address</label><div className="auth-input-wrap"><Mail size={17}/><input id="auth-email" type="email" value={values.email} onChange={e=>set('email',e.target.value)} placeholder="you@school.com" required autoComplete="email"/></div></div>}
     {isPasswordMode&&<div className="auth-field"><label htmlFor="auth-password">{passwordLabel}</label><div className="auth-input-wrap"><LockKeyhole size={17}/><input id="auth-password" type={showPassword?'text':'password'} value={values.password} onChange={e=>set('password',e.target.value)} placeholder={mode==='signin'?'Enter your password':'Create a strong password'} minLength={mode==='signin'?undefined:12} required autoComplete={mode==='signin'?'current-password':'new-password'}/><button className="auth-password-toggle" type="button" onClick={()=>setShowPassword(v=>!v)} aria-label={showPassword?'Hide password':'Show password'}>{showPassword?<EyeOff size={17}/>:<Eye size={17}/>}</button></div>{mode!=='signin'&&<small className="auth-help">Use at least 12 characters.</small>}</div>}
     {['verify','reset','mfa'].includes(mode)&&<div className="auth-field"><label htmlFor="auth-code">{mode==='mfa'?'Sign-in security code':'Email verification / reset code'}</label><div className="auth-input-wrap"><ShieldCheck size={17}/><input id="auth-code" inputMode="numeric" pattern="[0-9]{6}" maxLength={6} value={values.code} onChange={e=>set('code',e.target.value.replace(/\D/g,'').slice(0,6))} placeholder="6-digit code" required/></div></div>}
     {error&&<div className="error auth-message" role="alert">{error}</div>}{notice&&<div className="success auth-message" role="status">{notice}</div>}
     <button className="auth-submit" disabled={busy}>{busy?'Please wait…':<>{submitLabel}<ArrowRight size={17}/></>}</button>
     <div className="auth-links">{mode==='signin'?<><button type="button" onClick={()=>{setMode('school');setError('');setNotice('')}}>Register a school</button><button type="button" onClick={()=>{setMode('staff');setError('');setNotice('')}}>Register as staff</button><button type="button" onClick={()=>{setMode('forgot');setError('');setNotice('')}}>Forgot password?</button></>:<><button type="button" onClick={()=>{setMode('signin');setError('');setNotice('')}}><ArrowLeft size={14}/> Back to sign in</button>{mode==='mfa'&&<button type="button" onClick={()=>{setMode('signin');setMfaToken('');set('code','');setError('');setNotice('')}}>Start over</button>}{mode==='verify'&&<button type="button" onClick={async()=>{try{const d=await call('/api/auth/resend-verification',{email:values.email});setNotice(d.message);setError('')}catch(e:any){setError(e.message)}}}>Resend code</button>}</>}</div>
    </form>
    <p className="auth-copyright">© {new Date().getFullYear()} EduNexus · Education management platform</p>
   </section>
  </main>
 </div>
}

function ParentPortal({request,userRole,currentUserId,refreshKey,onLoadingChange,token}:{request:(url:string,options?:RequestInit)=>Promise<any>;userRole:string;currentUserId:number;refreshKey:number;onLoadingChange:(loading:boolean)=>void;token:string}) {
 const [children,setChildren]=useState<any[]>([]);
 const [activeParentSection,setActiveParentSection]=useState('home');
 const [parentChatQuestion,setParentChatQuestion]=useState('');
 const [parentChatReply,setParentChatReply]=useState('');
 const [childId,setChildId]=useState('');
 const [fees,setFees]=useState<any[]>([]);
 const [attendance,setAttendance]=useState<any[]>([]);
 const [homework,setHomework]=useState<any[]>([]);
 const [timetable,setTimetable]=useState<any[]>([]);
 const [examResults,setExamResults]=useState<any[]>([]);
 const [reportYear,setReportYear]=useState('all');
 const [reportMonth,setReportMonth]=useState('all');
 const [reportExam,setReportExam]=useState('all');
 const [reportSubject,setReportSubject]=useState('all');
 const [reportQuestion,setReportQuestion]=useState('');
 const [reportAnswer,setReportAnswer]=useState('');
 const [certificateApplications,setCertificateApplications]=useState<any[]>([]);
 const [facilityData,setFacilityData]=useState<any>({transport:null,hostel:null});
 const [facilityRequests,setFacilityRequests]=useState<any[]>([]);
 const [facilityType,setFacilityType]=useState<'transport'|'hostel'>('transport');
 const [facilityRequestType,setFacilityRequestType]=useState('pickup_change');
 const [facilityReason,setFacilityReason]=useState('');
 const [facilityDetails,setFacilityDetails]=useState({vehicle_id:'',route_name:'',pickup_point:'',drop_point:'',pickup_time:'',drop_time:'',hostel_id:'',room_no:'',bed_no:''});
 const [facilityError,setFacilityError]=useState('');
 const [facilityMessage,setFacilityMessage]=useState('');
 const [facilityLoading,setFacilityLoading]=useState(false);
 const [facilitySubmitting,setFacilitySubmitting]=useState(false);
 const [leaveRequests,setLeaveRequests]=useState<any[]>([]);
 const [leaveStart,setLeaveStart]=useState('');
 const [leaveEnd,setLeaveEnd]=useState('');
 const [leaveReason,setLeaveReason]=useState('');
 const [leaveError,setLeaveError]=useState('');
 const [leaveMessage,setLeaveMessage]=useState('');
 const [leaveSubmitting,setLeaveSubmitting]=useState(false);
 const [messageContacts,setMessageContacts]=useState<any[]>([]);
 const [parentMessages,setParentMessages]=useState<any[]>([]);
 const [messageRecipient,setMessageRecipient]=useState('');
 const [messageSubject,setMessageSubject]=useState('');
 const [messageBody,setMessageBody]=useState('');
 const [messageError,setMessageError]=useState('');
 const [messageNotice,setMessageNotice]=useState('');
 const [messageSubmitting,setMessageSubmitting]=useState(false);
 const [messagesLoading,setMessagesLoading]=useState(false);
 const [error,setError]=useState('');
 const [feesError,setFeesError]=useState('');
 const [attendanceError,setAttendanceError]=useState('');
 const [homeworkError,setHomeworkError]=useState('');
 const [timetableError,setTimetableError]=useState('');
 const [examResultsError,setExamResultsError]=useState('');
 const [certificateError,setCertificateError]=useState('');
 const [certificateMessage,setCertificateMessage]=useState('');
 const [certificateType,setCertificateType]=useState('bonafide');
 const [certificatePurpose,setCertificatePurpose]=useState('');
 const [certificateSubmitting,setCertificateSubmitting]=useState(false);
 const [loading,setLoading]=useState(true);
 const [feesLoading,setFeesLoading]=useState(false);
 const [attendanceLoading,setAttendanceLoading]=useState(false);
 const [homeworkLoading,setHomeworkLoading]=useState(false);
 const [timetableLoading,setTimetableLoading]=useState(false);
 const [examResultsLoading,setExamResultsLoading]=useState(false);
 const [certificateApplicationsLoading,setCertificateApplicationsLoading]=useState(false);

 useEffect(()=>{
  if(userRole!=='parent'){
   setLoading(false);
   onLoadingChange(false);
   return;
  }
  let active=true;
  setLoading(true);
  setError('');
  onLoadingChange(true);
  request('/api/parent/children')
   .then((data:any[])=>{
    if(!active)return;
    setChildren(data);
    setChildId(current=>data.some(child=>String(child.id)===current)?current:(data.length?String(data[0].id):''));
   })
   .catch((e:any)=>{if(active)setError(e.message)})
   .finally(()=>{if(active){setLoading(false);onLoadingChange(false)}});
  return()=>{active=false};
 },[userRole,refreshKey]);

 useEffect(()=>{
  let active=true;
  setFees([]);
  setAttendance([]);
  setHomework([]);
  setTimetable([]);
  setExamResults([]);
  setCertificateApplications([]);
  setFacilityData({transport:null,hostel:null});
  setFacilityRequests([]);
  setLeaveRequests([]);
  setLeaveError('');
  setLeaveMessage('');
  setMessageContacts([]);
  setParentMessages([]);
  setMessageError('');
  setMessageNotice('');
  setFacilityError('');
  setFacilityMessage('');
  setFeesError('');
  setAttendanceError('');
  setHomeworkError('');
  setTimetableError('');
  setExamResultsError('');
  setCertificateError('');
  setCertificateMessage('');
  if(childId&&userRole==='parent'){
   setFeesLoading(true);
   setAttendanceLoading(true);
   const encodedChildId=encodeURIComponent(childId);
   request('/api/parent/children/'+encodedChildId+'/fees')
    .then((data:any[])=>{if(active)setFees(data)})
    .catch((e:any)=>{if(active)setFeesError(e.message)})
    .finally(()=>{if(active)setFeesLoading(false)});
   request('/api/parent/children/'+encodedChildId+'/attendance?limit=90')
    .then((data:any[])=>{if(active)setAttendance(data)})
    .catch((e:any)=>{if(active)setAttendanceError(e.message)})
    .finally(()=>{if(active)setAttendanceLoading(false)});
   setHomeworkLoading(true);
   request('/api/parent/children/'+encodedChildId+'/homework')
    .then((data:any[])=>{if(active)setHomework(data)})
    .catch((e:any)=>{if(active)setHomeworkError(e.message||'Could not load homework')})
    .finally(()=>{if(active)setHomeworkLoading(false)});
   setTimetableLoading(true);
   request('/api/parent/children/'+encodedChildId+'/timetable')
    .then((data:any[])=>{if(active)setTimetable(data)})
    .catch((e:any)=>{if(active)setTimetableError(e.message||'Could not load class timetable')})
    .finally(()=>{if(active)setTimetableLoading(false)});
   setExamResultsLoading(true);
   request('/api/parent/children/'+encodedChildId+'/exam-results')
    .then((data:any[])=>{if(active)setExamResults(data)})
    .catch((e:any)=>{if(active)setExamResultsError(e.message)})
    .finally(()=>{if(active)setExamResultsLoading(false)});
   setFacilityLoading(true);
   Promise.all([
    request('/api/parent/children/'+encodedChildId+'/facilities'),
    request('/api/parent/children/'+encodedChildId+'/facility-requests')
   ]).then(([facilities,requests])=>{if(active){setFacilityData(facilities);setFacilityRequests(requests)}})
    .catch((e:any)=>{if(active)setFacilityError(e.message||'Could not load transport and hostel details')})
    .finally(()=>{if(active)setFacilityLoading(false)});
   request('/api/parent-portal/leave')
    .then((data:any[])=>{if(active)setLeaveRequests(data.filter(item=>String(item.student_id)===String(childId)))})
    .catch((e:any)=>{if(active)setLeaveError(e.message||'Could not load leave requests')});
   setMessagesLoading(true);
   Promise.all([
    request('/api/parent/children/'+encodedChildId+'/message-contacts'),
    request('/api/parent-messages')
   ]).then(([contacts,messages])=>{if(active){setMessageContacts(contacts);setMessageRecipient(current=>contacts.some((c:any)=>String(c.id)===current)?current:(contacts.length?String(contacts[0].id):''));setParentMessages(messages.filter((item:any)=>String(item.student_id)===String(childId)))}})
    .catch((e:any)=>{if(active)setMessageError(e.message||'Could not load parent-teacher messages')})
    .finally(()=>{if(active)setMessagesLoading(false)});
   setCertificateApplicationsLoading(true);
   request('/api/parent/children/'+encodedChildId+'/certificate-applications')
    .then((data:any[])=>{if(active)setCertificateApplications(data)})
    .catch((e:any)=>{if(active)setCertificateError(e.message)})
    .finally(()=>{if(active)setCertificateApplicationsLoading(false)});
  }else{
   setFeesLoading(false);
   setAttendanceLoading(false);
   setHomeworkLoading(false);
   setTimetableLoading(false);
   setExamResultsLoading(false);
   setCertificateApplicationsLoading(false);
  }
  return()=>{active=false};
 },[childId,userRole,refreshKey]);

 const reportYears=useMemo(()=>Array.from(new Set(examResults.map(r=>r.academic_year).filter(Boolean))).sort().reverse(),[examResults]);
 const reportExams=useMemo(()=>Array.from(new Set(examResults.map(r=>r.exam_name).filter(Boolean))).sort(),[examResults]);
 const reportSubjects=useMemo(()=>Array.from(new Set(examResults.map(r=>r.subject).filter(Boolean))).sort(),[examResults]);
 const filteredExamResults=useMemo(()=>examResults.filter(r=>{
  const d=new Date(r.exam_date+'T00:00:00');
  return (reportYear==='all'||r.academic_year===reportYear)&&(reportMonth==='all'||String(d.getMonth()+1)===reportMonth)&&(reportExam==='all'||r.exam_name===reportExam)&&(reportSubject==='all'||r.subject===reportSubject);
 }).sort((a,b)=>a.exam_date.localeCompare(b.exam_date)),[examResults,reportYear,reportMonth,reportExam,reportSubject]);
 const reportStats=useMemo(()=>{
  const obtained=filteredExamResults.reduce((sum,r)=>sum+Number(r.marks_obtained||0),0),maximum=filteredExamResults.reduce((sum,r)=>sum+Number(r.max_marks||0),0),passed=filteredExamResults.filter(r=>r.result==='passed').length;
  return {count:filteredExamResults.length,obtained,maximum,percentage:maximum?obtained/maximum*100:0,passed,failed:filteredExamResults.length-passed};
 },[filteredExamResults]);
 const subjectProgress=useMemo(()=>{
  const groups=new Map<string,{obtained:number;maximum:number;count:number}>();
  filteredExamResults.forEach(r=>{const key=r.subject||'Other',v=groups.get(key)||{obtained:0,maximum:0,count:0};v.obtained+=Number(r.marks_obtained||0);v.maximum+=Number(r.max_marks||0);v.count++;groups.set(key,v)});
  return Array.from(groups,([subject,v])=>({subject,percentage:v.maximum?v.obtained/v.maximum*100:0,obtained:v.obtained,maximum:v.maximum,count:v.count})).sort((a,b)=>b.percentage-a.percentage);
 },[filteredExamResults]);
 const examProgress=useMemo(()=>{
  const groups=new Map<string,{label:string;date:string;obtained:number;maximum:number}>();
  filteredExamResults.forEach(r=>{const key=r.exam_name+'|'+r.exam_date,v=groups.get(key)||{label:r.exam_name,date:r.exam_date,obtained:0,maximum:0};v.obtained+=Number(r.marks_obtained||0);v.maximum+=Number(r.max_marks||0);groups.set(key,v)});
  return Array.from(groups.values()).sort((a,b)=>a.date.localeCompare(b.date)).map(v=>({...v,percentage:v.maximum?v.obtained/v.maximum*100:0}));
 },[filteredExamResults]);
 function askAcademicReport(e:FormEvent<HTMLFormElement>){
  e.preventDefault();const q=reportQuestion.trim().toLowerCase();if(!q)return;
  let year='all',month='all',exam='all',subject='all';
  const matchedYear=reportYears.find(y=>q.includes(String(y).toLowerCase()));if(matchedYear)year=matchedYear;
  const monthNames=['january','february','march','april','may','june','july','august','september','october','november','december'];
  const monthIndex=monthNames.findIndex(m=>q.includes(m));if(monthIndex>=0)month=String(monthIndex+1);
  const matchedExam=reportExams.find(x=>q.includes(x.toLowerCase()));if(matchedExam)exam=matchedExam;
  const matchedSubject=reportSubjects.find(x=>q.includes(x.toLowerCase()));if(matchedSubject)subject=matchedSubject;
  if(q.includes('all year')||q.includes('entire year')||q.includes('annual')||q.includes('whole year')){year='all';month='all'}
  setReportYear(year);setReportMonth(month);setReportExam(exam);setReportSubject(subject);
  const labels=[year!=='all'?year:'all available years',month!=='all'?monthNames[Number(month)-1]:'all months',exam!=='all'?exam:'all exams',subject!=='all'?subject:'all subjects'];
  setReportAnswer('Showing '+labels.join(' · ')+'. '+(q.includes('compare')?'The exam trend below compares the available exam records.':'Your summary and graphs have been updated using published marks.'));
  setReportQuestion('');
 }
 async function submitLeaveRequest(e:FormEvent<HTMLFormElement>){
  e.preventDefault();
  if(!childId||!leaveStart||!leaveEnd||!leaveReason.trim()||leaveSubmitting)return;
  setLeaveSubmitting(true);setLeaveError('');setLeaveMessage('');
  try{
   const result=await request('/api/parent-portal/leave',{method:'POST',body:JSON.stringify({
    student_id:Number(childId),start_date:leaveStart,end_date:leaveEnd,reason:leaveReason.trim()
   })});
   setLeaveRequests(old=>[result,...old]);setLeaveReason('');
   setLeaveMessage('Leave application submitted. You can track its status below.');
  }catch(e:any){setLeaveError(e.message||'Could not submit leave application')}
  finally{setLeaveSubmitting(false)}
 }
 async function sendParentMessage(e:FormEvent<HTMLFormElement>){
  e.preventDefault();
  if(!childId||!messageRecipient||!messageBody.trim()||messageSubmitting)return;
  setMessageSubmitting(true);setMessageError('');setMessageNotice('');
  try{
   const result=await request('/api/parent-messages',{method:'POST',body:JSON.stringify({
    student_id:Number(childId),recipient_user_id:Number(messageRecipient),subject:messageSubject.trim(),body:messageBody.trim()
   })});
   setParentMessages(old=>[...old,result]);setMessageBody('');
   setMessageNotice('Message sent to '+(messageContacts.find(c=>String(c.id)===messageRecipient)?.name||'school staff')+'.');
  }catch(e:any){setMessageError(e.message||'Could not send message')}
  finally{setMessageSubmitting(false)}
 }
 async function submitFacilityRequest(e:FormEvent<HTMLFormElement>){
  e.preventDefault();
  if(!childId||!facilityReason.trim()||facilitySubmitting)return;
  setFacilitySubmitting(true);setFacilityError('');setFacilityMessage('');
  const keys=facilityType==='transport'
   ?['vehicle_id','route_name','pickup_point','drop_point','pickup_time','drop_time']
   :['hostel_id','room_no','bed_no'];
  const details:Record<string,string|number>={};
  keys.forEach(key=>{const value=(facilityDetails as any)[key];if(value.trim()){details[key]=(key==='vehicle_id'||key==='hostel_id')?Number(value):value.trim()}});
  try{
   const result=await request('/api/parent/children/'+encodeURIComponent(childId)+'/facility-requests',{
    method:'POST',body:JSON.stringify({facility_type:facilityType,request_type:facilityRequestType,reason:facilityReason.trim(),details})
   });
   setFacilityRequests(old=>[result,...old]);setFacilityReason('');
   setFacilityMessage('Request submitted. Your school team must approve it before any official allocation changes.');
  }catch(err:any){setFacilityError(err.message||'Could not submit facility request')}
  finally{setFacilitySubmitting(false)}
 }
 async function submitCertificate(e:FormEvent<HTMLFormElement>){
  e.preventDefault();
  if(!childId||!certificatePurpose.trim()||certificateSubmitting)return;
  setCertificateSubmitting(true);
  setCertificateError('');
  setCertificateMessage('');
  try{
   const result=await request('/api/parent/children/'+encodeURIComponent(childId)+'/certificate-applications',{
    method:'POST',
    body:JSON.stringify({student_id:Number(childId),certificate_type:certificateType,purpose:certificatePurpose.trim()})
   });
   setCertificateApplications(old=>[result,...old]);
   setCertificatePurpose('');
   setCertificateMessage('Certificate application submitted. Your school will review it and update the status here.');
  }catch(err:any){setCertificateError(err.message||'Could not submit certificate application')}
  finally{setCertificateSubmitting(false)}
 }
 return <div className="panel">
  <div className="panel-heading">
   <div><h3>Parent Workspace</h3><p>One secure place to view school information for every child linked to your parent account.</p></div>
   <Users size={20}/>
  </div>
  {userRole!=='parent'?<div className="empty-state"><strong>Parent account required</strong><p>The Parent Portal is available only to Parent accounts. Switch to a Parent demo account to view linked students, attendance, and fee balances.</p></div>
  :loading?<div className="empty-state"><strong>Loading linked students…</strong><p>Your family information will appear here shortly.</p></div>
  :error?<div className="error" role="alert">{error}</div>
  :children.length===0?<div className="empty-state"><strong>No student profiles linked</strong><p>Ask your school administrator to link your parent account to your child.</p></div>
  :<>
   <section className="parent-family-workspace" aria-label="Parent workspace">
    <header className="parent-workspace-header">
     <div><span className="parent-workspace-eyebrow">EDUNEXUS · FAMILY WORKSPACE</span><h2>Your family, one workspace</h2><p>All children linked to your verified parent account, with their school services in one place.</p></div>
     <div className="parent-workspace-secure"><ShieldCheck size={17}/><span>Secure parent access</span></div>
    </header>
    <section className="parent-children-section" aria-label="Linked children">
     <div className="parent-children-heading"><div><h3>Linked children</h3><p>{children.length} {children.length===1?'student profile':'student profiles'} available to your account</p></div><span>Choose a child to view their details</span></div>
     <div className="parent-child-cards">
      {children.map((child:any)=>{const selected=String(child.id)===String(childId);const initials=String(child.full_name||'Student').split(' ').filter(Boolean).slice(0,2).map((part:string)=>part[0]).join('').toUpperCase();return <button type="button" key={child.id} className={'parent-child-card '+(selected?'selected':'')} aria-pressed={selected} onClick={()=>{setChildId(String(child.id));setActiveParentSection('home')}}>
       <span className="parent-child-avatar">{initials||'ST'}</span><span className="parent-child-details"><strong>{child.full_name}</strong><small>{child.admission_no||'Admission details unavailable'}</small><small>{[child.class_name,child.section].filter(Boolean).join(' · ')||'Class details unavailable'}</small></span><span className="parent-child-selected">{selected?'Selected':'View profile'}</span>
      </button>})}
     </div>
    </section>
    <nav className="parent-service-nav" aria-label="Family services">
     {[
      {key:'home',label:'Overview',icon:LayoutDashboard},
      {key:'notifications',label:'Notifications',icon:Bell},
      {key:'attendance',label:'Attendance',icon:CalendarCheck},
      {key:'homework',label:'Homework',icon:BookOpen},
      {key:'timetable',label:'Timetable',icon:CalendarDays},
      {key:'fees',label:'Fees',icon:Wallet},
      {key:'academic',label:'Academic progress',icon:Award},
      {key:'leave',label:'Leave',icon:ClipboardList},
      {key:'messages',label:'Messages',icon:MessageCircle},
      {key:'facilities',label:'Transport & hostel',icon:Bus},
      {key:'certificates',label:'Certificates',icon:FileText}
     ].map(item=>{const Icon=item.icon;return <button type="button" key={item.key} className={'parent-service-link '+(activeParentSection===item.key?'active':'')} aria-current={activeParentSection===item.key?'page':undefined} onClick={()=>setActiveParentSection(item.key)}><Icon size={16}/><span>{item.label}</span></button>})}
    </nav>
    <main className="parent-workspace-content">
     {activeParentSection==='home'&&<section className="parent-chat-home">
      <div className="parent-chat-welcome"><div className="parent-chat-avatar"><GraduationCap size={22}/></div><div><span>EDUNEXUS FAMILY ASSISTANT</span><h3>Hello! How can I help with {children.find(c=>String(c.id)===String(childId))?.full_name||'your child'} today?</h3><p>Ask a question or choose a service from the family menu. I’ll show information published by your school.</p></div></div>
      <div className="parent-chat-summary">
       <button type="button" onClick={()=>setActiveParentSection('attendance')}><CalendarCheck size={18}/><span>Attendance</span><strong>{attendance.length} records</strong></button>
       <button type="button" onClick={()=>setActiveParentSection('homework')}><BookOpen size={18}/><span>Homework</span><strong>{homework.length} assignments</strong></button>
       <button type="button" onClick={()=>setActiveParentSection('academic')}><Award size={18}/><span>Exam results</span><strong>{examResults.length} published</strong></button>
       <button type="button" onClick={()=>setActiveParentSection('fees')}><Wallet size={18}/><span>Fee records</span><strong>{fees.length} records</strong></button>
      </div>
      <div className="parent-chat-thread">
       <div className="parent-chat-message assistant"><span className="parent-chat-mini-avatar"><MessageCircle size={15}/></span><div><strong>EduNexus Assistant</strong><p>Welcome to your family dashboard. You can ask me to open your child’s attendance, homework, timetable, fees, academic progress, leave, messages, transport, hostel or certificate information.</p></div></div>
       {parentChatReply&&<div className="parent-chat-message assistant"><span className="parent-chat-mini-avatar"><MessageCircle size={15}/></span><div><strong>EduNexus Assistant</strong><p>{parentChatReply}</p></div></div>}
      </div>
      <form className="parent-chat-composer" onSubmit={e=>{e.preventDefault();const q=parentChatQuestion.trim().toLowerCase();if(!q)return;const routes:[string,string,string][]=[['attendance','attendance','attendance'],['homework','homework','homework'],['assignment','homework','homework'],['timetable','timetable','timetable'],['class schedule','timetable','timetable'],['fee','fees','fee'],['payment','fees','fee'],['exam','academic','academic progress'],['mark','academic','academic progress'],['result','academic','academic progress'],['leave','leave','leave applications'],['message','messages','teacher messages'],['teacher','messages','teacher messages'],['transport','facilities','transport and hostel'],['hostel','facilities','transport and hostel'],['certificate','certificates','certificates']];const match=routes.find(([word])=>q.includes(word));if(match){setActiveParentSection(match[1]);setParentChatReply('Opening '+match[2]+' for '+(children.find(c=>String(c.id)===String(childId))?.full_name||'your child')+'. The page will show the school records available to your account.')}else{setParentChatReply('I can help navigate your family portal. Try asking about attendance, homework, timetable, fees, exam results, leave, teacher messages, transport, hostel or certificates. For school decisions or personal questions, send a message to an approved teacher.')}setParentChatQuestion('')}}>
       <input value={parentChatQuestion} onChange={e=>setParentChatQuestion(e.target.value)} placeholder="Ask about attendance, homework, fees, exam results…" aria-label="Ask the family assistant"/>
       <button className="primary" disabled={!parentChatQuestion.trim()}><MessageCircle size={17}/> Send</button>
      </form>
      <div className="parent-chat-suggestions"><span>TRY ASKING</span>{['Show attendance','Any homework?','Show exam results','Check fee balance','Apply for leave'].map((q,i)=><button type="button" key={q} onClick={()=>{const route=['attendance','homework','academic','fees','leave'][i];setActiveParentSection(route);setParentChatReply('Opening '+q.toLowerCase()+'.')}}>{q}</button>)}</div>
     </section>}
   {activeParentSection==='attendance'&&(   <section className="parent-portal-section">
    <div className="panel-heading"><div><h4>Recent attendance</h4><p>Latest attendance records for the selected student.</p></div></div>
    {attendanceError?<div className="error" role="alert">{attendanceError}</div>
    :<div className="table-wrap">
     <table>
      <thead><tr><th>Date</th><th>Status</th></tr></thead>
      <tbody>
       {attendance.map(record=><tr key={record.id}><td>{record.attendance_date}</td><td><span className="status-badge">{record.status}</span></td></tr>)}
       {attendanceLoading&&<tr><td colSpan={2}>Loading attendance…</td></tr>}
       {!attendanceLoading&&!attendance.length&&<tr><td colSpan={2}>No attendance has been recorded for this student yet. Once school staff mark attendance, it will appear here.</td></tr>}
      </tbody>
     </table>
    </div>}
   </section>)}

   {activeParentSection==='homework'&&(   <section className="parent-portal-section parent-homework-section">
    <div className="panel-heading"><div><h4>Homework and assignments</h4><p>Class and section assignments, instructions, due dates and teacher-shared attachments.</p></div></div>
    {homeworkError?<div className="error" role="alert">{homeworkError}</div>:<div className="table-wrap">
     <table><thead><tr><th>Subject</th><th>Assignment</th><th>Instructions</th><th>Due date</th><th>Attachment</th></tr></thead>
      <tbody>
       {homework.map(item=><tr key={item.id}><td>{item.subject}</td><td><strong>{item.title}</strong></td><td>{item.description||'—'}</td><td>{item.due_date}</td><td>{item.attachment_url?<a href={item.attachment_url} target="_blank" rel="noreferrer">View attachment</a>:'—'}</td></tr>)}
       {homeworkLoading&&<tr><td colSpan={5}>Loading homework…</td></tr>}
       {!homeworkLoading&&!homework.length&&<tr><td colSpan={5}>No homework has been published for this class and section yet.</td></tr>}
      </tbody>
     </table>
    </div>}
   </section>)}

   {activeParentSection==='timetable'&&(   <section className="parent-portal-section parent-timetable-section">
    <div className="panel-heading"><div><h4>Class timetable</h4><p>Weekly periods for the selected student's class and section.</p></div></div>
    {timetableError?<div className="error" role="alert">{timetableError}</div>:<div className="table-wrap">
     <table><thead><tr><th>Day</th><th>Period</th><th>Time</th><th>Subject</th><th>Teacher</th><th>Room</th></tr></thead>
      <tbody>
       {timetable.map(item=><tr key={item.id}><td>{item.day_of_week}</td><td>{item.period}</td><td>{item.start_time} – {item.end_time}</td><td><strong>{item.subject}</strong></td><td>{item.teacher_name||'—'}</td><td>{item.room||'—'}</td></tr>)}
       {timetableLoading&&<tr><td colSpan={6}>Loading timetable…</td></tr>}
       {!timetableLoading&&!timetable.length&&<tr><td colSpan={6}>No timetable has been published for this class and section yet.</td></tr>}
      </tbody>
     </table>
    </div>}
   </section>)}

   {activeParentSection==='fees'&&(   <section className="parent-portal-section">
    <div className="panel-heading"><div><h4>Fee balances</h4><p>Fee information for the selected student.</p></div></div>
    {feesError?<div className="error" role="alert">{feesError}</div>
    :<div className="table-wrap">
     <table>
      <thead><tr><th>Fee category</th><th>Academic year</th><th>Total</th><th>Paid</th><th>Balance</th><th>Status</th></tr></thead>
      <tbody>
       {fees.map(f=><tr key={f.fee_id}><td>{f.category}</td><td>{f.academic_year}</td><td>{money(f.total)}</td><td>{money(f.paid)}</td><td><strong>{money(f.balance)}</strong></td><td><span className="status-badge">{f.status}</span></td></tr>)}
       {feesLoading&&<tr><td colSpan={6}>Loading fee balances…</td></tr>}
       {!feesLoading&&!fees.length&&<tr><td colSpan={6}>No fee records found.</td></tr>}
      </tbody>
     </table>
    </div>}
   </section>)}

   {activeParentSection==='academic'&&(   <section className="parent-portal-section parent-academic-report">
    <div className="panel-heading"><div><h4>Student academic progress</h4><p>Explore published marks by academic year, month, exam or subject.</p></div><Award size={20}/></div>
    {examResultsError?<div className="error" role="alert">{examResultsError}</div>:<>
     <div className="academic-chat">
      <div className="academic-chat-heading"><MessageCircle size={17}/><div><strong>Ask about academic performance</strong><span>Try “Show March results”, “Compare exams”, or “Show the entire year”.</span></div></div>
      <form onSubmit={askAcademicReport} className="academic-chat-form"><input value={reportQuestion} onChange={e=>setReportQuestion(e.target.value)} placeholder="Ask for a month, academic year, exam or subject…" aria-label="Ask about academic performance"/><button className="primary" disabled={!reportQuestion.trim()}>Show report</button></form>
      {reportAnswer&&<p className="academic-chat-answer" role="status">{reportAnswer}</p>}
     </div>
     <div className="academic-report-filters">
      <label>Academic year<select value={reportYear} onChange={e=>setReportYear(e.target.value)}><option value="all">All available years</option>{reportYears.map(y=><option key={y} value={y}>{y}</option>)}</select></label>
      <label>Month<select value={reportMonth} onChange={e=>setReportMonth(e.target.value)}><option value="all">All months</option>{['January','February','March','April','May','June','July','August','September','October','November','December'].map((m,i)=><option key={m} value={String(i+1)}>{m}</option>)}</select></label>
      <label>Exam<select value={reportExam} onChange={e=>setReportExam(e.target.value)}><option value="all">All exams</option>{reportExams.map(x=><option key={x} value={x}>{x}</option>)}</select></label>
      <label>Subject<select value={reportSubject} onChange={e=>setReportSubject(e.target.value)}><option value="all">All subjects</option>{reportSubjects.map(x=><option key={x} value={x}>{x}</option>)}</select></label>
      <button type="button" className="secondary academic-reset" onClick={()=>{setReportYear('all');setReportMonth('all');setReportExam('all');setReportSubject('all');setReportAnswer('Showing all published exam results.')}}>Reset filters</button>
     </div>
     {examResultsLoading?<div className="empty-state"><strong>Loading academic report…</strong></div>:!examResults.length?<div className="empty-state"><strong>No exam results published yet</strong><p>When the school publishes report-card marks, the annual report and graphs will appear here.</p></div>:<>
      <div className="academic-summary-grid">
       <div className="academic-summary-card"><span>Overall percentage</span><strong>{reportStats.count?reportStats.percentage.toFixed(1)+'%':'—'}</strong><small>For selected filters</small></div>
       <div className="academic-summary-card"><span>Marks obtained</span><strong>{reportStats.count?reportStats.obtained.toFixed(1)+' / '+reportStats.maximum.toFixed(1):'—'}</strong><small>{reportStats.count} subject exam records</small></div>
       <div className="academic-summary-card"><span>Passed</span><strong>{reportStats.count?reportStats.passed:'—'}</strong><small>{reportStats.failed} failed records</small></div>
       <div className="academic-summary-card"><span>Top subject</span><strong>{subjectProgress[0]?.subject||'—'}</strong><small>{subjectProgress.length?subjectProgress[0].percentage.toFixed(1)+'% average':'No data'}</small></div>
      </div>
      {!filteredExamResults.length?<div className="empty-state"><strong>No results match these filters</strong><p>Try another month, exam, subject or academic year.</p></div>:<>
       <div className="academic-graphs-grid">
        <div className="academic-graph-card"><h5>Subject-wise performance</h5><p>Average percentage based on published marks</p>
         {subjectProgress.map(item=><div className="academic-bar-row" key={item.subject}><div><strong>{item.subject}</strong><span>{item.percentage.toFixed(1)}% · {item.obtained.toFixed(1)}/{item.maximum.toFixed(1)}</span></div><div className="academic-bar-track"><span style={{width:Math.max(0,Math.min(100,item.percentage))+'%'}}/></div></div>)}
        </div>
        <div className="academic-graph-card"><h5>Exam progress over time</h5><p>Combined percentage for each exam date</p>
         {examProgress.map(item=><div className="academic-bar-row" key={item.label+'-'+item.date}><div><strong>{item.label}</strong><span>{new Date(item.date+'T00:00:00').toLocaleDateString('en-IN')} · {item.percentage.toFixed(1)}%</span></div><div className="academic-bar-track"><span style={{width:Math.max(0,Math.min(100,item.percentage))+'%'}}/></div></div>)}
        </div>
       </div>
       <div className="table-wrap academic-results-table"><table><thead><tr><th>Exam</th><th>Subject</th><th>Date</th><th>Academic year</th><th>Marks</th><th>Pass marks</th><th>Result</th></tr></thead><tbody>
        {filteredExamResults.map(result=><tr key={result.id}><td>{result.exam_name}</td><td>{result.subject}</td><td>{result.exam_date}</td><td>{result.academic_year||'—'}</td><td><strong>{result.marks_obtained}</strong> / {result.max_marks}</td><td>{result.pass_marks}</td><td><span className={'status-badge '+result.result}>{result.result}</span></td></tr>)}
       </tbody></table></div>
      </>}
     </>}
    </>}
   </section>)}

   {activeParentSection==='leave'&&(   <section className="parent-portal-section parent-leave-section">
    <div className="panel-heading"><div><h4>Leave applications</h4><p>Apply for leave for the selected student and follow the school’s decision.</p></div><CalendarDays size={20}/></div>
    {leaveError&&<div className="error" role="alert">{leaveError}</div>}
    {leaveMessage&&<div className="success" role="status">{leaveMessage}</div>}
    <form className="record-form parent-leave-form" onSubmit={submitLeaveRequest}>
     <div className="parent-facility-fields">
      <label>From date<input type="date" required value={leaveStart} onChange={e=>setLeaveStart(e.target.value)}/></label>
      <label>To date<input type="date" required min={leaveStart||undefined} value={leaveEnd} onChange={e=>setLeaveEnd(e.target.value)}/></label>
     </div>
     <label>Reason<textarea required minLength={3} maxLength={500} value={leaveReason} onChange={e=>setLeaveReason(e.target.value)} placeholder="Explain the reason for leave."/></label>
     <button className="primary" disabled={leaveSubmitting||!leaveStart||!leaveEnd||!leaveReason.trim()}>{leaveSubmitting?'Submitting…':'Submit leave application'}</button>
    </form>
    <div className="table-wrap"><table><thead><tr><th>From</th><th>To</th><th>Reason</th><th>Submitted</th><th>Status</th><th>School note</th></tr></thead><tbody>
     {leaveRequests.map(item=><tr key={item.id}><td>{item.start_date}</td><td>{item.end_date}</td><td>{item.reason}</td><td>{item.created_at?new Date(item.created_at).toLocaleDateString('en-IN'):'—'}</td><td><span className={'status-badge '+item.status}>{item.status}</span></td><td>{item.reviewer_note||'—'}</td></tr>)}
     {!leaveRequests.length&&<tr><td colSpan={6}>No leave applications for this student yet.</td></tr>}
    </tbody></table></div>
   </section>)}

   {activeParentSection==='messages'&&(   <section className="parent-portal-section parent-messages-section">
    <div className="panel-heading"><div><h4>Messages to school</h4><p>Contact an approved teacher or school administrator about this student.</p></div><MessageCircle size={20}/></div>
    {messageError&&<div className="error" role="alert">{messageError}</div>}
    {messageNotice&&<div className="success" role="status">{messageNotice}</div>}
    {messagesLoading?<div className="empty-state">Loading conversations…</div>:<>
     <form className="record-form parent-message-form" onSubmit={sendParentMessage}>
      <label>Send to<select required value={messageRecipient} onChange={e=>setMessageRecipient(e.target.value)}><option value="">Select school staff</option>{messageContacts.map(contact=><option key={contact.id} value={contact.id}>{contact.name} · {contact.role.replaceAll('_',' ')}</option>)}</select></label>
      <label>Subject<input value={messageSubject} onChange={e=>setMessageSubject(e.target.value)} maxLength={180} placeholder="Optional subject"/></label>
      <label>Message<textarea required minLength={1} maxLength={10000} value={messageBody} onChange={e=>setMessageBody(e.target.value)} placeholder="Write your message to the school…"/></label>
      <button className="primary" disabled={messageSubmitting||!messageRecipient||!messageBody.trim()}>{messageSubmitting?'Sending…':'Send message'}</button>
     </form>
     <div className="parent-message-list">
      {parentMessages.map(item=>{
       const own=item.sender_user_id===currentUserId;
       const contact=messageContacts.find(c=>c.id===(own?item.recipient_user_id:item.sender_user_id));
       return <article className="parent-message-item" key={item.id}><div className="parent-message-meta"><strong>{own?'You → '+(contact?.name||'School staff'):(contact?.name||'School staff')}</strong><span>{new Date(item.created_at).toLocaleString('en-IN')}</span></div>{item.subject&&<h5>{item.subject}</h5>}<p>{item.body}</p></article>;
      })}
      {!parentMessages.length&&<div className="empty-state">No messages yet. Send a message to start a conversation with the school.</div>}
     </div>
    </>}
   </section>)}

   {activeParentSection==='facilities'&&(   <section className="parent-portal-section parent-facilities-section">
    <div className="panel-heading"><div><h4>Transport and hostel</h4><p>View school-approved allocations and request changes. Only authorized staff can change official records.</p></div><Bus size={20}/></div>
    {facilityError&&<div className="error" role="alert">{facilityError}</div>}
    {facilityMessage&&<div className="success" role="status">{facilityMessage}</div>}
    {facilityLoading?<div className="empty-state">Loading facility information…</div>:<>
     <div className="parent-facility-grid">
      <article className="parent-facility-card"><h5>Transport allocation</h5>
       {facilityData.transport?<dl><dt>Route</dt><dd>{facilityData.transport.route_name||'—'}</dd><dt>Vehicle</dt><dd>{facilityData.transport.vehicle_registration||'Not specified'}</dd><dt>Pickup</dt><dd>{facilityData.transport.pickup_point||'—'} {facilityData.transport.pickup_time}</dd><dt>Drop</dt><dd>{facilityData.transport.drop_point||'—'} {facilityData.transport.drop_time}</dd></dl>:<p>No active transport allocation is recorded for this student.</p>}
      </article>
      <article className="parent-facility-card"><h5>Hostel allocation</h5>
       {facilityData.hostel?<dl><dt>Hostel</dt><dd>{facilityData.hostel.hostel_name||'—'}</dd><dt>Building</dt><dd>{facilityData.hostel.building||'—'}</dd><dt>Room / Bed</dt><dd>{facilityData.hostel.room_no||'—'} / {facilityData.hostel.bed_no||'—'}</dd><dt>Warden</dt><dd>{facilityData.hostel.warden_name||'—'}</dd></dl>:<p>No active hostel allocation is recorded for this student.</p>}
      </article>
     </div>
    </>}
    <form className="record-form parent-facility-form" onSubmit={submitFacilityRequest}>
     <div className="form-heading"><h4>Submit a facility request</h4><p>Your request will be reviewed by the Transport Manager or Hostel Warden.</p></div>
     <div className="parent-facility-fields">
      <label>Facility<select value={facilityType} onChange={e=>{const v=e.target.value as 'transport'|'hostel';setFacilityType(v);setFacilityRequestType(v==='transport'?'pickup_change':'room_change')}}><option value="transport">Transport</option><option value="hostel">Hostel</option></select></label>
      <label>Request type<select value={facilityRequestType} onChange={e=>setFacilityRequestType(e.target.value)}>
       {facilityType==='transport'?<><option value="new_allocation">New allocation</option><option value="route_change">Route change</option><option value="pickup_change">Pickup point change</option><option value="drop_change">Drop point change</option><option value="discontinue">Discontinue transport</option></>:<><option value="new_allocation">New hostel allocation</option><option value="room_change">Room change</option><option value="bed_change">Bed change</option><option value="discontinue">Discontinue hostel</option></>}
      </select></label>
     </div>
     {facilityType==='transport'?<div className="parent-facility-fields">
      <label>Requested route<input value={facilityDetails.route_name} onChange={e=>setFacilityDetails(v=>({...v,route_name:e.target.value}))} maxLength={120}/></label>
      <label>Pickup point<input value={facilityDetails.pickup_point} onChange={e=>setFacilityDetails(v=>({...v,pickup_point:e.target.value}))} maxLength={180}/></label>
      <label>Drop point<input value={facilityDetails.drop_point} onChange={e=>setFacilityDetails(v=>({...v,drop_point:e.target.value}))} maxLength={180}/></label>
      <label>Pickup time<input value={facilityDetails.pickup_time} onChange={e=>setFacilityDetails(v=>({...v,pickup_time:e.target.value}))} placeholder="07:30" maxLength={10}/></label>
      <label>Drop time<input value={facilityDetails.drop_time} onChange={e=>setFacilityDetails(v=>({...v,drop_time:e.target.value}))} placeholder="16:00" maxLength={10}/></label>
     </div>:<div className="parent-facility-fields">
      <label>Requested room<input value={facilityDetails.room_no} onChange={e=>setFacilityDetails(v=>({...v,room_no:e.target.value}))} maxLength={40}/></label>
      <label>Requested bed<input value={facilityDetails.bed_no} onChange={e=>setFacilityDetails(v=>({...v,bed_no:e.target.value}))} maxLength={40}/></label>
     </div>}
     <label>Reason<textarea required minLength={5} maxLength={500} value={facilityReason} onChange={e=>setFacilityReason(e.target.value)} placeholder="Explain why this change is needed."/></label>
     <button className="primary" disabled={facilitySubmitting||!facilityReason.trim()}>{facilitySubmitting?'Submitting…':'Submit request'}</button>
    </form>
    <div className="table-wrap"><table><thead><tr><th>Facility</th><th>Request</th><th>Submitted</th><th>Status</th><th>School note</th></tr></thead><tbody>
     {facilityRequests.map(item=><tr key={item.id}><td>{item.facility_type}</td><td>{item.request_type.replaceAll('_',' ')}</td><td>{new Date(item.created_at).toLocaleDateString('en-IN')}</td><td><span className={'status-badge '+item.status}>{item.status}</span></td><td>{item.reviewer_note||'—'}</td></tr>)}
     {!facilityLoading&&!facilityRequests.length&&<tr><td colSpan={5}>No transport or hostel requests yet.</td></tr>}
    </tbody></table></div>
   </section>)}

   {activeParentSection==='notifications'&&<ParentNotifications request={request}/>}

   async function downloadParentCertificate(application:any){
  if(!application.certificate_number)return;
  setCertificateError('');
  try{
   const response=await fetch(API+'/api/parent/certificates/'+application.issue_id+'/download',{headers:{Authorization:'Bearer '+token}});
   if(!response.ok){const data=await response.json().catch(()=>({}));throw new Error(data.detail||'Certificate download failed')}
   const blob=await response.blob();const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download=application.certificate_number+'.pdf';document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(url);
  }catch(err:any){setCertificateError(err.message||'Could not download certificate')}
 }
 {activeParentSection==='certificates'&&(   <section className="parent-portal-section">
    <div className="panel-heading"><div><h4>Certificate applications</h4><p>Apply for school certificates and track the school's decision.</p></div></div>
    <form className="record-form parent-certificate-form" onSubmit={submitCertificate}>
     <label>Certificate type<select value={certificateType} onChange={e=>setCertificateType(e.target.value)}><option value="study">Study certificate</option><option value="bonafide">Bonafide certificate</option><option value="conduct">Conduct certificate</option><option value="transfer">Transfer certificate</option><option value="other">Other certificate</option></select></label>
     <label>Purpose<textarea required minLength={3} maxLength={500} value={certificatePurpose} onChange={e=>setCertificatePurpose(e.target.value)} placeholder="Tell the school why this certificate is needed."/></label>
     <button className="primary" disabled={certificateSubmitting||!certificatePurpose.trim()}>{certificateSubmitting?'Submitting…':'Submit certificate request'}</button>
    </form>
    {certificateError&&<div className="error" role="alert">{certificateError}</div>}
    {certificateMessage&&<div className="success" role="status">{certificateMessage}</div>}
    <div className="table-wrap">
     <table>
      <thead><tr><th>Certificate</th><th>Purpose</th><th>Applied on</th><th>Status</th><th>School note</th><th>Issued document</th></tr></thead>
      <tbody>
       {certificateApplications.map(application=><tr key={application.id}><td>{({study:'Study',bonafide:'Bonafide',conduct:'Conduct',transfer:'Transfer',other:'Other'} as Record<string,string>)[application.certificate_type]||application.certificate_type}</td><td>{application.purpose}</td><td>{new Date(application.created_at).toLocaleDateString('en-IN')}</td><td><span className={'status-badge '+application.status}>{application.status}</span></td><td>{application.reviewer_note||'—'}</td><td>{application.certificate_number?<button type="button" className="secondary" onClick={()=>downloadParentCertificate(application)}><Download size={14}/> Download PDF</button>:'Not issued'}</td></tr>)}
       {certificateApplicationsLoading&&<tr><td colSpan={6}>Loading certificate applications…</td></tr>}
       {!certificateApplicationsLoading&&!certificateApplications.length&&<tr><td colSpan={6}>No certificate applications submitted yet.</td></tr>}
      </tbody>
     </table>
    </div>
   </section>)}

    </main>
   </section>
  </>}
 </div>
}
function FacilityRequestsPanel({request,userRole,refreshKey}:{request:(url:string,options?:RequestInit)=>Promise<any>;userRole:string;refreshKey:number}) {
 const allowedTypes=userRole==='transport_manager'?['transport']:userRole==='hostel_warden'?['hostel']:['transport','hostel'];
 const [facilityType,setFacilityType]=useState<'transport'|'hostel'>(allowedTypes[0] as 'transport'|'hostel');
 const [rows,setRows]=useState<any[]>([]);
 const [assets,setAssets]=useState<any[]>([]);
 const [selectedAsset,setSelectedAsset]=useState<Record<number,string>>({});
 const [loading,setLoading]=useState(false);
 const [error,setError]=useState('');
 const [note,setNote]=useState<Record<number,string>>({});
 const [busy,setBusy]=useState<number|null>(null);
 const [message,setMessage]=useState('');
 useEffect(()=>{
  let active=true;setLoading(true);setError('');
  const inventoryUrl=facilityType==='transport'?'/api/vehicles':'/api/hostels';
  Promise.all([
   request('/api/facility-requests?facility_type='+facilityType),
   request(inventoryUrl)
  ]).then(([data,inventory])=>{if(active){setRows(data);setAssets(inventory)}})
   .catch((e:any)=>{if(active)setError(e.message||'Could not load requests and allocation inventory')})
   .finally(()=>{if(active)setLoading(false)});
  return()=>{active=false};
 },[facilityType,refreshKey]);
 async function review(id:number,status:'approved'|'rejected'){
  setBusy(id);setError('');setMessage('');
  const assetId=selectedAsset[id];
  const details=status==='approved'&&assetId
   ?(facilityType==='transport'?{vehicle_id:Number(assetId)}:{hostel_id:Number(assetId)}):{};
  try{
   await request('/api/facility-requests/'+id+'/review',{method:'POST',body:JSON.stringify({status,reviewer_note:note[id]||'',details})});
   setRows(old=>old.map(row=>row.id===id?{...row,status,reviewer_note:note[id]||''}:row));
   setMessage('Request '+status+'.');
  }catch(e:any){setError(e.message||'Could not review request')}
  finally{setBusy(null)}
 }
 return <div className="panel">
  <div className="panel-heading"><div><h3>Parent facility requests</h3><p>Review parent requests. Approval updates the official student allocation.</p></div><ClipboardCheck size={20}/></div>
  <label className="parent-child-select">Facility
   <select value={facilityType} onChange={e=>setFacilityType(e.target.value as 'transport'|'hostel')}>
    {allowedTypes.map(type=><option key={type} value={type}>{type==='transport'?'Transport':'Hostel'}</option>)}
   </select>
  </label>
  {error&&<div className="error" role="alert">{error}</div>}
  {message&&<div className="success" role="status">{message}</div>}
  {loading?<div className="empty-state">Loading parent requests…</div>:<div className="table-wrap">
   <table><thead><tr><th>Student ID</th><th>Request</th><th>Reason</th><th>Requested details</th><th>Status</th><th>Review note</th><th>Action</th></tr></thead><tbody>
    {rows.map(row=><tr key={row.id}>
     <td>{row.student_id}</td><td>{row.request_type.replaceAll('_',' ')}</td><td>{row.reason}</td>
     <td>{Object.entries(row.details||{}).map(([k,v])=>String(v??'')).filter(Boolean).join(' · ')||'—'}</td>
     <td><span className={'status-badge '+row.status}>{row.status}</span></td>
     <td><input aria-label={'Review note for request '+row.id} value={note[row.id]??row.reviewer_note??''} onChange={e=>setNote(old=>({...old,[row.id]:e.target.value}))} maxLength={500}/></td>
     <td>{row.status==='pending'?<div className="facility-review-actions">
      <select aria-label={'Select official '+facilityType+' allocation for request '+row.id} value={selectedAsset[row.id]||''} onChange={e=>setSelectedAsset(old=>({...old,[row.id]:e.target.value}))}>
       <option value="">Keep current / no new allocation</option>
       {assets.filter((asset:any)=>asset.status==='active').map((asset:any)=><option key={asset.id} value={asset.id}>{facilityType==='transport'?asset.registration_no+' · '+(asset.route_name||'No route'):asset.name+' · '+(asset.building||'')+' · '+(asset.room_no||'')}</option>)}
      </select>
      <button className="primary" disabled={busy===row.id} onClick={()=>review(row.id,'approved')}>Approve</button><button className="secondary" disabled={busy===row.id} onClick={()=>review(row.id,'rejected')}>Reject</button>
     </div>:'Reviewed'}</td>
    </tr>)}
    {!rows.length&&<tr><td colSpan={7}>No {facilityType} requests found.</td></tr>}
   </tbody></table>
  </div>}
 </div>
}

function HelpAssistant({request}:{request:(url:string,options?:RequestInit)=>Promise<any>}) {
 const [question,setQuestion]=useState(''),[messages,setMessages]=useState<{q:string,a:string}[]>([]),[busy,setBusy]=useState(false),[error,setError]=useState('');
 async function ask(e:FormEvent<HTMLFormElement>){e.preventDefault();if(!question.trim()||busy)return;const q=question.trim();setQuestion('');setBusy(true);setError('');try{const result=await request('/api/chatbot/faq',{method:'POST',body:JSON.stringify({question:q})});setMessages(old=>[...old,{q,a:result.answer}])}catch(err:any){setError(err.message)}finally{setBusy(false)}}
 return <div className="panel"><div className="panel-heading"><div><h3>EduNexus Help Assistant</h3><p>Ask common questions about school workflows. Answers are from approved FAQ content.</p></div><Activity size={20}/></div><div className="chat-faq-list">{messages.map((m,i)=><div className="chat-faq-item" key={i}><div className="chat-user-question">{m.q}</div><div className="chat-assistant-answer">{m.a}</div></div>)}{!messages.length&&<div className="empty-state"><strong>How can I help?</strong><p>Try “How do I pay fees?”, “How do I reset my password?”, or “Where is transport information?”</p></div>}</div>{error&&<div className="error">{error}</div>}<form className="chat-faq-form" onSubmit={ask}><input value={question} maxLength={500} onChange={e=>setQuestion(e.target.value)} placeholder="Ask EduNexus…" /><button className="primary" disabled={busy||!question.trim()}>{busy?'Thinking…':'Ask'}</button></form></div>
}

function InvitationAccept(){
 const token=new URLSearchParams(window.location.search).get('token')||''
 const [name,setName]=useState('')
 const [password,setPassword]=useState('')
 const [busy,setBusy]=useState(false)
 const [error,setError]=useState('')
 const [success,setSuccess]=useState('')
 async function submit(e:FormEvent){
  e.preventDefault();setBusy(true);setError('');setSuccess('')
  try{
   const response=await fetch(`${API}/api/platform/ops/invitations/accept`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,name,password})})
   const data=await response.json()
   if(!response.ok)throw new Error(data.detail||'Invitation could not be accepted')
   setSuccess(data.message||'Invitation accepted. You can now sign in.')
   setPassword('')
  }catch(err:any){setError(err.message||'Invitation could not be accepted')}finally{setBusy(false)}
 }
 return <div className="auth-page"><main className="auth-main"><section className="auth-form-shell"><form className="auth-form-card" onSubmit={submit}><div className="auth-mobile-brand"><div className="auth-brand-icon"><GraduationCap size={22}/></div><strong>EduNexus</strong></div><h2>Accept your institution invitation</h2><p>Create your account password to join your institution workspace.</p>{!token&&<div className="error auth-message">Invitation token is missing. Open the complete invitation link.</div>}{error&&<div className="error auth-message">{error}</div>}{success&&<div className="success auth-message">{success}<p><a href="/">Go to sign in</a></p></div>}<label className="auth-field">Full name<input required minLength={2} maxLength={160} value={name} onChange={e=>setName(e.target.value)}/></label><label className="auth-field">New password<input type="password" required minLength={12} value={password} onChange={e=>setPassword(e.target.value)} placeholder="At least 12 characters"/></label><button className="primary" disabled={busy||!token||Boolean(success)}>{busy?'Accepting invitation…':'Accept invitation'}</button></form></section></main></div>
}

function App(){
 const [token,setToken]=useState(localStorage.getItem('erp_token')||'')
 const [user,setUser]=useState<User|null>(null)
 const [rbacPermissions,setRbacPermissions]=useState<{role:string;configured:boolean;permissions:Record<string,boolean>}|null>(null)
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
 const [refreshVersion,setRefreshVersion]=useState(0)
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
 const defaultModuleKeys=roleModuleAccess[user?.role||'user']||roleModuleAccess.user
 const allowedModuleKeys=user?.role!=='super_admin'&&rbacPermissions!==null&&rbacPermissions.role===user?.role&&rbacPermissions.configured?modules.filter(m=>Boolean(rbacPermissions.permissions[m.key+':View'])).map(m=>m.key):defaultModuleKeys
 const availableModules=modules.filter(m=>allowedModuleKeys.includes(m.key))
 const selected=modules.find(m=>m.key===active)||modules[0]
 const roleLabel=user?.platform_workspace?'Developer · Client Workspace':(roleLabels[user?.role||'user']||'School User')
 const showRecordActions=active==='staff'||['attendance','timetable','exams','report-cards','homework','library-books','library-loans'].includes(active)||(active==='student-leave'&&user?.role!=='parent')
 const hasModule=(key:string)=>allowedModuleKeys.includes(key)
 const authHeaders=useMemo(()=>({'Authorization':`Bearer ${token}`,'Content-Type':'application/json'}),[token])
 useEffect(()=>{if(user){const first=allowedModuleKeys[0]||'dashboard';if(!allowedModuleKeys.includes(active))setActive(first)}},[user,rbacPermissions])
 useEffect(()=>{if(!token){setRbacPermissions(null);return}fetch(`${API}/api/rbac/me`,{headers:authHeaders}).then(r=>r.ok?r.json():Promise.reject()).then(setRbacPermissions).catch(()=>setRbacPermissions(null))},[token,authHeaders])
 useEffect(()=>{if(!token)return;fetch(`${API}/api/auth/me`,{headers:authHeaders}).then(r=>r.ok?r.json():Promise.reject()).then(setUser).catch(()=>{localStorage.removeItem('erp_token');setToken('');setUser(null)})},[token,authHeaders])
 useEffect(()=>{if(!token||!user)return;const ping=()=>fetch(`${API}/api/platform/activity/heartbeat`,{method:'POST',headers:authHeaders}).catch(()=>{});ping();const interval=window.setInterval(ping,60000);return()=>window.clearInterval(interval)},[token,user?.id,authHeaders])
 async function request(url:string,options:RequestInit={}){const r=await fetch(`${API}${url}`,{...options,headers:{...authHeaders,...options.headers}});if(r.status===401){logout();throw new Error('Session expired. Please sign in again.')}const raw=await r.text();let data:any={};try{data=raw?JSON.parse(raw):{}}catch{data={}}if(!r.ok){const detail=data.detail||data.message||raw.slice(0,240);throw new Error((detail||'API request failed')+` (HTTP ${r.status}: ${options.method||'GET'} ${url})`)}return data}
 async function enterClientWorkspace(schoolId:number){try{const result=await request('/api/platform/clients/'+schoolId+'/workspace',{method:'POST'});localStorage.setItem('erp_token',result.access_token);setToken(result.access_token);setUser(result.user);setRbacPermissions(null);setActive('dashboard');setSelectedStudent(null)}catch(e:any){setError(e.message||'Could not open client dashboard')}}
 async function returnToPlatformOwner(){try{const result=await request('/api/platform/workspace/exit',{method:'POST'});localStorage.setItem('erp_token',result.access_token);setToken(result.access_token);setUser(result.user);setRbacPermissions(null);setActive('developer-control');setSelectedStudent(null)}catch(e:any){setError(e.message||'Could not return to Developer Control Centre')}}
 function logout(){localStorage.removeItem('erp_token');setToken('');setUser(null);setRbacPermissions(null);setRows([]);setDemoTestingActive(false);setDemoTargetEmail('');setDemoSwitchPassword('');setDemoSwitchError('');sessionStorage.removeItem('demo_testing_active')}
 function handleLogin(t:string,u:User){localStorage.setItem('erp_token',t);setToken(t);setUser(u);const canTest=DEMO_MODE&&u.role==='super_admin'&&u.email==='demo.developer@jovoo.in';setDemoTestingActive(canTest);if(canTest)sessionStorage.setItem('demo_testing_active','true');else sessionStorage.removeItem('demo_testing_active');setActive(u.role==='super_admin'?'developer-control':'dashboard')}
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
     }else if(active==='parent-portal'||active==='chatbot'){setRows([])}else if(active==='approvals'){setRows(await request('/api/auth/pending-users'))}else if(active==='payments'){setFeeDues(await request('/api/fee-dues'));setRows([])}else if(active==='fee-reports'){const params=new URLSearchParams({year:reportYear});if(reportMonth)params.set('month',reportMonth);if(user.role==='super_admin'&&reportSchool)params.set('school_id',reportSchool);setReportData(await request('/api/fee-reports?'+params.toString()));setRows([])}else if(selected.endpoint){const listUrl=active==='student-leave'&&user?.role==='parent'?'/api/parent-portal/leave':selected.endpoint;setRows(await request(listUrl+'?q='+encodeURIComponent(query)))}}catch(e:any){setError(e.message)}finally{setLoading(false)}}
 useEffect(()=>{if(user&&active!=='fee-reports')load()},[active,user,query])
 useEffect(()=>{if(user&&active==='fee-reports')load()},[active,user,reportMonth,reportYear,reportSchool])
 useEffect(()=>{if(user)request('/api/schools').then(setSchools).catch(()=>setSchools([]))},[user,token])
 useEffect(()=>{if(user?.role==='super_admin'&&active==='schools')request('/api/users').then(setOwnerUsers).catch(()=>setOwnerUsers([]))},[user,active,token])
 useEffect(()=>{let cancelled=false;const timer=setTimeout(async()=>{if(!user||studentSearch.trim().length<2){setStudentResults([]);return}try{const found=await request('/api/students?q='+encodeURIComponent(studentSearch.trim()));if(!cancelled)setStudentResults(found)}catch{if(!cancelled)setStudentResults([])}},250);return()=>{cancelled=true;clearTimeout(timer)}},[studentSearch,user,token])
 function chooseStudent(student:any){setSelectedStudent(student);setStudentSearch('');setStudentResults([]);if(active==='student-fees'){setForm({total_amount:''});setShowForm(true)}if(active==='documents'){setForm(current=>({...current,owner_type:'student',owner_id:student.id}));setShowForm(true)}}
 async function save(e: FormEvent<HTMLFormElement>) {e.preventDefault();try{const payload={...form};for(const f of selected.fields||[]){if((f.type==='number'||f.type==='school-select')&&payload[f.key]!==''&&payload[f.key]!=null)payload[f.key]=Number(payload[f.key]);if(f.type==='checkbox')payload[f.key]=Boolean(payload[f.key]);if(payload[f.key]==='')delete payload[f.key]}if(active==='student-fees'){if(!selectedStudent)throw new Error('Search and select a student before adding a fee.');payload.student_id=selectedStudent.id;payload.category='tuition';payload.academic_year=`${new Date().getFullYear()}-${String(new Date().getFullYear()+1).slice(-2)}`;payload.term='annual';payload.discount=0;payload.description='Tuition fee'}const endpoint=active==='student-leave'&&user?.role==='parent'?'/api/parent-portal/leave':selected.endpoint!;const created=await request(endpoint+(editingRecordId?'/'+editingRecordId:''),{method:editingRecordId?'PUT':'POST',body:JSON.stringify(payload)});if(active==='students')setSelectedStudent(created);setShowForm(false);setForm({});setEditingRecordId(null);setNotice(editingRecordId?'Record updated successfully':(active==='staff'&&payload.create_account?'Staff record and login account created successfully':'Record created successfully'));if(active==='schools')setSchools(await request('/api/schools'));await load()}catch(e:any){setError(e.message)}}

 async function reviewLeave(row:any,status:'approved'|'rejected'){const note=window.prompt('Optional reviewer note','')??'';try{await request('/api/student-leave/'+row.id+'/review',{method:'POST',body:JSON.stringify({status,reviewer_note:note})});setNotice('Leave request '+status);await load()}catch(e:any){setError(e.message)}}
  async function returnLibraryLoan(row:any){if(!window.confirm('Record this book as returned?'))return;try{await request('/api/library-loans/'+row.id+'/return',{method:'POST'});setNotice('Book return recorded successfully');await load()}catch(e:any){setError(e.message)}}
 async function deleteAcademicRecord(row:any){if(!window.confirm('Delete this '+selected.label.toLowerCase()+' record? This cannot be undone.'))return;try{await request(selected.endpoint+'/'+row.id,{method:'DELETE'});setNotice(selected.label+' record deleted successfully');await load()}catch(e:any){setError(e.message)}} async function deleteStaff(row:any){if(!window.confirm('Delete staff record '+row.employee_no+' — '+row.full_name+'? This cannot be undone.'))return;try{await request('/api/staff/'+row.id,{method:'DELETE'});setNotice('Staff record deleted successfully');await load()}catch(e:any){setError(e.message)}}
 if(new URLSearchParams(window.location.search).has('token'))return <InvitationAccept/>
 if(!token||!user)return <Login onLogin={handleLogin}/>
 function refreshCurrentView(){if(active==='parent-portal'){setLoading(true);setRefreshVersion(version=>version+1)}else{load()}}
 const dashboardNow=new Date()
 const dashboardYear=dashboardNow.getFullYear()
 const dashboardMonth=dashboardNow.getMonth()+1
 const dashboardMonthlySeries=Array.from({length:dashboardMonth},(_,index)=>{const month=index+1;const period=dashboardYear+'-'+String(month).padStart(2,'0');const amount=Number((reportData.chart||[]).find((point:any)=>point.period===period)?.amount||0);return {period,amount,label:new Date(dashboardYear,index,1).toLocaleString('en-IN',{month:'short'})}})
 const dashboardMonthAmount=dashboardMonthlySeries[dashboardMonthlySeries.length-1]?.amount||0
 const dashboardPeakMonth=dashboardMonthlySeries.reduce((best:any,point:any)=>point.amount>best.amount?point:best,{label:'—',amount:0})
 const Icon=selected.icon
 return <div className="app-shell role-themed" style={{'--role-accent':roleAccent[user.role]||'#0f766e'} as any}>
  <aside className={`sidebar ${mobileNav?'open':''}`}><div className="brand"><div className="brand-mark"><GraduationCap/></div><div><strong>EduNexus</strong><span>EDUCATION MANAGEMENT PLATFORM</span></div><button className="icon-button mobile-close" onClick={()=>setMobileNav(false)}><X/></button></div><div className="school-switch school-identity"><div className="school-avatar"><GraduationCap size={19}/></div><div className="school-switch-copy"><span className="school-switch-kicker">{user.platform_workspace?'ACTIVE CLIENT':user.role==='super_admin'?'PLATFORM OWNER':'ACTIVE SCHOOL'}</span><strong>{user.platform_workspace?(schools.find(sc=>sc.id===user.school_id)?.name||'Selected client'):user.role==='super_admin'?'EduNexus Platform':(schools.find(sc=>sc.id===user.school_id)?.name||'My School')}</strong><span className="school-switch-action">{user.platform_workspace?'Developer client access':user.role==='super_admin'?'Global control centre':'School workspace'}</span></div></div><div className="workspace-nav-heading"><div><span className="nav-label">WORKSPACE</span><small>Modules for your role</small></div><span className="workspace-module-count">{availableModules.length}</span></div><nav>{availableModules.map(m=>{const I=m.icon;return <button key={m.key} className={`nav-item ${active===m.key?'selected':''}`} onClick={()=>{setActive(m.key);setMobileNav(false);setShowForm(false)}}><I size={18}/><span>{m.label}</span></button>})}</nav><div className="sidebar-bottom"><div className="user-mini"><div className="avatar">{user.name.slice(0,1).toUpperCase()}</div><div><strong>{user.name}</strong><span>{roleLabel}</span></div><button className="icon-button" title="Sign out" onClick={logout}><LogOut size={17}/></button></div></div></aside>
  <main className="main"><header className="topbar"><button className="icon-button mobile-menu" onClick={()=>setMobileNav(true)}><Menu/></button><div className="crumb">Workspace <span>/</span> <strong>{selected.label}</strong></div><span className="role-chip">{roleLabel}</span>{user.platform_workspace&&<button className="secondary" onClick={()=>returnToPlatformOwner()}>Return to Developer Control Centre</button>}{DEMO_MODE&&demoTestingActive&&user.role!=="super_admin"&&<button className="secondary" onClick={()=>{const password=window.prompt("Enter the shared demo password to return to Developer");if(password)switchDemoAccount("demo.developer@jovoo.in",password)}}>Return to Developer</button>}<div className="top-actions">{user.role!=='parent'&&<div className="student-global-search"><Search size={16}/><input aria-label="Find student across modules" placeholder="Find student by name / admission no." value={studentSearch} onChange={e=>setStudentSearch(e.target.value)}/>{studentResults.length>0&&<div className="student-search-results">{studentResults.map(s=><button type="button" key={s.id} onClick={()=>chooseStudent(s)}><strong>{s.full_name}</strong><span>{s.admission_no} · {s.class_name||'Class not set'} {s.section||''}</span></button>)}</div>}</div>}<div className="online-pill"><span/> System online</div><button className="icon-button" title="Notifications"><Bell size={19}/></button><div className="avatar">{user.name.slice(0,1).toUpperCase()}</div></div></header>
  <div className={`content ${active!=='dashboard'&&active!=='notifications'?'module-workspace':''}`} >{loading&&<div className="workspace-refresh-overlay" role="status" aria-live="polite"><div className="workspace-refresh-indicator"><RefreshCw size={22}/><span>Refreshing workspace…</span></div></div>}{selectedStudent&&<div className="selected-student-context"><div><strong>Selected student: {selectedStudent.full_name}</strong><span>{selectedStudent.admission_no} · {selectedStudent.class_name||'Class not set'} {selectedStudent.section||''} · Guardian: {selectedStudent.guardian_name||'—'} · Phone: {selectedStudent.guardian_phone||'—'}</span></div><button type="button" className="secondary" onClick={()=>setSelectedStudent(null)}>Clear student</button></div>}<div className="page-heading"><div><p className="eyebrow">SCHOOL ERP / {selected.key.toUpperCase()}</p><h1>{selected.label}</h1><p className="muted">{selected.description}</p></div><div className="heading-actions"><button className="secondary" onClick={refreshCurrentView} disabled={loading} aria-label="Refresh current page"><RefreshCw size={16}/> {loading?'Refreshing…':'Refresh'}</button>{active==='students'&&user.role!=='parent'&&<>{user.role==='super_admin'&&<select aria-label="Import school" value={importSchoolId} onChange={e=>setImportSchoolId(e.target.value)}><option value="">Select school</option>{schools.map(sc=><option key={sc.id} value={sc.id}>{sc.name}</option>)}</select>}<button className="secondary" onClick={downloadStudentTemplate}><Download size={16}/> Template</button><input id="student-bulk-file" type="file" accept=".csv,.xlsx" style={{display:"none"}} onChange={importStudents}/><button className="secondary" disabled={importing||(user.role==='super_admin'&&!importSchoolId)} onClick={()=>document.getElementById('student-bulk-file')?.click()}><Upload size={16}/> {importing?'Uploading…':'Bulk upload'}</button></>}{['staff','classes','vehicles','hostels','maintenance','fee-structures'].includes(active)&&user.role!=='parent'&&<>{user.role==='super_admin'&&<select aria-label="Import school" value={importSchoolId} onChange={e=>setImportSchoolId(e.target.value)}><option value="">Select school</option>{schools.map(sc=><option key={sc.id} value={sc.id}>{sc.name}</option>)}</select>}<input id="module-bulk-file" type="file" accept=".csv,.xlsx" style={{display:"none"}} onChange={importModule}/><button className="secondary" disabled={importing||(user.role==='super_admin'&&!importSchoolId)} onClick={()=>document.getElementById('module-bulk-file')?.click()}><Upload size={16}/> {importing?'Importing…':'Import CSV / Excel'}</button></>}{selected.endpoint&&(user.role!=='super_admin'||active==='schools'||active==='staff'||['attendance','timetable','exams','report-cards','homework','student-leave','parent-messages'].includes(active))&&<button className="primary" onClick={()=>{setEditingRecordId(null);setForm(active==='student-fees'&&selectedStudent?{student_id:selectedStudent.id,term:'annual',discount:0}:{});setShowForm(true)}}><Plus size={17}/> Add record</button>}</div></div>
  {error&&<div className="error banner"><span>{error}</span><button onClick={()=>setError('')}><X size={16}/></button></div>}{notice&&<div className="success banner">{notice}<button onClick={()=>setNotice('')}><X size={16}/></button></div>}
  {active==='parent-portal'?<ParentPortal request={request} userRole={user.role} currentUserId={user.id} refreshKey={refreshVersion} onLoadingChange={setLoading} token={token}/>:active==='parent-relationships'?<ParentRelationshipPanel request={request}/>:active==='certificate-management'?<CertificateManagementPanel request={request} token={token}/>:active==='notifications'?<NotificationManagementPanel request={request}/>:active==='facility-requests'?<FacilityRequestsPanel request={request} userRole={user.role} refreshKey={refreshVersion}/>:active==='chatbot'?<HelpAssistant request={request}/>:active==='developer-control'&&user.role==='super_admin'?<DeveloperControlCentre request={request} onEnterWorkspace={enterClientWorkspace} moduleList={modules} roles={roleCatalog}/>:active==='dashboard'?<>
    {DEMO_MODE&&demoTestingActive&&user.role==='super_admin'&&<div className="panel demo-role-testing-panel"><div className="panel-heading"><div><h3>Role testing workspace</h3><p>Open a real demo account to verify its dashboard and navigation. This does not change normal user access.</p></div><ShieldCheck size={20}/></div><div className="quick-grid"><label className="auth-field">Demo role<select value={demoTargetEmail} onChange={e=>setDemoTargetEmail(e.target.value)}><option value="">Choose a role to test…</option>{DEMO_USERS.filter(demo=>demo.email!=='demo.developer@jovoo.in').map(demo=><option key={demo.email} value={demo.email}>{demo.label}</option>)}</select></label><label className="auth-field">Shared demo password<input type="password" autoComplete="off" value={demoSwitchPassword} onChange={e=>setDemoSwitchPassword(e.target.value)} placeholder="Enter the password printed by the seeder"/></label><div><button className="primary" disabled={demoSwitchBusy||!demoTargetEmail||!demoSwitchPassword} onClick={()=>switchDemoAccount(demoTargetEmail)}>{demoSwitchBusy?'Opening workspace…':'Open selected role'}</button></div></div>{demoSwitchError&&<div className="error auth-message" role="alert">{demoSwitchError}</div>}</div>}
    <div className="welcome-panel"><div><span className="welcome-tag">{roleLabel.toUpperCase()} WORKSPACE</span><h2>Good to see you, {user.name.split(' ')[0]}</h2><p>{roleDescriptions[user.role]||'Your school workspace and assigned daily tasks.'} Use the options on the left to get started.</p></div><div className="welcome-icon"><GraduationCap size={44}/></div></div>
    <div className="stat-grid">{[{label:'Total students',key:'students',target:'students',icon:GraduationCap,tone:'teal'},{label:'Staff members',key:'staff',target:'staff',icon:Users,tone:'blue'},{label:'Classes & sections',key:'classes',target:'classes',icon:BookOpen,tone:'purple'},{label:'Transport vehicles',key:'vehicles',target:'vehicles',icon:Bus,tone:'orange'},{label:'Hostel rooms',key:'hostel_rooms',target:'hostels',icon:Building2,tone:'pink'},{label:'Open maintenance',key:'open_maintenance',target:'maintenance',icon:Wrench,tone:'red'},...(user.role==='super_admin'?[{label:'Schools',key:'schools',target:'schools',icon:Building2,tone:'purple'},{label:'Active accounts',key:'active_users',target:'schools',icon:Users,tone:'blue'}]:[])].filter(s=>hasModule(s.target)).map(s=>{const I=s.icon;return <div className="stat-card dashboard-link-card" key={s.key} role="link" tabIndex={0} onClick={()=>setActive(s.target)} onKeyDown={e=>{if(e.key==='Enter'){setActive(s.target)}}}><div className={`stat-icon ${s.tone}`}><I size={20}/></div><p>{s.label}</p><strong>{stats[s.key]??'—'}</strong><span className="stat-foot">{user.role==='super_admin'&&s.key==='schools'?stats.active_schools+' active · '+stats.inactive_schools+' inactive':'Current records · Click to open'}</span></div>})}</div>
    {user.role==='super_admin'&&<div className="panel dashboard-platform-panel"><div className="panel-heading"><div><h3>Platform attention</h3><p>Live operational items that may need a Developer review</p></div><ShieldCheck size={19}/></div><div className="platform-alert-grid"><button className="platform-alert-item" onClick={()=>setActive('schools')}><span className="platform-alert-icon"><Building2 size={18}/></span><span><strong>{Number(stats.inactive_schools||0)} inactive schools</strong><small>Review school activation and onboarding status</small></span><ArrowRight size={16}/></button><button className="platform-alert-item" onClick={()=>setActive('maintenance')}><span className="platform-alert-icon"><Wrench size={18}/></span><span><strong>{Number(stats.open_maintenance||0)} open maintenance requests</strong><small>Review outstanding campus service work</small></span><ArrowRight size={16}/></button><button className="platform-alert-item" onClick={()=>setActive('payments')}><span className="platform-alert-icon"><Wallet size={18}/></span><span><strong>{feeDues.length} fee records with balances</strong><small>Follow up on unpaid student fee records</small></span><ArrowRight size={16}/></button></div></div>}
    {hasModule('fee-reports')&&<>
     <div className="dashboard-section-heading"><div><h3>Finance overview</h3><p>Collections and outstanding balances · {new Date().getFullYear()}</p></div><button className="secondary" onClick={()=>setActive('fee-reports')}>Full fee reports <FileText size={15}/></button></div>
     <div className="fee-report-stats dashboard-finance-stats">
      <div className="stat-card dashboard-link-card" role="link" tabIndex={0} onClick={()=>setActive("fee-reports")}><div className="stat-icon teal"><Wallet size={19}/></div><p>Collected this year</p><strong>{money(reportData.collected||0)}</strong><span className="stat-foot">Payments received in {new Date().getFullYear()}</span></div>
      <div className="stat-card dashboard-link-card" role="link" tabIndex={0} onClick={()=>setActive("fee-reports")}><div className="stat-icon orange"><Activity size={19}/></div><p>Outstanding balance</p><strong>{money(reportData.outstanding||0)}</strong><span className="stat-foot">Balance on fees assigned this year</span></div>
      <div className="stat-card dashboard-link-card" role="link" tabIndex={0} onClick={()=>setActive("payments")}><div className="stat-icon purple"><Bell size={19}/></div><p>Fees with open balance</p><strong>{feeDues.length}</strong><span className="stat-foot">Student fee records needing follow-up</span></div>
     </div>
     <div className="dashboard-finance-grid">
      <div className="panel dashboard-chart-panel"><div className="panel-heading"><div><h3>Monthly fee collections</h3><p>Payment totals by month for {new Date().getFullYear()}</p></div></div>
       {reportData.chart?.length?<><div className="dashboard-finance-insights"><div><span>Collected this month</span><strong>{money(dashboardMonthAmount)}</strong></div><div><span>Best collection month</span><strong>{dashboardPeakMonth.amount?dashboardPeakMonth.label+' · '+money(dashboardPeakMonth.amount):'—'}</strong></div><div><span>Months with collections</span><strong>{dashboardMonthlySeries.filter((point:any)=>point.amount>0).length} / {dashboardMonthlySeries.length}</strong></div></div><div className="fee-chart">{dashboardMonthlySeries.map((point:any)=>{const max=Math.max(...dashboardMonthlySeries.map((p:any)=>Number(p.amount)),1);return <div className="fee-chart-column" key={point.period}><strong>{money(Number(point.amount))}</strong><div className="fee-chart-track"><div className="fee-chart-bar" style={{height:(Number(point.amount)/max*100)+'%'}}/></div><span>{point.label}</span></div>})}</div></>:<div className="empty-state compact-empty"><strong>No collections recorded this year</strong><p>Monthly totals will appear after payments are entered.</p></div>}
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
    <section className="panel dashboard-roles-panel" aria-labelledby="roles-auth-title">
     <div className="panel-heading roles-auth-heading">
      <div><span className="section-eyebrow">ACCESS CONTROL</span><h3 id="roles-auth-title">Roles &amp; Authentication</h3><p>Understand how each account type accesses the EduNexus platform.</p></div>
      <div className="roles-auth-total"><strong>{roleCatalog.length}</strong><span>Account roles</span></div>
     </div>
     <div className="roles-auth-grid">
      {roleCatalog.map(r=><article className={`role-auth-card ${user.role===r.roleKey?'is-current':''} ${r.roleKey==='super_admin'?'is-platform-role':r.roleKey==='parent'?'is-parent-role':''}`} key={r.roleKey}>
       <div className="role-auth-card-top"><span className="role-auth-avatar" aria-hidden="true">{r.role.split(/\\s+/).map(part=>part[0]).slice(0,2).join('').toUpperCase()}</span><div className="role-auth-title"><h4>{r.role}</h4><span>{r.roleKey==='super_admin'?'Platform administrator':r.roleKey==='parent'?'Family account':'School account'}</span></div>{user.role===r.roleKey&&<span className="role-current-badge"><span/>Signed in</span>}</div>
       <p className="role-auth-description">{r.scope}</p>
       <div className="role-auth-card-footer"><span className={`role-access-badge ${r.roleKey==='super_admin'?'platform':r.roleKey==='parent'?'linked':'workspace'}`}>{r.level}</span><span className="role-auth-state">{user.role===r.roleKey?'Current session':'Available role'}</span></div>
      </article>)}
     </div>
     <div className="roles-auth-note"><ShieldCheck size={17}/><p><strong>Access is controlled by role and permissions.</strong> School roles receive dedicated workspaces and navigation. Developer accounts have platform-wide administration access. Parent accounts are restricted to students linked through verified guardian relationships. Supported API routes enforce saved module permissions, and permission changes are recorded in the audit log.</p></div>
    </section>
    </>}
    {user.role==='super_admin'&&<DeveloperModulePermissionPanel moduleList={modules} roles={roleCatalog} schools={schools} request={request}/>}
    {user.role==='super_admin'&&<>
    <div className="panel dashboard-modules-panel compact-project-overview"><div className="panel-heading"><div><h3>Entire School ERP Project</h3><p>Complete list of modules available in this application</p></div><GraduationCap size={19}/></div><div className="table-wrap"><table><thead><tr><th>Module</th><th>Project area</th><th>Description</th><th>Action</th></tr></thead><tbody>{availableModules.map(m=><tr key={m.key}><td><strong>{m.label}</strong></td><td>{m.key==='dashboard'?'Overview':m.key.startsWith('fee')||m.key==='payments'||m.key==='student-fees'?'Finance':m.key==='students'||m.key==='classes'?'Academics':m.key==='staff'?'HR':m.key==='vehicles'?'Transport':m.key==='hostels'?'Accommodation':m.key==='documents'?'Administration':'Operations'}</td><td>{m.description}</td><td><button className="secondary" onClick={()=>setActive(m.key)}>Open</button></td></tr>)}</tbody></table></div><div className="table-footer">Available modules: {availableModules.length}<span>EduNexus · Project overview</span></div></div>
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
  </div>:<div className="panel data-panel"><div className="panel-heading"><div><h3>{selected.label} records</h3><p>Manage records and keep your school information up to date.</p></div><span className="record-count">{rows.length} records</span></div><div className="table-tools"><div className="search-box"><Search size={17}/><input placeholder={`Search ${selected.label.toLowerCase()}…`} value={query} onChange={e=>setQuery(e.target.value)}/></div><span className="muted small">{loading?'Loading records…':'Latest records first'}</span></div>{active==='schools'&&user.role==='super_admin'&&<div className="school-owner-assign"><div><strong>Assign existing school owner</strong><p>Link an existing standard user login to one school. The user will only see that school's records.</p></div><label>Standard user account<select value={ownerUserId} onChange={e=>setOwnerUserId(e.target.value)}><option value="">Select standard user account</option>{ownerUsers.filter(u=>u.role!=='super_admin'&&u.role!=='parent').map(u=><option key={u.id} value={u.id}>{u.name} · {u.email}{u.school_id?' (already assigned)':''}</option>)}</select></label><label>School<select value={ownerSchoolId} onChange={e=>setOwnerSchoolId(e.target.value)}><option value="">Select school</option>{schools.map(sc=><option key={sc.id} value={sc.id}>{sc.name}</option>)}</select></label><button className="primary" disabled={!ownerUserId||!ownerSchoolId} onClick={assignSchoolOwner}>Assign owner</button></div>}{showForm&&<form className={`record-form ${active==='staff'?'staff-record-form':''}`} onSubmit={save}><div className="form-heading"><h3>{editingRecordId?'Edit':'Add'} {selected.label.toLowerCase()} record</h3><button type="button" className="icon-button" onClick={()=>setShowForm(false)}><X size={18}/></button></div>{active==='student-fees'&&<>{selectedStudent?<div className="student-fee-details"><h4>Student details</h4><div className="student-fee-detail-grid">{[['Admission number',selectedStudent.admission_no],['Student name',selectedStudent.full_name],['Class',selectedStudent.class_name],['Section',selectedStudent.section],['Guardian name',selectedStudent.guardian_name],['Guardian phone',selectedStudent.guardian_phone],['Email',selectedStudent.email],['Date of birth',selectedStudent.date_of_birth],['Address',selectedStudent.address],['Transport required',selectedStudent.transport_required?'Yes':'No'],['Hostel required',selectedStudent.hostel_required?'Yes':'No'],['Student status',selectedStudent.status]].map(([label,value])=><div key={label}><span>{label}</span><strong>{value||'—'}</strong></div>)}</div></div>:<p className="muted">Search and select a student above before entering a fee amount.</p>}</> }<div className="form-grid">{selected.fields?.filter(f=>f.key!=='school_id'||user.role==='super_admin').map(f=><label key={f.key}>{f.type==='school-select'?<>{f.label}<select value={form[f.key]??''} required={f.required} onChange={e=>setForm({...form,[f.key]:e.target.value})}><option value="">Select school</option>{schools.map(sc=><option key={sc.id} value={sc.id}>{sc.name}</option>)}</select></>:active==='staff'&&f.key==='designation'?<>{f.label}<select value={form.designation??'Teacher'} required onChange={e=>setForm({...form,designation:e.target.value})}><option value="">Select designation</option><option>Principal</option><option>Vice Principal</option><option>Teacher</option><option>Accountant</option><option>Clerk</option><option>Office Assistant</option><option>Librarian</option><option>Lab Assistant</option><option>IT Administrator</option><option>Transport Manager</option><option>Hostel Warden</option><option>Security Guard</option><option>Other</option></select></>:active==='staff'&&f.key==='phone'?<><span className="staff-phone-label">{f.label}</span><div className="staff-phone-inputs"><span className="staff-phone-prefix">+91</span><input className="staff-phone-part" aria-label="First five phone digits" type="tel" inputMode="numeric" pattern="[0-9]{5}" maxLength={5} placeholder="98765" value={String(form.phone??'').replace(/^\+91\s*/,'').replace(/\D/g,'').slice(0,5)} required onChange={e=>{const digits=String(form.phone??'').replace(/^\+91\s*/,'').replace(/\D/g,'').slice(0,10);const first=e.target.value.replace(/\D/g,'').slice(0,5);const rest=digits.slice(5,10);setForm({...form,phone:'+91 '+first+rest})}}/><input className="staff-phone-part" aria-label="Last five phone digits" type="tel" inputMode="numeric" pattern="[0-9]{5}" maxLength={5} placeholder="43210" value={String(form.phone??'').replace(/^\+91\s*/,'').replace(/\D/g,'').slice(5,10)} required onChange={e=>{const digits=String(form.phone??'').replace(/^\+91\s*/,'').replace(/\D/g,'').slice(0,10);const first=digits.slice(0,5);const rest=e.target.value.replace(/\D/g,'').slice(0,5);setForm({...form,phone:'+91 '+first+rest})}}/></div><small className="staff-field-help">India +91 · Enter exactly 10 digits in two groups of five</small></>:active==='staff'&&f.key==='salary'?<>{f.label}<input className="staff-salary-input" type="text" inputMode="decimal" value={form.salary??''} required maxLength={10} pattern="[0-9]{1,7}\.[0-9]{2}" placeholder="25000.00" title="Maximum 7 digits before decimal and exactly 2 digits after decimal; maximum ₹150,000.00" onChange={e=>{let v=e.target.value.replace(/[^0-9.]/g,'');const dot=v.indexOf('.');if(dot>=0){v=v.slice(0,dot+1)+v.slice(dot+1).replace(/\./g,'').slice(0,2);v=v.slice(0,dot).slice(0,7)+v.slice(dot)}else{v=v.slice(0,7)}if(v&&Number(v)>150000.00)return;setForm({...form,salary:v})}}/><small className="staff-field-help">Up to 7 whole-number digits · exactly 2 decimal digits · maximum ₹150,000.00</small></>:active==='staff'&&f.key==='status'?<>{f.label}<select value={form.status??'active'} onChange={e=>setForm({...form,status:e.target.value})}><option value="active">Active</option><option value="absent">Absent</option><option value="suspended">Suspended</option><option value="terminated">Terminated</option><option value="sick">Sick</option><option value="leave">Leave</option></select></>:f.type==='textarea'?<>{f.label}<textarea value={form[f.key]??''} required={f.required} maxLength={10000} onChange={e=>setForm({...form,[f.key]:e.target.value})}/></>:f.type==='select'?<>{f.label}<select value={form[f.key]??''} required={f.required} onChange={e=>setForm({...form,[f.key]:e.target.value})}><option value="">Select {f.label.toLowerCase()}</option>{(f.options||[]).map(option=><option key={option} value={option}>{option.replaceAll('_',' ')}</option>)}</select></>:<>{f.label}<input type={f.type||'text'} value={form[f.key]??''} required={f.required} min={f.type==='number'?0:undefined} max={f.key==='salary'?150000:undefined} step={f.key==='salary'?0.01:undefined} maxLength={active==='staff'?({employee_no:8,full_name:100,department:32,email:40}[f.key] as number|undefined):undefined} pattern={active==='staff'?({employee_no:'[A-Z]{4}[0-9]{4}',full_name:"[A-Za-z][A-Za-z .'-]*",department:'[A-Za-z ]{0,32}',email:'[A-Za-z0-9._%+-]+@gmail\\.com'} as Record<string,string>)[f.key]:undefined} title={active==='staff'&&f.key==='employee_no'?'Enter exactly 4 letters followed by 4 digits':active==='staff'&&f.key==='email'?'Use a Gmail address (maximum 40 characters)':undefined} placeholder={active==='staff'&&f.key==='employee_no'?'e.g. SPVB0001':undefined} onChange={e=>setForm({...form,[f.key]:f.key==='employee_no'?(()=>{const raw=e.target.value.toUpperCase().replace(/[^A-Z0-9]/g,'');const letters=raw.replace(/[^A-Z]/g,'').slice(0,4);const digits=raw.replace(/[^0-9]/g,'').slice(0,4);return letters+digits})():e.target.value})}/></>}</label>)}</div>{active==='staff'&&user.role==='super_admin'&&!editingRecordId&&<div className="staff-account-options"><label className="checkbox-field"><input type="checkbox" checked={Boolean(form.create_account)} onChange={e=>setForm({...form,create_account:e.target.checked})}/> Create login account for this staff member</label>{form.create_account&&<div className="form-grid"><label>Permission / role<select value={form.account_role??'principal'} onChange={e=>setForm({...form,account_role:e.target.value})}>{Object.entries(roleLabels).filter(([key])=>key!=='super_admin'&&key!=='parent'&&key!=='user'&&key!=='admin'&&key!=='accountant').map(([key,label])=><option key={key} value={key}>{label}</option>)}<option value="parent">Parent</option></select></label><label>Temporary login password (minimum 12 characters)<input type="password" minLength={12} required value={form.account_password??''} onChange={e=>setForm({...form,account_password:e.target.value})}/></label><p className="muted">The Gmail address above is the login username. Staff sign in with this email, the password, and the selected school's code. All standard school users share the same EduNexus module access. School code: {schools.find(sc=>String(sc.id)===String(form.school_id))?.code||'Select a school first'}</p></div>}</div>}<div className="form-actions"><button type="button" className="secondary" onClick={()=>setShowForm(false)}>Cancel</button><button className="primary"><Plus size={16}/> {editingRecordId?'Update record':'Save record'}</button></div></form>}<div className="table-wrap"><table><thead><tr><th>ID</th>{active==='staff'&&user.role==='super_admin'&&<th>School</th>}{(selected.fields||[]).slice(0,5).map(f=><th key={f.key}>{f.label}</th>)}{active==='library-books'&&<th>Available</th>}<th>Status</th>{showRecordActions&&<th>Actions</th>}</tr></thead><tbody>{rows.map(r=><tr key={r.id}><td className="id-cell">#{r.id}</td>{active==='staff'&&user.role==='super_admin'&&<td>{schools.find(sc=>sc.id===r.school_id)?.name||'—'}</td>}{(selected.fields||[]).slice(0,5).map(f=><td key={f.key}>{f.type==='checkbox'?(r[f.key]?'Yes':'No'):(r[f.key]??'—')}</td>)}{active==='library-books'&&<td><strong>{r.available_copies}</strong> / {r.total_copies}</td>}<td><span className={`status-badge ${String(r.status||'active').toLowerCase()}`}>{r.status||(r.is_active?'active':'inactive')}</span></td>{showRecordActions&&<td><div className="row-actions"><button type="button" className="secondary" disabled={active==='library-loans'&&r.status!=='issued'} onClick={()=>{setEditingRecordId(r.id);setForm(active==='staff'?({...r,phone:r.phone?('+91 '+String(r.phone).replace(/^\\+91\\s*/,'').trim()):'+91 ',salary:Number(r.salary??0).toFixed(2)}):({...r}));setShowForm(true)}}>Edit</button>{active==='student-leave'&&user.role!=='parent'&&r.status==='pending'&&<><button type="button" className="secondary" onClick={()=>reviewLeave(r,'approved')}>Approve</button><button type="button" className="secondary" onClick={()=>reviewLeave(r,'rejected')}>Reject</button></>}{active==='library-loans'&&r.status==='issued'&&<button type="button" className="primary" onClick={()=>returnLibraryLoan(r)}>Return book</button>}{active!=='library-loans'&&(active!=='library-books'||user.role==='super_admin'||user.role==='admin'||user.role==='user')&&<button type="button" className="secondary" onClick={()=>active==='staff'?deleteStaff(r):deleteAcademicRecord(r)}>Delete</button>}</div></td>}</tr>)}{!rows.length&&<tr><td colSpan={(selected.fields?.slice(0,5).length||0)+2+(active==='staff'&&user.role==='super_admin'?1:0)+(active==='library-books'?1:0)+(showRecordActions?1:0)}><div className="empty-state"><div className="empty-icon"><Icon size={25}/></div><strong>{loading?'Loading records…':'No records found'}</strong><p>{loading?'Please wait.':'Create your first record to get started.'}</p>{!loading&&(user.role!=='super_admin'||active==='schools'||active==='staff'||['attendance','timetable','exams','report-cards'].includes(active))&&<button className="primary" onClick={()=>setShowForm(true)}><Plus size={16}/> Add first record</button>}</div></td></tr>}</tbody></table></div><div className="table-footer">Showing {rows.length} record(s) <span>EduNexus · Secure workspace</span></div></div>}
  <footer className="footer"><span>© {new Date().getFullYear()} EduNexus</span><span>School operations platform</span></footer></div></main>
 </div>
 }


function ParentRelationshipPanel({request}:{request:(url:string,options?:RequestInit)=>Promise<any>}) {
 const [links,setLinks]=useState<any[]>([]);
 const [query,setQuery]=useState('');
 const [status,setStatus]=useState<'all'|'active'|'inactive'>('all');
 const [busy,setBusy]=useState(false);
 const [updating,setUpdating]=useState<number|null>(null);
 const [error,setError]=useState('');
 const [notice,setNotice]=useState('');
 async function load(){
  setBusy(true);setError('');
  try{
   const result=await request('/api/parent-links');
   setLinks(Array.isArray(result)?result:[]);
  }catch(err:any){setError(err.message||'Could not load parent relationships')}
  finally{setBusy(false)}
 }
 useEffect(()=>{load()},[]);
 const filtered=useMemo(()=>{
  const term=query.trim().toLowerCase();
  return links.filter(link=>(status==='all'||(status==='active'?Boolean(link.is_active):!link.is_active))&&(!term||[link.parent_name,link.parent_email,link.student_name,link.admission_no,link.class_name,link.section,link.relationship]
   .some(value=>String(value||'').toLowerCase().includes(term))));
 },[links,query]);
 async function toggle(link:any){
  const next=!link.is_active;
  const action=next?'restore access to':'remove access to';
  if(!window.confirm('Are you sure you want to '+action+' '+link.student_name+' for '+link.parent_name+'?'))return;
  setUpdating(link.id);setError('');setNotice('');
  try{
   await request('/api/parent-links/'+link.id,{method:'PATCH',body:JSON.stringify({is_active:next})});
   setLinks(current=>current.map(item=>item.id===link.id?{...item,is_active:next}:item));
   setNotice(next?'Parent access restored.':'Parent access deactivated immediately.');
  }catch(err:any){setError(err.message||'Could not update relationship')}
  finally{setUpdating(null)}
 }
 return <section className="parent-relations-workspace">
  <div className="parent-relations-hero">
   <div><span className="parent-relations-eyebrow">FAMILY ACCESS GOVERNANCE</span><h2>Parent relationships</h2><p>Review which parent accounts can access each student. Access is granted only through approved, active school relationships.</p></div>
   <div className="parent-relations-security"><ShieldCheck size={17}/> School-scoped access</div>
  </div>
  <div className="parent-relations-stats">
   <div><span>Total relationships</span><strong>{links.length}</strong></div>
   <div><span>Active access</span><strong>{links.filter(item=>item.is_active).length}</strong></div>
   <div><span>Inactive access</span><strong>{links.filter(item=>!item.is_active).length}</strong></div>
  </div>
  <div className="panel parent-relations-panel">
   <div className="parent-relations-toolbar">
    <div><h3>Relationship register</h3><p>Search by parent, student, admission number or relationship.</p></div>
    <button className="secondary" type="button" onClick={load} disabled={busy}><RefreshCw size={15}/>{busy?'Refreshing…':'Refresh'}</button>
   </div>
   <div className="parent-relations-filters">
    <label className="parent-relations-search"><Search size={16}/><input aria-label="Search parent relationships" placeholder="Search parent or student…" value={query} onChange={event=>setQuery(event.target.value)}/></label>
    <label className="parent-relations-status">Access status<select value={status} onChange={event=>setStatus(event.target.value as 'all'|'active'|'inactive')}><option value="all">All relationships</option><option value="active">Active only</option><option value="inactive">Inactive only</option></select></label>
   </div>
   {error&&<div className="error auth-message" role="alert">{error}</div>}
   {notice&&<div className="success auth-message" role="status">{notice}</div>}
   <div className="table-wrap">
    <table className="parent-relations-table"><thead><tr><th>Parent account</th><th>Linked student</th><th>Relationship</th><th>Access</th><th>Action</th></tr></thead>
    <tbody>{filtered.map(link=><tr key={link.id}>
     <td><strong>{link.parent_name||'Parent account'}</strong><small>{link.parent_email||'Email not available'}</small></td>
     <td><strong>{link.student_name||'Student'}</strong><small>{link.admission_no||'No admission number'} · {link.class_name||'Class not set'} {link.section||''}</small></td>
     <td>{link.relationship||'parent'}</td>
     <td><span className={'status-badge '+(link.is_active?'active':'inactive')}>{link.is_active?'Active':'Inactive'}</span></td>
     <td><button type="button" className={link.is_active?'secondary':'primary'} disabled={updating===link.id} onClick={()=>toggle(link)}>{updating===link.id?'Updating…':link.is_active?'Deactivate':'Reactivate'}</button></td>
    </tr>)}
    {!filtered.length&&<tr><td colSpan={5}><div className="empty-state compact-empty"><strong>{busy?'Loading relationships…':'No parent relationships found'}</strong><p>{busy?'Please wait while the register loads.':query?'Try another search term or status filter.':'Approved parent–student links will appear here.'}</p></div></td></tr>}
    </tbody></table>
   </div>
   <div className="parent-relations-footer"><span>{filtered.length} of {links.length} relationship(s)</span><span>Changes are audited · Parent access is enforced by the backend</span></div>
  </div>
 </section>
}


function DeveloperModulePermissionPanel({moduleList,roles,schools,request}:{moduleList:ModuleDef[];roles:{role:string;roleKey:string;scope:string;level:string}[];schools:any[];request:(url:string,options?:RequestInit)=>Promise<any>}) {
 const [role,setRole]=useState('teacher');
 const [scope,setScope]=useState<'global'|'school'>('global');
 const [schoolId,setSchoolId]=useState('');
 const [permissions,setPermissions]=useState<Record<string,boolean>>({});
 const [audit,setAudit]=useState<any[]>([]);
 const [configured,setConfigured]=useState(false);
 const [globalConfigured,setGlobalConfigured]=useState(false);
 const [schoolConfigured,setSchoolConfigured]=useState(false);
 const [busy,setBusy]=useState(false);
 const [message,setMessage]=useState('');
 const [error,setError]=useState('');
 const actions=['View','Create','Edit','Delete','Approve','Export'];
 const approvedSchools=schools.filter(s=>s.approval_status==='approved'&&s.is_active!==false);
 const enabledCount=moduleList.filter(m=>permissions[m.key+':View']).length;
 const schoolQuery=scope==='school'&&schoolId?'?school_id='+encodeURIComponent(schoolId):'';
 const endpoint='/api/rbac/roles/'+encodeURIComponent(role)+'/permissions'+schoolQuery;
 async function loadPermissions(){
  if(scope==='school'&&!schoolId){setPermissions({});setConfigured(false);setSchoolConfigured(false);return}
  setBusy(true);setError('');
  try{const result=await request(endpoint);setPermissions(result.permissions||{});setConfigured(Boolean(result.configured));setGlobalConfigured(Boolean(result.global_configured));setSchoolConfigured(Boolean(result.school_configured))}
  catch(err:any){setError(err.message||'Could not load permissions')}
  finally{setBusy(false)}
 }
 useEffect(()=>{loadPermissions()},[role,scope,schoolId]);
 useEffect(()=>{let active=true;request('/api/rbac/audit-logs?limit=8').then(result=>{if(active)setAudit(result||[])}).catch(()=>{if(active)setAudit([])});return()=>{active=false}},[]);
 function toggle(key:string,action:string,value:boolean){setPermissions(old=>({...old,[key+':'+action]:value}))}
 function setAll(value:boolean){setPermissions(Object.fromEntries(moduleList.flatMap(m=>actions.map(a=>[m.key+':'+a,value]))))}
 async function save(){
  if(scope==='school'&&!schoolId){setError('Select a client school before saving.');return}
  setBusy(true);setError('');setMessage('');
  try{
   const complete=Object.fromEntries(moduleList.flatMap(m=>actions.map(a=>[m.key+':'+a,Boolean(permissions[m.key+':'+a])])));
   const url='/api/rbac/roles/'+encodeURIComponent(role)+'/permissions'+(scope==='school'?'?school_id='+encodeURIComponent(schoolId):'');
   const result=await request(url,{method:'PUT',body:JSON.stringify({permissions:complete})});
   setPermissions(complete);setConfigured(true);setGlobalConfigured(scope==='global'||globalConfigured);setSchoolConfigured(scope==='school'||schoolConfigured);
   setMessage(result.message||'Permissions saved successfully');setAudit(await request('/api/rbac/audit-logs?limit=8'));
  }catch(err:any){setError(err.message||'Could not save permissions')}
  finally{setBusy(false)}
 }
 async function resetToGlobal(){
  if(!schoolId)return;
  if(!window.confirm('Reset this school role to ERP-wide permissions? Its custom overrides will be deleted.'))return;
  setBusy(true);setError('');setMessage('');
  try{
   const result=await request('/api/rbac/roles/'+encodeURIComponent(role)+'/permissions?school_id='+encodeURIComponent(schoolId),{method:'DELETE'});
   setMessage(result.message||'School override reset');await loadPermissions();setAudit(await request('/api/rbac/audit-logs?limit=8'));
  }catch(err:any){setError(err.message||'Could not reset school permissions')}
  finally{setBusy(false)}
 }
 return <div className="panel developer-permissions-panel">
  <div className="panel-heading"><div><h3>Role permissions</h3><p>Configure permissions across the ERP or override access for an individual client school.</p></div><ShieldCheck size={20}/></div>
  <div className="permission-toolbar">
   <label className="auth-field">Permission scope<select value={scope} disabled={busy} onChange={e=>{const next=e.target.value as 'global'|'school';setScope(next);if(next==='school'&&!schoolId&&approvedSchools.length)setSchoolId(String(approvedSchools[0].id))}}><option value="global">ERP-wide (all clients)</option><option value="school">Client-wise (individual school)</option></select></label>
   {scope==='school'&&<label className="auth-field">Select client school<select value={schoolId} disabled={busy} onChange={e=>setSchoolId(e.target.value)}><option value="">Choose approved school</option>{approvedSchools.map(s=><option key={s.id} value={s.id}>{s.name} · {s.code}</option>)}</select></label>}
   <label className="auth-field">Select role<select value={role} disabled={busy} onChange={e=>setRole(e.target.value)}>{roles.filter(r=>r.roleKey!=='super_admin'&&r.roleKey!=='parent').map(r=><option key={r.roleKey} value={r.roleKey}>{r.role}</option>)}</select></label>
   <div className="permission-summary"><strong>{enabledCount} / {moduleList.length}</strong><span>modules with View enabled</span></div>
   <div className="permission-bulk-actions"><button type="button" className="secondary" disabled={busy||scope==='school'&&!schoolId} onClick={()=>setAll(true)}>Select all</button><button type="button" className="secondary" disabled={busy||scope==='school'&&!schoolId} onClick={()=>setAll(false)}>Clear all</button></div>
  </div>
  {scope==='school'&&!schoolId&&<p className="status-note">Choose an approved school to configure its permissions. Approvals pending from Developer are not available here.</p>}
  {scope==='school'&&schoolId&&!schoolConfigured&&<p className="status-note">This client has no custom matrix for this role. The displayed permissions are inherited from ERP-wide settings{globalConfigured?'':' or the system defaults'} until you save a client-specific override.</p>}
  {scope==='global'&&!configured&&<p className="status-note">Showing the existing system defaults for this role. Save to create ERP-wide permissions that apply to all clients unless overridden.</p>}
  {error&&<div className="error auth-message" role="alert">{error}</div>}{message&&<div className="success auth-message" role="status">{message}</div>}
  <div className="table-wrap permission-table-wrap"><table className="permission-table"><thead><tr><th>Module</th>{actions.map(a=><th key={a}>{a}</th>)}</tr></thead><tbody>{moduleList.map(m=><tr key={m.key}><td><strong>{m.label}</strong><small>{m.description}</small></td>{actions.map(a=><td key={a}><input aria-label={m.label+' '+a+' permission'} type="checkbox" disabled={busy||(scope==='school'&&!schoolId)} checked={Boolean(permissions[m.key+':'+a])} onChange={e=>toggle(m.key,a,e.target.checked)}/></td>)}</tr>)}</tbody></table></div>
  <div className="permission-footer"><span>{role.replaceAll('_',' ')} · {Object.values(permissions).filter(Boolean).length} permissions selected</span><div className="permission-bulk-actions">{scope==='school'&&schoolConfigured&&<button type="button" className="secondary" disabled={busy} onClick={resetToGlobal}>Reset to ERP-wide defaults</button>}<button type="button" className="primary" disabled={busy||(scope==='school'&&!schoolId)} onClick={save}>{busy?'Saving…':scope==='school'?'Save client permissions':'Save ERP-wide permissions'}</button></div></div>
  <p className="status-note">School-specific permissions take precedence over ERP-wide defaults. Resetting a client removes its override and restores inheritance. Developer access remains platform-wide.</p>
  <div className="permission-audit"><div className="panel-heading"><div><h3>Recent access changes</h3><p>Latest role-permission updates</p></div><span className="record-count">{audit.length} events</span></div><div className="table-wrap"><table><thead><tr><th>Event</th><th>Scope / role</th><th>Time</th></tr></thead><tbody>{audit.map(item=><tr key={item.id}><td>{item.event_type}</td><td>{item.target_id||'—'}</td><td>{item.created_at?new Date(item.created_at).toLocaleString('en-IN'):'—'}</td></tr>)}{!audit.length&&<tr><td colSpan={3}><div className="empty-state compact-empty"><strong>No access changes recorded yet</strong><p>Saved role-permission changes will appear here.</p></div></td></tr>}</tbody></table></div></div>
 </div>
}

export default App
