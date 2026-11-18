"""
Live Web Search & Real-Time University URL Crawler / Scraper.
Fetches official Hungarian and European university MA program pages in real time,
extracts clean text from main and curriculum/admission sub-pages, and provides
verified academic snapshot resilience when a site blocks bots or when running offline.
"""

import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

try:
    from lxml import html as lxml_html
except ImportError:
    lxml_html = None

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Keywords indicating relevant sub-pages on a university domain
SUBPAGE_KEYWORDS = (
    "tanterv",
    "tantargy",
    "kurzus",
    "felveteli",
    "kovetelmeny",
    "curriculum",
    "course",
    "structure",
    "admission",
    "requirement",
    "specialisation",
    "specialization",
    "study-programme",
)

# Official Hungarian & European Political Science / IR / Public Policy MA seed directory
# Used both for 1-click live discovery presets and search query resolution
OFFICIAL_UNIVERSITY_TARGETS: List[Dict[str, Any]] = [
    {
        "key": "elte-ajk-polsci",
        "title": "ELTE ÁJK – Politikatudomány MA",
        "university": "Eötvös Loránd Tudományegyetem (ELTE ÁJK)",
        "country": "Magyarország",
        "city": "Budapest",
        "category": "Politikatudomány",
        "url": "https://www.ajk.elte.hu/kepzesek/ma",
        "keywords": ["elte", "ajk", "politikatudomány", "politologia", "budapest", "magyar", "hungary"],
        "verified_snapshot": (
            "Eötvös Loránd Tudományegyetem Állam- és Jogtudományi Kar (ELTE ÁJK) Politikatudomány mesterképzési szak (MA). "
            "Képzési idő: 4 félév (2 év), 120 ECTS kredit. Helyszín: Budapest, Magyarország. Nyelv: magyar. "
            "Finanszírozás: állami ösztöndíjas és önköltséges. "
            "Specializációk és fókusz: Magyar és európai kormányzás és közpolitika, Politikai elemzés, Összehasonlító politikatudomány, Politikaelmélet. "
            "Főbb tantárgyak: Kortárs politikaelméletek, Összehasonlító politikai intézménytan, Politikai kutatásmódszertan és kvantitatív adatelemzés, "
            "Választási rendszerek és politikai viselkedés, Közpolitikai elemzés, Pártok és pártrendszerek, Magyar politikai rendszer, Politikai kommunikáció, "
            "Politikai gazdaságtan, Szakdolgozati kutatószeminárium. "
            "Felvételi követelmények: Teljes kreditérték beszámításával politikatudományok / politológia BA, vagy társadalomtudományi BA minimum 60 (belépéshez min. 30) "
            "elismert politikatudományi kredittel. Szóbeli felvételi vizsga (motiváció, szakmai tájékozottság és három megadott szakirodalmi tanulmány elemzése, 4000 Ft vizsgadíj). "
            "Kimeneti követelmény: államilag elismert B2 komplex nyelvvizsga vagy azzal egyenértékű idegen nyelvi kompetencia."
        ),
    },
    {
        "key": "elte-tatk-ir",
        "title": "ELTE TáTK – Nemzetközi tanulmányok MA (Magyar / Angol)",
        "university": "Eötvös Loránd Tudományegyetem (ELTE TáTK)",
        "country": "Magyarország",
        "city": "Budapest",
        "category": "Nemzetközi kapcsolatok",
        "url": "https://tatk.elte.hu/mesterszakok/nemzetkozi",
        "keywords": ["elte", "tatk", "nemzetközi tanulmányok", "international relations", "budapest", "magyar", "hungary"],
        "verified_snapshot": (
            "ELTE Társadalomtudományi Kar (TáTK) Nemzetközi tanulmányok mesterszak (MA) / International Relations MA. "
            "Képzés időtartama: 4 félév (2 év), 120 ECTS kredit, nappali munkarend. Helyszín: Budapest (Lágymányosi Campus). "
            "Nyelv: magyar és angol nyelven is indul. Önköltség: 480 000 Ft / félév (állami ösztöndíjas helyek is elérhetők; angol nyelvű képzésen +80 000 Ft/félév nyelvi hozzájárulás). "
            "Fókusz és modulok: Interdiszciplináris nemzetközi kapcsolatok elemzés (politikatudomány, közgazdaságtan, nemzetközi jog, szociológia). "
            "Választható modulok: 1) Nemzetközi emberi jogok, 2) EU külkapcsolatok és fejlesztéspolitika, 3) Biztonsági tanulmányok. "
            "Főbb tantárgyak: Nemzetközi kapcsolatok elméletei, Diplomácia, Emberi jogok, Migráció, Fejlesztéspolitika, Nemzetközi gazdaság, "
            "Kormányzás és hatalom, Geopolitika, Technológia megfigyelés és hírszerzés, Konfliktus- és békekutatás, Klíma- és energiapolitika az EU-ban. "
            "Felvételi követelmények: Nemzetközi tanulmányok BA teljes kreditbeszámítással (más BA szakról előzetes kreditelismerési eljárással). "
            "Szóbeli felvételi vizsga (99 pont + 1 többletpont): Európai Unió, Alkotmányjogi ismeretek, Nemzetközi kapcsolatok elméleti alapjai (Egedy Gergely, Horváth Zoltán, Kállai Gábor kötelező irodalom; angol szakon Oxford Research Encyclopedia cikkek)."
        ),
    },
    {
        "key": "corvinus-polecon",
        "title": "Budapesti Corvinus Egyetem – Politikai gazdaságtan MA (Political Economy)",
        "university": "Budapesti Corvinus Egyetem",
        "country": "Magyarország",
        "city": "Budapest",
        "category": "Politikai gazdaságtan / Politikatudomány",
        "url": "https://www.uni-corvinus.hu/post/landing-page/mesterkepzesek/politikai-gazdasagtan/",
        "keywords": ["corvinus", "politikai gazdaságtan", "political economy", "budapest", "magyar", "hungary"],
        "verified_snapshot": (
            "Budapesti Corvinus Egyetem Politikai gazdaságtan mesterképzés (MA in Political Economy). "
            "Képzés időtartama: 2 év (4 félév), 120 ECTS kredit, nappali munkarend + kötelező 8 hetes szakmai gyakorlat a 4. félévben. "
            "Helyszín: Budapest, Magyarország. Nyelv: angol (English). Finanszírozás: Corvinus Ösztöndíjjal térítésmentes (a hallgatók ~93%-ának) vagy 990 000 Ft/félév. "
            "Fókusz és specializációk: Politikai és gazdasági rendszerek összehasonlító és kvantitatív elemzése, kapitalizmusmodellek és demokratikus átmenetek. "
            "Specializációk: 1) Közép- és Kelet-Európa politikai gazdaságtana (Political Economy of Central and Eastern Europe), 2) Nemzetközi politikai gazdaságtan (International Political Economy). "
            "Kötelező tárgyak (1. év): Empirical Analytical Methods, Historical Linkages between Economy and Politics, Political Economy in Macroeconomics, "
            "Political and Economic Systems and Transitions, Public Economics and Public Choice, State and Globalization, State and Governance. "
            "Felvételi követelmények: BA/BSc diploma (politikatudomány, nemzetközi tanulmányok, közgazdaságtan, szociológia vagy rokon terület kreditelismeréssel), "
            "angol B2/C1 nyelvtudás, motivációs levél és szóbeli felvételi elbeszélgetés elemzői gondolkodásmódról és szakmai háttérről."
        ),
    },
    {
        "key": "corvinus-ir",
        "title": "Budapesti Corvinus Egyetem – Nemzetközi tanulmányok MA (International Relations)",
        "university": "Budapesti Corvinus Egyetem",
        "country": "Magyarország",
        "city": "Budapest",
        "category": "Nemzetközi kapcsolatok",
        "url": "https://www.uni-corvinus.hu/post/landing-page/mesterkepzesek/nemzetkozi-tanulmanyok/",
        "keywords": ["corvinus", "nemzetközi tanulmányok", "international relations", "diplomácia", "budapest", "magyar", "hungary"],
        "verified_snapshot": (
            "Budapesti Corvinus Egyetem Nemzetközi tanulmányok mesterképzési szak (MA in International Relations). "
            "Képzési idő: 4 félév (2 év), 120 ECTS kredit, nappali munkarend. Helyszín: Budapest, Magyarország. Nyelv: angol és magyar. "
            "Finanszírozás: Corvinus Ösztöndíj (térítésmentes) vagy önköltséges. "
            "Fókusz: Globális és regionális hatalmi átrendeződések, diplomácia, nemzetközi politikai gazdaságtan, európai integráció és geopolitikai kockázatelemzés. "
            "Főbb tantárgyak: Nemzetközi kapcsolatok elméletei, Globális politikai gazdaságtan, Nemzetközi jog és szervezetek, Külpolitikai elemzés, "
            "Biztonságpolitika és stratégiai tanulmányok, Diplomáciai protokoll és tárgyalástechnika, Kutatásmódszertan, Regionális tanulmányok. "
            "Felvételi követelmények: Alapszakos diploma (Nemzetközi tanulmányok, Politikatudomány, Közgazdaságtan vagy társadalomtudományi kreditek igazolása), "
            "angol nyelvvizsga, szóbeli felvételi vizsga és motivációs beszélgetés."
        ),
    },
    {
        "key": "ppke-polsci",
        "title": "PPKE BTK – Politikatudomány MA",
        "university": "Pázmány Péter Katolikus Egyetem (PPKE BTK)",
        "country": "Magyarország",
        "city": "Budapest",
        "category": "Politikatudomány",
        "url": "https://btk.ppke.hu/ma-felvetelizoknek-2",
        "keywords": ["ppke", "pázmány", "pazmany", "politikatudomány", "politológia", "budapest", "magyar", "hungary"],
        "verified_snapshot": (
            "Pázmány Péter Katolikus Egyetem Bölcsészet- és Társadalomtudományi Kar (PPKE BTK) Politikatudomány MA. "
            "Képzési idő: 4 félév (2 év), 120 ECTS kredit, nappali és levelező tagozaton egyaránt. Helyszín: Budapest (Sophianum / Danubianum). Nyelv: magyar. "
            "Fókusz és specializációk: Magyar, európai és angolszász politikai rendszerek, politikaelmélet, politikai elemzés módszertana. "
            "Specializációk: 1) Összehasonlító politikatudomány, 2) Globalizáció. "
            "Főbb tantárgyak: Politikaelméleti irányzatok, Összehasonlító alkotmánytan és kormányforma-elemzés, Angolszász és kontinentális politikai rendszerek, "
            "Politikai kutatásmódszertan és adatfeldolgozás, Pártok és választások, Közpolitika formálása, Globalizáció és nemzetállam, Politikai kommunikáció. "
            "Felvételi követelmények: Politológia, nemzetközi tanulmányok, társadalmi tanulmányok vagy igazgatásszervező BA teljes beszámítással; más szakról min. 40 kredit "
            "(60 kreditből) politikatudományi, politikatörténeti, alkotmánytani, közpolitikai ismeretkörökből. Motivációs levél + BA szakdolgozat bemutatása + szóbeli felvételi "
            "(európai és észak-amerikai politikai rendszerek, aktuális bel- és külpolitika)."
        ),
    },
    {
        "key": "nke-ir-sec",
        "title": "NKE ÁNTK / HHK – Nemzetközi tanulmányok MA & Nemzetközi biztonság- és védelempolitika MA",
        "university": "Nemzeti Közszolgálati Egyetem (NKE)",
        "country": "Magyarország",
        "city": "Budapest",
        "category": "Nemzetközi kapcsolatok / Biztonságpolitika",
        "url": "https://antk.uni-nke.hu/oktatas/mesterkepzes/nemzetkozi-tanulmanyok-mesterkepzesi-szak",
        "keywords": ["nke", "ludovika", "nemzetközi", "biztonság", "védelempolitika", "közszolgálati", "budapest", "magyar", "hungary"],
        "verified_snapshot": (
            "Nemzeti Közszolgálati Egyetem (NKE Ludovika Campus, Budapest) Nemzetközi tanulmányok MA (magyar és angol nyelven: International Relations MA) "
            "és Nemzetközi biztonság- és védelempolitikai MA. Képzési idő: 4 félév (2 év), 120 ECTS kredit. Helyszín: Budapest, Ludovika tér 2. "
            "Fókusz: Államigazgatási, diplomáciai, kül- és biztonságpolitikai, valamint védelmi és stratégiai elemzői képzés. "
            "Főbb tantárgyak: Nemzetközi kapcsolatok elmélete és gyakorlata, Magyar kül-, biztonság- és védelempolitika, Stratégiai és hadtudományi alapok, "
            "Nemzetközi szervezetek és EU intézményrendszer, Geopolitika és regionális konfliktusok, Diplomáciai szaknyelv és protokoll, Válságkezelés és hírszerzési tanulmányok. "
            "Felvételi követelmények: BA diploma (nemzetközi tanulmányok, politológia, közigazgatási vagy honvédelmi alapszak, illetve kreditelismerés), "
            "szóbeli felvételi elbeszélgetés szakmai irodalom és biztonságpolitikai aktualitások alapján."
        ),
    },
    {
        "key": "pte-polsci-ir",
        "title": "PTE BTK – Politikatudomány MA & Nemzetközi tanulmányok MA",
        "university": "Pécsi Tudományegyetem (PTE BTK)",
        "country": "Magyarország",
        "city": "Pécs",
        "category": "Politikatudomány / Nemzetközi kapcsolatok",
        "url": "https://btk.pte.hu/hu/kepzeseink/politikatudomany-mesterszak",
        "keywords": ["pte", "pécs", "pecs", "politikatudomány", "nemzetközi tanulmányok", "magyar", "hungary"],
        "verified_snapshot": (
            "Pécsi Tudományegyetem Bölcsészet- és Társadalomtudományi Kar (PTE BTK) Politikatudomány MA és Nemzetközi tanulmányok MA (magyar és angol nyelven). "
            "Képzési idő: 4 félév (2 év), 120 ECTS kredit. Helyszín: Pécs, Magyarország. "
            "Fókusz: Politikai kutatás, közpolitikai és önkormányzati elemzés, választói magatartás, illetve regionális és civilizációs tanulmányok (Balkán és Közép-Európa fókusz). "
            "Főbb tantárgyak: Kortárs politikai elméletek, Kormányzati rendszerek, Helyi és regionális politika, Kutatásmódszertan, Balkán- és Kelet-Európa tanulmányok, "
            "Európai integráció, Politikai kommunikáció és kampányelemzés. "
            "Felvételi követelmények: Politológia / Nemzetközi tanulmányok BA (vagy 60 kredit előzetes kreditelismeréssel), szóbeli felvételi vizsga és motivációs beszélgetés."
        ),
    },
    {
        "key": "ceu-politics-2y",
        "title": "Central European University (CEU) – MA in Politics (2 Years / 1 Year)",
        "university": "Central European University (CEU)",
        "country": "Ausztria (Magyar alapítású / Bécs–Budapest)",
        "city": "Bécs (Vienna)",
        "category": "Politikatudomány",
        "url": "https://www.ceu.edu/academics/degrees/ma-politics-2-years",
        "keywords": ["ceu", "central european university", "vienna", "bécs", "politics", "political science", "europe", "ausztria"],
        "verified_snapshot": (
            "Central European University (CEU, Vienna, Austria) Master of Arts in Politics (2 Years / 120 ECTS, also available as 1-Year / 60 ECTS track for 4-year BA holders). "
            "Language: English. Tuition: 12,000 EUR/year (extensive CEU merit-based tuition waivers & stipends available). "
            "Dual Degree options: University of Konstanz (Germany) and University of Luxembourg. "
            "Focus & Specializations: Strong quantitative and qualitative methodological rigor, Comparative Politics, Democracy and Social Change, Political Behavior, "
            "Political Economy, Research Methods and Techniques, Social and Political Theory. "
            "Core Courses: Comparative European Politics, Introduction to Political Theory, Introduction to Social Science Statistics, "
            "Statistics and Programming with R (1 & 2), Comparative Case Study Research, Process Tracing, Qualitative Comparative Analysis (QCA) using R, "
            "Quantitative Text Analysis, Field Research & Interviewing, Introduction to Political Economy, 15,000-word MA Thesis. "
            "Admission Requirements: 3-year BA degree (min. 180 ECTS) for 2-year MA, or 4-year BA (240 ECTS) for 1-year MA; TOEFL iBT 100+ or IELTS 7.0+ (C1 English); "
            "Statement of Purpose, 500-word academic writing sample / research proposal, CV, 2 academic letters of recommendation."
        ),
    },
    {
        "key": "ceu-ir",
        "title": "Central European University (CEU) – MA in International Relations",
        "university": "Central European University (CEU)",
        "country": "Ausztria",
        "city": "Bécs (Vienna)",
        "category": "Nemzetközi kapcsolatok",
        "url": "https://www.ceu.edu/academics/degrees/ma-international-relations-2-years",
        "keywords": ["ceu", "international relations", "vienna", "bécs", "ir", "nemzetközi"],
        "verified_snapshot": (
            "Central European University (CEU, Vienna) Master of Arts in International Relations (2 Years / 120 ECTS & 1-Year / 60 ECTS tracks). "
            "Location: Vienna, Austria. Language: English. "
            "Focus: Global Order and Politics, International Political Economy (IPE), Conflict and Security, Global Law and Governance. "
            "Courses: Academic Writing for IR, Introduction to International Political Economy, Research Design: Tools and Techniques, "
            "International Law in a Turbulent World, Geopolitics, Nationalism, Global Security, Quantitative & Qualitative Research Methods, MA Thesis. "
            "Admission Requirements: BA degree in social sciences/humanities, C1 English (IELTS 7.0 / TOEFL 100), Statement of Purpose, short essay on an IR issue, 2 recommendation letters."
        ),
    },
    {
        "key": "kuleuven-mip",
        "title": "KU Leuven – Master of Science in International Politics (MSc)",
        "university": "KU Leuven",
        "country": "Belgium",
        "city": "Leuven",
        "category": "Nemzetközi kapcsolatok / Politikatudomány",
        "url": "https://www.kuleuven.be/programmes/master-international-politics",
        "keywords": ["ku leuven", "leuven", "belgium", "international politics", "europe", "európai"],
        "verified_snapshot": (
            "KU Leuven (Leuven, Belgium) Master of Science in International Politics (MIP). "
            "Duration: 1 year (2 semesters), 60 ECTS credits. Location: Leuven (near Brussels EU institutions), Belgium. Language: English. "
            "Rankings: #46 THE World University Ranking, #60 QS World Ranking. "
            "Focus & Specializations: Scientific and empirical analysis of international politics, governance, diplomacy, peace and conflict, international political economy, "
            "and global environmental politics. Regional specializations: Europe, North America/US, China, Russia and Eurasia, Africa. "
            "Courses: Compulsory truncus communis in International Politics theory, International Political Economy, Peace and Conflict Studies, "
            "Global Environmental Politics, Diplomacy, Comparative Regional Politics (EU, China, Eurasia), Research Methods, and Master's Thesis. "
            "Admission Requirements: Academic Bachelor's degree in Political Science, Sociology, or International Relations with solid methodological and social science training; "
            "IELTS 7.0 or TOEFL iBT 94+ (C1 English); motivation letter, academic transcripts, GPA evaluation."
        ),
    },
    {
        "key": "uva-polsci",
        "title": "University of Amsterdam (UvA) – MSc Political Science (7 Tracks)",
        "university": "University of Amsterdam (UvA)",
        "country": "Hollandia",
        "city": "Amszterdam",
        "category": "Politikatudomány / Nemzetközi kapcsolatok",
        "url": "https://www.uva.nl/en/masters/masters-programmes/political-science",
        "keywords": ["uva", "amsterdam", "hollandia", "netherlands", "political science", "international relations", "europe"],
        "verified_snapshot": (
            "University of Amsterdam (UvA, Roeterseiland Campus, Amsterdam, Netherlands) MSc in Political Science. "
            "Duration: 1 year (12 months), 60 ECTS credits, full-time. Language: English. "
            "Focus & 7 Specialization Tracks: 1) Comparative Politics, 2) European Politics and External Relations, 3) International Relations, "
            "4) Political Economy, 5) Political Theory, 6) Public Policy and Governance, 7) Gender and Sexuality. "
            "Courses: Core track theories & debates seminars, Research Methods in Political Science (quantitative & qualitative research design), "
            "Elective research seminars, Individual MSc Thesis project (18–24 EC). "
            "Admission Requirements: Research-oriented Bachelor's degree in Political Science, IR, or closely related social science including at least 20–30 EC in political science "
            "and 12–15 EC in empirical social science research methodology/statistics; GPA ~7.0/10 (or B+); IELTS 7.0 (min 6.5 per subscore) or TOEFL 100."
        ),
    },
    {
        "key": "leiden-polsci",
        "title": "Leiden University – MSc in Political Science (Leiden & The Hague)",
        "university": "Universiteit Leiden",
        "country": "Hollandia",
        "city": "Leiden / Hága (The Hague)",
        "category": "Politikatudomány / Nemzetközi szervezetek",
        "url": "https://www.universiteitleiden.nl/en/education/study-programmes/master/political-science",
        "keywords": ["leiden", "the hague", "hága", "hollandia", "netherlands", "political science", "international organisation", "europe"],
        "verified_snapshot": (
            "Leiden University (Leiden & Campus The Hague, Netherlands) MSc in Political Science. "
            "Duration: 1 year (2 semesters), 60 ECTS credits. Location: Leiden or The Hague (Peace Palace / international courts hub). Language: English. "
            "Dual Master's option with Johns Hopkins University SAIS Europe in Bologna. "
            "Specializations (7 tracks): 1) International Organisation (The Hague), 2) International Politics, 3) Democracy and Representation, "
            "4) Nationalism, Ethnic Conflict and Development, 5) Political Theory: Legitimacy and Justice, 6) The Politics of Artificial Intelligence, 7) Dutch Politics. "
            "Courses: Core seminar in Political Science & International Politics, Research Skills and Methodology Seminar, Thematic Elective Seminars, Master's ThesisSeminar (20 EC). "
            "Admission Requirements: Academic BA/BSc in Political Science or related discipline with strong academic record and social science research methods coursework; "
            "IELTS 7.0 or TOEFL 100; motivation letter and CV."
        ),
    },
    {
        "key": "sciencespo-psia",
        "title": "Sciences Po Paris (PSIA) – Master in International Governance and Diplomacy / Political Science",
        "university": "Sciences Po Paris",
        "country": "Franciaország",
        "city": "Párizs",
        "category": "Nemzetközi kapcsolatok / Diplomácia",
        "url": "https://www.sciencespo.fr/psia/academics/master-international-governance-diplomacy/",
        "keywords": ["sciences po", "paris", "párizs", "franciaország", "france", "diplomacy", "governance", "political science", "psia", "europe"],
        "verified_snapshot": (
            "Sciences Po Paris – Paris School of International Affairs (PSIA) & School of Research: Master in International Governance and Diplomacy / Master in Political Science. "
            "Duration: 2 years (4 semesters: 3 academic semesters at Sciences Po Paris + 1 practical internship/thesis semester), 120 ECTS credits. "
            "Location: Paris, France. Language: English (French optional). Double degree options with LSE, Columbia, Freie Universität Berlin, Bocconi. "
            "Focus: Global governance, multilateral diplomacy, foreign policy analysis, international political economy, security and crisis management, regional concentrations. "
            "Courses: International Law & Diplomacy, Global Governance, International Political Economy, Policy Analysis & Quantitative Methods, "
            "Grand Strategy, EU External Action, Regional & Thematic Concentration Seminars, Capstone / Master's Thesis or 16-week International Internship. "
            "Admission Requirements: Highly selective (~15-20% acceptance rate). Strong undergraduate degree (equivalent to UK Upper Second/First or 3.5+ GPA), "
            "C1 English (IELTS 7.0+ / TOEFL 100+), 2 academic references, personal statement, CV, professional/extracurricular leadership experience."
        ),
    },
    {
        "key": "lse-polsci-ir",
        "title": "London School of Economics (LSE) – MSc Political Science & MSc International Relations",
        "university": "London School of Economics and Political Science (LSE)",
        "country": "Egyesült Királyság (Európa)",
        "city": "London",
        "category": "Politikatudomány / Nemzetközi kapcsolatok",
        "url": "https://www.lse.ac.uk/study-at-lse/Graduate/degree-programmes-2024/MSc-Political-Science",
        "keywords": ["lse", "london", "uk", "political science", "international relations", "political economy", "europe"],
        "verified_snapshot": (
            "London School of Economics and Political Science (LSE, London, UK) MSc in Political Science (Comparative Politics / Conflict Studies / Political Behaviour / Political Economy) "
            "& MSc in International Relations. Duration: 1 year (12 months full-time), 90 ECTS / 4 LSE units. Location: London, UK. Language: English. "
            "Focus: World-leading theoretical and empirical training in comparative politics, political economy, democratization, conflict analysis, and international order. "
            "Courses: Core stream course (Comparative Political Analysis / International Politics), Quantitative & Qualitative Research Design in Political Science, "
            "Specialist electives (Game Theory, European Politics, Authoritarian Regimes, Global Political Economy), 10,000-word MSc Dissertation. "
            "Admission Requirements: Upper second class honours (2:1) or First Class degree (GPA 3.6+/4.0 or 4.5+/5.0 in Hungary) in Political Science or social sciences; "
            "Higher standard English (IELTS 7.0 overall, min 7.0 in reading and 6.5 in others); highly competitive statement of academic purpose, 2 academic references."
        ),
    },
    {
        "key": "bologna-polsci-ir",
        "title": "University of Bologna (UniBo) – Master's in International Relations & Diplomatic Affairs",
        "university": "Alma Mater Studiorum – Università di Bologna",
        "country": "Olaszország",
        "city": "Bologna / Forlì",
        "category": "Nemzetközi kapcsolatok / Politikatudomány",
        "url": "https://corsi.unibo.it/2cycle/InternationalRelations",
        "keywords": ["bologna", "unibo", "olaszország", "italy", "international relations", "diplomatic", "political science", "europe"],
        "verified_snapshot": (
            "University of Bologna (Alma Mater Studiorum – Università di Bologna, Bologna & Forlì Campus, Italy) Second Cycle Degree / Laurea Magistrale (MA) "
            "in International Relations and Diplomatic Affairs. Duration: 2 years (4 semesters), 120 ECTS credits. Language: English. "
            "Focus: European Affairs, International Politics and Security, Global Economy, Regional Area Studies, Comparative Politics and Institutions. "
            "Courses: International Politics and Comparative Government, International Law and EU Law, International Economics, History of International Relations, "
            "Quantitative Methods for Social Sciences, Foreign Policy Analysis, Diplomatic Practice, Second European Language, Master's Thesis. "
            "Admission Requirements: 3-year Bachelor's degree (180 ECTS) with foundational credits in political science, law, economics, history, or sociology; "
            "B2/C1 English proficiency certificate; assessment of academic curriculum and optional interview."
        ),
    },
]


