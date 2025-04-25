# Selector

**Selector** — это инструмент для разбиения целевого профиля во взвешенную сумму профилей юнит-тестов. Построен в виде пайплайна из четырёх скриптов.

## 📦 Структура проекта

```
selector/
├── stage1/find_files.py    # Поиск и систематизация исходных профилей
├── stage2/build_histo.py   # Преобразование исходных профилей во внутренней представление (гистограммы), компрессия
├── stage3/solve_math.py    # Решение задачи разложения в терминах гистограмм
└── stage4/postprocess.py   # Формирование выходного набора артефактов
```

## 🚀 Быстрый старт

### 1. Установи переменные окружения

```bash
export TOOL_DIR="$(pwd)/tools"                # Директория, где хранятся скрипты
export WORK_DIR="$(pwd)/work_dir"             # Директория, куда мы складываем текущие артефакты и выходные артефакты
export SAMPLE_DIR="/home/user/profiles"       # Все профили кроме целевых считаются профилями юнит-тестов (шаг 1)
export REFERENCE_DIR="$SAMPLE_DIR/reference"  # Внутри директории ожидается ровно один профиль, который является целевым (шаг 1)
export LOOKUP_MASK="*.jfr"                    # Маска идентефецирующая профиль (шаг 1)
export BLOCK_COMPRESSION=true                 # Выбор сжимать ли в гистограммах идущие подряд функции с одним и тем же значением в одну (шаг 2)
export HOTNESS_COMPRESSION=97                 # До скольки процентов самых горячих функций сжимать профили (шаг 2) 
export MIN_SIMILARITY=95                      # Минимальная целевая похожесть в процентах (шаг 3)
export MAX_SELECTED_SAMPLES=5                 # Ограничения на максимальное колличество юнит-тестов (шаг 3)
export REFERENCE_ARTIFACT_DEPTH=2             # Насколько папок вверх от reference файлов будут копироваться артефакты (шаг 4) 
export SAMPLE_ARTIFACT_DEPTH=2                # Насколько папок вверх от sample файлов будут копироваться артефакты (шаг 4) 
```

### 2. Подготовь окружение
```bash
mkdir -p $TOOL_DIR
git clone http://gitlab.sberlab.nsu.ru/ilmat192/selector.git $TOOL_DIR
pip install -r $TOOL_DIR/selector/requirements.txt
```

### 3. Выполни шаги пайплайна по очереди

```bash
python $TOOL_DIR/stage1/find_files.py                     \
    --sample-dir=$SAMPLE_DIR                              \
    --reference-dir=$REFERENCE_DIR                        \
    --work-dir=$WORK_DIR                                  \
    --lookup-mask=$LOOKUP_MASK
python $TOOL_DIR/stage2/build_histo.py                    \
    --block-compression=$BLOCK_COMPRESSION                \
    --hotness-compression=$HOTNESS_COMPRESSION            \
    --work-dir=$WORK_DIR                                  \
    --lookup-mask=$LOOKUP_MASK
python $TOOL_DIR/stage3/solve_math.py                     \
    --min-similarity=$MIN_SIMILARITY                      \
    --max-selected-traces=$MAX_SELECTED_TRACES            \
    --work-dir=$WORK_DIR
python $TOOL_DIR/stage4/postprocess.py                    \
    --reference-artifact-depth=$REFERENCE_ARTIFACT_DEPTH  \
    --sample-artifact-depth=$SAMPLE_ARTIFACT_DEPTH
```

## 🔍 Что делает каждый этап?

### 🔹 Этап 1: `find_files.py`
Этот скрипт находит все файлы профилей по заданной маске `$LOOKUP_MASK`. Он классифицирует их как reference или sample и сохраняет информацию в JSON.

Пример структуры JSON на выходе:
```json
[
  {
    "type": "reference",
    "source_file": "/home/user/profiles/reference/profile.jfr"
  },
  {
    "type": "sample",
    "source_file": "/home/user/profiles/sample_1/profile.jfr"
  }
]
```
Скрипт сначала ищет и идентифицирует reference файл, затем находит все sample файлы (всё что не является reference) и сохраняет пути к ним в файл `$WORK_DIR/stages/stage1/files.json`.

### 🔹 Этап 2: `build_histo.py`
Преобразует найденные файлы профиля в формат гистограмм для дальнейшей работы. Скрипт не генерирует сами гистограммы, а извлекает их из профилей и сохраняет их в JSON файл для дальнейшей обработки.

Компрессия настраивается через параметры командной строки:

- `$BLOCK_COMPRESSION`: Выбор сжимать ли в гистограммах идущие подряд функции с одинаковым количеством вызовов в одну (по умолчанию `true`).

- `$HOTNESS_COMPRESSION`: До скольки процентов самых "горячих" функций сжимать профили (по умолчанию `97`).

#### Формат входных файлов

Скрипт извлекает гистограммы из профилей и сохраняет их во внутреннем формате внутри JSON. 

Поддерживаются следующие типы входных файлов:

- `.jfr` — Java Flight Recorder файлы  
- `.histo` — уже сгенерированные гистограммы  

Если передан файл в неподдерживаемом формате, скрипт завершится с ошибкой:

```
[ERROR] Unsupported file format: .xyz
```

Скрипт расширяемый — если вы хотите добавить поддержку собственных форматов профилей, вы можете дополнить логику обработки в соответствующей функции - `load_profile()`.

#### Структура гистограмм

Каждая гистограмма в файле JSON представляет собой пару "функция — количество вызовов". 

Структура гистограммы выглядит следующим образом:

```json
{
  "histo": {
    "id1": 6,
    "id2": 3,
    "id3": 1
  }
}
```

#### Выходные файлы

