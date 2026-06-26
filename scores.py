#!/usr/bin/env python3
"""
Scrape les scores de la Coupe du Monde 2026 depuis l'API publique ESPN
(fifa.world, sans cle) et ecrit results.json : { "<id>": [home, away, statut] }
statut = "live" (en cours) | "final" (termine).
Lance par GitHub Actions (cron + bouton Run workflow).
"""
import json, urllib.request, unicodedata, datetime, sys

LEAGUE = "fifa.world"
BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/%s/scoreboard?dates=%s"

# Fenetre du tournoi (poules + phase finale)
START = datetime.date(2026, 6, 11)
END   = datetime.date(2026, 7, 19)

# Equipes de chaque match de l'app : id -> (equipe1, equipe2) en anglais
FIXTURES = [
 [2,"Mexico","South Africa"],[3,"South Korea","Czechia"],[4,"Czechia","South Africa"],
 [5,"Mexico","South Korea"],[6,"Czechia","Mexico"],[7,"South Africa","South Korea"],
 [8,"Canada","Bosnia"],[9,"Switzerland","Qatar"],[10,"Switzerland","Bosnia"],
 [11,"Canada","Qatar"],[12,"Switzerland","Canada"],[13,"Bosnia","Qatar"],
 [14,"Brazil","Morocco"],[15,"Scotland","Haiti"],[16,"Morocco","Scotland"],
 [17,"Brazil","Haiti"],[18,"Scotland","Brazil"],[19,"Morocco","Haiti"],
 [20,"USA","Paraguay"],[21,"Australia","Turkiye"],[22,"USA","Australia"],
 [23,"Paraguay","Turkiye"],[24,"Turkiye","United States"],[25,"Paraguay","Australia"],
 [26,"Germany","Curacao"],[27,"Ivory Coast","Ecuador"],[28,"Germany","Ivory Coast"],
 [29,"Ecuador","Curacao"],[30,"Ecuador","Germany"],[31,"Curacao","Ivory Coast"],
 [32,"Netherlands","Japan"],[33,"Sweden","Tunisia"],[34,"Netherlands","Sweden"],
 [35,"Tunisia","Japan"],[36,"Tunisia","Netherlands"],[37,"Japan","Sweden"],
 [38,"Belgium","Egypt"],[39,"Iran","New Zealand"],[40,"Belgium","Iran"],
 [41,"New Zealand","Egypt"],[42,"New Zealand","Belgium"],[43,"Egypt","Iran"],
 [44,"Spain","Cape Verde"],[45,"Saudi Arabia","Uruguay"],[46,"Spain","Saudi Arabia"],
 [47,"Uruguay","Cape Verde"],[48,"Uruguay","Spain"],[49,"Cape Verde","Saudi Arabia"],
 [50,"France","Senegal"],[51,"Iraq","Norway"],[52,"France","Iraq"],
 [53,"Norway","Senegal"],[54,"Norway","France"],[55,"Senegal","Iraq"],
 [56,"Argentina","Algeria"],[57,"Austria","Jordan"],[58,"Argentina","Austria"],
 [59,"Jordan","Algeria"],[60,"Jordan","Argentina"],[61,"Algeria","Austria"],
 [62,"Portugal","DR Congo"],[63,"Uzbekistan","Colombia"],[64,"Portugal","Uzbekistan"],
 [65,"Colombia","DR Congo"],[66,"Colombia","Portugal"],[67,"DR Congo","Uzbekistan"],
 [68,"England","Croatia"],[69,"Ghana","Panama"],[70,"England","Ghana"],
 [71,"Panama","Croatia"],[72,"Panama","England"],[73,"Croatia","Ghana"],
]

# Reconciliation des variantes de noms (ESPN vs app) -> cle canonique
ALIAS = {
 "unitedstates":"usa","usmnt":"usa","us":"usa",
 "turkiye":"turkey","tukiye":"turkey",
 "czechrepublic":"czechia",
 "cotedivoire":"ivorycoast","cotedlvoire":"ivorycoast",
 "caboverde":"capeverde",
 "bosniaherzegovina":"bosnia","bosniaandherzegovina":"bosnia","bosniaherze":"bosnia",
 "congodr":"drcongo","democraticrepublicofcongo":"drcongo","drcongo":"drcongo","congo":"drcongo",
 "korearepublic":"southkorea","republicofkorea":"southkorea",
 "iriran":"iran","iranislamicrep":"iran",
}

def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = "".join(c for c in s.lower() if c.isalnum())
    return ALIAS.get(s, s)

# index app : frozenset{normA,normB} -> (id, normE1, normE2)
fx_index = {}
for mid, e1, e2 in FIXTURES:
    fx_index[frozenset((norm(e1), norm(e2)))] = (mid, norm(e1), norm(e2))

def fetch(dates):
    url = BASE % (LEAGUE, dates)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode())

def main():
    results = {}
    d = START
    while d <= END:
        ds = d.strftime("%Y%m%d")
        try:
            data = fetch(ds)
        except Exception as e:
            print("warn", ds, e, file=sys.stderr); d += datetime.timedelta(days=1); continue
        for ev in data.get("events", []):
            comp = (ev.get("competitions") or [{}])[0]
            cs = comp.get("competitors") or []
            if len(cs) != 2:
                continue
            home = next((c for c in cs if c.get("homeAway") == "home"), cs[0])
            away = next((c for c in cs if c.get("homeAway") == "away"), cs[1])
            hn = norm((home.get("team") or {}).get("displayName") or (home.get("team") or {}).get("name"))
            an = norm((away.get("team") or {}).get("displayName") or (away.get("team") or {}).get("name"))
            key = frozenset((hn, an))
            if key not in fx_index:
                continue
            st = ((ev.get("status") or {}).get("type") or {})
            state = st.get("state")  # pre / in / post
            iso = ev.get("date")      # heure de coup d'envoi (ISO UTC)
            mid, ne1, ne2 = fx_index[key]
            if state == "pre":
                results[str(mid)] = [None, None, "pre", iso]
                continue
            try:
                hs = int(home.get("score")); as_ = int(away.get("score"))
            except (TypeError, ValueError):
                continue
            # orientation app : e1 vs e2
            if hn == ne1:
                r1, r2 = hs, as_
            else:
                r1, r2 = as_, hs
            results[str(mid)] = [r1, r2, "live" if state == "in" else "final", iso]
        d += datetime.timedelta(days=1)
    out = {"updated": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"), "scores": results}
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print("OK", len(results), "matchs ecrits dans results.json")

if __name__ == "__main__":
    main()
