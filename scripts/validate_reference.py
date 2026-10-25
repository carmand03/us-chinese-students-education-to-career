"""Independent pandas references for the JavaScript selection and graph engines."""
import json,random
import pandas as pd
def prepare_reference(root,people,education,jobs,three_nodes,projection_nodes,summary):
    scenarios=[]
    def add(name,filters=None,basis='study_overlap',lo=1876,hi=1944,unknown=True):
        filters=filters or {}
        p=people.copy()
        for key,col in [('person','NameID'),('gender','gender')]:
            if key in filters:p=p[p[col].isin(filters[key])]
        if basis!='education_year':
            a=p.study_start if basis=='study_overlap' else p[basis]
            b=p.study_end if basis=='study_overlap' else a
            keep=(a<=hi)&(b>=lo) if basis=='study_overlap' else (a>=lo)&(a<=hi)
            if unknown:keep=keep|a.isna()|b.isna()
            p=p[keep]
        e=education[education.NameID.isin(p.NameID)]
        j=jobs[jobs.NameID.isin(p.NameID)]
        for col in ['university','university_country','discipline','education_level']:
            if col in filters:e=e[e[col].isin(filters[col])]
        for col in ['employer','employer_country','sector','level','status']:
            if col in filters:j=j[j[col].isin(filters[col])]
        if basis=='education_year':
            keep=e.year.between(lo,hi)
            if unknown:keep=keep|e.year.isna()
            e=e[keep]
        ids=set(e.loc[e.university.ne('Unknown'),'NameID'])&set(j.loc[j.employer.ne('Unknown'),'NameID'])
        e=e[e.NameID.isin(ids)&e.university.ne('Unknown')];j=j[j.NameID.isin(ids)&j.employer.ne('Unknown')]
        pairs={}
        eu=e.groupby('NameID').university.agg(set).to_dict();ej=j.groupby('NameID').employer.agg(set).to_dict()
        for person in ids:
            for u in eu[person]:
                for employer in ej[person]:pairs.setdefault((u,employer),set()).add(person)
        sankey=[{'source':'University: '+u,'target':'Employer: '+employer,'individuals':len(ps),'NameIDs':sorted(ps)} for (u,employer),ps in sorted(pairs.items())]
        from flow_reference import build_flow_reference
        flows,coverage=build_flow_reference(p.loc[p.NameID.isin(ids)],e,j)
        scenarios.append({'name':name,'filters':filters,'period':{'basis':basis,'min':lo,'max':hi,'unknown':unknown},'people':sorted(ids),'education':sorted(e.education_id),'jobs':sorted(j.record_id),'sankey':sankey,'map_flows':flows.to_dict('records'),'map_coverage':coverage})
    add('all')
    add('past only',{'status':['Past']});add('current only',{'status':['Current']})
    add('past and current',{'status':['Past','Current']});add('empty appointment status',{'status':[]})
    add('female',{'gender':['F']});add('male',{'gender':['M']})
    add('different countries',{'university_country':['China'],'employer_country':['United States']})
    add('multiple countries',{'university_country':['China','United States'],'employer_country':['China','United States']})
    add('multiple sectors and levels',{'sector':['Academic / education','Government / public administration'],'level':['senior','mid-level']})
    add('university and discipline coupling',{'university':['University of Michigan'],'discipline':['Chemistry']})
    add('university and education-level coupling',{'university':['University of Michigan'],'education_level':['Master','Doctor']})
    add('known discipline only',{'discipline':sorted(set(education.discipline)-{'Unknown'})})
    add('unknown discipline',{'discipline':['Unknown']})
    add('unknown education level',{'education_level':['Unknown']})
    add('multiple education levels',{'education_level':['Bachelor','Master']})
    add('empty education level',{'education_level':[]})
    add('unknown university',{'university':['Unknown']});add('unknown employer',{'employer':['Unknown']})
    add('known birth years',basis='birth_year',unknown=False)
    add('birth decade incl unknown',basis='birth_year',lo=1910,hi=1919)
    add('birth decade known',basis='birth_year',lo=1910,hi=1919,unknown=False)
    add('single year study overlap',basis='study_overlap',lo=1940,hi=1940,unknown=False)
    add('study start',basis='study_start',lo=1930,hi=1939,unknown=False)
    add('study end',basis='study_end',lo=1943,hi=1944,unknown=False)
    add('record year includes unknown',basis='education_year',lo=1943,hi=1944)
    add('record year known',basis='education_year',lo=1943,hi=1944,unknown=False)
    add('unknown span only',basis='study_overlap',lo=2000,hi=2001)
    add('unknown record year only',basis='education_year',lo=2000,hi=2001)
    random.seed(42)
    for i in range(10):
        cols=random.sample(['status','employer_country','sector','level'],2)
        filters={c:random.sample(sorted(jobs[c].unique()),min(2,jobs[c].nunique())) for c in cols}
        add(f'combined {i}',filters,basis=random.choice(['birth_year','study_overlap','education_year']),lo=1910 if i%2 else 1935,hi=1943,unknown=bool(i%2))
    two={}
    for role in ['university','employer']:
        two[role]=pd.read_csv(root/'tables'/f'person_{role}_nodes.csv').to_dict('records')
    data={'scenarios':scenarios,'three_nodes':three_nodes.to_dict('records'),'three_edges':pd.read_csv(root/'tables/three_mode_edges.csv').to_dict('records'),'two_nodes':two,'projection_nodes':projection_nodes.to_dict('records'),'projection_edges':pd.read_csv(root/'tables/university_employer_edges.csv').to_dict('records'),'summary':summary}
    (root/'reference_cases.json').write_text(json.dumps(data,ensure_ascii=False,allow_nan=False))
