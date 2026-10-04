# Grok Connector — slovenský návod

Komunitný konektor MCP sprístupní vybrané entity Home Assistantu na čítanie a pomenované sekvencie akcií na vykonanie. Vybrať možno ľubovoľný typ entity. Podmienky určuješ ty v akciách, skriptoch alebo automatizáciách HA.

Beta `0.1.0b1` prešla testami, GitHub CI, inštaláciou cez HACS a overením natívneho nastavenia a editora akcií v HA. Párovanie a čítanie stavov cez Nabu Casa funguje aj vo webovom Groku v Chrome. Fyzické ovládanie zariadení a klient v Tesle ešte vyžadujú praktické overenie. [Podrobný návod a stav](../README.md).

## Nastavenie cez HACS

Potrebuješ HA 2026.9.4+, HACS a zapnutý vzdialený prístup Nabu Casa. V HACS pridaj `https://github.com/Jenik5/GrokConnectorForHomeAssistant` ako vlastný repozitár typu **Integrácia**, stiahni verziu a reštartuj HA. Pridaj **Grok Connector** v **Nastavenia → Zariadenia a služby**.

Zadaj HTTPS adresu Nabu Casa bez cesty, vyber jazyk nástrojov MCP a entity na čítanie. V **Konfigurovať → Akcie** pridaj názov, opis pre Groka a sekvenciu v editore HA. Zaradenie entity do zoznamu na čítanie samo osebe neumožňuje jej ovládanie.

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
