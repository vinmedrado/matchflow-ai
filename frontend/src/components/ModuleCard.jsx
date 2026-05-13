export default function ModuleCard({title,desc,status='Preparado'}){return <div className="module-card"><span>{status}</span><h3>{title}</h3><p>{desc}</p></div>}
