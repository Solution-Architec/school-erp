import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { BadgeCheck, CircleAlert, Plus, RefreshCw, ShieldCheck, UserPlus, Users, X } from 'lucide-react'
import './InstitutionRoleBuilder.css'

type Request=(url:string,options?:RequestInit)=>Promise<any>
type Policy={module_key:string;actions:string[];scope:string}
type Template={template_id:number;template_key:string;template_name:string;description:string;category:string;version_id:number;version_number:number;permissions:Policy[];change_summary:string}
type Role={id:number;role_key:string;name:string;description:string;source_template_name:string;source_version_number:number;permissions:{module_key:string;action_key:string;scope:string;enabled:boolean}[];active_assignment_count:number;is_active:boolean}
type Staff={id:number;name:string;email:string;role:string;position:string}
type Assignment={id:number;user_id:number;user_name:string;user_email:string;legacy_role:string;role_id:number;role_name:string;role_key:string;is_active:boolean;starts_at:string;ends_at?:string|null}

const scopeLabels:Record<string,string>={own:'Own records',assigned:'Assigned records',class_section:'Class / section',department:'Department',institution:'Entire institution',selected_records:'Selected records',parent_student_relationship:'Linked parent / student'}
const title=(value:string)=>value.replaceAll('-',' ').replace(/\b\w/g,x=>x.toUpperCase())

