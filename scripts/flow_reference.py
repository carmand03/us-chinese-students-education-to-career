"""Independent Python reference for distinct-person education-city/work-city flows."""
import json
import pandas as pd
def build_flow_reference(people,education,jobs):
    records={'education':education,'work':jobs};places={};person_places={p:{'education':set(),'work':set()} for p in people.NameID}
    for role,df in records.items():
        for r in df.loc[df.valid_coordinates].itertuples():
            institution=r.university if role=='education' else r.employer
            country=r.university_country if role=='education' else r.employer_country
            key=(country,r.province,r.city) if r.city!='Unknown' else (country,r.province,r.city,institution,float(r.lat),float(r.lon))
            p=places.setdefault((role,key),{'coords':set(),'city':r.city,'province':r.province,'country':country,'institutions':set()})
            p['coords'].add((float(r.lat),float(r.lon)));p['institutions'].add(institution);person_places[r.NameID][role].add(key)
    pairs={};mapped_people=0
    for person,roles in person_places.items():
        if roles['education'] and roles['work']:mapped_people+=1
        for a in roles['education']:
            for b in roles['work']:pairs.setdefault((a,b),set()).add(person)
    names=people.set_index('NameID').label.to_dict()
    def location(role,key):
        p=places[(role,key)];coords=sorted(p['coords']);label=', '.join([p['city'] if p['city']!='Unknown' else 'Unspecified city ('+'; '.join(sorted(p['institutions']))+')',p['province'],p['country']])
        return label,sum(c[0] for c in coords)/len(coords),sum(c[1] for c in coords)/len(coords)
    rows=[]
    for (a,b),ids in pairs.items():
        al,alat,alon=location('education',a);bl,blat,blon=location('work',b)
        rows.append({'education_place':al,'work_place':bl,'education_lat':alat,'education_lon':alon,'work_lat':blat,'work_lon':blon,'individuals':len(ids),'NameIDs':json.dumps(sorted(ids),ensure_ascii=False),'individual_names':json.dumps([names[p] for p in sorted(ids)],ensure_ascii=False)})
    out=pd.DataFrame(rows,columns=['education_place','work_place','education_lat','education_lon','work_lat','work_lon','individuals','NameIDs','individual_names'])
    if len(out):out=out.sort_values(['individuals','education_place','work_place'],ascending=[False,True,True])
    coverage={'mapped_people':mapped_people,'mapped_city_pairs':len(rows),'mapped_education_records':int(education.valid_coordinates.sum()),'mapped_appointment_records':int(jobs.valid_coordinates.sum()),'unmapped_education_records':int((~education.valid_coordinates).sum()),'unmapped_appointment_records':int((~jobs.valid_coordinates).sum())}
    return out,coverage
