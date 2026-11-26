#!/bin/bash
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
curl -sL -A "$UA" "https://evf-web.dataproject.com/CompetitionMatches.aspx?ID=100" -o cup.html
curl -sL -A "$UA" "https://bvl-web.dataproject.com/CompetitionMatches.aspx?ID=29" -o bvl.html
for f in cup.html bvl.html; do echo "=== $f"; grep -n "Barrus" $f | sed 's/^\s*//' | cut -c1-260 | head -20
grep -oE 'id="[^"]*_(LB_DataOra|Label2|Label4)"[^>]*>[^<]*<' $f | sed -E 's/ctl00_Content_Main_//' | head -12; done
python3 - <<'PY'
import re
t=open('cup.html',encoding='utf-8').read()
i=t.find('26/11/2026'); print('CUP AROUND DATE:', re.sub(r'\s+',' ',t[i-300:i+3500])[:3000])
PY
