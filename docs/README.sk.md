# Grok Connector — slovenský návod

Komunitný konektor MCP sprístupní vybrané entity Home Assistantu na čítanie a pomenované sekvencie akcií na vykonanie. Vybrať možno ľubovoľný typ entity. Podmienky určuješ ty v akciách, skriptoch alebo automatizáciách HA.

Prvé stabilné vydanie má verziu `2026.10.4.1` a vychádza z otestovanej bety `0.1.0b7`. V beta verziách prešli testy, GitHub CI, inštalácia cez HACS a overenie nastavenia aj editora akcií v HA. Párovanie a čítanie stavov cez Nabu Casa funguje vo webovom Groku v Chrome; používateľ potvrdil tiež rozsvietenie a zhasnutie svetla. Klient v Tesle a ďalšie akcie vyžadujú vlastné praktické overenie. Stabilné vydanie nevyžaduje zapnutie beta verzií v HACS. [Podrobný návod a stav](../README.md).

## Nastavenie cez HACS

Potrebuješ HA 2026.9.4+, HACS a verejný HTTPS prístup cez Nabu Casa alebo vlastnú doménu s platným TLS certifikátom. V HACS pridaj `https://github.com/Jenik5/GrokConnectorForHomeAssistant` ako vlastný repozitár typu **Integrácia**, stiahni verziu a reštartuj HA. Pridaj **Grok Connector** v **Nastavenia → Zariadenia a služby**.

Zadaj verejnú HTTPS adresu bez cesty, napr. `https://tvoja-instancia.ui.nabu.casa` alebo `https://ha.example.org:8125`, a vyber jazyk nástrojov MCP. Podpora vlastných domén je dostupná od verzie `2026.10.5.1`; staršie vydanie `2026.10.4.1` zostáva obmedzené na Nabu Casa. Adresa musí byť dostupná Groku a mať platný certifikát. Port je súčasťou oprávnenia; zmena adresy vyžaduje nové párovanie. [Vlastná adresa a reverzná proxy](../README.md#using-your-own-public-address).

Vyber entity na čítanie. V **Konfigurovať → Akcie** pridaj názov, opis pre Groka a sekvenciu v editore HA. Zaradenie entity do zoznamu na čítanie samo osebe neumožňuje jej ovládanie.

## Príklady akcií

- Rozsvietenie svetla: `light.turn_on` s pevným cieľom. Akcia sa vykoná aj vtedy, keď už svetlo svieti.
- Spustenie automatizácie: `automation.trigger`; nastav `skip_condition: false`, ak sa majú vyhodnotiť jej podmienky.
- Spustenie skriptu: `script.turn_on`. Existujúci skript určuje vlastný priebeh.
- Ďalšie akcie a podmienky: priprav ich v bežnom editore HA.

Grok môže vyvolať pripravený nástroj bez dodatočných cieľov alebo parametrov. Zoznam na čítanie obmedzuje zdieľané údaje; rozsah nakonfigurovanej akcie určuje jej sekvencia.

## Pripojenie Groka

**Konfigurovať → Párovací kód** ukáže presnú adresu MCP a jednorazový kód platný desať minút. Adresa má tvar `https://tvoja-instancia.ui.nabu.casa/api/grok_connector/mcp`. V Groku vytvor vlastný konektor MCP a kód zadaj v jeho autorizačnom okne.

Ďalší používateľ HA ani dlhodobý token HA nie sú potrební. Konektor vydáva vlastné prihlasovacie údaje. Zmena entít či akcií zruší doterajší prístup a vyžaduje nové párovanie. Zmena samotného jazyka prístup zachová. **Zrušiť prístup Groka** zneplatní tokeny aj rozpracovanú autorizáciu.

Najskôr over čítanie stavu a porovnaj ho s HA. Potom zámerne otestuj jednu jednoduchú akciu. Návrat sekvencie nepotvrdzuje fyzický výsledok. Dostupnosť v Tesle závisí aj od schopností jej klienta Groka. Iná integrácia MCP môže zostať nainštalovaná súčasne.

Jazyky EN/CS/DE/PL/SK sú pripravené. Ďalší jazyk pridáš dvoma súbormi v `translations` a `locales`; ponuka ho nájde automaticky. [Preklady a vývoj](../CONTRIBUTING.md).
