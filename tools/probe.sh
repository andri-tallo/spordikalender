#!/bin/bash
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
mkdir -p probe
curl -sL -A "$UA" "https://bvl-web.dataproject.com/CompetitionMatches.aspx?ID=29" -o probe/bvl.html
sed -n '800,960p' probe/bvl.html | grep -v '^\s*$' | sed 's/^\s*//' | cut -c1-260
echo ===== FIBA
curl -sL -A "$UA" "https://www.fiba.basketball/en/events/fiba-basketball-world-cup-2027-european-qualifiers/games" -o probe/fiba.html
python3 - <<'PY'
import re
t=open('probe/fiba.html',encoding='utf-8').read()
t2=t.replace('\\"','"')
for m in list(re.finditer(r'\$D2026-11-2[0-9]T[0-9:.]+Z',t2))[:3]:
    print('---',t2[max(0,m.start()-900):m.end()+600].replace('\n',' '))
print('count EST', t2.count('"EST"'), 'count $D2027-02', t2.count('$D2027-02'), '$D2026-11', t2.count('$D2026-11'))
PY
