# Springtrap for Windows (prototype)

První desktopový základ pro Windows 10/11. Používá Python a knihovny dodávané s Windows/Pythonem; žádné balíčky z pipu nejsou zatím potřeba.

## Co tato verze obsahuje
- samostatné okno s jednoduchým kresleným avatarem Springtrapa a chatem;
- velké úvodní okno pro API klíč s uložením šifrovaným přes Windows DPAPI;
- volání Gemini API přes modul `brain/gemini_brain.py`;
- omezenou konverzační historii během běhu aplikace;
- volitelnou hlasovou odpověď přes Windows System.Speech;
- pokus o hlasový vstup přes Windows System.Speech Recognition;
- snímek primární obrazovky pouze po potvrzení uživatelem a odeslání do Gemini k analýze.

## Požadavky
- Windows 10/11;
- Python 3.10 nebo novější, při instalaci zaškrtnout **Add Python to PATH**;
- Gemini API key. Použití API může mít kvóty nebo náklady podle účtu a aktuálních podmínek.

## Spuštění
1. Stáhni nebo naklonuj větev `springtrap-rewrite` a otevři složku `springtrap`.
2. Dvakrát klikni na `start-springtrap.bat`.
3. Při prvním spuštění se otevře velké okno pro vložení Gemini API klíče. Klíč se při psaní skryje a uloží se šifrovaně pomocí Windows DPAPI do profilu aktuálního uživatele. Při dalších spuštěních se znovu nezadává. V aplikaci ho lze změnit tlačítkem **API klíč**.
4. Klíč neposílej do chatu, nevkládej ho do GitHubu a nesdílej složku s uloženým klíčem. Používá se účet Google, kvóty a podmínky jeho vlastníka.

Pokud Python příkaz nefunguje, zkus `py .\app.py`.

## Hlas
Tlačítko **Mluvit** využívá vestavěné Windows Speech Recognition. Dostupné jazyky a mikrofony závisí na nastavení Windows; čeština nemusí být na každém počítači podporována. Hlasový výstup používá hlas nainstalovaný ve Windows, takže český hlas není zaručen.

## Soukromí
Snímek obrazovky se pořizuje pouze po potvrzení dialogu a posílá se do Gemini API. Zatím není implementováno automatické sledování obrazovky, režim Nerušit, automatické spuštění Windows, ukládání dlouhodobé paměti ani ovládání her/počítače.

## Stav testování
Změny jsou zapsané v repozitáři, ale nebyly spuštěny ani otestovány na cílovém notebooku. Aplikace zatím nemá skutečný 3D model, animace postav ani originální herní hlasy; avatar je kreslený a hlasový výstup používá Windows TTS. Toto je rozšířený prototyp, nikoli hotový instalátor.
