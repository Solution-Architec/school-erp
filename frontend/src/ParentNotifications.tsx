import { useEffect, useState } from 'react'
import { Bell, CheckCheck, Clock3, RefreshCw } from 'lucide-react'

type NotificationItem = {
  id:number; title:string; body:string; category:string; audience:string;
  published_at:string; is_read:boolean;
  students:{id:number;full_name:string;class_name:string;section:string}[];
}

export default function ParentNotifications({request}:{request:(url:string,options?:RequestInit)=>Promise<any>}) {
  const [items,setItems]=useState<NotificationItem[]>([])
  const [loading,setLoading]=useState(true)
  const [busyId,setBusyId]=useState<number|null>(null)
  const [error,setError]=useState('')
  async function load(){
    setLoading(true);setError('')
    try{const result=await request('/api/parent/notifications');setItems(Array.isArray(result)?result:[])}
    catch(e:any){setError(e.message||'Could not load notifications')}
    finally{setLoading(false)}
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
