# GG — Gorgeous Gaps

**Разделители, текстовые рамки и TSV-таблицы для Bash и PowerShell.** Версия **1.1.1**. [English README](README.md).

Функции 1.1.0 вошли в `main`, но не публиковались как GitHub Release. Список опубликованных версий находится на [странице GitHub Releases](https://github.com/cyberianin/gg-terminal-divider/releases).

Обычный разделитель `gg` остаётся быстрым кодом Bash или PowerShell. Режимы `--box` и `--table` используют один исполняемый Rust-движок в обеих оболочках. Готовые сборки не требуют установки Rust или Python. Python-прототип хранится только в `prototype/` для сравнения.

## Bash

Для установки из архива Linux x64 распакуйте `gg-1.1.1-linux-x64.tar.gz`, перейдите в каталог `gg-1.1.1-linux-x64` и выполните `source ./install.sh --command gg`. В архиве сохранена необходимая структура `dist/linux-x64/` и приложены лицензионные уведомления.

Нужны Bash, UTF-8 и готовый `dist/linux-x64/gg-format`. Установщик сохраняет стабильный launcher v1 и размещает `gg`, `gg-names.sh` и `gg-format` в одном `version.*`, на который атомарно переключает `current`.

```bash
git clone https://github.com/cyberianin/gg-terminal-divider.git
cd gg-terminal-divider
source ./install.sh --check-names
source ./install.sh --command gg
gg "SYSTEM HEALTH"
gg version
gg --color cyan "STATUS"
gg --box "WARNING"
printf 'NAME\tSTATUS\nnginx\tRUNNING\n' | gg --table --header-first-row
docker ps --format '{{.Names}}\t{{.Status}}' | gg --table --header NAME,STATUS
```

Установщик не меняет `.bashrc`. При необходимости добавьте `$HOME/.local/bin` в `PATH` самостоятельно. Для повторных вызовов без запуска Bash-процесса включите функцию: `source "$HOME/.local/bin/.gg-divider/gg" --function gg`. Обычный `gg` в этом режиме не запускает Rust. Для короткого имени `vv` используйте `--command vv` и `--function vv`. Конфликтующие алиасы, функции и файлы не перезаписываются. Удаление выбранного имени: `source ./install.sh --command gg --uninstall`.

## PowerShell на Windows

Для установки из архива Windows x64 распакуйте `gg-1.1.1-windows-x64.zip`, перейдите в каталог `gg-1.1.1-windows-x64` и выполните команды ниже. В архиве сохранена структура `dist/windows-x64/` и приложены лицензионные уведомления.

Поддерживаются Windows PowerShell 5.1 и PowerShell 7+ на Windows 10/11. Проверены Unicode-разделители, цветные рамки, TSV-таблицы, текстовый UTF-8 конвейер и коды возврата. Сборка лежит в `dist/windows-x64/gg-format.exe`.

```powershell
& .\install.ps1 -CheckNames
& .\install.ps1 -Command gg
. "$HOME\.local\bin\.gg-divider-ps\activate.ps1" -Name gg
gg
gg "SYSTEM HEALTH"
gg --version
gg --color cyan "STATUS"
gg --box "WARNING"
@('NAME`tSTATUS', 'nginx`tRUNNING') | gg --table --header-first-row
```

`gg version` и `gg --version` показывают версию formatter из выбранной установленной версии GG. Для разделителя с буквальным заголовком `version` используйте `gg -- version`.

PowerShell проверяет алиасы и функции раньше внешних программ. Если `gg.ps1` не находится непосредственно через `PATH`, подключите короткую команду в текущем сеансе: `. "$HOME\.local\bin\.gg-divider-ps\activate.ps1" -Name gg`. Разрешены также `vv`, `xx`, `bn`, `bb`, `cv`. Повторная установка и обновление допускаются при активном собственном алиасе GG только если он указывает на launcher, принадлежность которого подтверждена; чужие алиасы, функции, команды и файлы остаются конфликтами. `-CheckNames` показывает тот же результат. Профиль не меняется без вашего действия. Для удаления: `& .\install.ps1 -Command gg -Uninstall`. Стабильный `gg.ps1` выбирает одну версию `version.*`; PowerShell-адаптер и Rust-бинарник берутся из неё. Переключение `current` атомарно, старые версии сохраняются для уже начатых вызовов.

Текстовый конвейер передаётся в Rust как UTF-8. Объекты PowerShell не преобразуются автоматически в таблицу: сначала сформируйте TSV-текст. В Windows Console Host цвета работают при подтверждённой поддержке VT через `GetConsoleMode` и `SetConsoleMode`. Интерактивный Unicode выводится через `WriteConsoleW`, перенаправленные stdout и stderr сохраняют байты UTF-8. `NO_COLOR` отключает автоматический цвет; `--force-color` включает его при перенаправлении, а `--no-color` имеет приоритет.
В Bash, PowerShell и Rust цвета границ (`GG_COLOR`) и текста (`GG_TEXT_COLOR`) по умолчанию равны `default`: вывод наследует foreground терминала как на синем, так и на светлом фоне. Свои цвета задаются переменными или явными `--color` и `--text-color`. `--force-color` разрешает запрошенный ANSI-цвет при перенаправлении, но не добавляет управляющие последовательности, если оба цвета равны `default`.

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

В репозитории находятся пересобранные для 1.1.1 Windows x64 MSVC и Linux x64 musl сборки. Исходники Rust собираются через `cargo build --release --locked`; для Linux x64 нужна цель `x86_64-unknown-linux-musl` и подходящий linker. Установщик копирует соответствующий бинарник из `dist/` в неизменяемую версию runtime. Windows ARM64, Linux ARM64 и macOS — **NOT VERIFIED**. CI собирает обе целевые платформы, запускает Rust-тесты, старые Bash golden fixtures и PowerShell-контракты. Результаты локальной проверки и ограничения указаны в [VALIDATION.md](VALIDATION.md).

GG не скачивает и не запускает двоичные файлы из сторонних источников автоматически. 1.1.0 осталась версией кода в `main` без отдельного GitHub Release; актуальные опубликованные версии перечислены на странице Releases.

## Лицензия

GG распространяется по стандартной [лицензии MIT](LICENSE), copyright (c) 2026 cyberianin. MIT разрешает использование, изменение, распространение и продажу копий при сохранении уведомлений об авторских правах и разрешении. Это включает работу в коммерческих организациях и production-инфраструктуре. Rust-зависимости сохраняют собственные лицензии; см. [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