export default function InstitutionRoleBuilder({request,canCreate=true,canEdit=true}:{request:Request;canCreate?:boolean;canEdit?:boolean}) {
 const [context,setContext]=useState<any>(null)
 const [templates,setTemplates]=useState<Template[]>([])
 const [roles,setRoles]=useState<Role[]>([])
 const [staff,setStaff]=useState<Staff[]>([])
 const [assignments,setAssignments]=useState<Assignment[]>([])
 const [selectedTemplate,setSelectedTemplate]=useState('')
 const [roleName,setRoleName]=useState('')
 const [roleKey,setRoleKey]=useState('')
 const [roleDescription,setRoleDescription]=useState('')
 const [policy,setPolicy]=useState<Policy[]>([])
 const [selectedRole,setSelectedRole]=useState('')
 const [selectedUser,setSelectedUser]=useState('')
 const [startsAt,setStartsAt]=useState('')
 const [endsAt,setEndsAt]=useState('')
 const [tab,setTab]=useState<'roles'|'assignments'>('roles')
 const [showCreate,setShowCreate]=useState(false)
 const [showAssign,setShowAssign]=useState(false)
 const [includeInactive,setIncludeInactive]=useState(false)
 const [busy,setBusy]=useState(false)
 const [error,setError]=useState('')
 const [notice,setNotice]=useState('')

 const template=templates.find(item=>String(item.version_id)===selectedTemplate)||null
 const activeRoles=roles.filter(item=>item.is_active)
 const visibleAssignments=includeInactive?assignments:assignments.filter(item=>item.is_active)
 const selectedRoleInfo=roles.find(item=>String(item.id)===selectedRole)||null
 const permissionCount=policy.length

 async function load() {
  setBusy(true);setError('')
  try {
   const [nextContext,nextTemplates,nextRoles,nextStaff,nextAssignments]=await Promise.all([
    request('/api/institution/rbac/context'),
    request('/api/institution/rbac/templates'),
    request('/api/institution/rbac/roles'),
    request('/api/institution/rbac/users'),
    request('/api/institution/rbac/assignments?include_inactive=true')
   ])
   setContext(nextContext);setTemplates(nextTemplates);setRoles(nextRoles);setStaff(nextStaff);setAssignments(nextAssignments)
   setSelectedRole(current=>nextRoles.some((item:Role)=>String(item.id)===current)?current:String(nextRoles[0]?.id||''))
  } catch(e:any){setError(e.message||'Could not load institution role settings')}
  finally{setBusy(false)}
 }
 useEffect(()=>{void load()},[])

 function beginCreate() {
  setSelectedTemplate(String(templates[0]?.version_id||''));setRoleName('');setRoleKey('');setRoleDescription('');setPolicy((templates[0]?.permissions||[]).map(item=>({module_key:item.module_key,actions:[...item.actions],scope:item.scope})))
  setError('');setNotice('');setShowCreate(true)
 }
 function chooseTemplate(id:string) {
  setSelectedTemplate(id)
  const next=templates.find(item=>String(item.version_id)===id)
  setPolicy((next?.permissions||[]).map(item=>({module_key:item.module_key,actions:[...item.actions],scope:item.scope})))
 }
 function togglePermission(moduleKey:string,action:string,checked:boolean) {
  setPolicy(current=>{
   const entry=current.find(item=>item.module_key===moduleKey)
   if(!entry&&checked){const ceiling=template?.permissions.find(item=>item.module_key===moduleKey);return [...current,{module_key:moduleKey,actions:[action],scope:ceiling?.scope||'institution'}]}
   if(!entry)return current
   const actions=checked?[...entry.actions,action]:entry.actions.filter(item=>item!==action)
   return actions.length?current.map(item=>item.module_key===moduleKey?{...item,actions}:item):current.filter(item=>item.module_key!==moduleKey)
  })
 }
 async function createRole(e:FormEvent) {
  e.preventDefault()
  if(!template){setError('Select a published Developer template.');return}
  if(!policy.some(item=>item.actions.length)){setError('Select at least one permission.');return}
  setBusy(true);setError('');setNotice('')
  const permissions=policy.flatMap(item=>item.actions.map(action=>({module_key:item.module_key,action_key:action,scope:item.scope})))
  try {
   const created=await request('/api/institution/rbac/roles',{method:'POST',body:JSON.stringify({role_key:roleKey,name:roleName,description:roleDescription,template_version_id:template.version_id,permissions})})
   setShowCreate(false);setSelectedRole(String(created.id));setNotice('Custom role created within the Developer-approved permission ceiling.');await load()
  } catch(e:any){setError(e.message||'Could not create custom role')}
  finally{setBusy(false)}
 }
 async function assignRole(e:FormEvent) {
  e.preventDefault()
  if(!selectedUser||!selectedRole){setError('Choose a staff member and a custom role.');return}
  setBusy(true);setError('');setNotice('')
  try {
   await request('/api/institution/rbac/assignments',{method:'POST',body:JSON.stringify({user_id:Number(selectedUser),role_id:Number(selectedRole),...(startsAt?{starts_at:new Date(startsAt).toISOString()}:{}),...(endsAt?{ends_at:new Date(endsAt).toISOString()}:{})})})
   setShowAssign(false);setSelectedUser('');setStartsAt('');setEndsAt('');setNotice('Custom role assigned. Existing legacy role remains unchanged.');await load()
  } catch(e:any){setError(e.message||'Could not assign custom role')}
  finally{setBusy(false)}
 }
 async function changeAssignment(item:Assignment,active:boolean) {
  if(!window.confirm((active?'Reactivate':'Revoke')+' '+item.role_name+' for '+item.user_name+'?'))return
  setBusy(true);setError('');setNotice('')
  try {await request('/api/institution/rbac/assignments/'+item.id,{method:'PATCH',body:JSON.stringify({is_active:active})});setNotice(active?'Role assignment reactivated.':'Role assignment revoked.');await load()}
  catch(e:any){setError(e.message||'Could not update assignment')}
  finally{setBusy(false)}
 }

 return <section className="institution-role-builder">
  <header className="institution-role-hero"><div><span className="institution-role-kicker"><ShieldCheck size={14}/> INSTITUTION GOVERNANCE</span><h2>Custom roles & staff assignments</h2><p>Create institution-specific roles from Developer-approved templates, then assign more than one custom role to a staff account without changing its existing login role.</p>{context&&<small>{context.school_name} · {title(context.institution_type)}</small>}</div><button className="primary" type="button" onClick={beginCreate} disabled={!templates.length||busy||!canCreate}><Plus size={16}/> Create custom role</button></header>
  {error&&<div className="institution-role-alert error" role="alert"><CircleAlert size={16}/><span>{error}</span><button type="button" onClick={()=>setError('')}><X size={15}/></button></div>}
  {notice&&<div className="institution-role-alert success" role="status"><BadgeCheck size={16}/><span>{notice}</span><button type="button" onClick={()=>setNotice('')}><X size={15}/></button></div>}
  <div className="institution-role-stats"><article><span>Published templates</span><strong>{templates.length}</strong><small>Approved for this institution type</small></article><article><span>Custom roles</span><strong>{roles.length}</strong><small>{activeRoles.length} active</small></article><article><span>Staff assignments</span><strong>{assignments.filter(item=>item.is_active).length}</strong><small>Across active custom roles</small></article><article><span>Staff accounts</span><strong>{staff.length}</strong><small>Eligible accounts in this institution</small></article></div>
  <div className="institution-role-tabs"><button className={tab==='roles'?'active':''} onClick={()=>setTab('roles')} type="button"><ShieldCheck size={15}/> Custom roles</button><button className={tab==='assignments'?'active':''} onClick={()=>setTab('assignments')} type="button"><Users size={15}/> Staff assignments</button><button className="refresh" type="button" onClick={()=>void load()} disabled={busy}><RefreshCw size={14}/> Refresh</button></div>
  {tab==='roles'?<div className="institution-role-cards">{roles.map(role=><article className={'institution-role-card '+(selectedRole===String(role.id)?'selected':'')} key={role.id}><div className="institution-role-card-head"><div className="institution-role-avatar"><ShieldCheck size={17}/></div><div className="institution-role-card-title"><strong>{role.name}</strong><small>{role.role_key}</small></div><span className={'institution-role-status '+(role.is_active?'active':'inactive')}>{role.is_active?'Active':'Inactive'}</span></div><p>{role.description||'No role description added.'}</p><div className="institution-role-meta"><span>{role.source_template_name} · v{role.source_version_number}</span><span>{role.active_assignment_count} assigned</span><span>{role.permissions.length} permission(s)</span></div><div className="institution-role-permission-chips">{role.permissions.slice(0,8).map((item,index)=><span key={item.module_key+item.action_key+index}>{title(item.module_key)} · {item.action_key}</span>)}{role.permissions.length>8&&<span>+{role.permissions.length-8} more</span>}</div><button type="button" className="secondary institution-role-assign-button" onClick={()=>{setSelectedRole(String(role.id));setShowAssign(true)}} disabled={!role.is_active||busy||!canCreate}><UserPlus size={14}/> Assign to staff</button></article>)}
   {!roles.length&&<div className="institution-role-empty"><ShieldCheck size={28}/><strong>No custom roles created</strong><span>Choose a published Developer template to create your first institution role.</span><button className="primary" type="button" onClick={beginCreate} disabled={!templates.length||!canCreate}>Create custom role</button></div>}
  </div>:<section className="institution-role-assignment-panel"><div className="institution-role-assignment-head"><div><h3>Staff role assignments</h3><p>Each staff member can hold multiple custom roles. Revoking an assignment does not alter their legacy account role.</p></div><div className="institution-role-assignment-actions"><label><input type="checkbox" checked={includeInactive} onChange={e=>setIncludeInactive(e.target.checked)}/> Show revoked</label><button className="primary" type="button" onClick={()=>{setSelectedRole(String(activeRoles[0]?.id||''));setShowAssign(true)}} disabled={!activeRoles.length||!staff.length||!canCreate}><UserPlus size={15}/> Assign role</button></div></div><div className="institution-role-table-wrap"><table><thead><tr><th>Staff member</th><th>Existing account role</th><th>Custom role</th><th>Validity</th><th>Status</th><th>Action</th></tr></thead><tbody>{visibleAssignments.map(item=><tr key={item.id}><td><strong>{item.user_name}</strong><small>{item.user_email}</small></td><td>{title(item.legacy_role)}</td><td>{item.role_name}</td><td><small>From {new Date(item.starts_at).toLocaleDateString('en-IN')}{item.ends_at?' · Until '+new Date(item.ends_at).toLocaleDateString('en-IN'):''}</small></td><td><span className={'institution-role-status '+(item.is_active?'active':'inactive')}>{item.is_active?'Active':'Revoked'}</span></td><td>{item.is_active?<button className="secondary danger-text" type="button" onClick={()=>void changeAssignment(item,false)} disabled={busy||!canEdit}>Revoke</button>:<button className="secondary" type="button" onClick={()=>void changeAssignment(item,true)} disabled={busy||!canEdit}>Reactivate</button>}</td></tr>)}{!visibleAssignments.length&&<tr><td colSpan={6}><div className="institution-role-empty compact"><strong>No assignments found</strong><span>Assign a custom role to a staff account to see it here.</span></div></td></tr>}</tbody></table></div></section>}
  {showCreate&&<div className="institution-role-modal-backdrop"><form className="institution-role-modal role-create-modal" onSubmit={createRole}><div className="institution-role-modal-head"><div><span className="institution-role-kicker">DEVELOPER-APPROVED POLICY</span><h3>Create institution custom role</h3></div><button className="icon-button" type="button" onClick={()=>setShowCreate(false)} aria-label="Close"><X size={18}/></button></div><div className="institution-role-form-grid"><label>Published template<select required value={selectedTemplate} onChange={e=>chooseTemplate(e.target.value)}><option value="">Select approved template</option>{templates.map(item=><option key={item.version_id} value={item.version_id}>{item.template_name} · v{item.version_number}</option>)}</select></label><label>Role name<input required minLength={2} maxLength={120} value={roleName} onChange={e=>{setRoleName(e.target.value);if(!roleKey)setRoleKey(e.target.value.toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^_|_$/g,''))}} placeholder="Attendance Coordinator"/></label><label>Role key<input required minLength={1} maxLength={80} pattern="[a-zA-Z0-9_-]+" value={roleKey} onChange={e=>setRoleKey(e.target.value.toLowerCase())} placeholder="attendance_coordinator"/></label><label className="wide">Description<textarea maxLength={4000} value={roleDescription} onChange={e=>setRoleDescription(e.target.value)} placeholder="Describe the responsibilities for this institution role."/></label></div>{template&&<div className="institution-role-template-note"><strong>{template.template_name} · version {template.version_number}</strong><span>{template.change_summary}</span><small>Only the published template's approved module/action/scope combinations can be selected. You may grant a subset, not exceed the template.</small></div>}<div className="institution-role-policy-area"><div className="institution-role-policy-head"><div><h4>Permission selection</h4><p>{permissionCount} module group(s) selected. Scopes remain bounded by the approved template.</p></div><button type="button" className="secondary" onClick={()=>setPolicy([])}>Clear selection</button></div>{template?.permissions.map(module=><article className="institution-role-policy-module" key={module.module_key}><div><strong>{title(module.module_key)}</strong><small>Allowed data scope: {scopeLabels[module.scope]||module.scope}</small></div><div className="institution-role-policy-actions">{module.actions.map(action=><label key={action}><input type="checkbox" checked={Boolean(policy.find(item=>item.module_key===module.module_key)?.actions.includes(action))} onChange={e=>togglePermission(module.module_key,action,e.target.checked)}/>{action}</label>)}</div></article>)}{!template&&<div className="institution-role-empty compact">Select a template to see its approved permissions.</div>}</div><div className="institution-role-modal-actions"><button className="secondary" type="button" onClick={()=>setShowCreate(false)}>Cancel</button><button className="primary" disabled={busy||!canCreate||!template||!policy.some(item=>item.actions.length)}><Plus size={15}/> Create role</button></div></form></div>}
  {showAssign&&<div className="institution-role-modal-backdrop"><form className="institution-role-modal assign-modal" onSubmit={assignRole}><div className="institution-role-modal-head"><div><span className="institution-role-kicker">MULTI-ROLE ASSIGNMENT</span><h3>Assign custom role</h3></div><button className="icon-button" type="button" onClick={()=>setShowAssign(false)} aria-label="Close"><X size={18}/></button></div><label>Staff account<select required value={selectedUser} onChange={e=>setSelectedUser(e.target.value)}><option value="">Select staff member</option>{staff.map(item=><option key={item.id} value={item.id}>{item.name} · {item.email} · {title(item.role)}</option>)}</select></label><label>Custom role<select required value={selectedRole} onChange={e=>setSelectedRole(e.target.value)}><option value="">Select custom role</option>{activeRoles.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</select></label><div className="institution-role-form-grid"><label>Start date (optional)<input type="datetime-local" value={startsAt} onChange={e=>setStartsAt(e.target.value)}/></label><label>End date (optional)<input type="datetime-local" min={startsAt||undefined} value={endsAt} onChange={e=>setEndsAt(e.target.value)}/></label></div><p className="institution-role-help">The staff member keeps their existing login role. This assignment adds another permission set; active explicit denies continue to take precedence in the multi-role resolver.</p><div className="institution-role-modal-actions"><button className="secondary" type="button" onClick={()=>setShowAssign(false)}>Cancel</button><button className="primary" disabled={busy||!canCreate||!selectedUser||!selectedRole}><UserPlus size={15}/> Assign role</button></div></form></div>}
 </section>
}