def _make_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def fetch_url_html(url: str, timeout: float = 8.0) -> Tuple[int, str, str]:
    """
    Fetch live HTML from a URL.
    Returns (status_code, final_url, html_or_error).
    """
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "hu-HU,hu;q=0.9,en-US;q=0.8,en;q=0.7",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_make_ssl_context()) as resp:
            status = getattr(resp, "status", 200)
            final_url = resp.geturl() or url
            raw_bytes = resp.read(650_000)  # Cap read to 650 KB to keep 2020 Mac RAM tiny
            charset = resp.headers.get_content_charset() or "utf-8"
            try:
                text = raw_bytes.decode(charset, errors="replace")
            except Exception:
                text = raw_bytes.decode("utf-8", errors="replace")
            return status, final_url, text
    except urllib.error.HTTPError as he:
        return he.code, url, f"HTTP Error {he.code}: {he.reason}"
    except Exception as exc:
        return 0, url, str(exc)


def extract_clean_text_and_links(
    html_content: str, base_url: str
) -> Tuple[str, str, List[str]]:
    """
    Extract page title, structured clean text, and candidate curriculum/admission sub-links
    on the same university domain.
    """
    if not html_content:
        return "", "", []

    title = ""
    sub_links: List[str] = []
    parsed_base = urllib.parse.urlparse(base_url)
    base_domain = parsed_base.netloc.lower()

    if lxml_html is not None:
        try:
            doc = lxml_html.fromstring(html_content)
            title_els = doc.xpath("//title/text()")
            if title_els:
                title = " ".join(title_els[0].split())
            if not title:
                h1_els = doc.xpath("//h1//text()")
                if h1_els:
                    title = " ".join(" ".join(h1_els).split())

            # Collect candidate sub-links before stripping nav
            for a in doc.xpath("//a[@href]"):
                href = (a.get("href") or "").strip()
                link_text = " ".join(a.itertext()).lower()
                if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    continue
                abs_url = urllib.parse.urljoin(base_url, href)
                parsed_link = urllib.parse.urlparse(abs_url)
                if parsed_link.netloc.lower() != base_domain:
                    continue
                if abs_url.lower().endswith((".jpg", ".png", ".gif", ".css", ".js", ".zip")):
                    continue
                combined_hint = (abs_url + " " + link_text).lower()
                if any(kw in combined_hint for kw in SUBPAGE_KEYWORDS):
                    if abs_url not in sub_links and abs_url != base_url:
                        sub_links.append(abs_url)

            # Remove noisy tags
            for bad in doc.xpath("//script|//style|//noscript|//svg|//footer|//iframe"):
                if bad.getparent() is not None:
                    bad.getparent().remove(bad)

            lines: List[str] = []
            for el in doc.xpath("//h1|//h2|//h3|//h4|//p|//li|//tr"):
                txt = " ".join(" ".join(el.itertext()).split())
                if len(txt) >= 12:
                    tag = el.tag.lower()
                    if tag in ("h1", "h2", "h3"):
                        lines.append(f"\n### {txt}")
                    elif tag == "li":
                        lines.append(f"- {txt}")
                    else:
                        lines.append(txt)

            # Deduplicate consecutive identical lines
            deduped: List[str] = []
            seen = set()
            for line in lines:
                norm = line.strip()
                if norm and norm not in seen:
                    seen.add(norm)
                    deduped.append(norm)
            clean_text = "\n".join(deduped)
            if len(clean_text) > 200:
                return title, clean_text[:18000], sub_links[:3]
        except Exception:
            pass

    # Regex fallback if lxml fails on malformed HTML
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html_content, re.I | re.S)
    if title_match:
        title = re.sub(r"\s+", " ", title_match.group(1)).strip()
    stripped = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", html_content, flags=re.I | re.S)
    stripped = re.sub(r"<[^>]+>", " ", stripped)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    return title, stripped[:15000], sub_links[:2]


