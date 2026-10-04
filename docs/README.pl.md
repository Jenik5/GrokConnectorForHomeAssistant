# Grok Connector — instrukcja po polsku

Społecznościowy konektor MCP udostępnia wybrane encje Home Assistant do odczytu oraz nazwane sekwencje akcji do wykonania. Można wybrać encje dowolnego typu. Warunki ustalasz samodzielnie w akcjach, skryptach lub automatyzacjach HA.

Beta `0.1.0b1` przeszła testy, GitHub CI, instalację przez HACS i sprawdzenie natywnej konfiguracji HA oraz edytora akcji. OAuth i odczyt stanów przez Nabu Casa działają również w internetowym Groku w Chrome. Polecenia sterujące urządzeniami i klient w Tesli wymagają jeszcze celowych testów praktycznych. [Pełna dokumentacja i stan](../README.md).

## Konfiguracja przez HACS

Wymagane są HA 2026.9.4+, HACS i włączony dostęp zdalny Nabu Casa. Dodaj `https://github.com/Jenik5/GrokConnectorForHomeAssistant` w HACS jako własne repozytorium typu **Integracja**, pobierz wersję i uruchom HA ponownie. Dodaj **Grok Connector** w **Ustawienia → Urządzenia i usługi**.

Podaj adres HTTPS Nabu Casa bez ścieżki, wybierz język narzędzi MCP i encje do odczytu. W **Konfiguruj → Akcje** dodaj nazwę, opis dla Groka i sekwencję w edytorze HA. Wybranie encji do odczytu nie pozwala samo w sobie na jej sterowanie.

## Przykłady akcji

- Włączenie światła: `light.turn_on` ze stałym celem. Akcja działa również wtedy, gdy światło już jest włączone.
- Uruchomienie automatyzacji: `automation.trigger`; ustaw `skip_condition: false`, jeśli jej warunki mają być sprawdzane.
- Uruchomienie skryptu: `script.turn_on`. Istniejący skrypt określa własne działanie.
- Inne akcje, warunki i sekwencje: przygotuj je w standardowym edytorze HA.

Grok może wywołać tylko przygotowane narzędzie, bez podawania innego celu lub dodatkowych parametrów. Lista encji do odczytu ogranicza ujawniane dane; zakres skonfigurowanej akcji określa jej sekwencja.

## Połączenie z Grokiem

**Konfiguruj → Kod parowania** pokazuje dokładny adres MCP i jednorazowy kod ważny przez dziesięć minut. Adres ma postać `https://twoja-instancja.ui.nabu.casa/api/grok_connector/mcp`. Utwórz własny konektor MCP w Groku i wpisz kod w jego oknie autoryzacji.

Nie potrzebujesz dodatkowego użytkownika HA ani długoterminowego tokenu HA. Konektor wydaje własne poświadczenia. Zmiany encji lub akcji cofają dotychczasowy dostęp i wymagają ponownego parowania. Sama zmiana języka zachowuje dostęp. **Cofnij dostęp Groka** unieważnia tokeny i oczekującą autoryzację.

Najpierw odczytaj stan i porównaj go z HA. Następnie świadomie sprawdź jedną prostą akcję. Zakończenie sekwencji nie potwierdza fizycznego efektu. Dostępność w Tesli zależy również od możliwości jej klienta Groka. Inna integracja MCP może pozostać zainstalowana równolegle.

Dostępne języki: EN/CS/DE/PL/SK. Nowy język wymaga dwóch plików w `translations` i `locales`; lista języków wykrywa go automatycznie. [Tłumaczenia i rozwój](../CONTRIBUTING.md).
