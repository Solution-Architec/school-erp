import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { Activity, Building2, CalendarClock, CheckCircle2, CircleAlert, FileText, Headset, IndianRupee, RefreshCw, Save, ShieldCheck, Users, X, Mail, UserPlus, Wrench, AlertTriangle, CreditCard } from 'lucide-react'
import './DeveloperControlCentre.css'

type Request = (url: string, options?: RequestInit) => Promise<any>
type Client = {
  id:number; name:string; code:string; institution_type:string; is_active:boolean; approval_status:string;
  users:number; students:number; staff:number; profile:Record<string,any>; subscription:any
}
type Overview = {
  institutions:number; active_institutions:number; users:number; students:number; staff:number;
  online_users:number; active_subscriptions:number; subscriptions_expiring_30_days:number;
  pending_quotations:number; received_amount:number; open_support_tickets:number
}
const emptyOverview:Overview={institutions:0,active_institutions:0,users:0,students:0,staff:0,online_users:0,active_subscriptions:0,subscriptions_expiring_30_days:0,pending_quotations:0,received_amount:0,open_support_tickets:0}
const tabs=['Overview','Client Requests','Clients','User access','Role access','Quotations','Subscriptions','Collections','Support','Platform operations','Live usage','Reports','System & audit']
const money=(v:any)=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:2}).format(Number(v||0))
const day=(v:any)=>v?new Date(v).toLocaleDateString('en-IN'):'—'
const dateInput=(v:any)=>v?String(v).slice(0,10):''
const INSTITUTION_ROLE_TEMPLATES:Record<string,{roleKey:string;role:string}[]> = {
  school:[
    {roleKey:'principal',role:'Principal'},{roleKey:'vice_principal',role:'Vice Principal'},{roleKey:'school_hod',role:'Head of Department'},
    {roleKey:'teacher',role:'Teacher'},{roleKey:'class_teacher',role:'Class Teacher'},{roleKey:'school_accountant',role:'Accountant'},
    {roleKey:'admission_officer',role:'Admission Officer'},{roleKey:'examination_controller',role:'Examination Controller'},
    {roleKey:'librarian',role:'Librarian'},{roleKey:'transport_manager',role:'Transport Manager'},
    {roleKey:'hostel_warden',role:'Hostel Warden'},{roleKey:'school_counsellor',role:'Counsellor'},
    {roleKey:'school_receptionist',role:'Receptionist'},{roleKey:'parent',role:'Parent'},{roleKey:'school_student',role:'Student'}
  ],
  college:[
    {roleKey:'college_admin',role:'College Administrator'},{roleKey:'college_principal',role:'Principal'},
    {roleKey:'college_vice_principal',role:'Vice Principal'},{roleKey:'dean',role:'Dean'},
    {roleKey:'college_hod',role:'Head of Department'},{roleKey:'lecturer',role:'Lecturer'},
    {roleKey:'college_professor',role:'Professor'},{roleKey:'academic_coordinator',role:'Academic Coordinator'},
    {roleKey:'registrar',role:'Registrar'},{roleKey:'college_exam_controller',role:'Controller of Examinations'},
    {roleKey:'college_admission_officer',role:'Admission Officer'},{roleKey:'accounts_officer',role:'Accounts Officer'},
    {roleKey:'college_librarian',role:'Librarian'},{roleKey:'lab_in_charge',role:'Lab In-charge'},
    {roleKey:'placement_officer',role:'Placement Officer'},{roleKey:'college_student',role:'Student'}
  ],
  university:[
    {roleKey:'university_admin',role:'University Administrator'},{roleKey:'chancellor',role:'Chancellor'},
    {roleKey:'vice_chancellor',role:'Vice Chancellor'},{roleKey:'university_registrar',role:'Registrar'},
    {roleKey:'university_dean',role:'Dean'},{roleKey:'university_director',role:'Director'},
    {roleKey:'department_head',role:'Department Head'},{roleKey:'university_professor',role:'Professor / Faculty'},
    {roleKey:'research_supervisor',role:'Research Supervisor'},{roleKey:'university_exam_controller',role:'Examination Controller'},
    {roleKey:'university_finance_officer',role:'Finance Officer'},{roleKey:'university_admission_officer',role:'Admission Officer'},
    {roleKey:'research_scholar',role:'Research Scholar'},{roleKey:'university_student',role:'Student'}
  ],
  other:[
    {roleKey:'institute_admin',role:'Institute Administrator'},{roleKey:'centre_director',role:'Centre Director'},
    {roleKey:'other_academic_coordinator',role:'Academic Coordinator'},{roleKey:'batch_coordinator',role:'Batch Coordinator'},
    {roleKey:'trainer',role:'Trainer / Faculty'},{roleKey:'admission_counsellor',role:'Admission Counsellor'},
    {roleKey:'admission_executive',role:'Admission Executive'},{roleKey:'other_accounts_officer',role:'Accounts Officer'},
    {roleKey:'training_librarian',role:'Librarian'},{roleKey:'training_student',role:'Learner / Student'}
  ]
}