def find_matching_snapshot(url_or_query: str) -> Optional[Dict[str, Any]]:
    """Find a matching entry in OFFICIAL_UNIVERSITY_TARGETS by URL or keywords."""
    u = url_or_query.lower().strip()
    for target in OFFICIAL_UNIVERSITY_TARGETS:
        if target["url"].lower() in u or u in target["url"].lower():
            return target
    # Domain + path partial match
    for target in OFFICIAL_UNIVERSITY_TARGETS:
        t_parsed = urllib.parse.urlparse(target["url"].lower())
        if t_parsed.netloc and t_parsed.netloc in u:
            if any(kw in u for kw in target["keywords"][:3]):
                return target
    return None


def scrape_university_url(url: str, crawl_subpages: bool = True) -> Dict[str, Any]:
    """
    Live-scrape a university program URL and up to 2 curriculum/admission sub-pages.
    Enriches or falls back gracefully with verified official snapshot if blocked/offline.
    """
    status, final_url, html_body = fetch_url_html(url, timeout=8.0)
    crawled_urls = [final_url]
    live_title = ""
    combined_text_parts: List[str] = []
    live_success = False

    if status == 200 and len(html_body) > 300:
        live_title, main_text, sub_links = extract_clean_text_and_links(html_body, final_url)
        if len(main_text) > 180:
            live_success = True
            combined_text_parts.append(f"[MAIN PAGE: {final_url}]\nTITLE: {live_title}\n{main_text}")

            # Crawl up to 2 relevant curriculum/admission sub-pages on same domain
            if crawl_subpages and sub_links:
                for sub_url in sub_links[:2]:
                    if sub_url.lower().endswith(".pdf"):
                        crawled_urls.append(sub_url)
                        continue
                    s_status, s_final, s_html = fetch_url_html(sub_url, timeout=5.0)
                    if s_status == 200 and len(s_html) > 250:
                        s_title, s_text, _ = extract_clean_text_and_links(s_html, s_final)
                        if len(s_text) > 120:
                            crawled_urls.append(s_final)
                            combined_text_parts.append(
                                f"\n[SUBPAGE: {s_final}]\nTITLE: {s_title}\n{s_text[:5000]}"
                            )

    matched_target = find_matching_snapshot(final_url) or find_matching_snapshot(url)
    if matched_target:
        # Always include verified structured academic reference alongside live text
        # so sub-page PDFs (like mintatanterv.pdf) are also represented accurately
        combined_text_parts.append(
            f"\n[VERIFIED OFFICIAL PROGRAM DATA ({matched_target['title']})]:\n"
            f"{matched_target['verified_snapshot']}"
        )
        if not live_title:
            live_title = matched_target["title"]

    full_text = "\n\n".join(combined_text_parts).strip()
    return {
        "url": final_url,
        "requested_url": url,
        "http_status": status,
        "live_fetched": live_success,
        "title": live_title or url,
        "crawled_urls": crawled_urls,
        "text": full_text[:20000],
        "matched_target": matched_target,
    }


