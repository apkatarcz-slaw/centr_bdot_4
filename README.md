# Centrum wtyczek BDOT10k / BDOO (QGIS 4.x)

Jedno okno z kafelkami ulubionych wtyczek - do pracy z danymi BDOT10k, BDOO,
GUGiK i z dowolnymi innymi wtyczkami QGIS.
Launcher **integruje** wtyczki - nie pobiera ani nie instaluje ich samodzielnie.

## Wymagania

- QGIS 4.0 – 4.99 (Python 3, PyQt6). Dla QGIS 3.x jest osobna wtyczka
  `centrum_bdot_bdoo` - *Centrum wtyczek BDOT10k / BDOO (QGIS 3.x)*.
- Ustawienia (grupy, kafelki, nazwy) są zapisywane w profilu QGIS 4 i nie są
  przenoszone z QGIS 3.
- Brak dodatkowych bibliotek Pythona - wszystko, czego używa wtyczka, jest częścią QGIS.
- Dostęp do internetu jest potrzebny tylko do sprawdzenia wersji w repozytorium
  QGIS i pobrania ikon niezainstalowanych wtyczek. Bez sieci launcher działa
  dla wtyczek już zainstalowanych.

## Lista startowa wtyczek

| Kafelek | Identyfikator w repozytorium QGIS |
|---|---|
| BDOT10k Import (QGIS 4.x) | `bdot10k_import_qgis4` |
| BDOT10k | `bdot10k` |
| BDOT10k_GML_SHP | `BDOT10k_GML_SHP_Loader` |
| Pobieracz danych GUGiK | `pobieracz_danych_gugik` |
| Walidator plików GML | `Walidator_plikow_gml` |
| Import BDOO (QGIS 4.x) | `BDOO_import_qgis4` |
| BDOO_GML | `BDOO_GML_Loader` |

Wtyczki, które nie mają jeszcze wersji dla QGIS 4 (np. BDOT10k_GML_SHP -
według repozytorium działa tylko do QGIS 3.99), są pokazywane jako wyszarzone
kafelki *Niedostępna dla tej wersji QGIS*. Gdy autor wyda wersję dla QGIS 4,
kafelek uaktywni się sam.

Listę zmieniasz w oknie launchera (patrz *Dodawanie i usuwanie wtyczek*).
Lista startowa jest zapisana w pliku `catalog.py` (`DEFAULT_PLUGINS`), a Twoja
lista - w ustawieniach QGIS.

## Instalacja

1. QGIS → *Wtyczki → Zarządzaj wtyczkami → Instaluj z pliku ZIP*.
2. Wskaż plik `centrum_bdot_bdoo_qgis4.zip` i kliknij *Zainstaluj wtyczkę*.
3. Ikona pojawi się na pasku narzędzi oraz w menu *Wtyczki → Centrum wtyczek
   BDOT10k / BDOO (QGIS 4.x)*.


## Obsługa

Kliknięcie kafelka:

| Stan kafelka | Co się dzieje |
|---|---|
| Zainstalowana (zielony) | Otwiera wtyczkę (polecenie albo algorytm Processing). Gdy jest kilka możliwości, pokazuje listę do wyboru. |
| Dostępna aktualizacja (pomarańczowa strzałka) | Otwiera wtyczkę. Przycisk *Aktualizuj* otwiera Menedżer wtyczek na zakładce aktualizacji. |
| Wyłączona (szara) | Pyta „Włączyć ją teraz?”, po potwierdzeniu włącza i otwiera wtyczkę. |
| Nie zainstalowana (czerwony) | Komunikat „Zainstaluj wtyczkę z repozytorium” i otwarcie Menedżera wtyczek z wpisaną nazwą. Instalację zatwierdzasz sam. |
| Błąd wtyczki | Pokazuje przyczynę i proponuje otwarcie Menedżera wtyczek. |
| Niedostępna dla tej wersji QGIS | Tylko informacja. |
| Znaczek EXP | W repozytorium jest nowsza wersja eksperymentalna. Aby ją zobaczyć: Menedżer wtyczek → *Ustawienia* → *Pokaż także wtyczki eksperymentalne*. |

Prawy przycisk myszy na kafelku: *Otwórz*, *Pokaż w Menedżerze wtyczek*,
*Strona wtyczki w repozytorium QGIS*.

Przyciski: *Zamknij* (lewy dolny róg), *Odśwież*, *Aktualizuj*, *Otwórz*
(prawy dolny róg); w wierszu z *Log*: *Skaluj ikony* i *Wyłącz ikony*;
*Dodaj wtyczkę*, *Usuń wtyczkę*, *Duplikuj ikonę*
(i w grupach 2–10 *Usuń grupę*) obok wyszukiwarki.
Okno można minimalizować, maksymalizować i przewijać na małych ekranach.

## Dodawanie i usuwanie wtyczek

- **Dodaj wtyczkę** pokazuje wtyczki **zainstalowane** w QGIS z repozytorium
  (także wyłączone, oznaczone na szaro). Wtyczki wbudowane w QGIS (np.
  Processing) nie są pokazywane. Wtyczki BDOO / BDOT10k są na górze
  i pogrubione. Można zaznaczyć kilka (Ctrl+klik), dwuklik dodaje od razu.
  Nową wtyczkę najpierw zainstaluj w Menedżerze wtyczek, potem dodaj kafelek.
