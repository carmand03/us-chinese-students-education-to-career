"""Portable, offline HTML authoring; libraries and data are embedded per export."""
from pathlib import Path
import re,html,json
VIEWS=[('people','Individuals, universities and employers','individual_institutions.html'),('projection','University–employer network','university_employer.html'),('sankey','Education institutions → employers','education_employment_sankey.html'),('map','Education-to-work flow map','education_work_flows.html')]
def build_pages(root):
    for view,title,file in VIEWS:
        nav=''.join(f'<a href="{f}" class="{"active" if v==view else ""}">{html.escape(t)}</a>' for v,t,f in VIEWS)
        def script(name):
            s=(root/'assets'/name).read_text()
            return '<script>'+re.sub(r'</script',r'<\\/script',s,flags=re.I)+'</script>'
        libraries=script('ui_helpers.js')+script('plotly.min.js' if view=='sankey' else 'leaflet.js' if view=='map' else 'vis-network.min.js')
        if view=='map':libraries='<style>'+(root/'assets/leaflet.css').read_text()+'</style>'+script('world_data.js')+libraries
        page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{(root/'assets/style.css').read_text()}</style>{script('combined_data.js')}{script('engine.js')}{libraries}</head>
<body data-view="{view}"><header><div><span class="eyebrow">EDUCATION AND HISTORICAL CAREERS</span><h1>{title}</h1><p>Linked through recorded individuals. Current appointment status refers to the historical source.</p></div><a href="methods.html">Methods, findings and files ↗</a></header><nav>{nav}</nav>
<div class="layout"><aside><div class="filterhead"><h2>Filter records</h2><button id="reset">Reset</button></div><p class="muted">Multiple choices within a filter use OR. Different filters use AND. All choices start selected.</p><div id="filters"></div><fieldset><legend>Period range</legend><label>Basis<select id="periodBasis"><option value="study_overlap">Full recorded study span overlaps</option><option value="study_start">First recorded study year</option><option value="study_end">Last recorded study year</option><option value="birth_year">Year of birth</option><option value="education_year">Matching education record year</option></select></label><div class="range"><label>From<input id="yearMin" type="number" value="1876"></label><label>To<input id="yearMax" type="number" value="1944"></label></div><label class="check"><input id="unknownYears" type="checkbox" checked> Include unknown years</label></fieldset><div id="special"></div><button id="apply" class="primary">Apply filters</button><p class="muted">University and employer country filters are independent. Institution/discipline/education-level filters match the same education row. A person needs a known university and employer after filters to enter these views.</p></aside><main><div id="kpis" class="kpis"></div><p id="notice" class="notice"></p><div id="viewControls" class="toolbar"></div><div id="visual"></div><div id="legend"></div><div id="detail"></div><footer>All data and libraries are embedded for offline use. Associations do not establish a sequence from education to employment. Study bounds are recorded years, not complete attendance dates.</footer></main></div>{script('app.js')}</body></html>'''
        (root/file).write_text(page)
    # A small entry point keeps the complete separate analysis easy to find.
    (root/'index.html').write_text((root/'individual_institutions.html').read_text())

def write_methods(root,s):
    methods=f'''# Combined education and career analysis

This is a separate analysis and notebook. Open index.html, or any of the four independently portable HTML exports. Each embeds its own data and required libraries; no server or internet connection is needed.

## Source and matched population

The source contains {s['source_people']:,} people. After requiring at least one known university and one known employer, the combined views include {s['eligible_people']:,} people, {s['universities']:,} university labels and {s['employers']:,} employer labels. There are {s['three_mode_edges']:,} distinct individual–institution affiliations and {s['projection_edges']:,} university–employer pairs linked by individuals. See tables/person_coverage.csv for people outside this matched population. Missing affiliations do not establish a lack of education or employment.

## Inputs and normalization

The original three CSVs are preserved in data/ with SHA-256 hashes in tables/source_manifest.csv. The main and career CSVs use semicolons; education uses commas. Blank trailing columns are removed and strings trimmed. NameID identifies individuals; record_id identifies appointment records. Stable education_id values identify education source rows in their original order. The synthetic student list uses birth year and gender from main, with the minimum/maximum nonmissing education Year across the full source. No raw education-to-appointment join is used to count appointments.

University identity uses University_clean when present, otherwise University. This explicit fallback is exported in university_label_fallbacks.csv. It retains useful raw labels where cleaned labels are missing, without additional fuzzy matching. Employer identity uses Institution_normalized at the parent institution level, not a department or branch. USA is standardized to United States, Former to Past, and missing categories to Unknown. University and employer roles remain separate even when their institution labels are identical; the same institution can legitimately be an education destination and an employer. Unknown institution labels remain in cleaned records but cannot identify graph nodes or Sankey institution endpoints. Unknown discipline, education degree level, sector, position level, status and countries remain selectable. The education filter uses the Level field as recorded (Bachelor, Master, Doctor, Doctorate, etc.); raw Degree is retained only in record exports. Doctor and Doctorate remain separate source categories.

