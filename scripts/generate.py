import collections
import datetime as dt
import html
import json
import math
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
USER = 'xPeiPeix'
CYAN, PURPLE, TEXT, MUTED, LINE = '#43d9ed', '#ad8bfa', '#e2eafb', '#91aac8', '#24425c'

def api(endpoint, query=None):
    args = ['gh', 'api', endpoint]
    if query:
        args += ['--input', '-']
    result = subprocess.run(args, input=json.dumps({'query': query}) if query else None,
                            text=True, capture_output=True, check=True)
    value = json.loads(result.stdout)
    if isinstance(value, dict) and value.get('errors'):
        raise RuntimeError('GitHub returned incomplete data')
    return value

def text(x, y, value, size=16, color=TEXT, weight=400, anchor='start'):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{html.escape(str(value))}</text>'

def line(x1,y1,x2,y2,color=LINE):
    return f'<path d="M{x1} {y1}H{x2}" stroke="{color}"/>' if y1 == y2 else f'<path d="M{x1} {y1}L{x2} {y2}" stroke="{color}"/>'

def rect(x,y,w,h,color,rx=0):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{color}"/>'

def svg(title, height, body, width=960):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">
<title>{html.escape(title)}</title><defs><linearGradient id="fade" x1="0" y1="0" x2="0" y2="1"><stop stop-color="{PURPLE}" stop-opacity=".15"/><stop offset="1" stop-color="{PURPLE}" stop-opacity="0"/></linearGradient></defs>
<g font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif">{body}</g></svg>'''

def heading(label, note='', width=960):
    return text(25,39,label.capitalize(),20,TEXT,600)+text(width-26,39,note,12,MUTED,anchor='end')

