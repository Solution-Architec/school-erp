import { useEffect, useState } from 'react'
import { Bell, CheckCheck, Clock3, RefreshCw } from 'lucide-react'

type NotificationItem = {
  id:number; title:string; body:string; category:string; audience:string;
  published_at:string; is_read:boolean;
  students:{id:number;full_name:string;class_name:string;section:string}[];
}
type NotificationPreferences = {
  in_app_enabled:boolean; announcement:boolean; attendance:boolean;
  homework:boolean; examination:boolean; fees:boolean; general:boolean;
}
const preferenceLabels:Record<keyof Omit<NotificationPreferences,'in_app_enabled'>,string> = {
  announcement:'School announcements', attendance:'Attendance alerts',
  homework:'Homework updates', examination:'Examination results',
  fees:'Fee updates', general:'General messages'
}

export default function ParentNotifications({request}:{request:(url:string,options?:RequestInit)=>Promise<any>}) {
  const [items,setItems]=useState<NotificationItem[]>([])
  const [loading,setLoading]=useState(true)
  const [busyId,setBusyId]=useState<number|null>(null)
  const [error,setError]=useState('')
  const [preferences,setPreferences]=useState<NotificationPreferences|null>(null)
  const [savingPreference,setSavingPreference]=useState<string|null>(null)
  async function load(){
    setLoading(true);setError('')
    try{
      const [result,settings]=await Promise.all([
        request('/api/parent/notifications'),
        request('/api/parent/notification-preferences')
      ])
      setItems(Array.isArray(result)?result:[])
      setPreferences(settings)
    }catch(e:any){setError(e.message||'Could not load notifications and preferences')}
    finally{setLoading(false)}
  }
  async function updatePreference(field:keyof NotificationPreferences,value:boolean){
    if(!preferences||savingPreference)return
    setSavingPreference(field);setError('')
    try{
      const updated=await request('/api/parent/notification-preferences',{
        method:'PATCH',body:JSON.stringify({[field]:value})
      })
      setPreferences(updated)
      const result=await request('/api/parent/notifications')
      setItems(Array.isArray(result)?result:[])
    }catch(e:any){setError(e.message||'Could not save notification preference')}
    finally{setSavingPreference(null)}
  }
  useEffect(()=>{load()},[])
  async function markRead(item:NotificationItem){
    if(item.is_read||busyId===item.id)return
    setBusyId(item.id);setError('')
    try{
      await request('/api/parent/notifications/'+item.id+'/read',{method:'POST'})
      setItems(current=>current.map(row=>row.id===item.id?{...row,is_read:true}:row))
    }catch(e:any){setError(e.message||'Could not update notification')}
    finally{setBusyId(null)}
  }
  const unread=items.filter(item=>!item.is_read).length
  return <section className="parent-notifications">
    <div className="parent-notifications-heading">
      <div><span>FAMILY INBOX</span><h3>School notifications</h3><p>Announcements and important updates from your school.</p></div>
      <div className="parent-notifications-actions"><strong>{unread} unread</strong><button type="button" className="secondary" onClick={load} disabled={loading}><RefreshCw size={15}/>{loading?'Refreshing…':'Refresh'}</button></div>
    </div>
    {error&&<div className="error auth-message" role="alert">{error}</div>}
    {preferences&&<div className="panel parent-notification-preferences">
      <div className="panel-heading"><div><h3>Notification preferences</h3><p>Choose which in-app updates appear in your family inbox. Your school records are not changed.</p></div></div>
      <label className="notification-preference-row">
        <span><strong>In-app notifications</strong><small>Pause or resume all notification categories</small></span>
        <input type="checkbox" checked={preferences.in_app_enabled} disabled={savingPreference!==null} onChange={e=>updatePreference('in_app_enabled',e.target.checked)}/>
      </label>
      <div className="notification-preference-grid">
        {(Object.keys(preferenceLabels) as (keyof typeof preferenceLabels)[]).map(field=><label className="notification-preference-row" key={field}>
          <span><strong>{preferenceLabels[field]}</strong></span>
          <input type="checkbox" checked={preferences[field]} disabled={!preferences.in_app_enabled||savingPreference!==null} onChange={e=>updatePreference(field,e.target.checked)}/>
        </label>)}
      </div>
      {savingPreference&&<small role="status">Saving preference…</small>}
    </div>}
    {loading?<div className="empty-state"><strong>Loading notifications…</strong><p>Please wait while your school inbox loads.</p></div>
    :!items.length?<div className="empty-state"><Bell size={26}/><strong>You’re all caught up</strong><p>New school announcements and updates will appear here.</p></div>
    :<div className="parent-notification-list">{items.map(item=><article key={item.id} className={'parent-notification-card '+(!item.is_read?'unread':'')}>
      <div className="parent-notification-icon"><Bell size={18}/></div>
      <div className="parent-notification-main">
        <div className="parent-notification-meta"><span>{item.category.replaceAll('_',' ')}</span><time>{item.published_at?new Date(item.published_at).toLocaleString('en-IN'):'Recently published'}</time></div>
        <h4>{item.title}</h4><p>{item.body}</p>
        {item.students?.length>0&&<small>For: {item.students.map(student=>student.full_name).join(', ')}</small>}
      </div>
      <div className="parent-notification-state">{item.is_read?<span><CheckCheck size={15}/> Read</span>:<button type="button" className="secondary" disabled={busyId===item.id} onClick={()=>markRead(item)}>{busyId===item.id?'Saving…':'Mark read'}</button>}</div>
    </article>)}</div>}
  </section>
}
