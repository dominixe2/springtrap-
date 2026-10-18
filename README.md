# Springtrap Desktop Buddy

Samostatný prototyp desktopového společníka pro Windows 10/11. Projekt je oddělený od JARVIS: tento repozitář obsahuje pouze Springtrapa.

## Co obsahuje
- Windows chat aplikaci v Pythonu/Tkinteru (app.py).
- Gemini API pro konverzaci (brain/gemini_brain.py).
- Šifrované lokální uložení API klíče přes Windows DPAPI (key_store.py).
- 3D avatar laboratoř (avatar-3d.html) a starší animovaný prototyp (avatar-prototype.html).
- Volitelnou analýzu snímku obrazovky po výslovném kliknutí uživatele.

## Spuštění na Windows
1. Nainstaluj Python 3.10 nebo novější z https://www.python.org/downloads/windows/ a při instalaci zaškrtni Add Python to PATH.
2. Stáhni tento repozitář přes Code → Download ZIP a rozbal ZIP.
3. Dvakrát klikni na start-springtrap.bat nebo spusť v PowerShellu: python app.py
4. Při prvním spuštění vlož Gemini API klíč z https://aistudio.google.com/apikey. Klíč se uloží šifrovaně pro aktuální účet Windows. Lze jej změnit tlačítkem API klíč.

Aplikace používá Python standard library, takže není potřeba instalovat balíčky přes pip. Připojení k internetu je potřeba pro Gemini; 3D laboratoř načítá Three.js z CDN.

## Co je prototyp a co ještě ne
- Chat s Gemini a čtení odpovědí přes hlasové funkce Windows jsou prototypové funkce.
- 3D avatar se otevírá v prohlížeči, není to zatím průhledné always-on-top okno na ploše.
- Aplikace zatím nemá skutečnou automatickou detekci her ani autonomní ovládání počítače.
- Snímek obrazovky se analyzuje až po kliknutí uživatele. Nepředstíráme nepřetržité sledování.

## Soubory
- README-WINDOWS.md: detailní návod pro Windows.
- TODO.md: známá omezení a další kroky.
- CHARACTER-ASSET-PIPELINE.md: plán práce s modely postav.
- brain/: Gemini klient.
- tests/: offline testy.

## Bezpečnost
Nikdy necommituj API klíč ani soubor s tajnými údaji. Veřejné issue a logy nesmí obsahovat API klíče. Ovládání počítače nebo automatické akce budou vyžadovat samostatné, výslovné povolení.