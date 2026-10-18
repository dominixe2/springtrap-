# Springtrap — nový začátek

Tato složka je čistý začátek Springtrap projektu. Původní aplikace JARVIS mimo tuto složku zatím zůstává nedotčená; prototyp je na větvi `springtrap-rewrite`, nikoli na `main`.

## První avatar prototyp
Otevři `avatar-prototype.html` v prohlížeči. Obsahuje stylizovanou animovanou postavu, pohyb očí podle kurzoru a několik ukázkových reakcí.

## Co zatím funguje
- CSS avatar s idle animací a mrkáním
- sledování kurzoru očima
- tlačítka s ukázkovými reakcemi

## Co zatím nefunguje
- nejde o skutečný 3D model Springtrapa
- nejde o samostatné průhledné okno na ploše Windows
- není zapojen mikrofon, hlasová AI, snímání obrazovky ani skutečná analýza her

## Další milníky
1. Ověřit prototyp a založit desktopový obal pro Windows.
2. Přidat průhledné okno a automatické spuštění po přihlášení.
3. Přidat hlasové vstupy/výstupy.
4. Přidat výslovně povolené snímání obrazovky a analýzu na požádání.
5. Přidat opatrné průběžné reakce a nastavení soukromí.


## Windows desktop prototype

Byl přidán první samostatný Windows GUI prototyp do [`app.py`](app.py). Podrobný návod ke spuštění, požadavkům, hlasu a soukromí je v [`README-WINDOWS.md`](README-WINDOWS.md). Stav a další milníky sleduje [`TODO.md`](TODO.md).

Automatické kontroly syntaxe a offline testy jsou definované v [GitHub Actions workflow](../.github/workflows/springtrap-checks.yml). Jejich zelený výsledek neznamená, že byla aplikace spuštěna na tvém notebooku nebo že funguje API klíč.