- **Usuń wtyczkę** (albo prawy przycisk na kafelku → *Usuń kafelek*) usuwa
  kafelek po potwierdzeniu. Sama wtyczka zostaje zainstalowana w QGIS.
- **Przywróć listę startową** (w oknie *Dodaj wtyczkę*) wraca po
  potwierdzeniu do 7 wtyczek startowych z oryginalnymi nazwami i kolejnością.

## Kolejność kafelków

- Kafelki układasz **przeciąganiem myszą**.
- Launcher liczy uruchomienia każdej wtyczki i **przy każdym otwarciu okna**
  ustawia najczęściej używane na początku; kafelki z równą liczbą uruchomień
  zostają w kolejności z przeciągania. W trakcie pracy kafelki się nie
  przestawiają.
- Przeciągnięcie kafelka zeruje liczniki - od tej chwili obowiązuje Twoja
  kolejność, aż launcher zbierze nowe dane.

## Zmiana nazw

- **Kafelek:** prawy przycisk → *Zmień nazwę kafelka…* albo *Przywróć
  oryginalną nazwę*. Początkowo kafelek ma oryginalną nazwę wtyczki.
- **Launcher:** prawy przycisk na tytule okna → *Zmień nazwę launchera…*
  albo *Przywróć oryginalną nazwę*. Nowa nazwa pojawia się w tytule okna
  i na ikonie paska narzędzi. Pusta nazwa przywraca oryginalną.

## Grupy (maksymalnie 10)

- **Duplikuj ikonę** tworzy kolejną grupę (numer 2–10) z własną ikoną na
  pasku narzędzi QGIS i w menu *Wtyczki*. Ikony mają nałożony numer grupy.
  Przy tworzeniu wpisujesz opis tematyczny (np. Raster, Wektor, AI,
  Klasyfikacja) - pojawia się w dymku ikony i w tytule okna grupy.
- Nowa grupa startuje pusta (tylko kafel autora). Ta sama wtyczka może być
  w kilku grupach. Każda grupa ma własną listę, kolejność, nazwy kafelków
  i liczniki użycia; log jest wspólny.
- Opis grupy zmieniasz prawym przyciskiem na tytule okna grupy.
- **Usuń grupę** (w oknie grupy 2–10) usuwa grupę i jej ikonę po
  potwierdzeniu. Grupy 1 nie można usunąć.
- *Przywróć listę startową* w grupie 1 wraca do 7 wtyczek startowych,
  w grupach 2–10 czyści grupę.

## Ukrywanie ikon na paskach narzędzi (Wyłącz ikony)

- Przycisk **Wyłącz ikony** (w wierszu z *Log*, po prawej) chowa z pasków
  narzędzi QGIS ikony wszystkich wtyczek, które mają kafelek w którejkolwiek
  grupie. Napis zmienia się na **Włącz ikony** - kolejne kliknięcie
  przywraca ikony. Przełącznik jest wspólny dla wszystkich grup.
- **Domyślnie ikony są widoczne.** Wybór jest zapamiętywany po ponownym
  uruchomieniu QGIS.
- Menu QGIS (Wtyczki, Wektor, Raster…) się nie zmienia, a wtyczka działa
  normalnie - kafelek uruchamia ją tak jak ikona. Jeśli wtyczka ma własny
  pasek narzędzi, chowany jest cały pasek.
- **Wyjątki:** gdy ikony są wyłączone, prawy przycisk na kafelku →
  *Pokaż ikonę na pasku narzędzi* zostawia ikonę tej wtyczki na pasku.
  Gdy ikony są włączone, ta opcja jest nieaktywna.
- Po usunięciu kafelka (z ostatniej grupy) ikony wtyczki wracają na swoje
  pierwotne miejsce.
- Przy wyłączonych ikonach launcher chowa je po każdym starcie QGIS, gdy
  wczytają się wszystkie wtyczki (przez ułamek sekundy mogą być widoczne),
  oraz po każdym odświeżeniu okna (np. po aktualizacji wtyczki).
- **Wyłączenie lub odinstalowanie launchera przywraca wszystkie ikony.**
- Launcher niczego nie usuwa ani nie zmienia w innych wtyczkach. Nie są
  ukrywane panele boczne wtyczek ani algorytmy w panelu Processing.

## Rozmiar kafelków (Skaluj ikony)

- Przycisk **Skaluj ikony** (na środku wiersza z *Log*) otwiera suwak
  połączony z okienkiem do wpisania wartości. Rozmiar kafelków z wtyczkami
  zmienia się od **70% do 100%** (co 1%), od razu podczas przesuwania.
- Wartości spoza zakresu nie da się wpisać. Aktualny rozmiar widać na
  przycisku, np. *Skaluj ikony (80%)*.
- Rozmiar jest wspólny dla wszystkich grup i okna *Inne wtyczki autora*
  i zostaje zapamiętany po ponownym uruchomieniu QGIS.
