# GG — Gorgeous Gaps

**Разделители, текстовые рамки и TSV-таблицы для Bash и PowerShell.** Целевая версия **1.1.0**. [English README](README.md).

Обычный разделитель `gg` в Bash остаётся быстрым кодом оболочки. Новые режимы `--box` и `--table` используют один исполняемый Rust-движок в Bash и PowerShell. Готовые сборки не требуют установки Rust или Python. Python-прототип хранится только в `prototype/` для сравнения.

## Bash

Нужны Bash, UTF-8 и готовый `dist/linux-x64/gg-format`. Установщик сохраняет стабильный launcher v1 и размещает `gg`, `gg-names.sh` и `gg-format` в одном `version.*`, на который атомарно переключает `current`.

```bash
git clone https://github.com/cyberianin/gg-terminal-divider.git
cd gg-terminal-divider
source ./install.sh --check-names
source ./install.sh --command gg
gg "SYSTEM HEALTH"
gg --color cyan "STATUS"
gg --box "WARNING"
printf 'NAME\tSTATUS\nnginx\tRUNNING\n' | gg --table --header-first-row
docker ps --format '{{.Names}}\t{{.Status}}' | gg --table --header NAME,STATUS
```

Установщик не меняет `.bashrc`. При необходимости добавьте `$HOME/.local/bin` в `PATH` самостоятельно. Для повторных вызовов без запуска Bash-процесса включите функцию: `source "$HOME/.local/bin/.gg-divider/gg" --function gg`. Обычный `gg` в этом режиме не запускает Rust. Для короткого имени `vv` используйте `--command vv` и `--function vv`. Конфликтующие алиасы, функции и файлы не перезаписываются. Удаление выбранного имени: `source ./install.sh --command gg --uninstall`.

## PowerShell на Windows

Основная цель — PowerShell 7+ на Windows 10/11. Windows PowerShell 5.1 проверена отдельно для текстового UTF-8 конвейера, пустых TSV-полей и кодов возврата. Сборка лежит в `dist/windows-x64/gg-format.exe`.

```powershell
& .\install.ps1 -CheckNames
& .\install.ps1 -Command gg
$env:PATH = "$HOME\.local\bin;$env:PATH"
gg
gg "SYSTEM HEALTH"
gg --color cyan "STATUS"
gg --box "WARNING"
@('NAME`tSTATUS', 'nginx`tRUNNING') | gg --table --header-first-row
```

PowerShell проверяет алиасы и функции раньше внешних программ. Если `gg.ps1` не находится непосредственно через `PATH`, подключите короткую команду в текущем сеансе: `. "$HOME\.local\bin\.gg-divider-ps\activate.ps1" -Name gg`. Разрешены также `vv`, `xx`, `bn`, `bb`, `cv`; установщик и активация проверяют конфликты. Профиль не меняется без вашего действия. Для удаления: `& .\install.ps1 -Command gg -Uninstall`. Стабильный `gg.ps1` выбирает одну версию `version.*`; PowerShell-адаптер и Rust-бинарник берутся из неё. Старые версии сохраняются для уже начатых вызовов.

Текстовый конвейер передаётся в Rust как UTF-8. Объекты PowerShell не преобразуются автоматически в таблицу: сначала сформируйте TSV-текст. Вывод в файл или трубу отключает цвет, если не указан `--force-color`.

Если запускать `pwsh -File gg.ps1` из другой программы и передавать сырые Unicode-байты в stdin, входная кодировка консоли этой программы может повредить текст до вызова скрипта. Для такого случая используйте текстовый конвейер PowerShell с UTF-8 входом хоста; прямая передача сырых байтов при разных кодировках консоли — **NOT VERIFIED**.

## Рамки и таблицы

```bash
printf 'CPU: 12%%\nRAM: 1.2 GiB\n' | gg --box --title 'SYSTEM HEALTH'
printf 'Service unavailable\nRetry later\n' | gg --box --style double --color red
printf 'A\tB\nx\t\n' | gg --table --header-first-row
```

`--box` принимает позиционный текст **или** многострочный stdin. `--table` принимает TSV из stdin; первая строка по умолчанию считается данными. Заголовки задаются через `--header A,B` либо `--header-first-row`. Пустые ячейки между табуляциями и после последней табуляции сохраняются. Число колонок должно совпадать. Принимаются LF и CRLF.

Общие параметры: `--style single|double|heavy|ascii|dashed|dotted`, `--title`, `--width 8..500`, `--align left|center|right`, `--color`, `--text-color`, `--no-color`, `--force-color` и `--overflow wrap|truncate|error`. Для dashed/dotted используются углы и вертикальные линии стиля single. Рамка по умолчанию переносит текст; таблица обрезает с `…`. При слишком малой ширине для границ и хотя бы одной позиции каждой колонке команда возвращает код 2 и ничего не рисует.

`--max-bytes` по умолчанию ограничивает вход 8 МиБ. `--max-rows` ограничивает таблицу 10000 физическими строками TSV, включая строку заголовка из входа. Вход ограничивается до декодирования и расчёта ширин. Для расчёта ширин таблица буферизуется целиком в заданном лимите. Управляющие последовательности ANSI во входе удаляются; цвет вывода создаёт GG. Ширина Unicode считается по графемам и таблицам `unicode-width`; отображение некоторых emoji и символов неопределённой ширины зависит от терминала.

## Платформы и сборка

В репозитории находятся Windows x64 MSVC и Linux x64 musl сборки. Исходники Rust собираются через `cargo build --release`; для Linux x64 нужна цель `x86_64-unknown-linux-musl` и подходящий linker. Windows ARM64, Linux ARM64 и macOS — **NOT VERIFIED**. CI собирает обе целевые платформы, запускает Rust-тесты, старые Bash golden fixtures и новые PowerShell-контракты. Результаты локальной проверки и ограничения указаны в [VALIDATION.md](VALIDATION.md).

GG не скачивает и не запускает двоичные файлы из сторонних источников автоматически. Выпуск 1.1.0, tag и GitHub Release пока не создавались.

## Лицензия

GG распространяется по стандартной [лицензии MIT](LICENSE), copyright (c) 2026 cyberianin. MIT разрешает использование, изменение, распространение и продажу копий при сохранении уведомлений об авторских правах и разрешении. Это включает работу в коммерческих организациях и production-инфраструктуре. Rust-зависимости сохраняют собственные лицензии; см. [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
