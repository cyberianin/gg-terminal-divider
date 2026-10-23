# GG — Gorgeous Gaps

> Установка и режим `source` изменились: актуальные безопасные инструкции находятся в [English README](README.md). Используйте `source ./install.sh` для установки, а для явного режима функции — `source "$HOME/.local/bin/.gg-divider/gg" --function gg`. Прежние инструкции установки ниже устарели.

**Красивые настраиваемые разделители для терминала Bash.** Версия **1.0.0**. [English README](README.md).

GG выводит разделитель или секцию с заголовком. Это один Bash-файл без обязательных сторонних зависимостей. Его можно запускать как команду или подключить как функцию: при повторных вызовах в интерактивной SSH-сессии новый процесс Bash не создаётся.

```text
════════════════════════════════════════
             SYSTEM HEALTH
════════════════════════════════════════

━━━━━━━  DOCKER STATUS  ━━━━━━━
```

Поддерживаются именованные ANSI-цвета, палитра 256 цветов и RGB `#RRGGBB`. При перенаправлении вывода цвета отключаются автоматически; `--force-color` включает их принудительно.

## Требования

Bash и локаль UTF-8 для Unicode-стилей. `tput` необязателен. Автоматическая ширина берётся из `COLUMNS`, затем из `tput cols` для терминала, иначе используется 80; резервируются две колонки, максимум автоматической ширины — 120.

## Установка с GitHub

```bash
git clone git@github.com:cyberianin/gg-terminal-divider.git
cd gg-terminal-divider
mkdir -p "$HOME/.local/bin"
cp gg "$HOME/.local/bin/gg"
chmod +x "$HOME/.local/bin/gg"
```

Если SSH-ключ не настроен, используйте `git clone https://github.com/cyberianin/gg-terminal-divider.git`. Для отдельной команды при необходимости добавьте `export PATH="$HOME/.local/bin:$PATH"` в `~/.bashrc`. Для работы как Bash-функции добавьте строку подключения один раз:

```bash
grep -Fqx 'source "$HOME/.local/bin/gg"' "$HOME/.bashrc" || printf '\nsource "$HOME/.local/bin/gg"\n' >> "$HOME/.bashrc"
source "$HOME/.bashrc"
gg --help
```

Если функция `gg` уже существует, подключение файла заменит её определение в текущей оболочке. Для обновления выполните `git pull` в клоне и снова скопируйте `gg`.

## Установка копированием кода

Откройте [gg](gg), скопируйте всё содержимое и сохраните его в `~/.local/bin/gg`, предварительно выполнив `mkdir -p "$HOME/.local/bin"`. Затем выполните `chmod +x "$HOME/.local/bin/gg"`. Добавьте PATH или строку `source` из инструкции выше. Git для этого способа не нужен. Перед запуском просмотрите код скрипта.

## Использование

```bash
gg
gg "DOCKER STATUS"
gg --char '*' "SYSTEM"
gg --char '=-' --color red "WARNING"
gg --style heavy --color '#A855F7' "SERVER HEALTH"
gg --layout inline --text-color yellow "DATABASE"
gg --width 100 --align right "FINISHED"
gg --no-color "PLAIN OUTPUT"
gg --help
```

Несколько позиционных слов соединяются пробелами. `--text` заменяет позиционный текст; одновременно их указывать нельзя. Если текст начинается с `-`, поставьте перед ним `--`. Длинные параметры со значением также принимают форму `--option=value`.

### Параметры и короткие алиасы

| Длинный параметр | Короткий алиас | Значение или действие |
| --- | --- | --- |
| `--text` | `-t` | Заголовок |
| `--style` | `-s` | `double`, `single`, `heavy`, `dashed`, `dotted`, `ascii` |
| `--char` | `-c` | Повторяемый шаблон из 1–16 печатных узких символов; заменяет символ стиля |
| `--color` | — | Цвет разделителя |
| `--text-color` | — | Цвет заголовка |
| `--width` | `-w` | Ширина 8–500 колонок |
| `--align` | `-a` | `left`, `center`, `right` |
| `--layout` | `-l` | `box` или `inline` |
| `--no-color` | — | Отключить ANSI-цвета |
| `--force-color` | — | Сохранить цвета при перенаправлении; `--no-color` имеет приоритет |
| `--help` | `-h` | Показать справку |

Других алиасов команды нет. Короткие флаги — алиасы длинных параметров из таблицы. `--` завершает разбор параметров.

Цвета: `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`, `gray`, `bright-red`, `bright-green`, `bright-yellow`, `bright-blue`, `bright-magenta`, `bright-cyan`, `bright-white`, `#RRGGBB` или индекс `0`–`255`. `none` и `default` отключают один из цветов.

### Настройки по умолчанию

| Переменная | Значение по умолчанию | Соответствующий параметр |
| --- | --- | --- |
| `GG_STYLE` | `double` | `--style` |
| `GG_COLOR` | `magenta` | `--color` |
| `GG_TEXT_COLOR` | `cyan` | `--text-color` |
| `GG_WIDTH` | Автоматически | `--width` |
| `GG_ALIGN` | `center` | `--align` |
| `GG_LAYOUT` | `box` | `--layout` |

Задавайте переменные до подключения файла, например:

```bash
export GG_STYLE=heavy GG_COLOR='#A855F7' GG_TEXT_COLOR=white
export GG_LAYOUT=inline GG_ALIGN=center GG_WIDTH=80
source "$HOME/.local/bin/gg"
```

Параметры команды переопределяют переменные окружения. `NO_COLOR` отключает цвета, кроме случая с `--force-color`.

## Пример сценария

```bash
gg "SYSTEM HEALTH"
uptime
free -h
gg -l inline -s heavy "DOCKER CONTAINERS"
docker ps
gg "DONE"
```

## Ограничения

Выравнивание считает символы, а не занимаемые колонки терминала. Эмодзи и широкие CJK-символы могут нарушить геометрию. Для пользовательского шаблона нужны узкие символы. Unicode-стили требуют поддержки терминала и шрифта. Совместимость с Bash на macOS и другими конфигурациями терминалов отдельно не проверялась.

## Участие и лицензия

Приветствуются сообщения об ошибках и pull request. Лицензия — [LICENSE](LICENSE). Контакт: `211379639+cyberianin@users.noreply.github.com`.