- Kafel *Inne wtyczki autora* zachowuje swój rozmiar.

## Wtyczki uruchamiane z panelu Processing (algorytmów)

- Launcher rozpoznaje, jak uruchamia się wtyczka: polecenia w menu / na
  pasku narzędzi, algorytmy w panelu Processing, albo jedno i drugie.
- Algorytmy wtyczki są wykrywane po jej dostawcy Processing (zapisanym
  w wtyczce, np. `self.provider`, albo zdefiniowanym w jej katalogu).
- Kliknięcie kafelka:
  - jeden algorytm → od razu otwiera się okno algorytmu (jak dwuklik
    w panelu Processing),
  - kilka algorytmów → lista do wyboru (z nazwą grupy),
  - polecenia i algorytmy → wspólna lista w dwóch częściach.
- Dymek kafelka pokazuje liczbę i nazwy algorytmów.
- Prawy przycisk → **Pokaż w panelu Processing** otwiera panel z wpisaną
  nazwą algorytmu (przy kilku - identyfikatorem dostawcy).
- Wymaga włączonej wbudowanej wtyczki Processing (domyślnie włączona).
  *Wyłącz ikony* nie dotyczy algorytmów - zostają w panelu Processing.

## Kafel „Inne wtyczki autora”

- Jest w każdej grupie, zawsze w prawym górnym rogu obszaru kafelków,
  o 25% mniejszy od pozostałych. Nie można go usunąć, przenieść ani
  przemianować.
- Otwiera mały launcher z wtyczkami autora (Sławek Szymański) z repozytorium
  QGIS: stan, otwieranie, aktualizacja tak jak w oknie grupy. Pokazywane są
  tylko wersje zgodne z zainstalowanym QGIS (instalator QGIS sam pomija
  niezgodne). Nowo opublikowana wtyczka autora pojawia się sama, bez
  aktualizacji launchera. Bez internetu - tylko zainstalowane wtyczki autora.

## Dymki i tytuł okna

- Dymki są dwujęzyczne: tekst polski, a pod nim angielski (na niebiesko).
  Przyciski, komunikaty i log są po polsku.
- Pasek tytułu pokazuje nazwę launchera i grupy. Tuż pod nim, w oknie, jest
  podpowiedź w dwóch liniach: *(W celu zmiany nazwy wtyczki najedź na jej
  nazwę w oknie i kliknij prawym klawiszem)*, a pod nią *(To rename, hover
  over its name in the window and right-click)*.

## Informacja o nowych wtyczkach BDOO / BDOT10k

Po pobraniu listy z repozytorium QGIS launcher szuka wtyczek, które mają
„BDOO” lub „BDOT” w nazwie, identyfikatorze, opisie lub tagach i nie mają
kafelka w żadnej grupie. Nowo wykryta wtyczka jest zapisywana w logu,
a czerwony komunikat o niej pojawia się na **5 sekund przy 3 kolejnych
otwarciach** dowolnego okna launchera (licznik wspólny dla wszystkich grup),
potem już nie wraca. Pozostałe komunikaty znikają po 2 sekundach. Bez
internetu skanowanie nie działa.

## Log

- Panel *Log* w oknie (można zwinąć).
- Plik `centrum_bdot_bdoo.log` (UTF-8) w katalogu profilu QGIS
  (*Ustawienia → Profile użytkownika → Otwórz katalog aktywnego profilu*).
  Po przekroczeniu 1 MB poprzedni log trafia do `centrum_bdot_bdoo.log.1`.
- Zakładka *Centrum BDOT10k/BDOO* w panelu *Komunikaty* QGIS.
- Krótkie komunikaty w oknie znikają po 2 sekundach; ostrzeżenia są czerwone.

## Ustawienia zapamiętywane między sesjami

Dla każdej grupy osobno: rozmiar i położenie okna, tekst wyszukiwania,
wybrany filtr, widoczność logu, opis grupy, lista i kolejność kafelków, nazwy kafelków i launchera, liczniki
użycia oraz lista wtyczek już zgłoszonych jako nowe.

## Bezpieczeństwo

Launcher nie pobiera ani nie uruchamia kodu z internetu. Dane o wersjach
pochodzą z wbudowanego instalatora QGIS (`pyplugin_installer`); z sieci
pobierane są wyłącznie obrazki ikon (`QgsNetworkAccessManager`, ustawienia proxy
QGIS), zapisywane w `cache/centrum_bdot_bdoo` w profilu QGIS.

## Licencja

GNU General Public License v2.0 lub nowsza (plik `LICENSE`).

## Historia zmian

- **1.0** - pierwsza wersja dla QGIS 4.x (PyQt6): kafelki wtyczek (polecenia
  i algorytmy Processing), grupy 1–10, dodawanie / usuwanie i zmiana nazw
  kafelków, kolejność przeciąganiem i według użycia, *Skaluj ikony*
  (70–100%), *Wyłącz / Włącz ikony* na paskach narzędzi, kafel *Inne
  wtyczki autora*, informacja o nowych wtyczkach BDOO / BDOT10k, dymki PL/EN.
