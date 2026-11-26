#!/bin/bash
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
mkdir -p probe
curl -sL -A "$UA" "https://bvl-web.dataproject.com/CompetitionMatches.aspx?ID=29" -o probe/bvl.html; echo "BVL $(wc -c < probe/bvl.html)"
grep -n -m3 "Barrus" probe/bvl.html | cut -c1-400
L=$(grep -n -m1 "Barrus" probe/bvl.html | cut -d: -f1); sed -n "$((L-40)),$((L+15))p" probe/bvl.html | cut -c1-300
echo ===== FIBA
curl -sL -A "$UA" "https://www.fiba.basketball/en/events/fiba-basketball-world-cup-2027-european-qualifiers/games" -o probe/fiba.html; echo "FIBA $(wc -c < probe/fiba.html)"
grep -o '__NEXT_DATA__' probe/fiba.html | head -1
grep -oE '.{200}EST.{300}' probe/fiba.html | grep -iE 'date|time' | head -3
grep -oE '"[a-zA-Z]*[Dd]ate[a-zA-Z]*":"[^"]{5,40}"' probe/fiba.html | sort | uniq -c | sort -rn | head -10
curl -sL -A "$UA" "https://www.fiba.basketball/en/games/127088" -o probe/g.html; echo "GAME $(wc -c < probe/g.html)"
grep -oE '"[a-zA-Z]*([Dd]ate|[Tt]ime)[a-zA-Z]*\\?":\\?"[^"\\]{5,40}' probe/g.html | sort | uniq -c | head -15
echo ===== SOFA
curl -s -A "$UA" "https://api.sofascore.com/api/v1/search/teams?q=estonia&sport=basketball" | head -c 800; echo