export default function DeveloperControlCentre({request,onEnterWorkspace,moduleList}:{request:Request;onEnterWorkspace:(schoolId:number)=>Promise<void>;moduleList:{key:string;label:string;description:string}[];roles:{role:string;roleKey:string;scope:string;level:string}[]}) {
  const [tab,setTab]=useState('Overview')
  const [overview,setOverview]=useState<Overview>(emptyOverview)
  const [clients,setClients]=useState<Client[]>([])
  const [quotes,setQuotes]=useState<any[]>([])
  const [subscriptions,setSubscriptions]=useState<any[]>([])
  const [payments,setPayments]=useState<any[]>([])
  const [tickets,setTickets]=useState<any[]>([])
  const [activity,setActivity]=useState<any[]>([])
  const [health,setHealth]=useState<any>({api:'unknown',database:'unknown',checked_at:null})
  const [audit,setAudit]=useState<any[]>([])
  const [selected,setSelected]=useState<Client|null>(null)
  const [clientDetail,setClientDetail]=useState<any|null>(null)
  const [profile,setProfile]=useState<Record<string,string>>({})
  const [query,setQuery]=useState('')
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  const [notice,setNotice]=useState('')
  const [formKind,setFormKind]=useState('')
  const [form,setForm]=useState<Record<string,string>>({})
  const [roleInstitutionType,setRoleInstitutionType]=useState('school')
  const [roleClientId,setRoleClientId]=useState('')
  const [roleKey,setRoleKey]=useState('principal')
  const roleTemplates=INSTITUTION_ROLE_TEMPLATES[roleInstitutionType]||INSTITUTION_ROLE_TEMPLATES.school
  const [rolePermissions,setRolePermissions]=useState<Record<string,boolean>>({})
  const [rolePermissionMeta,setRolePermissionMeta]=useState<any>({})
  const [roleBusy,setRoleBusy]=useState(false)
  const [roleError,setRoleError]=useState('')
  const [roleNotice,setRoleNotice]=useState('')
  const [clientRequests,setClientRequests]=useState<any[]>([])
  const [opsClientId,setOpsClientId]=useState('')
  const [opsUsers,setOpsUsers]=useState<any[]>([])
  const [inviteEmail,setInviteEmail]=useState('')
  const [inviteRole,setInviteRole]=useState('teacher')
  const [inviteLink,setInviteLink]=useState('')
  const [incidents,setIncidents]=useState<any[]>([])
  const [windows,setWindows]=useState<any[]>([])
  const [infra,setInfra]=useState<any>({})
  const [opsReport,setOpsReport]=useState<any>({})
  const [incidentForm,setIncidentForm]=useState({title:'',description:'',severity:'medium',affected_scope:'platform',school_id:'',assigned_to:''})
  const [windowForm,setWindowForm]=useState({title:'',description:'',starts_at:'',ends_at:''})
  const [checkoutSchoolId,setCheckoutSchoolId]=useState('')
  const [checkoutAmount,setCheckoutAmount]=useState('')

  useEffect(()=>{
    if(tab!=='Role access'||!roleClientId)return
    let current=true
    setRoleBusy(true);setRoleError('')
    request('/api/rbac/roles/'+encodeURIComponent(roleKey)+'/permissions?school_id='+encodeURIComponent(roleClientId))
      .then(result=>{if(current){setRolePermissions(result.permissions||{});setRolePermissionMeta(result)}})
      .catch((e:any)=>{if(current)setRoleError(e.message||'Could not load role permissions')})
      .finally(()=>{if(current)setRoleBusy(false)})
    return()=>{current=false}
  },[tab,roleClientId,roleKey,request])


  async function load(){
    setBusy(true);setError('')
    try{
      const [o,c,q,s,p,t,a,h,logs,cr,inc,win,ih,rp]=await Promise.all([
        request('/api/platform/overview'),request('/api/platform/clients'),request('/api/platform/quotations'),
        request('/api/platform/subscriptions'),request('/api/platform/payments'),request('/api/platform/support-tickets'),
        request('/api/platform/activity'),request('/api/platform/system-health'),request('/api/rbac/audit-logs?limit=30'),
        request('/api/platform/ops/client-requests'),request('/api/platform/ops/incidents'),
        request('/api/platform/ops/maintenance-windows'),request('/api/platform/ops/infrastructure-health'),
        request('/api/platform/ops/reports')
      ])
      setOverview(o);setClients(c);setQuotes(q);setSubscriptions(s);setPayments(p);setTickets(t);setActivity(a);setHealth(h);setAudit(logs)
      setClientRequests(cr);setIncidents(inc);setWindows(win);setInfra(ih);setOpsReport(rp)
      if(selected){const fresh=c.find((item:Client)=>item.id===selected.id);if(fresh){setSelected(fresh);setProfile(toProfile(fresh.profile))}}
    }catch(e:any){setError(e.message||'Could not load platform data')}
    finally{setBusy(false)}
  }
  function toProfile(p:Record<string,any>={}){return Object.fromEntries(['contact_person','contact_email','contact_phone','address','city','state','country','affiliation','registration_no','website','notes'].map(k=>[k,String(p[k]??'')]))}
  useEffect(()=>{load()},[])
  async function loadOpsUsers(schoolId:string){
    setOpsClientId(schoolId);setOpsUsers([]);setInviteLink('')
    if(!schoolId)return
    try{setOpsUsers(await request('/api/platform/ops/users?school_id='+encodeURIComponent(schoolId)))}
    catch(e:any){setError(e.message||'Could not load institution users')}
    const c=clients.find(x=>String(x.id)===schoolId)
    const key=c?.institution_type==='school'?'school':c?.institution_type==='college'?'college':c?.institution_type==='university'?'university':'other'
    setInviteRole((INSTITUTION_ROLE_TEMPLATES[key]||INSTITUTION_ROLE_TEMPLATES.school)[0].roleKey)
  }
  async function decideRequest(item:any,decision:string){
    let reason=''
    if(decision==='request_info'){reason=window.prompt('What additional information is required?','Please provide the institution registration documents and contact details.')||'';if(!reason.trim())return}
    else if(!window.confirm((decision==='approve'?'Approve':'Reject')+' '+item.school_name+'?'))return
    setBusy(true);setError('');setNotice('')
    try{await request('/api/platform/ops/client-requests/'+item.school_id+'/decision',{method:'POST',body:JSON.stringify({decision,reason})});setNotice('Client request updated.');await load()}
    catch(e:any){setError(e.message||'Could not update client request')}finally{setBusy(false)}
  }
  async function sendInvitation(e:FormEvent){
    e.preventDefault();if(!opsClientId)return
    setBusy(true);setError('');setNotice('');setInviteLink('')
    try{const result=await request('/api/platform/ops/invitations',{method:'POST',body:JSON.stringify({school_id:Number(opsClientId),email:inviteEmail,role:inviteRole})});setInviteLink(result.invitation_url||'');setNotice(result.email_sent?'Invitation email sent.':'Invitation created; copy the one-time link below and share it securely.');setInviteEmail('');await loadOpsUsers(opsClientId)}
    catch(e:any){setError(e.message||'Could not create invitation')}finally{setBusy(false)}
  }
  async function changeUserRole(userId:number,role:string){
    if(!opsClientId)return
    setBusy(true);setError('')
    try{await request('/api/platform/ops/clients/'+opsClientId+'/users/'+userId+'/role',{method:'PUT',body:JSON.stringify({role})});setNotice('Institution role updated and audited.');await loadOpsUsers(opsClientId)}
    catch(e:any){setError(e.message||'Could not update user role')}finally{setBusy(false)}
  }
  async function createIncident(e:FormEvent){
    e.preventDefault();setBusy(true);setError('')
    try{await request('/api/platform/ops/incidents',{method:'POST',body:JSON.stringify({...incidentForm,school_id:incidentForm.school_id?Number(incidentForm.school_id):null})});setIncidentForm({title:'',description:'',severity:'medium',affected_scope:'platform',school_id:'',assigned_to:''});setNotice('Platform incident created.');await load()}
    catch(e:any){setError(e.message||'Could not create incident')}finally{setBusy(false)}
  }
  async function updateIncident(item:any,status:string){
    setBusy(true);setError('')
    try{await request('/api/platform/ops/incidents/'+item.id,{method:'PATCH',body:JSON.stringify({status,severity:item.severity,assigned_to:item.assigned_to||'',resolution_notes:item.resolution_notes||''})});setNotice('Incident updated.');await load()}
    catch(e:any){setError(e.message||'Could not update incident')}finally{setBusy(false)}
  }
  async function createMaintenanceWindow(e:FormEvent){
    e.preventDefault();setBusy(true);setError('')
    try{await request('/api/platform/ops/maintenance-windows',{method:'POST',body:JSON.stringify({...windowForm,starts_at:new Date(windowForm.starts_at).toISOString(),ends_at:new Date(windowForm.ends_at).toISOString()})});setWindowForm({title:'',description:'',starts_at:'',ends_at:''});setNotice('Maintenance window scheduled.');await load()}
    catch(e:any){setError(e.message||'Could not schedule maintenance')}finally{setBusy(false)}
  }
  async function runExpirySweep(){
    if(!window.confirm('Run subscription expiry enforcement now? Institutions beyond the configured grace period will be suspended.'))return
    setBusy(true);setError('')
    try{const result=await request('/api/platform/ops/subscriptions/expiry-sweep',{method:'POST'});setNotice(result.count+' institution(s) suspended after subscription expiry.');await load()}
    catch(e:any){setError(e.message||'Expiry check failed')}finally{setBusy(false)}
  }
  async function startGatewayCheckout(){
    if(!checkoutSchoolId||!checkoutAmount)return
    setBusy(true);setError('')
    try{
      const order=await request('/api/platform/ops/payments/checkout',{method:'POST',body:JSON.stringify({school_id:Number(checkoutSchoolId),amount:checkoutAmount})})
      if(!(window as any).Razorpay){
        await new Promise<void>((resolve,reject)=>{const script=document.createElement('script');script.src='https://checkout.razorpay.com/v1/checkout.js';script.onload=()=>resolve();script.onerror=()=>reject(new Error('Could not load Razorpay Checkout'));document.body.appendChild(script)})
      }
      const RazorpayCtor=(window as any).Razorpay
      const checkout=new RazorpayCtor({key:order.key_id,amount:order.amount,currency:order.currency,name:'EduNexus',description:'Institution subscription payment',order_id:order.order_id,
        handler:async(response:any)=>{try{const verified=await request('/api/platform/ops/payments/verify',{method:'POST',body:JSON.stringify({school_id:Number(checkoutSchoolId),order_id:response.razorpay_order_id,payment_id:response.razorpay_payment_id,signature:response.razorpay_signature})});setNotice('Payment verified and recorded. Reference: '+(verified.payment_id||response.razorpay_payment_id));await load()}catch(err:any){setError(err.message||'Payment verification failed')}},
        modal:{ondismiss:()=>setNotice('Payment window closed. No payment was recorded unless provider verification completed.')}})
      checkout.open()
    }catch(e:any){setError(e.message||'Could not start checkout')}finally{setBusy(false)}
  }
  const filteredClients=useMemo(()=>clients.filter(c=>(c.name+' '+c.code+' '+c.institution_type).toLowerCase().includes(query.toLowerCase())),[clients,query])
  const clientName=(id:number)=>clients.find(c=>c.id===id)?.name||'Unknown institution'
  async function openClient(c:Client){setSelected(c);setProfile(toProfile(c.profile));setClientDetail(null);try{setClientDetail(await request('/api/platform/clients/'+c.id))}catch(e:any){setError(e.message||'Could not load client details')}}
  function openForm(kind:string,c?:Client){
    setFormKind(kind)
    setForm(kind==='client'?(c?{school_id:String(c.id),name:c.name,code:c.code,institution_type:c.institution_type}:{name:'',code:'',institution_type:'school'}):(c?{school_id:String(c.id)}:{}))
    if(kind==='quotation')setForm(c?{school_id:String(c.id),title:'EduNexus subscription / services',amount:'',tax_amount:'0',discount_amount:'0',valid_until:'',status:'draft',notes:''}:{title:'EduNexus subscription / services',amount:'',tax_amount:'0',discount_amount:'0',valid_until:'',status:'draft',notes:''})
    if(kind==='subscription')setForm(c?{school_id:String(c.id),plan_name:'Standard',amount:'',billing_cycle:'annual',start_date:dateInput(new Date()),end_date:'',status:'active',notes:''}:{plan_name:'Standard',amount:'',billing_cycle:'annual',start_date:dateInput(new Date()),end_date:'',status:'active',notes:''})
    if(kind==='payment')setForm(c?{school_id:String(c.id),amount:'',payment_date:dateInput(new Date()),payment_method:'bank_transfer',status:'received',transaction_reference:'',notes:''}:{amount:'',payment_date:dateInput(new Date()),payment_method:'bank_transfer',status:'received',transaction_reference:'',notes:''})
    if(kind==='ticket')setForm(c?{school_id:String(c.id),subject:'',description:'',category:'technical',priority:'normal',requester_name:'',requester_email:''}:{subject:'',description:'',category:'technical',priority:'normal',requester_name:'',requester_email:''})
  }
  async function submitForm(e:FormEvent){
    e.preventDefault();setBusy(true);setError('');setNotice('')
    try{
      if(formKind==='client'){
        const editing=Boolean(form.school_id)
        const payload={name:form.name,code:form.code,institution_type:form.institution_type}
        await request(editing?'/api/platform/clients/'+form.school_id:'/api/platform/clients',{method:editing?'PUT':'POST',body:JSON.stringify(payload)})
        setFormKind('');setNotice(editing?'Client institution updated.':'Client institution created.');await load()
        return
      }
      const endpoint=({quotation:'/api/platform/quotations',subscription:'/api/platform/subscriptions',payment:'/api/platform/payments',ticket:'/api/platform/support-tickets'} as Record<string,string>)[formKind]
      const payload:any={...form}
      if(payload.school_id)payload.school_id=Number(payload.school_id);if(formKind==='quotation'&&!payload.valid_until)payload.valid_until=null
      await request(endpoint,{method:'POST',body:JSON.stringify(payload)})
      setFormKind('');setNotice('Record saved successfully.');await load()
    }catch(err:any){setError(err.message||'Could not save record')}
    finally{setBusy(false)}
  }
  async function saveProfile(e:FormEvent){
    e.preventDefault();if(!selected)return;setBusy(true);setError('');setNotice('')
    try{await request('/api/platform/clients/'+selected.id+'/profile',{method:'PUT',body:JSON.stringify(profile)});setNotice('Client profile updated.');await load()}
    catch(err:any){setError(err.message||'Could not update client profile')}
    finally{setBusy(false)}
  }
  async function changeClientLifecycle(action:'pause'|'reactivate'|'archive'|'restore'){
    if(!selected)return
    const prompts:Record<string,string>={pause:'Pause this client? Its users will no longer be able to sign in. Existing records will be preserved.',reactivate:'Reactivate this client and allow its users to sign in again?',archive:'Archive this client? It will be deactivated and hidden from normal active operations. No tenant data will be deleted.',restore:'Restore this archived client and reactivate it?'}
    if(!window.confirm(prompts[action]))return
    setBusy(true);setError('');setNotice('')
    try{
      await request('/api/platform/clients/'+selected.id+'/lifecycle',{method:'PATCH',body:JSON.stringify({action})})
      setNotice('Client '+action+'d successfully. Existing institution data was preserved.')
      await load()
      const fresh=await request('/api/platform/clients/'+selected.id)
      setClientDetail(fresh)
    }catch(err:any){setError(err.message||'Could not update client status')}
    finally{setBusy(false)}
  }
  async function updateTicket(ticket:any,status:string){
    setBusy(true);setError('')
    try{await request('/api/platform/support-tickets/'+ticket.id,{method:'PATCH',body:JSON.stringify({status,priority:ticket.priority,resolution_notes:ticket.resolution_notes||''})});setNotice('Support ticket updated.');await load()}
    catch(err:any){setError(err.message||'Could not update support ticket')}
    finally{setBusy(false)}
  }
  const cards=[
    {label:'Client institutions',value:overview.institutions,icon:Building2},
    {label:'Online users (5 min)',value:overview.online_users,icon:Activity},
    {label:'Students',value:overview.students,icon:Users},
    {label:'Staff',value:overview.staff,icon:Users},
    {label:'Active subscriptions',value:overview.active_subscriptions,icon:CalendarClock},
    {label:'Expiring in 30 days',value:overview.subscriptions_expiring_30_days,icon:CircleAlert},
    {label:'Pending quotations',value:overview.pending_quotations,icon:FileText},
    {label:'Open support tickets',value:overview.open_support_tickets,icon:Headset},
  ]
  return <section className="dcc">
    <div className="dcc-heading"><div><div className="dcc-eyebrow"><ShieldCheck size={15}/> PLATFORM OWNER WORKSPACE</div><h2>Developer Control Centre</h2><p>Manage client institutions, commercial records, subscriptions, support and platform usage.</p></div><button className="secondary" onClick={load} disabled={busy}><RefreshCw size={16}/> Refresh</button></div>
    {error&&<div className="dcc-alert error">{error}<button onClick={()=>setError('')}><X size={15}/></button></div>}
    {notice&&<div className="dcc-alert success">{notice}<button onClick={()=>setNotice('')}><X size={15}/></button></div>}
    <nav className="dcc-tabs">{tabs.map(t=><button key={t} className={tab===t?'active':''} onClick={()=>setTab(t)}>{t}</button>)}</nav>
    {tab==='Overview'&&<><div className="dcc-stats">{cards.map(c=>{const I=c.icon;return <article className="dcc-stat" key={c.label}><span><I size={18}/></span><strong>{c.value.toLocaleString('en-IN')}</strong><small>{c.label}</small></article>})}</div><div className="dcc-columns"><article className="dcc-panel"><div className="dcc-panel-title"><div><h3>Subscription attention</h3><p>Institutions whose subscriptions need follow-up</p></div><CalendarClock size={19}/></div>{subscriptions.filter(s=>s.status==='active'&&new Date(s.end_date+'T00:00:00')<=new Date(Date.now()+30*86400000)).slice(0,6).map(s=><div className="dcc-list-row" key={s.id}><div><strong>{clientName(s.school_id)}</strong><small>{s.plan_name} · expires {day(s.end_date)}</small></div><span className="dcc-status warning">{s.status}</span></div>)}{!subscriptions.some(s=>s.status==='active'&&new Date(s.end_date+'T00:00:00')<=new Date(Date.now()+30*86400000))&&<p className="dcc-empty">No active subscriptions expiring in the next 30 days.</p>}</article><article className="dcc-panel"><div className="dcc-panel-title"><div><h3>Recent support requests</h3><p>Latest client issues requiring attention</p></div><Headset size={19}/></div>{tickets.slice(0,6).map(t=><div className="dcc-list-row" key={t.id}><div><strong>{t.subject}</strong><small>{clientName(t.school_id)} · {t.priority} priority</small></div><span className="dcc-status">{t.status.replaceAll('_',' ')}</span></div>)}{!tickets.length&&<p className="dcc-empty">No support tickets recorded.</p>}</article></div></>}
    {tab==='Clients'&&<div className="dcc-panel"><div className="dcc-panel-title"><div><h3>All client institutions</h3><p>Institution profiles and individual client records</p></div><span className="dcc-count">{filteredClients.length} clients</span></div><div className="dcc-toolbar"><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search institution, code or type…"/><button className="primary" onClick={()=>openForm('client')}>+ Add client</button><button className="secondary" onClick={()=>openForm('ticket',selected||undefined)}>Create support ticket</button></div><div className="dcc-table-wrap"><table><thead><tr><th>Institution</th><th>Type</th><th>Users</th><th>Students</th><th>Staff</th><th>Subscription</th><th>Status</th><th></th></tr></thead><tbody>{filteredClients.map(c=><tr key={c.id}><td><strong>{c.name}</strong><small>{c.code}</small></td><td>{c.institution_type.replaceAll('_',' ')}</td><td>{c.users}</td><td>{c.students}</td><td>{c.staff}</td><td>{c.subscription?day(c.subscription.end_date):'Not set'}</td><td><span className={'dcc-status '+(c.is_active?'good':'warning')}>{c.approval_status==='archived'?'Archived':c.is_active?'Active':'Paused'}</span></td><td><button className="secondary compact" onClick={()=>openClient(c)}>Manage</button></td></tr>)}{!filteredClients.length&&<tr><td colSpan={8}><p className="dcc-empty">No client institutions found.</p></td></tr>}</tbody></table></div>
      {selected&&<div className="dcc-client-detail"><div className="dcc-panel-title"><div><h3>{selected.name}</h3><p>{selected.code} · {selected.institution_type.replaceAll('_',' ')}</p></div><button className="secondary compact" onClick={()=>{setSelected(null);setClientDetail(null)}}>Close</button></div><div className="dcc-client-actions"><button className="primary" disabled={!selected.is_active||selected.approval_status==='archived'} onClick={()=>onEnterWorkspace(selected.id)}>Open client dashboard</button><button className="secondary" onClick={()=>openForm('client',selected)}>Edit institution</button><button className="secondary" onClick={()=>openForm('quotation',selected)}>New quotation</button><button className="secondary" onClick={()=>openForm('subscription',selected)}>Add subscription</button><button className="secondary" onClick={()=>openForm('payment',selected)}>Record collection</button><button className="secondary" onClick={()=>openForm('ticket',selected)}>Support ticket</button>{selected.approval_status==='archived'?<button className="secondary" disabled={busy} onClick={()=>changeClientLifecycle('restore')}>Restore</button>:selected.is_active?<button className="secondary" disabled={busy} onClick={()=>changeClientLifecycle('pause')}>Pause client</button>:<button className="secondary" disabled={busy} onClick={()=>changeClientLifecycle('reactivate')}>Reactivate</button>}{selected.approval_status!=='archived'&&<button className="secondary" disabled={busy} onClick={()=>changeClientLifecycle('archive')}>Archive client</button>}</div><form className="dcc-profile-form" onSubmit={saveProfile}><h4>Institution contact and registration details</h4><div className="dcc-form-grid">{[['contact_person','Contact person'],['contact_email','Contact email'],['contact_phone','Contact phone'],['affiliation','Affiliation / board'],['registration_no','Registration number'],['website','Website'],['city','City'],['state','State'],['country','Country']].map(([k,l])=><label key={k}>{l}<input value={profile[k]||''} onChange={e=>setProfile({...profile,[k]:e.target.value})}/></label>)}<label className="wide">Address<textarea value={profile.address||''} onChange={e=>setProfile({...profile,address:e.target.value})}/></label><label className="wide">Internal notes<textarea value={profile.notes||''} onChange={e=>setProfile({...profile,notes:e.target.value})}/></label></div><button className="primary" disabled={busy}><Save size={15}/> Save client details</button></form><div className="dcc-client-users"><h4>Client user accounts</h4><div className="dcc-table-wrap"><table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Account status</th></tr></thead><tbody>{(clientDetail?.users||[]).map((u:any)=><tr key={u.id}><td>{u.name}</td><td>{u.email}</td><td>{u.role.replaceAll('_',' ')}</td><td><span className={'dcc-status '+(u.is_active?'good':'warning')}>{u.is_active?'Active':'Inactive'}</span></td></tr>)}{!clientDetail?.users?.length&&<tr><td colSpan={4}><p className="dcc-empty">No client accounts returned.</p></td></tr>}</tbody></table></div></div></div>}
    </div>}

    {tab==='Role access'&&<div className="dcc-panel">
      <div className="dcc-panel-title"><div><h3>Institution-specific role access</h3><p>Choose an institution type and client, then configure permissions for each role in that client only.</p></div><ShieldCheck size={19}/></div>
      <div className="dcc-role-types">
        {[['school','Schools'],['college','Colleges'],['university','Universities'],['other','Other institutions']].map(([key,label])=><button key={key} className={roleInstitutionType===key?'active':''} onClick={()=>{setRoleInstitutionType(key);setRoleClientId('');setRoleKey((INSTITUTION_ROLE_TEMPLATES[key]||INSTITUTION_ROLE_TEMPLATES.school)[0].roleKey);setRolePermissions({});setRolePermissionMeta({});setRoleError('');setRoleNotice('')}}>{label}</button>)}
      </div>
      <div className="dcc-role-selectors">
        <label>Client institution
          <select value={roleClientId} onChange={e=>{setRoleClientId(e.target.value);setRolePermissions({});setRolePermissionMeta({});setRoleError('');setRoleNotice('')}}>
            <option value="">Choose a client</option>
            {clients.filter(c=>c.approval_status!=='archived'&&(roleInstitutionType==='other'?['coaching_centre','training_institute','other'].includes(c.institution_type):c.institution_type===roleInstitutionType)).map(c=><option key={c.id} value={c.id}>{c.name} · {c.code}</option>)}
          </select>
        </label>
        <label>Role template
          <select value={roleKey} onChange={e=>{setRoleKey(e.target.value);setRolePermissions({});setRolePermissionMeta({});setRoleError('');setRoleNotice('')}}>
            {roleTemplates.map(r=><option key={r.roleKey} value={r.roleKey}>{r.role}</option>)}
          </select>
        </label>
      </div>
      {!roleClientId&&<p className="dcc-empty">Select an institution category and one of its clients to manage role permissions.</p>}
      {roleClientId&&<>
        <div className="dcc-role-context"><strong>{clients.find(c=>String(c.id)===roleClientId)?.name||'Selected client'}</strong><span>Changes apply only to this client. Other institutions keep their own settings.</span></div>
        {roleError&&<div className="dcc-alert error">{roleError}</div>}
        {roleNotice&&<div className="dcc-alert success">{roleNotice}</div>}
        <div className="dcc-role-permission-heading"><div><h4>{roleTemplates.find(r=>r.roleKey===roleKey)?.role||roleKey} permissions</h4><p>{rolePermissionMeta.school_configured?'Client-specific permissions are configured.':rolePermissionMeta.global_configured?'Using platform defaults with client override available.':'No saved override for this client yet.'}</p></div><span className="dcc-count">{moduleList.filter(m=>rolePermissions[m.key+':View']).length} modules enabled</span></div>
        <div className="dcc-table-wrap"><table><thead><tr><th>Module</th>{['View','Create','Edit','Delete','Approve','Export'].map(a=><th key={a}>{a}</th>)}</tr></thead><tbody>
          {moduleList.filter(m=>m.key!=='developer-control').map(m=><tr key={m.key}><td><strong>{m.label}</strong><small>{m.description}</small></td>{['View','Create','Edit','Delete','Approve','Export'].map(action=><td key={action}><input aria-label={m.label+' '+action} type="checkbox" checked={Boolean(rolePermissions[m.key+':'+action])} onChange={e=>setRolePermissions(old=>({...old,[m.key+':'+action]:e.target.checked}))}/></td>)}</tr>)}
        </tbody></table></div>
        <div className="dcc-role-actions"><button className="secondary" disabled={roleBusy} onClick={async()=>{setRoleBusy(true);setRoleError('');setRoleNotice('');try{await request('/api/rbac/roles/'+encodeURIComponent(roleKey)+'/permissions?school_id='+encodeURIComponent(roleClientId),{method:'DELETE'});const r=await request('/api/rbac/roles/'+encodeURIComponent(roleKey)+'/permissions?school_id='+encodeURIComponent(roleClientId));setRolePermissions(r.permissions||{});setRolePermissionMeta(r);setRoleNotice('Client override reset. The role now inherits platform defaults.')}catch(e:any){setRoleError(e.message||'Could not reset role permissions')}finally{setRoleBusy(false)}}}>Reset to platform defaults</button><button className="primary" disabled={roleBusy} onClick={async()=>{setRoleBusy(true);setRoleError('');setRoleNotice('');try{const complete=Object.fromEntries(moduleList.filter(m=>m.key!=='developer-control').flatMap(m=>['View','Create','Edit','Delete','Approve','Export'].map(a=>[m.key+':'+a,Boolean(rolePermissions[m.key+':'+a])])));await request('/api/rbac/roles/'+encodeURIComponent(roleKey)+'/permissions?school_id='+encodeURIComponent(roleClientId),{method:'PUT',body:JSON.stringify({permissions:complete})});setRolePermissions(complete);setRolePermissionMeta({...rolePermissionMeta,configured:true,school_configured:true});setRoleNotice('Role permissions saved for this client only. The change is recorded in the audit log.')}catch(e:any){setRoleError(e.message||'Could not save role permissions')}finally{setRoleBusy(false)}}}>{roleBusy?'Saving…':'Save client role permissions'}</button></div>
      </>}
    </div>}
    {tab==='Client Requests'&&<div className="dcc-panel"><div className="dcc-panel-title"><div><h3>Institution applications</h3><p>Review new school, college, university and institute registrations.</p></div><span className="dcc-count">{clientRequests.filter(r=>r.approval_status==='pending').length} pending</span></div><div className="dcc-table-wrap"><table><thead><tr><th>Institution / Code</th><th>Type</th><th>Founder</th><th>Email verified</th><th>Submitted</th><th>Review status</th><th>Actions</th></tr></thead><tbody>{clientRequests.map(r=><tr key={r.school_id}><td><strong>{r.school_name}</strong><small>{r.school_code}</small></td><td>{r.institution_type.replaceAll('_',' ')}</td><td>{r.founder?.name||'—'}<small>{r.founder?.email||'Founder unavailable'}</small></td><td>{r.founder?.email_verified?'Yes':'Pending'}</td><td>{day(r.created_at)}</td><td><span className={'dcc-status '+(r.review_status==='approved'?'good':'warning')}>{r.review_status.replaceAll('_',' ')}</span>{r.requested_information&&<small>{r.requested_information}</small>}</td><td><div className="dcc-inline-actions"><button className="primary compact" disabled={busy||!r.founder?.email_verified} onClick={()=>decideRequest(r,'approve')}>Approve</button><button className="secondary compact" disabled={busy} onClick={()=>decideRequest(r,'request_info')}>Request info</button><button className="secondary compact" disabled={busy} onClick={()=>decideRequest(r,'reject')}>Reject</button></div></td></tr>)}{!clientRequests.length&&<tr><td colSpan={7}><p className="dcc-empty">No pending institution applications.</p></td></tr>}</tbody></table></div><p className="dcc-note">Approval activates the institution and assigns its founder the institution administrator role. Email verification is required before the founder can sign in.</p></div>}
    {tab==='User access'&&<div className="dcc-columns"><article className="dcc-panel"><div className="dcc-panel-title"><div><h3>Institution account access</h3><p>Invite users and assign institution-specific roles.</p></div><UserPlus size={19}/></div><label>Client institution<select value={opsClientId} onChange={e=>loadOpsUsers(e.target.value)}><option value="">Select institution</option>{clients.filter(c=>c.approval_status==='approved'&&c.is_active).map(c=><option key={c.id} value={c.id}>{c.name} · {c.institution_type}</option>)}</select></label>{opsClientId&&<form className="dcc-profile-form" onSubmit={sendInvitation}><div className="dcc-form-grid"><label>Invite email<input type="email" required value={inviteEmail} onChange={e=>setInviteEmail(e.target.value)}/></label><label>Institution role<select value={inviteRole} onChange={e=>setInviteRole(e.target.value)}>{(INSTITUTION_ROLE_TEMPLATES[(clients.find(c=>String(c.id)===opsClientId)?.institution_type==='school'?'school':clients.find(c=>String(c.id)===opsClientId)?.institution_type==='college'?'college':clients.find(c=>String(c.id)===opsClientId)?.institution_type==='university'?'university':'other')]||INSTITUTION_ROLE_TEMPLATES.school).map(r=><option key={r.roleKey} value={r.roleKey}>{r.role}</option>)}</select></label></div><button className="primary" disabled={busy}><Mail size={15}/> Send invitation</button></form>}{inviteLink&&<div className="dcc-invite-link"><strong>One-time invitation link</strong><code>{inviteLink}</code><button className="secondary compact" onClick={()=>navigator.clipboard?.writeText(inviteLink)}>Copy link</button></div>}</article><article className="dcc-panel"><div className="dcc-panel-title"><div><h3>Existing accounts</h3><p>Role changes are checked against institution type and audited.</p></div><Users size={19}/></div><div className="dcc-table-wrap"><table><thead><tr><th>User</th><th>Current role</th><th>Assign role</th><th>Status</th></tr></thead><tbody>{opsUsers.map(u=><tr key={u.id}><td><strong>{u.name}</strong><small>{u.email}</small></td><td>{u.role.replaceAll('_',' ')}</td><td><select value={u.role} onChange={e=>changeUserRole(u.id,e.target.value)}><option value={u.role}>{u.role.replaceAll('_',' ')}</option>{(INSTITUTION_ROLE_TEMPLATES[(clients.find(c=>String(c.id)===opsClientId)?.institution_type==='school'?'school':clients.find(c=>String(c.id)===opsClientId)?.institution_type==='college'?'college':clients.find(c=>String(c.id)===opsClientId)?.institution_type==='university'?'university':'other')]||INSTITUTION_ROLE_TEMPLATES.school).filter(r=>r.roleKey!==u.role).map(r=><option key={r.roleKey} value={r.roleKey}>{r.role}</option>)}</select></td><td><span className={'dcc-status '+(u.is_active?'good':'warning')}>{u.is_active?'Active':u.approval_status}</span></td></tr>)}{!opsUsers.length&&<tr><td colSpan={4}><p className="dcc-empty">Select an institution to view its accounts.</p></td></tr>}</tbody></table></div></article></div>}
    {tab==='Platform operations'&&<><div className="dcc-columns"><article className="dcc-panel"><div className="dcc-panel-title"><div><h3>Platform incidents</h3><p>Track service outages, security events and client-impacting incidents.</p></div><AlertTriangle size={19}/></div><form className="dcc-profile-form" onSubmit={createIncident}><div className="dcc-form-grid"><label>Incident title<input required value={incidentForm.title} onChange={e=>setIncidentForm({...incidentForm,title:e.target.value})}/></label><label>Severity<select value={incidentForm.severity} onChange={e=>setIncidentForm({...incidentForm,severity:e.target.value})}>{['low','medium','high','critical'].map(x=><option key={x}>{x}</option>)}</select></label><label>Scope<select value={incidentForm.affected_scope} onChange={e=>setIncidentForm({...incidentForm,affected_scope:e.target.value})}><option value="platform">Entire platform</option><option value="institution">One institution</option></select></label>{incidentForm.affected_scope==='institution'&&<label>Institution<select required value={incidentForm.school_id} onChange={e=>setIncidentForm({...incidentForm,school_id:e.target.value})}><option value="">Select client</option>{clients.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>}<label>Assigned to<input value={incidentForm.assigned_to} onChange={e=>setIncidentForm({...incidentForm,assigned_to:e.target.value})}/></label><label className="wide">Description<textarea value={incidentForm.description} onChange={e=>setIncidentForm({...incidentForm,description:e.target.value})}/></label></div><button className="primary" disabled={busy}>Create incident</button></form><div className="dcc-ticket-list">{incidents.map(x=><article className="dcc-ticket" key={x.id}><div><strong>#{x.id} · {x.title}</strong><small>{x.severity} · {x.affected_scope} · {day(x.created_at)}</small><p>{x.description}</p>{x.resolution_notes&&<small>{x.resolution_notes}</small>}</div><div className="dcc-ticket-controls"><select value={x.status} disabled={busy} onChange={e=>updateIncident(x,e.target.value)}>{['open','investigating','identified','monitoring','resolved','closed'].map(st=><option key={st}>{st}</option>)}</select></div></article>)}{!incidents.length&&<p className="dcc-empty">No platform incidents recorded.</p>}</div></article><article className="dcc-panel"><div className="dcc-panel-title"><div><h3>Scheduled maintenance</h3><p>Plan maintenance windows and publish operational timing.</p></div><Wrench size={19}/></div><form className="dcc-profile-form" onSubmit={createMaintenanceWindow}><div className="dcc-form-grid"><label className="wide">Maintenance title<input required value={windowForm.title} onChange={e=>setWindowForm({...windowForm,title:e.target.value})}/></label><label>Starts at<input type="datetime-local" required value={windowForm.starts_at} onChange={e=>setWindowForm({...windowForm,starts_at:e.target.value})}/></label><label>Ends at<input type="datetime-local" required value={windowForm.ends_at} onChange={e=>setWindowForm({...windowForm,ends_at:e.target.value})}/></label><label className="wide">Description<textarea value={windowForm.description} onChange={e=>setWindowForm({...windowForm,description:e.target.value})}/></label></div><button className="primary" disabled={busy}>Schedule maintenance</button></form>{windows.map(w=><div className="dcc-list-row" key={w.id}><div><strong>{w.title}</strong><small>{new Date(w.starts_at).toLocaleString()} – {new Date(w.ends_at).toLocaleString()}</small></div><span className="dcc-status">{w.status}</span></div>)}{!windows.length&&<p className="dcc-empty">No maintenance windows scheduled.</p>}</article></div><article className="dcc-panel"><div className="dcc-panel-title"><div><h3>Infrastructure monitoring</h3><p>Live application, database, storage and backup checks.</p></div><Activity size={19}/></div><div className="dcc-health-row"><span>API</span><strong className="dcc-status good">{infra.api||'unknown'}</strong></div><div className="dcc-health-row"><span>Database</span><strong className={'dcc-status '+(infra.database==='healthy'?'good':'warning')}>{infra.database||'unknown'}{infra.database_latency_ms!=null?' · '+infra.database_latency_ms+' ms':''}</strong></div><div className="dcc-health-row"><span>Disk usage</span><strong>{infra.disk?.used_percent!=null?infra.disk.used_percent+'% used':'unavailable'}</strong></div><div className="dcc-health-row"><span>Backup status</span><strong>{infra.backup?.latest_file?infra.backup.latest_file+' · '+infra.backup.age_hours+'h ago':infra.backup?.configured?'No backup file found':'Not configured'}</strong></div><div className="dcc-health-row"><span>CPU load average</span><strong>{infra.cpu_load_average?.join(' / ')||'Unavailable'}</strong></div><p className="dcc-note">SSL/domain expiry checks require an external monitor and are not reported as healthy unless configured. Backup status is based on BACKUP_DIR and the latest recognised backup file.</p></article></>}
    {tab==='Reports'&&<div className="dcc-panel"><div className="dcc-panel-title"><div><h3>Platform operational report</h3><p>Institution activity, subscriptions, collections and incident overview.</p></div><button className="secondary" onClick={()=>{request('/api/platform/ops/reports').then(setOpsReport).catch((e:any)=>setError(e.message||'Report refresh failed'))}}><RefreshCw size={15}/> Refresh report</button></div><div className="dcc-stats"><article className="dcc-stat"><strong>{opsReport.institutions||0}</strong><small>Institutions</small></article><article className="dcc-stat"><strong>{opsReport.active_institutions||0}</strong><small>Active institutions</small></article><article className="dcc-stat"><strong>{opsReport.open_platform_incidents||0}</strong><small>Open platform incidents</small></article><article className="dcc-stat"><strong>{money(overview.received_amount)}</strong><small>All-time collections</small></article></div><DataTable headers={['Institution','Type','Status','Users','Students','Staff','Subscription end','Received this month']} rows={(opsReport.clients||[]).map(r=>[r.institution,r.type,r.active?'Active':'Inactive',r.users,r.students,r.staff,day(r.subscription_end),money(r.received_this_month)])}/><p className="dcc-note">Report generated: {opsReport.generated_at?new Date(opsReport.generated_at).toLocaleString():'Not generated'}. Export and scheduled delivery are not yet enabled.</p></div>}
    {tab==='Quotations'&&<div className="dcc-panel"><div className="dcc-panel-title"><div><h3>Client quotations</h3><p>Prepare and track quotations for implementation, modules and services</p></div><button className="primary" onClick={()=>openForm('quotation')}>New quotation</button></div><DataTable headers={['Quotation','Institution','Title','Amount','Valid until','Status']} rows={quotes.map(q=>[q.quotation_no,clientName(q.school_id),q.title,money(Number(q.amount)+Number(q.tax_amount)-Number(q.discount_amount)),day(q.valid_until),q.status])}/></div>}
    {tab==='Subscriptions'&&<div className="dcc-panel"><div className="dcc-panel-title"><div><h3>Subscriptions and renewals</h3><p>Track plan value, start date, expiry date and status</p></div><button className="primary" onClick={()=>openForm('subscription')}>Add subscription</button></div><DataTable headers={['Institution','Plan','Amount','Billing','Start date','Expiry date','Status']} rows={subscriptions.map(s=>[clientName(s.school_id),s.plan_name,money(s.amount),s.billing_cycle,day(s.start_date),day(s.end_date),s.status])}/><div className="dcc-renew-list"><h4>Renewal actions</h4>{subscriptions.slice(0,20).map(s=><div className="dcc-list-row" key={s.id}><div><strong>{clientName(s.school_id)} · {s.plan_name}</strong><small>Current expiry: {day(s.end_date)}</small></div><button className="secondary compact" disabled={busy} onClick={async()=>{const start=window.prompt('Renewal start date (YYYY-MM-DD)',dateInput(new Date()));if(!start)return;const end=window.prompt('New expiry date (YYYY-MM-DD)',start.slice(0,4)+'-12-31');if(!end)return;try{await request('/api/platform/ops/subscriptions/'+s.id+'/renew',{method:'POST',body:JSON.stringify({start_date:start,end_date:end,amount:String(s.amount),notes:'Renewed from Developer Control Centre'})});setNotice('Subscription renewed and institution reactivated.');await load()}catch(e:any){setError(e.message||'Renewal failed')}}}>Renew</button></div>)}</div><button className="secondary" disabled={busy} onClick={runExpirySweep}>Run expiry enforcement</button></div>}
    {tab==='Collections'&&<div className="dcc-panel"><div className="dcc-panel-title"><div><h3>Amount collections</h3><p>Record payments and review collection history</p></div><button className="primary" onClick={()=>openForm('payment')}>Record payment</button></div><div className="dcc-gateway"><h4><CreditCard size={16}/> Online subscription payment</h4><div className="dcc-inline-fields"><select value={checkoutSchoolId} onChange={e=>setCheckoutSchoolId(e.target.value)}><option value="">Select client</option>{clients.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select><input type="number" min="1" step="0.01" placeholder="Amount in ₹" value={checkoutAmount} onChange={e=>setCheckoutAmount(e.target.value)}/><button className="secondary" disabled={busy||!checkoutSchoolId||!checkoutAmount} onClick={startGatewayCheckout}>Create Razorpay checkout</button></div><p className="dcc-note">Requires RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET. Payments are recorded only after server-side signature, order, amount and captured-status verification.</p></div><div className="dcc-revenue"><IndianRupee size={19}/><div><small>Total received (all clients)</small><strong>{money(overview.received_amount)}</strong></div></div><DataTable headers={['Institution','Amount','Payment date','Method','Reference','Status']} rows={payments.map(p=>[clientName(p.school_id),money(p.amount),day(p.payment_date),p.payment_method,p.transaction_reference||'—',p.status])}/></div>}
    {tab==='Support'&&<div className="dcc-panel"><div className="dcc-panel-title"><div><h3>Client support desk</h3><p>Track requests, complaints and technical follow-ups</p></div><button className="primary" onClick={()=>openForm('ticket')}>New support ticket</button></div><div className="dcc-ticket-list">{tickets.map(t=><article key={t.id} className="dcc-ticket"><div><strong>{t.subject}</strong><small>{clientName(t.school_id)} · {t.category} · {t.priority} · {day(t.created_at)}</small><p>{t.description}</p>{t.resolution_notes&&<small>Resolution: {t.resolution_notes}</small>}</div><div className="dcc-ticket-controls"><select value={t.status} disabled={busy} onChange={e=>updateTicket(t,e.target.value)}>{['open','in_progress','waiting_client','resolved','closed'].map(s=><option key={s} value={s}>{s.replaceAll('_',' ')}</option>)}</select></div></article>)}{!tickets.length&&<p className="dcc-empty">No support requests recorded.</p>}</div></div>}
    {tab==='System & audit'&&<div className="dcc-columns"><article className="dcc-panel"><div className="dcc-panel-title"><div><h3>Platform health</h3><p>Basic API and database connectivity checks</p></div><ShieldCheck size={19}/></div><div className="dcc-health-row"><span>Application API</span><strong className={'dcc-status '+(health.api==='healthy'?'good':'warning')}>{health.api}</strong></div><div className="dcc-health-row"><span>Database connection</span><strong className={'dcc-status '+(health.database==='healthy'?'good':'warning')}>{health.database}</strong></div><p className="dcc-empty">Last checked: {health.checked_at?new Date(health.checked_at).toLocaleString('en-IN'):'Not checked'}</p><p className="dcc-note">This endpoint checks database connectivity only. It does not verify backups, disk capacity, SSL, domain expiry or external integrations.</p></article><article className="dcc-panel"><div className="dcc-panel-title"><div><h3>Recent audit events</h3><p>Platform security and administrative activity</p></div><span className="dcc-count">{audit.length} events</span></div><div className="dcc-table-wrap"><table><thead><tr><th>Event</th><th>Target</th><th>Details</th><th>Time</th></tr></thead><tbody>{audit.map((item:any)=><tr key={item.id}><td>{item.event_type}</td><td>{item.target_type} · {item.target_id}</td><td>{item.details}</td><td>{new Date(item.created_at).toLocaleString('en-IN')}</td></tr>)}{!audit.length&&<tr><td colSpan={4}><p className="dcc-empty">No audit events recorded yet.</p></td></tr>}</tbody></table></div></article></div>}
    {tab==='Live usage'&&<div className="dcc-panel"><div className="dcc-panel-title"><div><h3>Client and user activity</h3><p>Online means an authenticated heartbeat received within the last five minutes.</p></div><span className="dcc-count">{activity.filter(a=>a.online).length} online</span></div><div className="dcc-table-wrap"><table><thead><tr><th>User</th><th>Institution</th><th>Role</th><th>Last seen</th><th>Status</th></tr></thead><tbody>{activity.map(a=><tr key={a.user_id}><td><strong>{a.name}</strong><small>{a.email}</small></td><td>{a.institution}</td><td>{a.role.replaceAll('_',' ')}</td><td>{new Date(a.last_seen_at).toLocaleString('en-IN')}</td><td><span className={'dcc-status '+(a.online?'good':'')}>{a.online?'Online':'Offline'}</span></td></tr>)}{!activity.length&&<tr><td colSpan={5}><p className="dcc-empty">No activity heartbeats received yet. Online monitoring begins as users sign in and the application sends periodic heartbeats.</p></td></tr>}</tbody></table></div></div>}
    {formKind&&<div className="dcc-modal-backdrop" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget)setFormKind('')}}><form className="dcc-modal" onSubmit={submitForm}><div className="dcc-panel-title"><div><h3>{({client:form.school_id?'Edit client institution':'Add client institution',quotation:'New quotation',subscription:'New subscription',payment:'Record client payment',ticket:'Create support ticket'} as Record<string,string>)[formKind]}</h3><p>Changes are saved to the selected client record.</p></div><button type="button" className="secondary compact" onClick={()=>setFormKind('')}><X size={15}/></button></div><div className="dcc-form-grid">
      {formKind==='client'&&<><label className="wide">Institution name<input required minLength={2} maxLength={180} value={form.name||''} onChange={e=>setForm({...form,name:e.target.value})}/></label><label>Institution code<input required minLength={2} maxLength={40} value={form.code||''} onChange={e=>setForm({...form,code:e.target.value.toUpperCase()})}/></label><label>Institution type<select required value={form.institution_type||'school'} onChange={e=>setForm({...form,institution_type:e.target.value})}>{[['school','School'],['college','College'],['university','University'],['coaching_centre','Coaching centre'],['training_institute','Training institute'],['other','Other institution']].map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label></>}
      {formKind!=='client'&&      <label className="wide">Client institution<select required value={form.school_id||''} onChange={e=>setForm({...form,school_id:e.target.value})}><option value="">Select client</option>{clients.map(c=><option key={c.id} value={c.id}>{c.name} · {c.code}</option>)}</select></label>}
      {formKind==='quotation'&&<><label className="wide">Quotation title<input required value={form.title||''} onChange={e=>setForm({...form,title:e.target.value})}/></label><label>Base amount (₹)<input type="number" min="0" step="0.01" required value={form.amount||''} onChange={e=>setForm({...form,amount:e.target.value})}/></label><label>Tax amount (₹)<input type="number" min="0" step="0.01" value={form.tax_amount||'0'} onChange={e=>setForm({...form,tax_amount:e.target.value})}/></label><label>Discount (₹)<input type="number" min="0" step="0.01" value={form.discount_amount||'0'} onChange={e=>setForm({...form,discount_amount:e.target.value})}/></label><label>Valid until<input type="date" value={form.valid_until||''} onChange={e=>setForm({...form,valid_until:e.target.value})}/></label><label>Status<select value={form.status||'draft'} onChange={e=>setForm({...form,status:e.target.value})}>{['draft','sent','accepted','rejected','expired'].map(s=><option key={s}>{s}</option>)}</select></label><label className="wide">Notes<textarea value={form.notes||''} onChange={e=>setForm({...form,notes:e.target.value})}/></label></>}
      {formKind==='subscription'&&<><label>Plan name<input required value={form.plan_name||''} onChange={e=>setForm({...form,plan_name:e.target.value})}/></label><label>Amount (₹)<input type="number" min="0" step="0.01" required value={form.amount||''} onChange={e=>setForm({...form,amount:e.target.value})}/></label><label>Billing cycle<select value={form.billing_cycle||'annual'} onChange={e=>setForm({...form,billing_cycle:e.target.value})}>{['monthly','quarterly','half_yearly','annual','custom'].map(s=><option key={s}>{s}</option>)}</select></label><label>Start date<input type="date" required value={form.start_date||''} onChange={e=>setForm({...form,start_date:e.target.value})}/></label><label>Expiry date<input type="date" required value={form.end_date||''} onChange={e=>setForm({...form,end_date:e.target.value})}/></label><label>Status<select value={form.status||'active'} onChange={e=>setForm({...form,status:e.target.value})}>{['active','pending','expired','suspended','cancelled'].map(s=><option key={s}>{s}</option>)}</select></label><label className="wide">Notes<textarea value={form.notes||''} onChange={e=>setForm({...form,notes:e.target.value})}/></label></>}
      {formKind==='payment'&&<><label>Amount received (₹)<input type="number" min="0.01" step="0.01" required value={form.amount||''} onChange={e=>setForm({...form,amount:e.target.value})}/></label><label>Payment date<input type="date" required value={form.payment_date||''} onChange={e=>setForm({...form,payment_date:e.target.value})}/></label><label>Payment method<select value={form.payment_method||'bank_transfer'} onChange={e=>setForm({...form,payment_method:e.target.value})}>{['cash','upi','bank_transfer','card','cheque','other'].map(s=><option key={s}>{s}</option>)}</select></label><label>Reference number<input value={form.transaction_reference||''} onChange={e=>setForm({...form,transaction_reference:e.target.value})}/></label><label>Status<select value={form.status||'received'} onChange={e=>setForm({...form,status:e.target.value})}>{['received','pending','failed','refunded'].map(s=><option key={s}>{s}</option>)}</select></label><label className="wide">Notes<textarea value={form.notes||''} onChange={e=>setForm({...form,notes:e.target.value})}/></label></>}
      {formKind==='ticket'&&<><label className="wide">Subject<input required value={form.subject||''} onChange={e=>setForm({...form,subject:e.target.value})}/></label><label>Category<select value={form.category||'technical'} onChange={e=>setForm({...form,category:e.target.value})}>{['technical','billing','data','training','feature_request','general'].map(s=><option key={s}>{s}</option>)}</select></label><label>Priority<select value={form.priority||'normal'} onChange={e=>setForm({...form,priority:e.target.value})}>{['low','normal','high','urgent'].map(s=><option key={s}>{s}</option>)}</select></label><label>Requester name<input value={form.requester_name||''} onChange={e=>setForm({...form,requester_name:e.target.value})}/></label><label>Requester email<input type="email" value={form.requester_email||''} onChange={e=>setForm({...form,requester_email:e.target.value})}/></label><label className="wide">Description<textarea value={form.description||''} onChange={e=>setForm({...form,description:e.target.value})}/></label></>}
    </div><div className="dcc-modal-actions"><button type="button" className="secondary" onClick={()=>setFormKind('')}>Cancel</button><button className="primary" disabled={busy}>{busy?'Saving…':'Save record'}</button></div></form></div>}
  </section>
}

function DataTable({headers,rows}:{headers:string[];rows:any[][]}){
  return <div className="dcc-table-wrap"><table><thead><tr>{headers.map(h=><th key={h}>{h}</th>)}</tr></thead><tbody>{rows.map((row,i)=><tr key={i}>{row.map((cell,j)=><td key={j}>{cell}</td>)}</tr>)}{!rows.length&&<tr><td colSpan={headers.length}><p className="dcc-empty">No records found.</p></td></tr>}</tbody></table></div>
}
