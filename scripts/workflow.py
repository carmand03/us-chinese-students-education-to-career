"""Separate combined education/career workflow. Run in this directory."""
# %% 1. Read and validate the three source tables
from pathlib import Path
import json, hashlib, itertools
import pandas as pd
import numpy as np
import networkx as nx

ROOT=Path.cwd()
if not (ROOT/'data/main.csv').exists(): ROOT=Path(__file__).resolve().parent
TABLES=ROOT/'tables'; TABLES.mkdir(exist_ok=True)
UNKNOWN='Unknown'
def read(name,sep=','):
    d=pd.read_csv(ROOT/'data'/name,sep=sep)
    d=d.loc[:,~d.columns.str.startswith('Unnamed:')].copy()
    for c in d.select_dtypes('object'): d[c]=d[c].str.strip().replace('',np.nan)
    return d
main=read('main.csv',';');education=read('educ.csv');career=read('career.csv',';')
assert main.NameID.is_unique and main.NameID.notna().all()
assert career.record_id.is_unique and career.record_id.notna().all()
assert set(education.NameID)<=set(main.NameID)
assert set(career.NameID)<=set(main.NameID)
pd.DataFrame([{'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted((ROOT/'data').glob('*.csv'))]).to_csv(TABLES/'source_manifest.csv',index=False)
print(f'{len(main):,} people; {len(education):,} education rows; {len(career):,} appointment rows.')

# %% 2. Person attributes and normalized education and employment records
education['Year']=pd.to_numeric(education.Year,errors='coerce')
span=education.groupby('NameID').Year.agg(study_start='min',study_end='max')
people=main[['NameID','Gender','birth_year','Birth_province_py_st']].merge(span,on='NameID',how='left',validate='one_to_one').rename(columns={'Gender':'gender'})
names=career.groupby('NameID').NameFull.first().combine_first(education.groupby('NameID').FullName_PY.first())
people['label']=people.NameID.map(lambda p:p+' · '+str(names.get(p,p)))
people.gender=people.gender.fillna(UNKNOWN)
people['birth_decade']=people.birth_year.map(lambda y:f'{int(y)//10*10}s' if pd.notna(y) else UNKNOWN)
people['study_start_decade']=people.study_start.map(lambda y:f'{int(y)//10*10}s' if pd.notna(y) else UNKNOWN)
edu=education[['NameID','University_clean','University','Country','discipline','Degree','Level','Year','City','Province_State']].copy()
edu['lat']=education.latitude_revised.combine_first(education.Latitude)
edu['lon']=education.longitude_revised.combine_first(education.Longitude)
edu['education_id']=[f'ED{i+1:05d}' for i in range(len(edu))]
edu['university_label_source']=np.where(edu.University_clean.notna(),'University_clean',np.where(edu.University.notna(),'University','missing'))
edu['University_clean']=edu.University_clean.combine_first(edu.University)
edu=edu.drop(columns='University').rename(columns={'University_clean':'university','Country':'university_country','Degree':'degree','Level':'education_level','Year':'year','City':'city','Province_State':'province'})
jobs=career[['record_id','NameID','Institution_normalized','Country_completed','institution_sector','advancement_level_valid','appointment_status_normalized','Position_normalized']].rename(columns={'Institution_normalized':'employer','Country_completed':'employer_country','institution_sector':'sector','advancement_level_valid':'level','appointment_status_normalized':'status','Position_normalized':'position'})
jobs['city']=career.City_completed;jobs['province']=career.State_province_completed
jobs['lat']=career.latitude;jobs['lon']=career.longitude
for d,cols in [(edu,['university','university_country','discipline','degree','education_level','city','province']),(jobs,['employer','employer_country','sector','level','status','position','city','province'])]:
    for c in cols:d[c]=d[c].fillna(UNKNOWN)
for d in [edu,jobs]:d['valid_coordinates']=d.lat.between(-90,90)&d.lon.between(-180,180)
edu.university_country=edu.university_country.replace({'USA':'United States'})
jobs.employer_country=jobs.employer_country.replace({'USA':'United States'})
jobs.status=jobs.status.replace({'Former':'Past'})
def export(d,name):d.to_csv(TABLES/(name+'.csv'),index=False,encoding='utf-8-sig')
export(people,'students_synthetic');export(edu,'education_normalized');export(jobs,'employment_normalized')
export(edu.merge(people,on='NameID',validate='many_to_one'),'education_with_person_attributes')
export(jobs.merge(people,on='NameID',validate='many_to_one'),'employment_with_person_attributes')
export(edu.loc[edu.university_label_source.ne('University_clean')],'university_label_fallbacks')
print('University labels prefer University_clean, then University. Unknown institution labels cannot identify a network node.')

# %% 3. Matched population, affiliation tables and three/two mode graphs
known_edu=edu.loc[edu.university.ne(UNKNOWN)]
known_jobs=jobs.loc[jobs.employer.ne(UNKNOWN)]
eligible=sorted(set(known_edu.NameID)&set(known_jobs.NameID))
em=known_edu.loc[known_edu.NameID.isin(eligible)].copy()
jm=known_jobs.loc[known_jobs.NameID.isin(eligible)].copy()
university_aff=em[['NameID','university']].drop_duplicates()
employer_aff=jm[['NameID','employer']].drop_duplicates()
export(university_aff,'individual_university_affiliations');export(employer_aff,'individual_employer_affiliations')
coverage=people[['NameID','gender']].copy()
coverage['has_known_university']=coverage.NameID.isin(known_edu.NameID)
coverage['has_known_employer']=coverage.NameID.isin(known_jobs.NameID)
coverage['eligible_for_combined_views']=coverage.NameID.isin(eligible)
export(coverage,'person_coverage')
universities=sorted(university_aff.university.unique());employers=sorted(employer_aff.employer.unique())
G=nx.Graph()
G.add_nodes_from(('p:'+p,{'kind':'person'}) for p in eligible)
G.add_nodes_from(('u:'+u,{'kind':'university'}) for u in universities)
G.add_nodes_from(('e:'+e,{'kind':'employer'}) for e in employers)
G.add_edges_from(('p:'+r.NameID,'u:'+r.university) for r in university_aff.itertuples())
G.add_edges_from(('p:'+r.NameID,'e:'+r.employer) for r in employer_aff.itertuples())
def graph_tables(graph,counts):
    nodes=[]
    for n,d in sorted(graph.nodes(data=True)):
        denominator=counts['university']+counts['employer'] if d['kind']=='person' else counts['person']
        nodes.append({'id':n,'kind':d['kind'],'degree':graph.degree(n),'centrality':graph.degree(n)/denominator if denominator else 0})
    return pd.DataFrame(nodes),pd.DataFrame([{'source':a,'target':b,'weight':1} for a,b in graph.edges()])
sizes={'person':len(eligible),'university':len(universities),'employer':len(employers)}
nodes,edges=graph_tables(G,sizes);export(nodes,'three_mode_nodes');export(edges,'three_mode_edges')
for kind in ['university','employer']:
    graph=G.subgraph([n for n,d in G.nodes(data=True) if d['kind'] in ['person',kind]]).copy()
    n,e=graph_tables(graph,{'person':len(eligible),'university':len(universities) if kind=='university' else 0,'employer':len(employers) if kind=='employer' else 0})
    export(n,'person_'+kind+'_nodes');export(e,'person_'+kind+'_edges')
summary={'source_people':len(people),'eligible_people':len(eligible),'universities':len(universities),'employers':len(employers),'education_records_retained':len(em),'appointments_retained':len(jm),'three_mode_nodes':G.number_of_nodes(),'three_mode_edges':G.number_of_edges(),'unknown_university_records':int(edu.university.eq(UNKNOWN).sum()),'unknown_employer_records':int(jobs.employer.eq(UNKNOWN).sum())}
print(json.dumps(summary,indent=2))

# %% 4. University/employer projection: distinct shared individuals
# The affiliation cross-product is explicit and labelled. It is not a raw-record join.
pair_people={}
u_by=university_aff.groupby('NameID').university.agg(list)
e_by=employer_aff.groupby('NameID').employer.agg(list)
links_by_person=[]
for person in eligible:
    for u,e in itertools.product(u_by[person],e_by[person]):
        pair_people.setdefault((u,e),set()).add(person)
        links_by_person.append({'NameID':person,'university':u,'employer':e,'allocated_student_weight':1/(len(u_by[person])*len(e_by[person]))})
pair_rows=[{'university':u,'employer':e,'shared_students':len(ps),'NameIDs':'|'.join(sorted(ps))} for (u,e),ps in sorted(pair_people.items())]
projection_edges=pd.DataFrame(pair_rows)
P=nx.Graph()
P.add_nodes_from(('u:'+u,{'kind':'university'}) for u in universities)
P.add_nodes_from(('e:'+e,{'kind':'employer'}) for e in employers)
P.add_weighted_edges_from(('u:'+u,'e:'+e,len(ps)) for (u,e),ps in pair_people.items())
projection_nodes=pd.DataFrame([{'id':n,'label':n[2:],'kind':d['kind'],'degree':P.degree(n),'centrality':P.degree(n)/(len(employers) if d['kind']=='university' else len(universities)),'strength':P.degree(n,weight='weight')} for n,d in sorted(P.nodes(data=True))])
export(projection_nodes,'university_employer_nodes');export(projection_edges,'university_employer_edges')
export(pd.DataFrame(links_by_person),'university_employer_links_by_person')
summary['projection_edges']=P.number_of_edges()
print(f'{P.number_of_nodes():,} institution nodes and {P.number_of_edges():,} distinct university–employer pairs.')

# %% 5. Direct university-to-employer Sankey
labels=people.set_index('NameID').label.to_dict()
direct_links=pd.DataFrame([{'source':'University: '+u,'target':'Employer: '+e,'weight':len(ps),'individuals':len(ps),'NameIDs':json.dumps(sorted(ps),ensure_ascii=False),'individual_names':json.dumps([labels[p] for p in sorted(ps)],ensure_ascii=False)} for (u,e),ps in sorted(pair_people.items())])
export(direct_links,'sankey_direct_links')
for stale in ['sankey_individual_links.csv','sankey_education_detail_links.csv']:
    if (TABLES/stale).exists():(TABLES/stale).unlink()
print(f'Direct Sankey: {len(direct_links):,} university–employer pairs. Link weight is distinct bridging people; counts across pairs are not additive unique-person totals.')

# %% 6. Education-place to workplace flow map reference
from flow_reference import build_flow_reference
flow_rows,flow_coverage=build_flow_reference(people.loc[people.NameID.isin(eligible)],em,jm)
export(flow_rows,'education_work_city_flows')
export(em.loc[~em.valid_coordinates],'unmapped_education_records')
export(jm.loc[~jm.valid_coordinates],'unmapped_employment_records')
export(pd.DataFrame(flow_coverage.items(),columns=['metric','value']),'map_coverage')
summary.update(flow_coverage)
(ROOT/'assets/world_data.js').write_text('window.WORLD='+ (ROOT/'assets/world.geojson').read_text()+';',encoding='utf-8')
print(json.dumps(flow_coverage,indent=2))

# %% 7. Offline HTML exports and reference tests
def records(d):return json.loads(d.to_json(orient='records',force_ascii=False))
payload={'people':records(people),'education':records(edu),'jobs':records(jobs),'summary':summary}
(ROOT/'assets/combined_data.js').write_text('window.COMBINED='+json.dumps(payload,ensure_ascii=False,separators=(',',':'))+';',encoding='utf-8')
export(pd.DataFrame(summary.items(),columns=['metric','value']),'summary_metrics')
from render_combined import build_pages,write_methods
build_pages(ROOT);write_methods(ROOT,summary)
from validate_reference import prepare_reference
prepare_reference(ROOT,people,edu,jobs,nodes,projection_nodes,summary)
checks={'person_key_unique':people.NameID.is_unique,'education_rows_preserved':len(edu)==len(education),'appointment_rows_preserved':len(jobs)==len(career),'three_mode_nodes':G.number_of_nodes(),'three_mode_edges':G.number_of_edges(),'projection_nodes':P.number_of_nodes(),'projection_edges':P.number_of_edges(),'sankey_direct_pairs':len(direct_links),'map_people':flow_coverage['mapped_people']}
(ROOT/'validation.json').write_text(json.dumps(checks,indent=2))
print('Created networks, direct institution Sankey, education-to-work flow map and reproducible test references.')
