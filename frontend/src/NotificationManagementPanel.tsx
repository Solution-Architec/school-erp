import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Bell, Plus, RefreshCw, Send } from 'lucide-react'

type StudentOption={id:number;full_name:string;class_name?:string;section?:string;admission_no?:string}
type Notice={id:number;title:string;body:string;category:string;audience:string;class_name?:string;section?:string;student_id?:number|null;is_published:boolean;created_at:string}

export default function NotificationManagementPanel({request}:{request:(url:string,options?:RequestInit)=>Promise<any>}) {
 const [items,setItems]=useState<Notice[]>([])
 const [students,setStudents]=useState<StudentOption[]>([])
 const [title,setTitle]=useState('')
 const [body,setBody]=useState('')
 const [category,setCategory]=useState('announcement')
 const [audience,setAudience]=useState('school')
 const [className,setClassName]=useState('')
 const [section,setSection]=useState('')
 const [studentId,setStudentId]=useState('')
 const [busy,setBusy]=useState(false)
 const [loading,setLoading]=useState(true)
 const [error,setError]=useState('')
 const [notice,setNotice]=useState('')
 async function load(){
  setLoading(true);setError('')
  try{
   const [notifications,studentRows]=await Promise.all([request('/api/school/notifications'),request('/api/students')])
   setItems(Array.isArray(notifications)?notifications:[])
   setStudents(Array.isArray(studentRows)?studentRows:[])
  }catch(e:any){setError(e.message||'Could not load notification workspace')}
  finally{setLoading(false)}
 }
 useEffect(()=>{load()},[])
 async function publish(e:FormEvent<HTMLFormElement>){
  e.preventDefault()
  if(busy)return
  setBusy(true);setError('');setNotice('')
  try{
   const created=await request('/api/school/notifications',{method:'POST',body:JSON.stringify({
    title:title.trim(),body:body.trim(),category,audience,
    class_name:audience==='class'?className.trim():'',
    section:audience==='class'?section.trim():'',
    student_id:audience==='student'?Number(studentId):null,
    is_published:true
   })})
   setItems(current=>[created,...current]);setTitle('');setBody('');setNotice('Notification published to the selected parent audience.')
  }catch(e:any){setError(e.message||'Could not publish notification')}
  finally{setBusy(false)}
 }
 return <section className="notification-management">
  <div className="notification-management-hero"><div><span>SCHOOL COMMUNICATION</span><h2>Notification centre</h2><p>Publish school updates to parents. Audience visibility is checked against active parent–student links.</p></div><Bell size={25}/></div>
  <div className="panel notification-compose">
   <div className="panel-heading"><div><h3>Compose notification</h3><p>In-app delivery is enabled. Email and SMS can be added as optional channels later.</p></div><Plus size={18}/></div>
   <form onSubmit={publish}>
    <div className="notification-form-grid">
     <label>Title<input required minLength={3} maxLength={180} value={title} onChange={e=>setTitle(e.target.value)} placeholder="e.g. Parent-teacher meeting on Friday"/></label>
     <label>Category<select value={category} onChange={e=>setCategory(e.target.value)}><option value="announcement">Announcement</option><option value="attendance">Attendance alert</option><option value="homework">Homework reminder</option><option value="examination">Examination notice</option><option value="fees">Fee reminder</option><option value="general">General update</option></select></label>
     <label>Audience<select value={audience} onChange={e=>setAudience(e.target.value)}><option value="school">All linked parents in this school</option><option value="class">Specific class / section</option><option value="student">One linked student’s parent(s)</option></select></label>
     {audience==='class'&&<><label>Class<input required maxLength={80} value={className} onChange={e=>setClassName(e.target.value)} placeholder="e.g. Class 5"/></label><label>Section (optional)<input maxLength={40} value={section} onChange={e=>setSection(e.target.value)} placeholder="e.g. A"/></label></>}
     {audience==='student'&&<label>Student<select required value={studentId} onChange={e=>setStudentId(e.target.value)}><option value="">Select student</option>{students.map(student=><option key={student.id} value={student.id}>{student.full_name} · {student.admission_no||'No admission no.'} · {student.class_name||'Class'} {student.section||''}</option>)}</select></label>}
    </div>
    <label className="notification-body-field">Message<textarea required minLength={3} maxLength={5000} rows={4} value={body} onChange={e=>setBody(e.target.value)} placeholder="Write the details parents need to know…"/></label>
    {error&&<div className="error auth-message" role="alert">{error}</div>}{notice&&<div className="success auth-message" role="status">{notice}</div>}
    <div className="notification-form-actions"><span>Published messages are immediately visible to eligible linked parents.</span><button className="primary" disabled={busy||!title.trim()||!body.trim()||audience==='class'&&!className.trim()||audience==='student'&&!studentId}>{busy?'Publishing…':<><Send size={15}/> Publish notification</>}</button></div>
   </form>
  </div>
  <div className="panel notification-register">
   <div className="panel-heading"><div><h3>Published and drafted messages</h3><p>Recent notifications created for this school.</p></div><button type="button" className="secondary" onClick={load} disabled={loading}><RefreshCw size={15}/> Refresh</button></div>
   {loading?<div className="empty-state"><strong>Loading messages…</strong></div>:<div className="table-wrap"><table><thead><tr><th>Title</th><th>Category</th><th>Audience</th><th>Status</th><th>Created</th></tr></thead><tbody>
    {items.map(item=><tr key={item.id}><td><strong>{item.title}</strong><small>{item.body}</small></td><td>{item.category}</td><td>{item.audience==='school'?'All parents':item.audience==='class'?[item.class_name,item.section].filter(Boolean).join(' · '):'Selected student'}</td><td><span className={'status-badge '+(item.is_published?'active':'pending')}>{item.is_published?'Published':'Draft'}</span></td><td>{item.created_at?new Date(item.created_at).toLocaleDateString('en-IN'):'—'}</td></tr>)}
    {!items.length&&<tr><td colSpan={5}>No notifications created yet.</td></tr>}
   </tbody></table></div>}
  </div>
 </section>
}
