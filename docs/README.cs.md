# Grok Connector — český návod

Komunitní MCP konektor pro Home Assistant. Vybereš libovolné entity ke čtení a přidáš pojmenované akce v běžném editoru HA. Konektor nemá zabudované podmínky pro vrata ani jiné zařízení; podmínky si nastavíš v akcích, skriptech nebo automatizacích.

První stabilní vydání má verzi `2026.10.4.1` a vychází z otestované bety `0.1.0b7`. V beta řadě prošly testy, GitHub CI, instalace přes HACS a ověření nastavení i editoru akcí v HA. Párování a čtení stavů přes Nabu Casa funguje ve webovém Groku v Chrome; uživatel potvrdil také rozsvícení a zhasnutí světla. Klient v Tesle a další akce vyžadují vlastní praktické ověření. Pro stabilní vydání není potřeba zapínat beta verze v HACS. [Podrobný návod a stav](../README.md).

## Instalace přes HACS

Potřebuješ HA 2026.9.4+, HACS a veřejný HTTPS přístup přes Nabu Casa nebo vlastní doménu s platným TLS certifikátem. V HACS přidej vlastní repozitář `https://github.com/Jenik5/GrokConnectorForHomeAssistant`, typ **Integrace**. Stáhni verzi a restartuj HA. Pak v **Nastavení → Zařízení a služby → Přidat integraci** vyber **Grok Connector**.

Zadej veřejnou HTTPS adresu bez cesty, např. `https://tvoje-instance.ui.nabu.casa` nebo `https://ha.example.org:8125`, a vyber jazyk nástrojů. Podpora vlastních domén je dostupná od verze `2026.10.5.1`; starší vydání `2026.10.4.1` zůstává omezené na Nabu Casa. Veřejná adresa musí být dostupná Groku a mít platný certifikát. Port je součástí oprávnění; změna adresy vyžaduje nové párování. [Vlastní adresa a reverzní proxy](../README.md#using-your-own-public-address).

Označ entity ke čtení; jejich typ není omezen. V **Konfigurovat → Akce → Přidat akci** zadej název, popis pro Groka a sekvenci akcí. Samotné zařazení entity do seznamu ke čtení neumožňuje její ovládání.

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
