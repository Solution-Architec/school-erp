import { useEffect, useState } from 'react'
import { Award, Download, RefreshCw, CheckCircle2, XCircle, FileCheck2 } from 'lucide-react'

type Props = {
 request:(url:string,options?:RequestInit)=>Promise<any>
 token:string
}

export default function CertificateManagementPanel({request,token}:Props) {
 const [rows,setRows]=useState<any[]>([])
 const [status,setStatus]=useState('pending')
 const [busy,setBusy]=useState(false)
 const [working,setWorking]=useState<number|null>(null)
 const [notes,setNotes]=useState<Record<number,string>>({})
 const [error,setError]=useState('')
 const [notice,setNotice]=useState('')

 async function load() {
  setBusy(true);setError('')
  try { setRows(await request('/api/certificate-applications?status='+status)) }
  catch(e:any) { setError(e.message||'Could not load certificate applications') }
  finally { setBusy(false) }
 }
 useEffect(()=>{load()},[status])

 async function review(row:any,next:'approved'|'rejected') {
  const note=notes[row.id]||''
  if(!window.confirm((next==='approved'?'Approve':'Reject')+' the '+row.certificate_type+' certificate request for '+row.student_name+'?'))return
  setWorking(row.id);setError('');setNotice('')
  try {
   await request('/api/certificate-applications/'+row.id+'/review',{method:'POST',body:JSON.stringify({status:next,reviewer_note:note})})
   setNotice('Certificate application '+next+'.')
   await load()
  } catch(e:any) { setError(e.message||'Could not review certificate application') }
  finally { setWorking(null) }
 }

 async function issue(row:any) {
  if(!window.confirm('Issue the approved certificate for '+row.student_name+'? The certificate number cannot be changed after issuance.'))return
  setWorking(row.id);setError('');setNotice('')
  try {
   const issued=await request('/api/certificate-applications/'+row.id+'/issue',{method:'POST'})
   setNotice('Certificate issued: '+issued.certificate_number)
   await load()
  } catch(e:any) { setError(e.message||'Could not issue certificate') }
  finally { setWorking(null) }
 }

 async function download(issueId:number,number:string) {
  setWorking(issueId);setError('')
  try {
   const response=await fetch('/api/certificate-issues/'+issueId+'/download',{headers:{Authorization:'Bearer '+token}})
   if(!response.ok){const body=await response.json().catch(()=>({}));throw new Error(body.detail||'Certificate download failed')}
   const blob=await response.blob()
   const url=URL.createObjectURL(blob)
   const anchor=document.createElement('a')
   anchor.href=url;anchor.download=number+'.pdf';document.body.appendChild(anchor);anchor.click();anchor.remove();URL.revokeObjectURL(url)
  } catch(e:any) { setError(e.message||'Could not download certificate') }
  finally { setWorking(null) }
 }

 const pending=rows.filter(row=>row.status==='pending').length
 const approved=rows.filter(row=>row.status==='approved').length
 const issued=rows.filter(row=>Boolean(row.certificate_number)).length

 return <section className="certificate-management-workspace">
  <div className="panel certificate-management-hero">
   <div className="panel-heading"><div><span className="parent-relations-eyebrow">STUDENT DOCUMENTS · GOVERNED ISSUANCE</span><h3>Certificate management</h3><p>Review parent requests, issue approved certificates and provide secure PDF downloads.</p></div><Award size={23}/></div>
   <div className="parent-relations-stats">
    <div><span>Pending in view</span><strong>{pending}</strong></div>
    <div><span>Approved in view</span><strong>{approved}</strong></div>
    <div><span>Issued in view</span><strong>{issued}</strong></div>
   </div>
  </div>
  <div className="panel certificate-management-list">
   <div className="parent-relations-toolbar">
    <div><h3>Application register</h3><p>Only requests from this school are shown. Every action is recorded in the audit log.</p></div>
    <button className="secondary" type="button" disabled={busy} onClick={load}><RefreshCw size={15}/>{busy?'Refreshing…':'Refresh'}</button>
   </div>
   <div className="parent-relations-filters">
    <label className="parent-relations-status">Application status<select value={status} onChange={e=>setStatus(e.target.value)}><option value="pending">Pending review</option><option value="approved">Approved</option><option value="rejected">Rejected</option><option value="all">All applications</option></select></label>
   </div>
   {error&&<div className="error auth-message" role="alert">{error}</div>}
   {notice&&<div className="success auth-message" role="status">{notice}</div>}
   <div className="table-wrap">
    <table className="parent-relations-table"><thead><tr><th>Student</th><th>Parent</th><th>Certificate / purpose</th><th>Applied</th><th>Status</th><th>Certificate number</th><th>Actions</th></tr></thead>
     <tbody>{rows.map(row=><tr key={row.id}>
      <td><strong>{row.student_name}</strong><small>{row.admission_no} · {row.class_name||'Class not set'} {row.section||''}</small></td>
      <td><strong>{row.parent_name}</strong><small>{row.parent_email}</small></td>
      <td><strong>{row.certificate_type.replaceAll('_',' ')}</strong><small>{row.purpose}</small></td>
      <td>{new Date(row.created_at).toLocaleDateString('en-IN')}</td>
      <td><span className={'status-badge '+row.status}>{row.status}</span></td>
      <td>{row.certificate_number||'—'}</td>
      <td><div className="certificate-row-actions">
       {row.status==='pending'&&<><input aria-label={'Review note for '+row.student_name} placeholder="Optional note" value={notes[row.id]||''} onChange={e=>setNotes(old=>({...old,[row.id]:e.target.value}))}/><button className="primary" type="button" disabled={working===row.id} onClick={()=>review(row,'approved')}><CheckCircle2 size={14}/> Approve</button><button className="secondary" type="button" disabled={working===row.id} onClick={()=>review(row,'rejected')}><XCircle size={14}/> Reject</button></>}
       {row.status==='approved'&&!row.certificate_number&&<button className="primary" type="button" disabled={working===row.id} onClick={()=>issue(row)}><FileCheck2 size={14}/> Issue certificate</button>}
       {row.certificate_number&&<button className="secondary" type="button" disabled={working===row.id} onClick={()=>download(row.id,row.certificate_number)}><Download size={14}/> Download PDF</button>}
       {working===row.id&&<span className="muted small">Working…</span>}
      </div></td>
     </tr>)}
     {!rows.length&&<tr><td colSpan={7}><div className="empty-state compact-empty"><strong>{busy?'Loading applications…':'No certificate applications in this view'}</strong><p>{busy?'Please wait while the school register loads.':'New parent requests will appear here when submitted.'}</p></div></td></tr>}
     </tbody>
    </table>
   </div>
   <div className="parent-relations-footer"><span>{rows.length} application(s)</span><span>PDF access is authenticated and school / parent-link scoped</span></div>
  </div>
 </section>
}