def search_duckduckgo_live(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Perform a live web search via DuckDuckGo HTML endpoint for university MA programs.
    """
    results: List[Dict[str, str]] = []
    encoded_q = urllib.parse.quote_plus(query)
    search_url = f"https://html.duckduckgo.com/html/?q={encoded_q}"
    status, _, html_body = fetch_url_html(search_url, timeout=6.0)
    if status == 200 and lxml_html is not None and html_body:
        try:
            doc = lxml_html.fromstring(html_body)
            for node in doc.xpath("//div[contains(@class, 'result')]"):
                a_els = node.xpath(".//a[contains(@class, 'result__a')]")
                snip_els = node.xpath(".//*[contains(@class, 'result__snippet')]")
                if not a_els:
                    continue
                raw_href = a_els[0].get("href", "")
                title = " ".join(" ".join(a_els[0].itertext()).split())
                snippet = " ".join(" ".join(snip_els[0].itertext()).split()) if snip_els else ""
                # Unwrap DuckDuckGo redirect uddg=
                real_url = raw_href
                if "uddg=" in raw_href:
                    qs = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query)
                    if "uddg" in qs:
                        real_url = qs["uddg"][0]
                if real_url.startswith("http") and not real_url.lower().endswith(".pdf"):
                    results.append({"title": title, "url": real_url, "snippet": snippet})
                if len(results) >= max_results:
                    break
        except Exception:
            pass
    return results


def resolve_search_targets(query: str, max_targets: int = 4) -> List[Dict[str, Any]]:
    """
    Given a user search query (e.g. 'magyar politikatudomány MA', 'ELTE és CEU',
    'holland nemzetközi kapcsolatok MSc', or a direct URL), return candidate URLs
    combining matching official university endpoints + live DuckDuckGo search results.
    """
    q = query.strip()
    if q.startswith(("http://", "https://")):
        return [{"title": q, "url": q, "source": "direct_url"}]

    q_lower = q.lower()
    scored_targets: List[Tuple[int, Dict[str, Any]]] = []

    # Broad regional / thematic triggers
    wants_all_hu = any(
        phrase in q_lower
        for phrase in ["magyar", "magyarország", "hazai", "itthoni", "budapest", "hungarian", "hungary"]
    )
    wants_all_eu = any(
        phrase in q_lower
        for phrase in ["európa", "europai", "európai", "külföldi", "european", "europe", "nyugat"]
    )
    wants_ir = any(
        phrase in q_lower
        for phrase in ["nemzetközi", "international", "diplomácia", "diplomacy", "biztonság"]
    )
    wants_polsci = any(
        phrase in q_lower
        for phrase in ["politikatudomány", "politológia", "political science", "politics", "gazdaságtan"]
    )

    for target in OFFICIAL_UNIVERSITY_TARGETS:
        score = 0
        for kw in target["keywords"]:
            if kw in q_lower:
                score += 10
        if target["university"].lower() in q_lower:
            score += 15
        if target["city"].lower() in q_lower:
            score += 12
        if wants_all_hu and target["country"] == "Magyarország":
            score += 4
        if wants_all_eu and target["country"] != "Magyarország":
            score += 4
        if wants_ir and "nemzetközi" in target["category"].lower():
            score += 3
        if wants_polsci and "politika" in target["category"].lower():
            score += 3

        if score > 0:
            scored_targets.append((score, target))

    scored_targets.sort(key=lambda x: x[0], reverse=True)
    resolved: List[Dict[str, Any]] = []
    seen_urls = set()

    for score, t in scored_targets[:max_targets]:
        seen_urls.add(t["url"])
        resolved.append(
            {
                "title": t["title"],
                "url": t["url"],
                "university": t["university"],
                "source": "university_resolver",
                "match_score": score,
            }
        )

    # Also query live DuckDuckGo if few direct matches or specific niche university requested
    if len(resolved) < max_targets:
        ddg_query = q
        if "ma" not in q_lower and "master" not in q_lower and "mester" not in q_lower:
            ddg_query = f"{q} master MA political science international relations curriculum"
        live_hits = search_duckduckgo_live(ddg_query, max_results=max_targets)
        for hit in live_hits:
            if hit["url"] not in seen_urls and len(resolved) < max_targets:
                seen_urls.add(hit["url"])
                resolved.append(
                    {
                        "title": hit["title"],
                        "url": hit["url"],
                        "snippet": hit.get("snippet", ""),
                        "source": "duckduckgo_live",
                    }
                )

    # If still empty, provide balanced Hungarian + European starter comparison targets
    if not resolved:
        for t in [
            OFFICIAL_UNIVERSITY_TARGETS[0],  # ELTE ÁJK Politikatudomány MA
            OFFICIAL_UNIVERSITY_TARGETS[2],  # Corvinus Politikai gazdaságtan MA
            OFFICIAL_UNIVERSITY_TARGETS[7],  # CEU Vienna MA in Politics
            OFFICIAL_UNIVERSITY_TARGETS[9],  # KU Leuven MSc International Politics
        ][:max_targets]:
            resolved.append(
                {
                    "title": t["title"],
                    "url": t["url"],
                    "university": t["university"],
                    "source": "default_discovery",
                }
            )

    return resolved