## Filter semantics

Expand a filter and use its checkboxes; the search box narrows choices visually. All selects every choice and Clear selects none. Click Apply filters after changing a selection or range. Multiple choices within a field use OR, while fields use AND. Reset restores defaults. All appointment statuses includes Past, Current and Unknown; selecting Past and Current excludes Unknown. Current means current in the historical source, not today.

University, discipline, education degree level (Level) and university country must all match the same education row. Employer, employer country, sector, level and appointment status must match the same appointment row. This avoids assigning a discipline from one school to another school attended by the same person. The selectors operate on records first; the eligible person set is then the intersection of people retaining at least one known university and one known employer. Only matching education and appointment rows for those people form the visualizations. Selecting a university therefore keeps that university and qualifying people's matching employers, rather than all other universities those people attended. Different university and employer country selections allow cross-border links.

Birth-year and first/last-study-year filters select people. The full study span is always computed from all education records before any filters. The overlap condition is first year ≤ upper bound AND last year ≥ lower bound. It does not prove continuous attendance. The optional Matching education record year basis applies the range directly to education rows. Unknown years are included by default and can be excluded. In record-year mode this means unknown education Year; in person-span modes it means unknown person bounds. Select a birth or study cohort without treating it as an appointment date.

## Individuals, universities and employers

The three-mode graph links each person to each distinct matching university and each distinct matching employer. It contains no direct university–employer edges. The view selector also offers two-mode person–university and person–employer graphs, using the same jointly eligible population so views can be compared. Repeated education or appointment rows cannot create extra edges. Edge tooltips expose the count of supporting raw records; edge weight remains one distinct affiliation.

Mode-normalized degree centrality measures distinct neighbors divided by the number of possible neighbors in the permitted opposite modes. For a person in the three-mode graph, the denominator is university count + employer count; for universities and employers it is person count. In a two-mode person graph, the denominator for a person is the corresponding institution count. It is zero when no opposite nodes exist. Degree is also exported.

Centrality is recalculated after all record/period filters and the network-mode choice, before node thresholds. The range creates a displayed induced graph; retained nodes can become isolates. Tooltips and CSV exports retain these pre-threshold measures so the range has a stable meaning. Colors/shapes identify roles, and node size follows degree. Layout has a fixed random seed. Drag nodes, pan, zoom, locate a label or ID, and click nodes/edges for details. No nodes or edges are silently sampled.

## University–employer two-mode projection

Each individual links every distinct matching university to every distinct matching employer. This is an affiliation cross-product, not a dated school-to-job transition. One edge per university–employer pair is weighted by distinct shared NameIDs. Repeated source records do not inflate it. One person may support several pairs. The baseline pair-by-person table additionally allocates a total weight of one across that person's pairs, for researchers who need a fractional alternative. Interactive graph edge weights use integer shared-person counts.

Degree counts distinct institutions in the opposite mode. Centrality is university degree / number of matching employers, or employer degree / number of matching universities. Strength is the sum of incident shared-person edge weights. All three measures are recalculated after record filters and exported. The centrality threshold is then applied without recalculating the retained measures. Edge tooltips/clicks identify the shared people.

## Physics and network popups

Both networks have ongoing physics with a pace slider from 0.25× to 2× and Pause/Resume controls. Pace changes simulation time step and maximum node velocity, not the graph data or measures. Pausing explicitly stops the simulation and prevents pace adjustments from restarting it. Paused/running state and pace persist when filters or label settings change. Retained nodes reuse their positions across redraws. A settled layout can remain stationary with physics enabled; changing pace or resuming starts the simulation again. The status distinguishes settled, running and paused states. Tooltips use real text elements on separate lines, so HTML break tags do not appear literally and special characters are handled as text.

## Direct education-to-employer Sankey

Two stages link education institutions directly to employers. Discipline and degree are no longer stages; discipline and education degree level remain filters. Each university–employer link counts distinct bridging NameIDs after all active filters. A person with U universities and E employers can contribute once to each of U×E institution pairs. Repeated education or appointment records cannot increase a person's contribution to the same pair. Thus counts across pairs are not additive unique-person totals. Link hover text and CSV exports include the count, IDs and names. Node totals are sums of incident link counts (bridge participations), not unique people per institution.

All institutions are displayed by default. Top-20/top-40 options group other institutions. Each displayed grouped pair uses the union of bridging NameIDs, so one person is counted once even when several original pairs collapse into Other. All filters rebuild the links and counts. Centrality thresholds apply only to network nodes, not to the Sankey or map. Country, gender, discipline, education level, sector, status, position level and period filters remain available.

## Interactive education-to-work map

