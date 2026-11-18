# PolSci & IR MA AI Ügynök (Magyar + Európai Mesterszak Összesítő és Összehasonlító)

Valós idejű, élő webes keresésre és hivatalos egyetemi honlapok (URL-ek) automatikus elemzésére épülő **AI ügynök és interaktív webes alkalmazás**, amely összesíti és összehasonlítja a **magyarországi és európai egyetemek politikatudományi (Political Science MA/MSc)**, **nemzetközi tanulmányok (International Relations)**, **politikai gazdaságtan (Political Economy)**, **közpolitika (Public Policy)** és **biztonságpolitika** mesterszakjait.

Kifejezetten **2020-as Mac gépekre (Apple Silicon M1 és Intel Core i5/i7, 8 GB / 16 GB RAM)** és **teljesen helyi (offline-képes) Ollama LLM** futtatásra optimalizálva.

---

## 1. Az Összesítés és Összehasonlítás 7 Alappillére

Az AI ügynök minden megadott egyetemi URL-ből vagy élő keresési találatból az alábbi **7 dimenziót** nyeri ki és hasonlítja össze:

1. **Képzés és Egyetem (`program_name`, `university`, `degree_type`, `category`, `tuition`)**: Pontos szakmegnevezés (MA / MSc), kar, oktatási nyelv, állami ösztöndíjas / Corvinus Ösztöndíjas vagy EU-s tandíjinformációk.
2. **Képzés hossza (`duration`, `ects`)**: Félévek és évek száma (pl. 2 éves / 120 ECTS bolognai modell vs. 1 éves intenzív / 60–90 ECTS nyugat-európai mesterszakok).
3. **Képzés helye (`country`, `city`, `region_group`)**: Város, ország, valamint `Magyarország` vs. `Európa` régiós bontás.
4. **Szakmai fókusz (`focus`, `specializations`)**: Elméleti, összehasonlító, kvantitatív adatelemző, diplomáciai vagy közpolitikai profil, választható specializációkkal és modulokkal.
5. **Tárgyak (`courses`)**: A mintatanterv és a szakoldal alapján kinyert kötelező és törzstárgyak listája.
6. **Felvételi követelmények (`admission_requirements`, `admission_details`)**: Elfogadott BA diplomák és kreditek (pl. 40–60 kredit szabály), szóbeli felvételi tételek, nyelvvizsga (B2 vs. IELTS 7.0 / TOEFL 100 C1), kutatási terv és ajánlólevelek.
7. **A képzés nehézsége (`difficulty_score` 1.0–10.0 skálán + 4-dimenziós bontás)**:
   - *Felvételi szelektivitás* (`selectivity`)
   - *Módszertani és kvantitatív szigor* (`methodology` – statisztika, R programozás, ökonometria)
   - *Olvasmány- és féléves terhelés / intenzitás* (`workload`)
   - *Idegen nyelvi és akadémiai elvárások* (`language_academic`)

---

## 2. Miért fut gyorsan és kíméletesen egy 2020-as Mac-en?

Egy 2020-as MacBook Air / MacBook Pro / Mac mini (legyen akár **2020 végi Apple M1**, akár **2020 eleji Intel i5/i7**, 8 GB vagy 16 GB memóriával) esetén a legnagyobb kihívás a memóriahasználat (RAM / Swap). A projekt architektúrája ezért:

- **Könnyűsúlyú Ollama Modell Profilokat** használ (`qwen2.5:3b` ~1.9 GB RAM, `llama3.2:3b` ~2.0 GB RAM, vagy Intel 8 GB Mac-re `qwen2.5:1.5b` ~1.0 GB RAM).
- **Korlátozott kontextusablakot (`num_ctx: 4096`) és `keep_alive: "10m"`** memóriafelszabadítást állít be az Ollama API-n keresztül, így a Mac nem lassul be.
- **Zéró-overhead Vanilla HTML5/CSS/JS + FastAPI + SQLite** felépítést használ (nem igényel nehéz Electron vagy Node.js dev szervert, a teljes háttérfolyamat ~35 MB RAM-ot fogyaszt).
- **Hibrid Determinisztikus + Ollama Motor**: Ha az Ollama épp nem fut a háttérben, a beépített akadémiai szabálymotor akkor is valós időben letölti és elemzi az egyetemi URL-eket.

---

## 3. Telepítés és Indítás 2020-as Mac-en (3 lépésben)

### 1. lépés: Ollama telepítése (ha még nincs a gépeden)
Nyisd meg a **Terminal** alkalmazást a Mac-en, és futtasd:
```bash
brew install --cask ollama
```
*(Vagy töltsd le közvetlenül a [https://ollama.com/download/mac](https://ollama.com/download/mac) oldalról, és húzd az Applications mappába.)*

### 2. lépés: A repository klónozása
```bash
git clone <REPO_URL>
cd eu-hu-polsci-ma-agent
```

### 3. lépés: Indítás 1 kattintással vagy paranccsal
- **Finder-ből (Dupla kattintással):** Kattints duplán a **`start_mac.command`** fájlra!
- **Vagy Terminal-ból:**
```bash
chmod +x run_mac.sh start_mac.command
./run_mac.sh
```

A script automatikusan:
1. Felismeri a 2020-as Mac típusát (`arm64` M1 vagy `x86_64` Intel) és a RAM méretét,
2. Elindítja az Ollama szervert (`ollama serve`) és letölti az ajánlott `qwen2.5:3b` modellt (~1.9 GB),
3. Létrehozza a `.venv` Python környezetet és telepíti a függőségeket,
4. Elindítja a webes felületet a **`http://127.0.0.1:8000`** címen és megnyitja a böngésződben!

---

## 4. Támogatott Magyar és Európai Egyetemi Célpontok (Élő URL + Kereső)

A felületen bármilyen saját egyetemi URL beilleszthető vagy szabad szövegesen kereshető, emellett 1 kattintásos élő gyorsgombok érhetők el többek között:
- **Magyarország:** ELTE ÁJK (Politikatudomány MA), ELTE TáTK (Nemzetközi tanulmányok MA), Budapesti Corvinus Egyetem (Politikai gazdaságtan MA, Nemzetközi tanulmányok MA), PPKE BTK (Politikatudomány MA), NKE (Nemzetközi tanulmányok MA & Biztonság- és védelempolitika MA), PTE BTK (Politikatudomány & Nemzetközi tanulmányok MA).
- **Európa:** Central European University – CEU Vienna (MA in Politics, MA in International Relations), KU Leuven (MSc in International Politics), University of Amsterdam – UvA (MSc Political Science), Leiden University / The Hague (MSc Political Science), Sciences Po Paris – PSIA (Master in International Governance and Diplomacy), LSE London (MSc Political Science), University of Bologna (MA International Relations).

---

## 5. Tesztek futtatása

```bash
python3 -m unittest discover -s tests -v
```
