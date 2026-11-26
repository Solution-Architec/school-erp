import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { CheckCircle2, CircleAlert, Layers3, Plus, RefreshCw, Save, ShieldCheck, Tag, X } from 'lucide-react'
import './DeveloperRoleDesigner.css'

type Request = (url:string, options?:RequestInit)=>Promise<any>
type Catalog = {institution_types:{key:string;label:string}[];modules:{key:string;label:string;description:string;category:string;platform_only:boolean;institution_types:string[];actions:string[]}[];actions:{key:string;label:string;description:string}[]}
type Permission = {module_key:string;actions:string[];scope:string}
type Version = {id:number;template_id:number;version_number:number;status:string;institution_types:string[];permissions:Permission[];change_summary:string;created_at:string;published_at?:string|null}
type Template = {id:number;template_key:string;name:string;description:string;category:string;is_active:boolean;versions:Version[]}

const emptyCatalog:Catalog={institution_types:[],modules:[],actions:[]}
const scopes=[['own','Own records'],['assigned','Assigned records'],['class_section','Class / section'],['department','Department'],['institution','Entire institution'],['selected_records','Selected records'],['parent_student_relationship','Linked parent / student']]

export default function DeveloperRoleDesigner({request}:{request:Request}) {
 const [catalog,setCatalog]=useState<Catalog>(emptyCatalog)
 const [templates,setTemplates]=useState<Template[]>([])
 const [selectedId,setSelectedId]=useState('')
 const [selectedVersionId,setSelectedVersionId]=useState('')
 const [name,setName]=useState('')
 const [templateKey,setTemplateKey]=useState('')
 const [description,setDescription]=useState('')
 const [category,setCategory]=useState('academic')
 const [institutionTypes,setInstitutionTypes]=useState<string[]>(['school'])
 const [permissions,setPermissions]=useState<Permission[]>([])
 const [changeSummary,setChangeSummary]=useState('Initial role policy')
 const [editingDraft,setEditingDraft]=useState(false)
 const [busy,setBusy]=useState(false)
 const [error,setError]=useState('')
 const [notice,setNotice]=useState('')
 const [showCreate,setShowCreate]=useState(false)
 const [showVersionEditor,setShowVersionEditor]=useState(false)

 const selected=templates.find(item=>String(item.id)===selectedId)||null
 const versions=selected?.versions||[]
 const selectedVersion=versions.find(item=>String(item.id)===selectedVersionId)||versions[0]||null
 const availableModules=useMemo(()=>catalog.modules.filter(item=>!item.platform_only),[catalog.modules])
 const enabledActionCount=permissions.reduce((sum,item)=>sum+item.actions.length,0)

 async function load(preferredId?:string) {
  setBusy(true);setError('')
  try {
   const [nextCatalog,nextTemplates]=await Promise.all([
    request('/api/developer/rbac/catalog'),
    request('/api/developer/rbac/templates?include_inactive=true')
   ])
   setCatalog(nextCatalog)
   setTemplates(nextTemplates)
   const wanted=preferredId||selectedId
   const next=nextTemplates.find((item:Template)=>String(item.id)===wanted)||nextTemplates[0]
   setSelectedId(next?String(next.id):'')
   setSelectedVersionId(current=>next?.versions?.some((v:Version)=>String(v.id)===current)?current:String(next?.versions?.[0]?.id||''))
  } catch(e:any) {setError(e.message||'Could not load the Developer role catalogue')}
  finally {setBusy(false)}
 }
 useEffect(()=>{void load()},[])

 function startVersion(version?:Version) {
  setError('');setNotice('')
  if(version) {
   setSelectedVersionId(String(version.id))
   setInstitutionTypes(version.institution_types||[])
   setPermissions((version.permissions||[]).map(item=>({module_key:item.module_key,actions:[...item.actions],scope:item.scope||'institution'})))
   setChangeSummary(version.change_summary||'')
   setEditingDraft(true)
  } else {
   setSelectedVersionId('')
   setInstitutionTypes(['school'])
   setPermissions([])
   setChangeSummary('Initial role policy')
   setEditingDraft(false)
  }
  setShowVersionEditor(true)
 }
 function toggleInstitutionType(key:string) {
  setInstitutionTypes(current=>current.includes(key)?current.filter(item=>item!==key):[...current,key])
 }
 function togglePermission(moduleKey:string,action:string,checked:boolean) {
  setPermissions(current=>{
   const existing=current.find(item=>item.module_key===moduleKey)
   if(!existing&&checked)return [...current,{module_key:moduleKey,actions:[action],scope:'institution'}]
   if(!existing)return current
   const actions=checked?[...existing.actions,action]:existing.actions.filter(item=>item!==action)
   return actions.length?current.map(item=>item.module_key===moduleKey?{...item,actions}:item):current.filter(item=>item.module_key!==moduleKey)
  })
 }
 function setScope(moduleKey:string,scope:string) {
  setPermissions(current=>current.map(item=>item.module_key===moduleKey?{...item,scope}:item))
 }
 async function createTemplate(e:FormEvent) {
  e.preventDefault();setBusy(true);setError('');setNotice('')
  try {
   const created=await request('/api/developer/rbac/templates',{method:'POST',body:JSON.stringify({template_key:templateKey,name,description,category})})
   setShowCreate(false);setTemplateKey('');setName('');setDescription('');setCategory('academic')
   setNotice('Role template created. Add a draft version to define its permissions.')
   await load(String(created.id))
  } catch(e:any) {setError(e.message||'Could not create role template')}
  finally {setBusy(false)}
 }
 async function saveVersion(e:React.FormEvent) {
  e.preventDefault()
  if(!selected)return
  if(!institutionTypes.length){setError('Select at least one institution type.');return}
  if(!permissions.length){setError('Add at least one module permission before saving.');return}
  setBusy(true);setError('');setNotice('')
  const payload={institution_types:institutionTypes,permissions,change_summary:changeSummary}
  try {
   const result=editingDraft&&selectedVersionId
    ?await request('/api/developer/rbac/versions/'+selectedVersionId,{method:'PATCH',body:JSON.stringify(payload)})
    :await request('/api/developer/rbac/templates/'+selected.id+'/versions',{method:'POST',body:JSON.stringify(payload)})
   setShowVersionEditor(false);setSelectedVersionId(String(result.id))
   setNotice('Draft version saved. Review the policy before publishing.')
   await load(String(selected.id))
   setSelectedVersionId(String(result.id))
  } catch(e:any) {setError(e.message||'Could not save draft version')}
  finally {setBusy(false)}
 }
 async function updateTemplateActive() {
  if(!selected)return
  const next=!selected.is_active
  if(!window.confirm((next?'Reactivate':'Pause')+' this role template? Existing institution roles will not be changed.'))return
  setBusy(true);setError('');setNotice('')
  try {await request('/api/developer/rbac/templates/'+selected.id,{method:'PATCH',body:JSON.stringify({is_active:next})});setNotice(next?'Template reactivated.':'Template paused.');await load(String(selected.id))}
  catch(e:any){setError(e.message||'Could not update template')}
  finally {setBusy(false)}
 }
 async function publishVersion(version:Version) {
  if(!window.confirm('Publish version '+version.version_number+'? Published policy becomes immutable.'))return
  setBusy(true);setError('');setNotice('')
  try {await request('/api/developer/rbac/versions/'+version.id+'/publish',{method:'POST'});setNotice('Version published successfully. Institutions can now adopt this version.');await load(String(selected?.id));setSelectedVersionId(String(version.id))}
  catch(e:any){setError(e.message||'Could not publish version')}
  finally {setBusy(false)}
 }
 async function retireVersion(version:Version) {
  if(!window.confirm('Retire version '+version.version_number+'? Existing institution roles keep their adopted permissions; new adoption will be blocked.'))return
  setBusy(true);setError('');setNotice('')
  try {await request('/api/developer/rbac/versions/'+version.id+'/retire',{method:'POST'});setNotice('Version retired. Existing adopted roles were not modified.');await load(String(selected?.id));setSelectedVersionId(String(version.id))}
  catch(e:any){setError(e.message||'Could not retire version')}
  finally {setBusy(false)}
 }

 return <section className="role-designer">
  <header className="role-designer-hero">
   <div><span className="role-designer-eyebrow"><ShieldCheck size={14}/> PLATFORM GOVERNANCE · DEVELOPER ONLY</span><h2>Role template designer</h2><p>Define reusable role templates for schools, colleges, universities and other institutions. Institution teams can only adopt published Developer-approved policies.</p></div>
   <button className="primary" type="button" onClick={()=>{setShowCreate(true);setError('');setNotice('')}}><Plus size={16}/> New role template</button>
  </header>
  {error&&<div className="role-designer-alert error" role="alert"><CircleAlert size={16}/><span>{error}</span><button type="button" onClick={()=>setError('')}><X size={15}/></button></div>}
  {notice&&<div className="role-designer-alert success" role="status"><CheckCircle2 size={16}/><span>{notice}</span><button type="button" onClick={()=>setNotice('')}><X size={15}/></button></div>}
  <div className="role-designer-layout">
   <aside className="role-designer-list">
    <div className="role-designer-list-head"><div><h3>Master templates</h3><p>{templates.length} template(s)</p></div><button type="button" className="secondary compact" onClick={()=>void load()} disabled={busy} aria-label="Refresh templates"><RefreshCw size={15}/></button></div>
    {templates.map(item=><button type="button" key={item.id} className={'role-template-option '+(selectedId===String(item.id)?'active':'')} onClick={()=>{setSelectedId(String(item.id));setSelectedVersionId(String(item.versions?.[0]?.id||''));setShowVersionEditor(false);setError('');setNotice('')}}><span className="role-template-option-icon"><Tag size={16}/></span><span className="role-template-option-copy"><strong>{item.name}</strong><small>{item.template_key} · {item.category}</small></span><span className={'role-designer-status '+(item.is_active?'published':'paused')}>{item.is_active?'Active':'Paused'}</span></button>)}
    {!templates.length&&!busy&&<div className="role-designer-empty"><Layers3 size={25}/><strong>No role templates yet</strong><span>Create your first master template to begin.</span></div>}
    {busy&&!templates.length&&<div className="role-designer-empty">Loading role templates…</div>}
   </aside>
   <main className="role-designer-detail">
    {!selected?<div className="role-designer-empty large"><ShieldCheck size={32}/><strong>Build your role library</strong><span>Create a role template, then add a version with institution types, modules, actions and data scopes.</span><button className="primary" type="button" onClick={()=>setShowCreate(true)}>Create first template</button></div>:<>
     <div className="role-designer-detail-head"><div><span className="role-designer-eyebrow">MASTER ROLE TEMPLATE</span><h3>{selected.name}</h3><p>{selected.description||'No description added.'}</p><small>Key: <code>{selected.template_key}</code> · Category: {selected.category}</small></div><div className="role-designer-detail-actions"><span className={'role-designer-status '+(selected.is_active?'published':'paused')}>{selected.is_active?'Active':'Paused'}</span><button className="secondary compact" type="button" onClick={updateTemplateActive} disabled={busy}>{selected.is_active?'Pause template':'Reactivate template'}</button></div></div>
     <div className="role-designer-version-heading"><div><h4>Version history</h4><p>Drafts can be edited. Published and retired policy is immutable.</p></div><button className="primary" type="button" onClick={()=>startVersion()} disabled={!selected.is_active||busy}><Plus size={15}/> New version</button></div>
     <div className="role-version-list">{versions.map(version=><article className={'role-version-card '+(selectedVersion?.id===version.id?'selected':'')} key={version.id}><button type="button" className="role-version-main" onClick={()=>setSelectedVersionId(String(version.id))}><span className="role-version-number">v{version.version_number}</span><span className="role-version-copy"><strong>{version.change_summary||'Policy update'}</strong><small>{version.institution_types.map(key=>catalog.institution_types.find(item=>item.key===key)?.label||key).join(' · ')}</small></span><span className={'role-designer-status '+version.status}>{version.status}</span></button><div className="role-version-actions">{version.status==='draft'&&<><button className="secondary compact" type="button" onClick={()=>startVersion(version)} disabled={busy}>Edit draft</button><button className="primary compact" type="button" onClick={()=>void publishVersion(version)} disabled={busy}>Publish</button></>}{version.status==='published'&&<button className="secondary compact" type="button" onClick={()=>void retireVersion(version)} disabled={busy}>Retire version</button>}</div></article>)}
      {!versions.length&&<div className="role-designer-empty">No versions yet. Create the first draft to configure this role.</div>}
     </div>
     {selectedVersion&&<section className="role-version-preview"><div><h4>Version {selectedVersion.version_number} · {selectedVersion.status}</h4><p>{selectedVersion.change_summary}</p></div><div className="role-version-summary"><span><strong>{selectedVersion.permissions.reduce((sum,item)=>sum+item.actions.length,0)}</strong> action grants</span><span><strong>{selectedVersion.permissions.length}</strong> modules</span><span><strong>{selectedVersion.institution_types.length}</strong> institution types</span></div><div className="role-policy-preview">{selectedVersion.permissions.map(item=><div key={item.module_key}><strong>{availableModules.find(module=>module.key===item.module_key)?.label||item.module_key}</strong><span>{item.actions.join(' · ')}</span><small>Scope: {scopes.find(([key])=>key===item.scope)?.[1]||item.scope}</small></div>)}</div></section>}
    </>}
   </main>
  </div>
  {showCreate&&<div className="role-designer-modal-backdrop" role="presentation"><form className="role-designer-modal" onSubmit={createTemplate}><div className="role-designer-modal-head"><div><span className="role-designer-eyebrow">NEW MASTER TEMPLATE</span><h3>Create role template</h3></div><button type="button" className="icon-button" onClick={()=>setShowCreate(false)} aria-label="Close"><X size={18}/></button></div><div className="role-designer-form-grid"><label>Template key<input required minLength={2} maxLength={80} pattern="[a-z0-9][a-z0-9_-]*" value={templateKey} onChange={e=>setTemplateKey(e.target.value.toLowerCase().replace(/\s+/g,'-'))} placeholder="e.g. school-academic-lead"/></label><label>Display name<input required minLength={2} maxLength={120} value={name} onChange={e=>setName(e.target.value)} placeholder="Academic Coordinator"/></label><label>Category<input required maxLength={60} value={category} onChange={e=>setCategory(e.target.value)} placeholder="academic"/></label><label className="wide">Description<textarea maxLength={4000} value={description} onChange={e=>setDescription(e.target.value)} placeholder="Describe the responsibilities this role is designed for."/></label></div><div className="role-designer-modal-actions"><button type="button" className="secondary" onClick={()=>setShowCreate(false)}>Cancel</button><button className="primary" disabled={busy}><Save size={15}/> Create template</button></div></form></div>}
  {showVersionEditor&&selected&&<div className="role-designer-modal-backdrop" role="presentation"><form className="role-designer-modal role-designer-version-modal" onSubmit={saveVersion}><div className="role-designer-modal-head"><div><span className="role-designer-eyebrow">{editingDraft?'EDIT DRAFT':'NEW DRAFT VERSION'}</span><h3>{editingDraft?'Edit draft policy':'Create version for '+selected.name}</h3></div><button type="button" className="icon-button" onClick={()=>setShowVersionEditor(false)} aria-label="Close"><X size={18}/></button></div><label className="role-designer-summary-field">Change summary<input required minLength={1} maxLength={2000} value={changeSummary} onChange={e=>setChangeSummary(e.target.value)}/></label><div className="role-designer-subsection"><h4>Institution types</h4><p>Choose every institution type this template supports. Each selected module must be available to all selected types.</p><div className="role-designer-check-grid">{catalog.institution_types.map(item=><label key={item.key}><input type="checkbox" checked={institutionTypes.includes(item.key)} onChange={()=>toggleInstitutionType(item.key)}/>{item.label}</label>)}</div></div><div className="role-designer-subsection"><div className="role-designer-module-head"><div><h4>Module permissions</h4><p>{enabledActionCount} action grant(s) selected · Platform-only modules are excluded.</p></div><button type="button" className="secondary compact" onClick={()=>setPermissions([])}>Clear all</button></div><div className="role-designer-permission-list">{availableModules.map(module=>{const entry=permissions.find(item=>item.module_key===module.key);const allowed=module.institution_types.length?module.institution_types:catalog.institution_types.map(item=>item.key);const incompatible=institutionTypes.length>0&&!institutionTypes.every(type=>allowed.includes(type));return <article className={'role-designer-module '+(entry?'enabled':'')} key={module.key}><div className="role-designer-module-title"><div><strong>{module.label}</strong><small>{module.description}</small></div><span>{module.category}</span></div>{incompatible&&<p className="role-designer-warning">Not available for every selected institution type.</p>}<div className="role-designer-actions-grid">{module.actions.map(action=><label key={action}><input type="checkbox" disabled={incompatible} checked={Boolean(entry?.actions.includes(action))} onChange={e=>togglePermission(module.key,action,e.target.checked)}/>{action}</label>)}</div>{entry&&<label className="role-designer-scope">Data scope<select value={entry.scope} onChange={e=>setScope(module.key,e.target.value)}>{scopes.map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>}</article>})}</div></div><div className="role-designer-modal-actions"><button type="button" className="secondary" onClick={()=>setShowVersionEditor(false)}>Cancel</button><button className="primary" disabled={busy||!institutionTypes.length||!permissions.length}><Save size={15}/> Save draft</button></div></form></div>}
 </section>
}
