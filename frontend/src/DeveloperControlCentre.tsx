import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { Activity, Building2, CalendarClock, CheckCircle2, CircleAlert, FileText, Headset, IndianRupee, RefreshCw, Save, ShieldCheck, Users, X } from 'lucide-react'
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
const tabs=['Overview','Clients','Quotations','Subscriptions','Collections','Support','Live usage']
const money=(v:any)=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:2}).format(Number(v||0))
const day=(v:any)=>v?new Date(v).toLocaleDateString('en-IN'):'—'
const dateInput=(v:any)=>v?String(v).slice(0,10):''

export default function DeveloperControlCentre({request,onEnterWorkspace}:{request:Request;onEnterWorkspace:(schoolId:number)=>Promise<void>}) {
  const [tab,setTab]=useState('Overview')
  const [overview,setOverview]=useState<Overview>(emptyOverview)
  const [clients,setClients]=useState<Client[]>([])
  const [quotes,setQuotes]=useState<any[]>([])
  const [subscriptions,setSubscriptions]=useState<any[]>([])
  const [payments,setPayments]=useState<any[]>([])
  const [tickets,setTickets]=useState<any[]>([])
  const [activity,setActivity]=useState<any[]>([])
  const [selected,setSelected]=useState<Client|null>(null)
  const [clientDetail,setClientDetail]=useState<any|null>(null)
  const [profile,setProfile]=useState<Record<string,string>>({})
  const [query,setQuery]=useState('')
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  const [notice,setNotice]=useState('')
  const [formKind,setFormKind]=useState('')
  const [form,setForm]=useState<Record<string,string>>({})

  async function load(){
    setBusy(true);setError('')
    try{
      const [o,c,q,s,p,t,a]=await Promise.all([
        request('/api/platform/overview'),request('/api/platform/clients'),request('/api/platform/quotations'),
        request('/api/platform/subscriptions'),request('/api/platform/payments'),request('/api/platform/support-tickets'),
        request('/api/platform/activity')
      ])
      setOverview(o);setClients(c);setQuotes(q);setSubscriptions(s);setPayments(p);setTickets(t);setActivity(a)
      if(selected){const fresh=c.find((item:Client)=>item.id===selected.id);if(fresh){setSelected(fresh);setProfile(toProfile(fresh.profile))}}
    }catch(e:any){setError(e.message||'Could not load platform data')}
    finally{setBusy(false)}
  }
  function toProfile(p:Record<string,any>={}){return Object.fromEntries(['contact_person','contact_email','contact_phone','address','city','state','country','affiliation','registration_no','website','notes'].map(k=>[k,String(p[k]??'')]))}
  useEffect(()=>{load()},[])
  const filteredClients=useMemo(()=>clients.filter(c=>(c.name+' '+c.code+' '+c.institution_type).toLowerCase().includes(query.toLowerCase())),[clients,query])
  const clientName=(id:number)=>clients.find(c=>c.id===id)?.name||'Unknown institution'
  async function openClient(c:Client){setSelected(c);setProfile(toProfile(c.profile));setClientDetail(null);try{setClientDetail(await request('/api/platform/clients/'+c.id))}catch(e:any){setError(e.message||'Could not load client details')}}
  function openForm(kind:string,c?:Client){
    setFormKind(kind)
    setForm(c?{school_id:String(c.id)}:{})
    if(kind==='quotation')setForm(c?{school_id:String(c.id),title:'EduNexus subscription / services',amount:'',tax_amount:'0',discount_amount:'0',valid_until:'',status:'draft',notes:''}:{title:'EduNexus subscription / services',amount:'',tax_amount:'0',discount_amount:'0',valid_until:'',status:'draft',notes:''})
    if(kind==='subscription')setForm(c?{school_id:String(c.id),plan_name:'Standard',amount:'',billing_cycle:'annual',start_date:dateInput(new Date()),end_date:'',status:'active',notes:''}:{plan_name:'Standard',amount:'',billing_cycle:'annual',start_date:dateInput(new Date()),end_date:'',status:'active',notes:''})
    if(kind==='payment')setForm(c?{school_id:String(c.id),amount:'',payment_date:dateInput(new Date()),payment_method:'bank_transfer',status:'received',transaction_reference:'',notes:''}:{amount:'',payment_date:dateInput(new Date()),payment_method:'bank_transfer',status:'received',transaction_reference:'',notes:''})
    if(kind==='ticket')setForm(c?{school_id:String(c.id),subject:'',description:'',category:'technical',priority:'normal',requester_name:'',requester_email:''}:{subject:'',description:'',category:'technical',priority:'normal',requester_name:'',requester_email:''})
  }
  async function submitForm(e:FormEvent){
    e.preventDefault();setBusy(true);setError('');setNotice('')
    try{
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
    {tab==='Clients'&&<div className="dcc-panel"><div className="dcc-panel-title"><div><h3>All client institutions</h3><p>Institution profiles and individual client records</p></div><span className="dcc-count">{filteredClients.length} clients</span></div><div className="dcc-toolbar"><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search institution, code or type…"/><button className="primary" onClick={()=>openForm('ticket',selected||undefined)}>Create support ticket</button></div><div className="dcc-table-wrap"><table><thead><tr><th>Institution</th><th>Type</th><th>Users</th><th>Students</th><th>Staff</th><th>Subscription</th><th>Status</th><th></th></tr></thead><tbody>{filteredClients.map(c=><tr key={c.id}><td><strong>{c.name}</strong><small>{c.code}</small></td><td>{c.institution_type.replaceAll('_',' ')}</td><td>{c.users}</td><td>{c.students}</td><td>{c.staff}</td><td>{c.subscription?day(c.subscription.end_date):'Not set'}</td><td><span className={'dcc-status '+(c.is_active?'good':'warning')}>{c.is_active?'Active':'Inactive'}</span></td><td><button className="secondary compact" onClick={()=>openClient(c)}>Manage</button></td></tr>)}{!filteredClients.length&&<tr><td colSpan={8}><p className="dcc-empty">No client institutions found.</p></td></tr>}</tbody></table></div>
      {selected&&<div className="dcc-client-detail"><div className="dcc-panel-title"><div><h3>{selected.name}</h3><p>{selected.code} · {selected.institution_type.replaceAll('_',' ')}</p></div><button className="secondary compact" onClick={()=>{setSelected(null);setClientDetail(null)}}>Close</button></div><div className="dcc-client-actions"><button className="primary" onClick={()=>onEnterWorkspace(selected.id)}>Open client dashboard</button><button className="secondary" onClick={()=>openForm('quotation',selected)}>New quotation</button><button className="secondary" onClick={()=>openForm('subscription',selected)}>Add subscription</button><button className="secondary" onClick={()=>openForm('payment',selected)}>Record collection</button><button className="secondary" onClick={()=>openForm('ticket',selected)}>Support ticket</button></div><form className="dcc-profile-form" onSubmit={saveProfile}><h4>Institution contact and registration details</h4><div className="dcc-form-grid">{[['contact_person','Contact person'],['contact_email','Contact email'],['contact_phone','Contact phone'],['affiliation','Affiliation / board'],['registration_no','Registration number'],['website','Website'],['city','City'],['state','State'],['country','Country']].map(([k,l])=><label key={k}>{l}<input value={profile[k]||''} onChange={e=>setProfile({...profile,[k]:e.target.value})}/></label>)}<label className="wide">Address<textarea value={profile.address||''} onChange={e=>setProfile({...profile,address:e.target.value})}/></label><label className="wide">Internal notes<textarea value={profile.notes||''} onChange={e=>setProfile({...profile,notes:e.target.value})}/></label></div><button className="primary" disabled={busy}><Save size={15}/> Save client details</button></form><div className="dcc-client-users"><h4>Client user accounts</h4><div className="dcc-table-wrap"><table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Account status</th></tr></thead><tbody>{(clientDetail?.users||[]).map((u:any)=><tr key={u.id}><td>{u.name}</td><td>{u.email}</td><td>{u.role.replaceAll('_',' ')}</td><td><span className={'dcc-status '+(u.is_active?'good':'warning')}>{u.is_active?'Active':'Inactive'}</span></td></tr>)}{!clientDetail?.users?.length&&<tr><td colSpan={4}><p className="dcc-empty">No client accounts returned.</p></td></tr>}</tbody></table></div></div></div>}
    </div>}
    {tab==='Quotations'&&<div className="dcc-panel"><div className="dcc-panel-title"><div><h3>Client quotations</h3><p>Prepare and track quotations for implementation, modules and services</p></div><button className="primary" onClick={()=>openForm('quotation')}>New quotation</button></div><DataTable headers={['Quotation','Institution','Title','Amount','Valid until','Status']} rows={quotes.map(q=>[q.quotation_no,clientName(q.school_id),q.title,money(Number(q.amount)+Number(q.tax_amount)-Number(q.discount_amount)),day(q.valid_until),q.status])}/></div>}
    {tab==='Subscriptions'&&<div className="dcc-panel"><div className="dcc-panel-title"><div><h3>Subscriptions and renewals</h3><p>Track plan value, start date, expiry date and status</p></div><button className="primary" onClick={()=>openForm('subscription')}>Add subscription</button></div><DataTable headers={['Institution','Plan','Amount','Billing','Start date','Expiry date','Status']} rows={subscriptions.map(s=>[clientName(s.school_id),s.plan_name,money(s.amount),s.billing_cycle,day(s.start_date),day(s.end_date),s.status])}/></div>}
    {tab==='Collections'&&<div className="dcc-panel"><div className="dcc-panel-title"><div><h3>Amount collections</h3><p>Record payments and review collection history</p></div><button className="primary" onClick={()=>openForm('payment')}>Record payment</button></div><div className="dcc-revenue"><IndianRupee size={19}/><div><small>Total received (all clients)</small><strong>{money(overview.received_amount)}</strong></div></div><DataTable headers={['Institution','Amount','Payment date','Method','Reference','Status']} rows={payments.map(p=>[clientName(p.school_id),money(p.amount),day(p.payment_date),p.payment_method,p.transaction_reference||'—',p.status])}/></div>}
    {tab==='Support'&&<div className="dcc-panel"><div className="dcc-panel-title"><div><h3>Client support desk</h3><p>Track requests, complaints and technical follow-ups</p></div><button className="primary" onClick={()=>openForm('ticket')}>New support ticket</button></div><div className="dcc-ticket-list">{tickets.map(t=><article key={t.id} className="dcc-ticket"><div><strong>{t.subject}</strong><small>{clientName(t.school_id)} · {t.category} · {t.priority} · {day(t.created_at)}</small><p>{t.description}</p>{t.resolution_notes&&<small>Resolution: {t.resolution_notes}</small>}</div><div className="dcc-ticket-controls"><select value={t.status} disabled={busy} onChange={e=>updateTicket(t,e.target.value)}>{['open','in_progress','waiting_client','resolved','closed'].map(s=><option key={s} value={s}>{s.replaceAll('_',' ')}</option>)}</select></div></article>)}{!tickets.length&&<p className="dcc-empty">No support requests recorded.</p>}</div></div>}
    {tab==='Live usage'&&<div className="dcc-panel"><div className="dcc-panel-title"><div><h3>Client and user activity</h3><p>Online means an authenticated heartbeat received within the last five minutes.</p></div><span className="dcc-count">{activity.filter(a=>a.online).length} online</span></div><div className="dcc-table-wrap"><table><thead><tr><th>User</th><th>Institution</th><th>Role</th><th>Last seen</th><th>Status</th></tr></thead><tbody>{activity.map(a=><tr key={a.user_id}><td><strong>{a.name}</strong><small>{a.email}</small></td><td>{a.institution}</td><td>{a.role.replaceAll('_',' ')}</td><td>{new Date(a.last_seen_at).toLocaleString('en-IN')}</td><td><span className={'dcc-status '+(a.online?'good':'')}>{a.online?'Online':'Offline'}</span></td></tr>)}{!activity.length&&<tr><td colSpan={5}><p className="dcc-empty">No activity heartbeats received yet. Online monitoring begins as users sign in and the application sends periodic heartbeats.</p></td></tr>}</tbody></table></div></div>}
    {formKind&&<div className="dcc-modal-backdrop" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget)setFormKind('')}}><form className="dcc-modal" onSubmit={submitForm}><div className="dcc-panel-title"><div><h3>{({quotation:'New quotation',subscription:'New subscription',payment:'Record client payment',ticket:'Create support ticket'} as Record<string,string>)[formKind]}</h3><p>Changes are saved to the selected client record.</p></div><button type="button" className="secondary compact" onClick={()=>setFormKind('')}><X size={15}/></button></div><div className="dcc-form-grid">
      <label className="wide">Client institution<select required value={form.school_id||''} onChange={e=>setForm({...form,school_id:e.target.value})}><option value="">Select client</option>{clients.map(c=><option key={c.id} value={c.id}>{c.name} · {c.code}</option>)}</select></label>
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