The flow map uses matching education and appointment records with valid coordinates. Education latitude/longitude prefer revised coordinates, then the original values. Workplace coordinates come directly from career. Missing coordinates are not inferred. Coverage counts show mapped records and people retaining at least one valid location on both sides; missing-coordinate records are exported separately and remain in the nongeographic analyses.

Links group education and work locations by country, province and city. Repeated records or different institutions within the same city cannot count the same person twice within a city-pair link. Unknown city labels with known coordinates are kept separate by institution and coordinates, rather than merged into a fictitious single city. Within a city, the reference position is the unweighted mean of distinct supplied venue-coordinate pairs under the current filters. It is not a verified city centroid. The city-pair CSV retains exact derived reference coordinates and bridging identities.

Line width scales with the square root of distinct people. Endpoint circle area scales with the number of distinct linked people at that endpoint, using radius proportional to square root(count). Blue circles mark education and teal circles employment; arrowheads show direction. Purple rings identify within-location links. Geographic lines use the shorter longitude span and split at the antimeridian to avoid drawing Pacific links across the wrong side of the world. All source filters apply to the map, including separate university/employer countries and education levels. Pan, zoom, hover/click flows, fit the map and export the current city-pair table. Natural Earth outlines and Leaflet are bundled for offline use; no online map tiles or geocoding requests are required. These are geographic associations, not observed travel paths or chronologically verified moves.

## Interpretation limits

The records do not contain appointment dates. A recorded degree may precede or follow a particular job. Neither graph links nor Sankey direction demonstrates that a qualification led to a job, a confirmed chronological transition, or a causal relationship. Educational discipline and degree are often missing; Unknown is retained rather than inferred. The analysis describes recorded affiliations in the matched population, not the employment rate of the full student population. Main-file gender and birth year are retained as recorded.

## Reproduce and verify

Use Python 3.12 with requirements.txt installed. Open education_career.ipynb in Jupyter and run all cells from this directory, or run python workflow.py. The notebook includes the full data preparation, graph/projection construction, Sankey calculations and HTML export workflow. render_combined.py writes the HTML shell; assets/engine.js contains the exact filter, graph and Sankey algorithms used by the browser, and assets/app.js provides the interface. These files and JavaScript libraries are bundled, so rebuilding HTML does not need an external download.

The notebook also runs independent pandas/NetworkX-to-JavaScript comparisons when Node.js is installed. Run node validate_engine.cjs to repeat them after python workflow.py. Tests cover simultaneous choices, empty selections, unknown years, raw education-year filtering, institution/discipline/education-level row coupling, repeated affiliations, role separation, graph degrees/centralities/weights, node thresholds, direct Sankey counts/grouping, map city-pair counts/coordinates, antimeridian splitting, and physics pause/resume/pace options. Validation JSON files record the results. The prior session's local-file browser preview was blocked by application security, so this analysis uses code/data checks without claiming a visual browser test.

## Exports

The tables folder contains the synthetic student list, normalized records, per-person attributes and coverage, distinct affiliations, three-mode and two-mode graph nodes/edges, university–employer pair weights with shared NameIDs, allocated pair-by-person weights, direct Sankey links, mapped city-pair flows, coordinate coverage and missing-location audits and source hashes. Matching education rows, appointment rows, visible graph nodes/edges and displayed Sankey links can also be downloaded after interactive filtering. Graph CSVs include zero-threshold baseline nodes and pre-threshold centralities. Complete source rows remain in the original CSVs.

Software: pandas, NumPy, NetworkX; vis-network 9.1.9, Plotly.js 2.35.2 and Leaflet 1.9.4. Country outlines use Natural Earth 1:110m reference geography (public domain), from https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_0_countries.geojson, bundled under assets/. JavaScript licenses are included in assets/. No external services receive student data.
'''
    (root/'README.txt').write_text(methods)
    parts=[]
    for paragraph in methods.split('\n\n'):
        p=paragraph.strip()
        if not p:continue
        tag='h1' if p.startswith('# ') else 'h2' if p.startswith('## ') else 'p'
        parts.append(f'<{tag}>'+html.escape(re.sub(r'^#{1,2} ','',p))+f'</{tag}>')
    links='<h2>Open the deliverables</h2><ul>'+''.join(f'<li><a href="{f}">{html.escape(t)}</a></li>' for v,t,f in VIEWS)+'<li><a href="education_career.ipynb">Executed separate notebook</a></li></ul><h2>Tables</h2><ul>'+''.join(f'<li><a href="tables/{p.name}">{p.stem.replace("_"," ")}</a></li>' for p in sorted((root/'tables').glob('*.csv')))+'</ul>'
    (root/'methods.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Education and career methods</title><style>'+(root/'assets/style.css').read_text()+'</style><article class="methods"><a href="index.html">← Open analysis</a>'+''.join(parts)+links+'</article></html>')
