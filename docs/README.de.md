# Grok Connector — deutsche Anleitung

Dieser Community-MCP-Connector stellt ausgewählte Home-Assistant-Entitäten zum Lesen und benannte Aktionsfolgen zur Ausführung bereit. Alle Entitätstypen können ausgewählt werden. Bedingungen definierst du selbst in HA-Aktionen, Skripten oder Automationen.

Die erste stabile Version `2026.10.4.1` basiert auf der getesteten Beta `0.1.0b7`. Die Betaversionen haben Tests, GitHub CI, HACS-Installation und die native HA-Konfiguration einschließlich Aktionseditor bestanden. OAuth und das Lesen von Zuständen über Nabu Casa funktionieren mit Grok im Chrome-Browser; der Benutzer hat auch das Ein- und Ausschalten eines Lichts bestätigt. Der Tesla-Client und weitere Aktionen benötigen eigene Praxistests. Für stabile Versionen muss die Beta-Option in HACS nicht aktiviert sein. [Vollständige Dokumentation und Status](../README.md).

## Einrichtung über HACS

Voraussetzungen: HA 2026.9.4+, HACS und aktivierter Nabu-Casa-Fernzugriff. Füge in HACS `https://github.com/Jenik5/GrokConnectorForHomeAssistant` als benutzerdefiniertes Repository vom Typ **Integration** hinzu. Lade die Version herunter, starte HA neu und füge **Grok Connector** unter **Einstellungen → Geräte & Dienste** hinzu.

Gib die Nabu-Casa-HTTPS-Adresse ohne Pfad ein und wähle die Sprache der MCP-Werkzeuge. Wähle die lesbaren Entitäten. Unter **Konfigurieren → Aktionen** kannst du einen Namen, eine Beschreibung für Grok und eine Aktionsfolge mit dem HA-Editor anlegen. Leseberechtigung allein erlaubt keine Steuerung.

## Aktionen

- Licht einschalten: `light.turn_on` mit einem festen Ziel. Die Aktion wird auch bei bereits eingeschaltetem Licht ausgeführt.
- Automation starten: `automation.trigger`; mit `skip_condition: false` werden ihre Bedingungen geprüft.
- Skript starten: `script.turn_on`. Das vorhandene Skript bestimmt seinen eigenen Ablauf.
- Weitere Folgen und Bedingungen: im normalen HA-Aktionseditor konfigurieren.

Grok darf nur die vorbereiteten Werkzeuge ohne zusätzliche Ziele oder Parameter aufrufen. Die lesbare Entitätenliste begrenzt die Datenweitergabe, nicht die Reichweite einer von dir konfigurierten Aktionsfolge.

## Grok verbinden

**Konfigurieren → Kopplungscode** zeigt die genaue MCP-Adresse und einen einmaligen Code, gültig für zehn Minuten. Die Adresse lautet `https://deine-instanz.ui.nabu.casa/api/grok_connector/mcp`. Erstelle in Grok einen benutzerdefinierten MCP-Connector und gib den Code in dessen Autorisierungsfenster ein.

Ein zusätzlicher HA-Benutzer oder langfristiger HA-Token ist nicht erforderlich. Dieser Connector erstellt eigene Zugangsdaten. Änderungen an Entitäten oder Aktionen widerrufen vorhandenen Zugriff; danach erneut koppeln. Eine reine Sprachänderung erhält den Zugriff. **Grok-Zugriff widerrufen** entzieht Tokens und ausstehende Autorisierung.

Prüfe zuerst einen Zustand und vergleiche ihn mit HA. Teste danach bewusst eine einfache Aktion. Das Ende der Aktionsfolge bestätigt keine physische Wirkung. Unterstützung im Tesla-Client hängt von dessen Grok-Funktionen ab. Eine vorhandene MCP-Integration kann parallel installiert bleiben.

EN/CS/DE/PL/SK sind enthalten. Weitere Sprachen lassen sich mit je einer Datei in `translations` und `locales` ergänzen; die Sprachliste erkennt sie automatisch. [Übersetzungen und Entwicklung](../CONTRIBUTING.md).
