# Grok Connector — český návod

Komunitní MCP konektor pro Home Assistant. Vybereš libovolné entity ke čtení a přidáš pojmenované akce v běžném editoru HA. Konektor nemá zabudované podmínky pro vrata ani jiné zařízení; podmínky si nastavíš v akcích, skriptech nebo automatizacích.

První beta verze `0.1.0b1` má lokální testy. Instalace nové integrace přes HACS a propojení s Grokem ještě vyžadují ověření na skutečném HA. [Podrobný návod a stav](../README.md).

## Instalace po zveřejnění

Potřebuješ HA 2026.9.4+, HACS a vzdálený přístup Nabu Casa. V HACS přidej vlastní repozitář `https://github.com/Jenik5/GrokConnectorForHomeAssistant`, typ **Integrace**. Stáhni verzi a restartuj HA. Pak v **Nastavení → Zařízení a služby → Přidat integraci** vyber **Grok Connector**.

Zadej HTTPS adresu Nabu Casa bez cesty a vyber jazyk nástrojů. Označ entity ke čtení; jejich typ není omezen. V **Konfigurovat → Akce → Přidat akci** zadej název, popis pro Groka a sekvenci akcí. Samotné zařazení entity do seznamu ke čtení neumožňuje její ovládání.

## Příklady akcí

- **Rozsviť světlo:** `light.turn_on` a cílová entita. Provede se přímo, i když už světlo svítí.
- **Spusť automatizaci:** `automation.trigger` a cílová automatizace. Nastav `skip_condition: false`, pokud se mají vyhodnotit podmínky automatizace.
- **Spusť skript:** `script.turn_on` a cílový skript. Skript běží podle své vlastní konfigurace.
- **Složitější akce:** doplň podmínky, větvení nebo další kroky standardním editorem HA.

Grok může vyvolat připravenou sekvenci, nemůže jí podstrčit jiný cíl ani parametry. Podmínky a rozsah sekvence určuješ ty. Konektor zveřejní stav, název, ID a případnou jednotku vybraných entit; ostatní atributy neposílá.

## Připojení Groka

V **Konfigurovat → Párovací kód** se zobrazí přesná adresa a jednorázový kód platný 10 minut. Adresa má tvar `https://tvoje-instance.ui.nabu.casa/api/grok_connector/mcp`. V Groku vytvoř vlastní MCP konektor a kód zadej v jeho přihlašovacím okně.

Další uživatel HA ani dlouhodobý HA token nejsou potřeba: konektor má vlastní přihlašovací údaje. Po změně entit či akcí se dosavadní přístup zruší a musíš Groka znovu spárovat. Změna jazyka přístup zachová. Tlačítko **Zrušit přístup Groka** ruší tokeny i rozpracované párování.

Nejdřív ověř dotaz na stav a porovnej ho s HA. Pak záměrně vyzkoušej jednu jednoduchou akci. Návrat sekvence sám nepotvrzuje fyzický výsledek. Dostupnost konektorů v Tesle musí podporovat také tamní aplikace Groka.

## Jazyky a další vývoj

Rozhraní HA, párovací stránka a popisy nástrojů mají EN/CS/DE/PL/SK. Další jazyk se přidá dvěma soubory `translations/<jazyk>.json` a `locales/<jazyk>.json`; nabídka jazyků ho najde automaticky. [Vývoj a překlady](../CONTRIBUTING.md).

Původní MCP integrace může zůstat nainstalovaná: nový konektor má samostatný název domény, adresu i úložiště. Jeho přístup se nepřenáší automaticky z jiné integrace.