Скрипт сохраняет результаты в формате JSON в файл `$WORK_DIR/stages/stage2/histos.json`. 

Пример структуры JSON на выходе:

```json
[
  {
    "type": "reference",
    "source_file": "/home/user/profiles/reference/profile.jfr",
    "histo": {
      "id1": 6,
      "id2": 3,
      "id3": 1
    }
  },
  {
    "type": "sample",
    "source_file": "/home/user/profiles/sample_1/profile.jfr",
    "histo": {
      "id1": 1,
      "id2": 2,
      "id3": 3
    }
  }
]
```


### 🔹 Этап 3: `solve_math.py`

Скрипт решает математическую часть задачи с помощью ЗЛП с бинарной переменной. 

Параметры:

- `$MAX_SELECTED_SAMPLES`: Максимальное количество юнит-тестов, которые мы выберем. (По умолчанию `5`)

- `$MIN_SIMILARITY`: Минимальная схожесть в процентах для выбора юнит-тестов. (По умолчанию `95`)

Задача заключается в том, чтобы выбрать колличество (не превыщающим `MAX_SELECTED_SAMPLES`) юнит-тестов с некоторыми весами, чтобы схожесть взвешшеной суммы с целевым профилем достигла `MIN_SIMILARITY`. 
В случае недостижения требуемой схожести выбирается максимально возможное количество юнит-тестов, и определяется максимально возможная схожесть.

После выполнения задачи скрипт генерирует файл с весами для выбранных юнит-тестов, который находится в папке `$WORK_DIR/stages/stage3/weight.json`.

Пример структуры JSON на выходе:
```json
{
  "reference_file": "/home/user/profiles/reference/profile.jfr",
  "similarity": 98,
  "selected_unit_tests": [
    {
      "unit_test_path": "/home/user/profiles/sample_1/profile.jfr",
      "weight": 0.33
    },
    {
      "unit_test_path": "/home/user/profiles/sample_2/profile.jfr",
      "weight": 0.67
    },
  ]
}
```
#### Математическая постановка задачи

Задача оптимизации сводится к задаче минимизации отклонений между взвешенными тестами и целевой гистограммой. Пусть:

- $` S = \{s_1, s_2, ..., s_n\} `$ — это набор функций, полученных из различных тестов. Каждый элемент гистограммы теста $` i `$ ($` s_i `$) — это вектор чисел $` s_i = [s_{i1}, s_{i2}, ..., s_{in}] `$ с вещественными значениями $` s_{ij} \in \mathbb{R} `$.

- $` T = [t_1, t_2, ..., t_n] `$ — это целевой вектор-гистограмма. Каждый элемент $` t_j \in \mathbb{R} `$ представляет целевое значение по $` j `$-й характеристике.

- $` w = [w_1, w_2, ..., w_n] `$ — это веса тестов которые подбираются в результате оптимизации. Каждый вес — вещественное число.

- $` z = [z_1, z_2, ..., z_n] `$ — бинарные переменные, где:
  - $` z_i \in \{0, 1\} `$
  - $` z_i = 1 `$ означает, что тест $` i `$ выбран
  - $` z_i = 0 `$ означает, что тест $` i `$ не выбран

##### Целевая функция:

Мы минимизируем отклонение между суммой взвешенных тестов и целевой гистограммой. Целевая функция выражается как:

$$
\text{minimize} \quad \sum_{i=1}^{n} \left| w_i \cdot s_i - T \right|
$$

где $` w_i \cdot s_i `$ — это взвешенная сумма тестов, а $` T `$ — это целевая гистограмма.

##### Ограничения:

- Ограничение на веса:
  $`
  w_i \geq 0, \quad \forall i
  `$
  
- Ограничение на нормализацию весов:
  $`
  \sum_{i=1}^{n} w_i = 1
  `$

- Ограничение на бинарные переменные:
  $`
  w_i \leq z_i, \quad \forall i
  `$

  Вес $` w_i `$ может быть положительным только в случае, если тест выбран (то есть $` z_i = 1 `$).

- Ограничение на количество выбранных тестов:
  $`
  \sum_{i=1}^{n} z_i \leq \text{max\_selected\_samples}
  `$

### 🔹 Этап 4: `postprocess.py`

Скрипт на основе `weight.json` копирует артефакты в итоговые папки и создает файл weight. 

Параметры:

- `$REFERENCE_ARTIFACT_DEPTH`: Насколько папок вверх от reference файлов будут копироваться артефакты. (По умолчанию `2`)

- `$SAMPLE_ARTIFACT_DEPTH`: Насколько папок вверх от sample файлов будут копироваться артефакты (По умолчанию `2`)

```
stages/stage4/
├── weight
├── artifact1
├── reference/
│       └── profile.jfr
│       └── artifact2
├── sample_1/
│       └── profile.jfr
│       └── artifact_folder1/
│       │       └── artifact3
├── sample_2/
│       └── profile.jfr
│       └── artifact_folder2/
```

Файл `weight` представляет собой пару "имя папки в `stages/stage4` — вес профиля теста внутри этой папки". 

Структура `weight` выглядит следующим образом:

```
sample_1 0.33
sample_2 0.67
```

## 🧪 Пример структуры входных данных
```
profiles/
├── artifact1
├── reference/
│       └── profile.jfr
│       └── artifact2
├── sample_1/
│       └── profile.jfr
│       └── artifact_folder1/
│       │       └── artifact3
├── sample_2/
│       └── profile.jfr
│       └── artifact_folder2/
```

## 💡 Особенности

- Возможность запуска каждого шага отдельно
- Поддержка сжатия гистограмм
- JSON-форматы для промежуточных данных

## 📧 Обратная связь

Разработка: **Timur Ilyinykh**  
Telegram: **@ElfHunterAO**