def generate():
    user = api(f'users/{USER}')
    repos = []
    page = 1
    while True:
        batch = api(f'users/{USER}/repos?per_page=100&page={page}')
        repos.extend(r for r in batch if not r['private'] and not r['fork'])
        if len(batch)<100:
            break
        page += 1
    query = '{user(login:"xPeiPeix"){contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{date contributionCount contributionLevel weekday}}}}}}'
    calendar = api('graphql',query)['data']['user']['contributionsCollection']['contributionCalendar']
    weeks = calendar['weeks']
    days = [d for week in weeks for d in week['contributionDays']]
    if not 360 <= len(days) <= 367 or sum(d['contributionCount'] for d in days) != calendar['totalContributions']:
        raise ValueError('Incomplete contribution calendar; keeping existing assets')
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M UTC+8')
    stars = sum(r['stargazers_count'] for r in repos)
    languages = collections.Counter(r['language'] for r in repos if r['language'])
    files = {}
    # The pixel cat and charts are self-contained vector artwork.
    cat = ['10000000001','11000000011','11111111111','11111111111','11011111011','11111111111','11110101111','01111111110','00111111100']
    body = ''
    for y,row in enumerate(cat):
        for x,pixel in enumerate(row):
            if pixel=='1': body += rect(37+x*9,48+y*9,6,6,CYAN)
    body += text(40,166,'>_',26,CYAN,600)
    body += text(178,70,'Peip',44,TEXT,700)+text(294,70,'/ xPeiPeix',32,CYAN,600)
    body += text(180,105,'Personal tools. Open source.',18,TEXT)+text(180,133,'Everyday experiments.',18,TEXT)
    body += text(180,177,'Build small things. Make them useful.',14,MUTED)
    body += line(687,37,687,183)+text(712,66,'Python / TypeScript',14,CYAN)+text(712,100,'Automation & tooling',14,MUTED)+text(712,134,'Vision & web projects',14,MUTED)+text(712,174,'github.com/xPeiPeix',13,PURPLE)
    files['header.svg'] = svg('Peip / xPeiPeix — personal tools and open source',195,body)
    body = ''
    values=[(user['public_repos'],'PUBLIC REPOS'),(user['followers'],'FOLLOWERS'),(stars,'STARS / ORIGINALS'),(calendar['totalContributions'],'CONTRIBUTIONS / YEAR')]
    for i,(value,label) in enumerate(values):
        x=28+i*236
        body += text(x,65,f'{value:,}',36,CYAN if i==3 else TEXT,700)+text(x,94,label,12,MUTED)
        if i<3: body+=line(x+213,27,x+213,99)
    files['overview.svg']=svg('Public repositories, followers, original repository stars and last-year contributions',120,body)
    body=heading('CONTRIBUTIONS',f"{days[0]['date']} → {days[-1]['date']}")
    palette={'NONE':'#172a3e','FIRST_QUARTILE':'#16556d','SECOND_QUARTILE':'#1687a3','THIRD_QUARTILE':'#24b5cc','FOURTH_QUARTILE':CYAN}
    step=16.2
    last_month=None
    for i,week in enumerate(weeks):
        for day in week['contributionDays']:
            date=dt.date.fromisoformat(day['date'])
            if date.month!=last_month and (i==0 or date.day<=7):
                if i<51: body+=text(63+i*step,79,date.strftime('%b'),11,MUTED)
                last_month=date.month
            body+=f'<g><title>{day["date"]}: {day["contributionCount"]} contributions</title>'+rect(round(63+i*step,1),92+day['weekday']*18,13,14,palette[day['contributionLevel']],2)+'</g>'
    for weekday,label in [(1,'Mon'),(3,'Wed'),(5,'Fri')]: body+=text(25,103+weekday*18,label,11,MUTED)
    active=sum(d['contributionCount']>0 for d in days)
    best=max(d['contributionCount'] for d in days)
    body+=text(26,245,f'{active} active days · {best:,} best day · GitHub contribution calendar',12,MUTED)
    body+=text(730,245,'Less',11,MUTED)
    for i,color in enumerate(palette.values()): body+=rect(770+i*19,233,13,13,color,2)
    body+=text(878,245,'More',11,MUTED)
    files['contributions.svg']=svg('Last year contribution heatmap',269,body)
    totals=[sum(d['contributionCount'] for d in w['contributionDays']) for w in weeks]
    maximum=max(max(totals),1)
    ceiling=max(1,math.ceil(maximum/4))*4
    body=heading('CONTRIBUTION TREND','Weekly totals · first / last week may be partial')
    for i in range(5):
        y=82+i*34
        body+=line(65,y,930,y)+text(53,y+4,str(int(ceiling*(4-i)/4)),11,MUTED,anchor='end')
    coords=[(65+i*865/(len(totals)-1),218-v/ceiling*136) for i,v in enumerate(totals)]
    path='M'+' L'.join(f'{x:.1f} {y:.1f}' for x,y in coords)
    body+=f'<path d="{path} L930 218 L65 218 Z" fill="url(#fade)"/><path d="{path}" fill="none" stroke="{PURPLE}" stroke-width="2.5" stroke-linejoin="round"/>'
    for i in range(0,len(weeks),8):
        body+=text(round(coords[i][0]),243,dt.date.fromisoformat(weeks[i]['contributionDays'][0]['date']).strftime('%b %d'),11,MUTED)
    body+=text(26,277,'Contribution totals include private counts when GitHub makes them available.',11,MUTED)
    files['trend.svg']=svg('Weekly GitHub contributions',298,body)
    body=heading('LANGUAGES','Original public repos',472)
    colors=['#43d9ed','#ad8bfa','#efd16b','#54d8b2','#90baf4']
    items=languages.most_common(5)
    for i,(lang,count) in enumerate(items):
        y=96+i*44
        body+=rect(25,y-11,7,7,colors[i],2)+text(44,y,lang,16)+rect(193,y-12,205,12,'#172c41',5)+rect(193,y-12,205*count/max(languages.values()),12,colors[i],5)+text(442,y,count,16,TEXT,anchor='end')
    body+=text(25,320,'Count by primary repository language.',11,MUTED)+text(25,342,'Forks and undetected languages excluded.',11,MUTED)
    files['languages.svg']=svg('Primary languages of original public repositories',368,body,472)
    featured={'face_mosaic':'Image / video face anonymization','claude-repath':'Move projects; preserve sessions','multi_qrcode':'Offline transfer through QR arrays','utahon':'Learn Japanese through song lyrics'}
    ranked=sorted(repos,key=lambda r:(-r['stargazers_count'],r['name']))
    ranked=[r for r in ranked if r['name'] in featured]
    body=heading('TOP PROJECTS','Stars / originals',472)
    for i,r in enumerate(ranked):
        y=91+i*66
        body+=text(25,y,f'{i+1:02}',13,PURPLE)+text(62,y,r['name'],16,CYAN,600)+text(447,y,f"★ {r['stargazers_count']}",15,'#efd16b',anchor='end')+text(62,y+23,featured[r['name']],11,MUTED)
        if i<3: body+=line(25,y+37,447,y+37)
    body+=text(25,350,'Explore the project links below.',11,MUTED)
    files['projects.svg']=svg('Featured original repositories and their stars',368,body,472)
    def combined(mobile):
        children = []
        for i, name in enumerate(['languages.svg', 'projects.svg']):
            child = files[name].replace('<svg ', f'<svg x="{0 if mobile else i*488}" y="{i*384 if mobile else 0}" ', 1)
            # Each panel has its own pattern; prefix IDs in the composed document.
            child = child.replace('id="', f'id="panel{i}-').replace('url(#', f'url(#panel{i}-')
            children.append(child)
        width, height = (472, 752) if mobile else (960, 368)
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">' + ''.join(children) + '</svg>'
    files['insights.svg'] = combined(False)
    files['insights-mobile.svg'] = combined(True)
    files['footer.svg']=svg('Dashboard last successful update',70,text(25,43,'> Keep building. Stay curious.',16,CYAN)+text(935,42,stamp,12,MUTED,anchor='end'))
    files['header-mobile.svg']=svg('Peip / xPeiPeix',190,
        text(25,56,'Peip / xPeiPeix',30,CYAN,700)+text(25,94,'Personal tools. Open source.',17)+
        text(25,124,'Everyday experiments.',17)+text(25,164,'Python / TypeScript · Build small things.',12,MUTED),472)
    body=''
    for i,(value,label) in enumerate(values):
        x,y=25+(i%2)*236,54+(i//2)*90
        body+=text(x,y,f'{value:,}',30,CYAN if i==3 else TEXT,700)+text(x,y+25,label,11,MUTED)
    files['overview-mobile.svg']=svg('Profile statistics',191,body,472)
    body=heading('CONTRIBUTIONS','Last year',472)
    for i,week in enumerate(weeks):
        col,row=i%27,i//27
        if col==0: body+=text(25,82+row*149,week['contributionDays'][0]['date'],12,MUTED)
        for day in week['contributionDays']:
            body+=rect(25+col*15.6,96+row*149+day['weekday']*16,12,12,palette[day['contributionLevel']],2)
    body+=text(25,391,f'{active} active days · {best:,} best day',13,MUTED)
    files['contributions-mobile.svg']=svg('Last year contribution heatmap in two rows',414,body,472)
    body=heading('WEEKLY TREND','Last year',472)
    for i in range(3):
        y=82+i*60
        body+=line(55,y,447,y)+text(45,y+4,str(int(ceiling*(2-i)/2)),12,MUTED,anchor='end')
    coords=[(55+i*392/(len(totals)-1),202-v/ceiling*120) for i,v in enumerate(totals)]
    path='M'+' L'.join(f'{x:.1f} {y:.1f}' for x,y in coords)
    body+=f'<path d="{path} L447 202 L55 202Z" fill="url(#fade)"/><path d="{path}" fill="none" stroke="{PURPLE}" stroke-width="2.5"/>'
    for i in [0,16,32,48]: body+=text(round(coords[i][0]),230,dt.date.fromisoformat(weeks[i]['contributionDays'][0]['date']).strftime('%b'),12,MUTED)
    body+=text(25,263,'First / last week may be partial.',12,MUTED)
    files['trend-mobile.svg']=svg('Weekly contribution totals',285,body,472)
    files['footer-mobile.svg']=svg('Last successful update',91,text(25,36,'> Keep building. Stay curious.',16,CYAN)+text(25,66,stamp,12,MUTED),472)
    def dashboard(mobile):
        names = ['header', 'overview', 'contributions', 'trend', 'insights', 'footer']
        width = 472 if mobile else 960
        offset = 0
        children = []
        for i, name in enumerate(names):
            source = files[name + ('-mobile' if mobile else '') + '.svg']
            height = int(ET.fromstring(source).attrib['height'])
            child = source.replace('<svg ', f'<svg x="0" y="{offset}" ', 1)
            child = child.replace('id="', f'id="section{i}-').replace('url(#', f'url(#section{i}-')
            children.append(child)
            offset += height
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{offset}" viewBox="0 0 {width} {offset}" role="img"><title>Peip — GitHub activity and projects</title>' + ''.join(children) + '</svg>'

    dark = {f'dashboard{suffix}-dark.svg': dashboard(mobile)
            for suffix, mobile in [('', False), ('-mobile', True)]}
    light_colors = {
        TEXT: '#1f2328', MUTED: '#59636e', LINE: '#d8dee4',
        CYAN: '#087e8b', PURPLE: '#7955c7', '#efd16b': '#926b16',
        '#54d8b2': '#148568', '#90baf4': '#4169aa',
        '#172c41': '#eaeef2', '#172a3e': '#edf0f3',
        '#16556d': '#c5e9e6', '#1687a3': '#82c9c3', '#24b5cc': '#3aa59f',
    }
    files = dict(dark)
    for name, content in dark.items():
        for old, new in light_colors.items():
            content = content.replace(old, new)
        files[name.replace('-dark.svg', '-light.svg')] = content
    # Validate every asset before changing any existing output. Failed runs never publish.
    for content in files.values(): ET.fromstring(content)
    for name,content in files.items(): (ROOT/'assets'/name).write_text(content+'\n')
    print(f'Generated {len(files)} SVGs; {len(days)} days; {len(repos)} original public repositories')

if __name__=='__main__':
    generate()
