#!/bin/bash
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
mkdir -p probe
for g in 127088 127090 127094 127095; do
curl -sL -A "$UA" "https://www.fiba.basketball/en/games/$g" -o probe/g$g.html
python3 - $g <<'PY'
import re,sys
g=sys.argv[1]
t=open(f'probe/g{g}.html',encoding='utf-8').read().replace('\\"','"')
print('====',g)
for k in ['gameDateTime','gameDateTimeUTC','"date":"$D2026','"date":"$D2027','startDate','hasTimeGameDateTime']:
    for m in list(re.finditer(re.escape(k),t))[:3]:
        print(k,'::',t[max(0,m.start()-250):m.end()+150].replace('\n',' '))
PY
done
curl -sL -A "$UA" "https://www.fiba.basketball/en/events/fiba-basketball-world-cup-2027-european-qualifiers/teams/estonia" -o probe/team.html
python3 - <<'PY'
import re
t=open('probe/team.html',encoding='utf-8').read().replace('\\"','"')
ids=re.findall(r'"gameId":(\d+)[^{}]{0,200}?"date":"\$D([0-9T:.Z-]+)"',t)
print('TEAM games',ids[:30])
PY
