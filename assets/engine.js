/* Pure data functions shared by the HTML exports and independent Node.js checks. */
'use strict';
const EducationCareer=(()=>{
 const UNKNOWN='Unknown';
 const unique=xs=>[...new Set(xs)].sort((a,b)=>String(a).localeCompare(String(b)));
 const allows=(filters,key,value)=>!Object.hasOwn(filters,key)||filters[key].includes(String(value??UNKNOWN));
 function yearOK(a,b,p,interval=false){if(a==null||b==null)return p.unknown;return interval?a<=p.max&&b>=p.min:a>=p.min&&a<=p.max;}
 function select(data,filters={},period={basis:'study_overlap',min:1876,max:1944,unknown:true}){
  const persons=data.people.filter(p=>allows(filters,'person',p.NameID)&&allows(filters,'gender',p.gender)&&(period.basis==='education_year'||yearOK(period.basis==='study_overlap'?p.study_start:p[period.basis],period.basis==='study_overlap'?p.study_end:p[period.basis],period,period.basis==='study_overlap')));
  const allowed=new Set(persons.map(p=>p.NameID));
  let education=data.education.filter(e=>allowed.has(e.NameID)&&['university','university_country','education_level','discipline'].every(k=>allows(filters,k,e[k]))&&(period.basis!=='education_year'||yearOK(e.year,e.year,period)));
  let jobs=data.jobs.filter(j=>allowed.has(j.NameID)&&['employer','employer_country','sector','level','status'].every(k=>allows(filters,k,j[k])));
  const ep=new Set(education.filter(e=>e.university!==UNKNOWN).map(e=>e.NameID)),jp=new Set(jobs.filter(j=>j.employer!==UNKNOWN).map(j=>j.NameID));
  const eligible=new Set([...ep].filter(p=>jp.has(p)));
  const matchedEducation=education.length,matchedJobs=jobs.length;
  const unknownUniversities=education.filter(e=>e.university===UNKNOWN).length,unknownEmployers=jobs.filter(j=>j.employer===UNKNOWN).length;
  education=education.filter(e=>eligible.has(e.NameID)&&e.university!==UNKNOWN);
  jobs=jobs.filter(j=>eligible.has(j.NameID)&&j.employer!==UNKNOWN);
  return {people:persons.filter(p=>eligible.has(p.NameID)),education,jobs,matchedEducation,matchedJobs,unknownUniversities,unknownEmployers};
 }
 function affiliations(selection){
  const m=new Map(selection.people.map(p=>[p.NameID,{person:p,universities:new Set(),employers:new Set(),education:[],jobs:[]}]));
  selection.education.forEach(e=>{const p=m.get(e.NameID);p.universities.add(e.university);p.education.push(e);});
  selection.jobs.forEach(j=>{const p=m.get(j.NameID);p.employers.add(j.employer);p.jobs.push(j);});
  return m;
 }
 function metrics(nodes,edges,denominator){
  const deg=new Map(nodes.map(n=>[n.id,0])),strength=new Map(nodes.map(n=>[n.id,0]));
  edges.forEach(e=>{deg.set(e.from,deg.get(e.from)+1);deg.set(e.to,deg.get(e.to)+1);strength.set(e.from,strength.get(e.from)+e.weight);strength.set(e.to,strength.get(e.to)+e.weight);});
  return {nodes:nodes.map(n=>({...n,degree:deg.get(n.id),centrality:denominator(n)?deg.get(n.id)/denominator(n):0,strength:strength.get(n.id)})),edges};
 }
 function personNetwork(selection,mode='three'){
  const m=affiliations(selection),universities=unique(selection.education.map(e=>e.university)),employers=unique(selection.jobs.map(j=>j.employer));
  let nodes=selection.people.map(p=>({id:'p:'+p.NameID,label:p.label,kind:'person',NameID:p.NameID})),edges=[];
  if(mode!=='employers')nodes.push(...universities.map(u=>({id:'u:'+u,label:u,kind:'university'})));
  if(mode!=='universities')nodes.push(...employers.map(e=>({id:'e:'+e,label:e,kind:'employer'})));
  m.forEach((r,p)=>{
   if(mode!=='employers')r.universities.forEach(u=>edges.push({from:'p:'+p,to:'u:'+u,weight:1,relation:'education',record_count:r.education.filter(e=>e.university===u).length}));
   if(mode!=='universities')r.employers.forEach(e=>edges.push({from:'p:'+p,to:'e:'+e,weight:1,relation:'employment',record_count:r.jobs.filter(j=>j.employer===e).length}));
  });
  return metrics(nodes,edges,n=>n.kind==='person'?(mode==='three'?universities.length+employers.length:mode==='universities'?universities.length:employers.length):selection.people.length);
 }
 function projection(selection){
  const m=affiliations(selection),universities=unique(selection.education.map(e=>e.university)),employers=unique(selection.jobs.map(j=>j.employer)),pairs=new Map();
  m.forEach((r,p)=>r.universities.forEach(u=>r.employers.forEach(e=>{let key=JSON.stringify([u,e]);if(!pairs.has(key))pairs.set(key,{from:'u:'+u,to:'e:'+e,university:u,employer:e,people:[]});pairs.get(key).people.push(p);})));
  const nodes=[...universities.map(u=>({id:'u:'+u,label:u,kind:'university'})),...employers.map(e=>({id:'e:'+e,label:e,kind:'employer'}))];
  return metrics(nodes,[...pairs.values()].map(e=>({...e,weight:e.people.length})),n=>n.kind==='university'?employers.length:universities.length);
 }
 function threshold(graph,min=0,max=1){const nodes=graph.nodes.filter(n=>n.centrality>=min&&n.centrality<=max),ids=new Set(nodes.map(n=>n.id));return {nodes,edges:graph.edges.filter(e=>ids.has(e.from)&&ids.has(e.to))};}
 function sankey(selection,top=0){
  const p=projection(selection),labels=new Map(selection.people.map(r=>[r.NameID,r.label])),totals={university:new Map(),employer:new Map()};
  for(const e of p.edges)for(const [role,key] of [['university',e.university],['employer',e.employer]]){if(!totals[role].has(key))totals[role].set(key,new Set());e.people.forEach(id=>totals[role].get(key).add(id));}
  const keep={};for(const role of ['university','employer'])keep[role]=new Set([...totals[role]].sort((a,b)=>b[1].size-a[1].size||a[0].localeCompare(b[0])).slice(0,top||Infinity).map(x=>x[0]));
  const links=new Map();p.edges.forEach(e=>{const source='University: '+(keep.university.has(e.university)?e.university:'[Other universities]'),target='Employer: '+(keep.employer.has(e.employer)?e.employer:'[Other employers]'),key=JSON.stringify([source,target]);if(!links.has(key))links.set(key,{source,target,people:new Set()});e.people.forEach(id=>links.get(key).people.add(id));});
  return {links:[...links.values()].map(l=>({source:l.source,target:l.target,weight:l.people.size,individuals:l.people.size,NameIDs:[...l.people].sort(),individual_names:[...l.people].sort().map(id=>labels.get(id)||id)})).sort((a,b)=>b.individuals-a.individuals||a.source.localeCompare(b.source)||a.target.localeCompare(b.target)),people:selection.people.length,stages:2};
 }
 function mapFlows(selection){
  const valid=r=>r.lat!=null&&r.lon!=null&&Number.isFinite(r.lat)&&Number.isFinite(r.lon)&&Math.abs(r.lat)<=90&&Math.abs(r.lon)<=180;
  const places={education:new Map(),work:new Map()},personPlaces=new Map(selection.people.map(p=>[p.NameID,{education:new Set(),work:new Set()}]));
  function add(row,role,institution,country){
   if(!valid(row))return;
   const city=row.city||UNKNOWN,province=row.province||UNKNOWN;
   const key=JSON.stringify(city===UNKNOWN?[country,province,city,institution,row.lat,row.lon]:[country,province,city]);
   if(!places[role].has(key))places[role].set(key,{key,country,province,city,coordinates:new Map(),institutions:new Set(),people:new Set()});
   const g=places[role].get(key);g.coordinates.set(JSON.stringify([row.lat,row.lon]),[row.lat,row.lon]);g.institutions.add(institution);g.people.add(row.NameID);personPlaces.get(row.NameID)[role].add(key);
  }
  selection.education.forEach(e=>add(e,'education',e.university,e.university_country));selection.jobs.forEach(j=>add(j,'work',j.employer,j.employer_country));
  for(const role of ['education','work'])for(const p of places[role].values()){const coords=[...p.coordinates.values()];p.lat=coords.reduce((x,c)=>x+c[0],0)/coords.length;p.lon=coords.reduce((x,c)=>x+c[1],0)/coords.length;p.label=[p.city===UNKNOWN?'Unspecified city ('+[...p.institutions].join('; ')+')':p.city,p.province,p.country].join(', ');}
  const links=new Map();personPlaces.forEach((r,id)=>r.education.forEach(a=>r.work.forEach(b=>{const key=JSON.stringify([a,b]);if(!links.has(key))links.set(key,{source:a,target:b,people:new Set()});links.get(key).people.add(id);})));const names=new Map(selection.people.map(p=>[p.NameID,p.label]));
  const flows=[...links.values()].map(l=>{const a=places.education.get(l.source),b=places.work.get(l.target),ids=[...l.people].sort();return {education_place:a.label,work_place:b.label,education_country:a.country,work_country:b.country,education_city:a.city,work_city:b.city,education_lat:a.lat,education_lon:a.lon,work_lat:b.lat,work_lon:b.lon,individuals:ids.length,NameIDs:ids,individual_names:ids.map(id=>names.get(id)||id),source:l.source,target:l.target};}).sort((a,b)=>b.individuals-a.individuals||a.source.localeCompare(b.source)||a.target.localeCompare(b.target));
  const endpointPeople={education:new Map(),work:new Map()};links.forEach(l=>{for(const [role,key] of [['education',l.source],['work',l.target]]){if(!endpointPeople[role].has(key))endpointPeople[role].set(key,new Set());l.people.forEach(id=>endpointPeople[role].get(key).add(id));}});const endpoints={};for(const role of ['education','work'])endpoints[role]=[...places[role].values()].filter(p=>endpointPeople[role].has(p.key)).map(p=>({key:p.key,label:p.label,lat:p.lat,lon:p.lon,individuals:endpointPeople[role].get(p.key).size}));
  return {flows,endpoints,people:selection.people.filter(p=>{const r=personPlaces.get(p.NameID);return r.education.size&&r.work.size;}).length,educationRecordsMapped:selection.education.filter(valid).length,jobRecordsMapped:selection.jobs.filter(valid).length};
 }
 // Split geographic association lines at the antimeridian using the shorter longitude span.
 function flowSegments(a,b){let end=b[1],delta=end-a[1];if(delta>180)end-=360;else if(delta< -180)end+=360;if(end<=180&&end>=-180)return [[a,[b[0],end]]];const boundary=end>180?180:-180,t=(boundary-a[1])/(end-a[1]),lat=a[0]+t*(b[0]-a[0]);return [[a,[lat,boundary]],[[lat,-boundary],b]];}
 return {select,affiliations,personNetwork,projection,threshold,sankey,mapFlows,flowSegments};
})();
if(typeof module!=='undefined')module.exports=EducationCareer;
