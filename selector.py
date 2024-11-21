import os
import shutil
import numpy as np
import cvxpy as cp

def create_selected_folder_and_copy_files(times_tests, reference_file_path, weights, base_directory):
    """
    Создает папку test_folder_selected вне base_directory, копирует выбранные тесты с новыми именами,
    сохраняет reference.histo и весовой файл в compare_input рядом с первым тестом.
    :param times_tests: Словарь тестов, содержащий пути и данные.
    :param reference_file_path: Путь к референсному файлу.
    :param weights: Словарь с весами для каждого теста.
    :param base_directory: Базовая директория, где находятся исходные тесты.
    """
    # Создаем папку test_folder_selected вне base_directory
    parent_directory = os.path.abspath(os.path.join(base_directory, os.pardir))
    selected_folder = os.path.join(parent_directory, f"{os.path.basename(base_directory)}_selected")
    if not os.path.exists(selected_folder):
        os.makedirs(selected_folder)

    # Переносим и переименовываем тесты, учитывая порядок, как они идут в weights
    test_number = 1
    compare_input_folder = None

    for test, weight in weights.items():
        if weight > 0:  # Обрабатываем только тесты с ненулевыми весами
            test_file_path = times_tests[test][1]  # Путь к файлу trace.histo

            # Получаем путь до директории теста (например, test_1, test_2)
            test_dir_path = os.path.dirname(os.path.dirname(test_file_path))
            rel_path = os.path.relpath(test_dir_path, base_directory)
            path_parts = rel_path.split(os.sep)

            # Определяем новый путь для переноса
            original_test_folder = path_parts[1]  # Исходное имя папки после <x>
            path_parts[1] = f"test_{test_number}"  # Переименовываем test_1, test_2 и т.д.
            new_test_dir_path = os.path.join(selected_folder, os.path.join(*path_parts))

            # Копируем всю директорию теста
            if not os.path.exists(new_test_dir_path):
                shutil.copytree(test_dir_path, new_test_dir_path)

            print(f"Copied folder '{original_test_folder}' to '{os.path.basename(new_test_dir_path)}'.")

            # Устанавливаем папку compare_input рядом с test_1
            if test_number == 1:
                compare_input_folder = os.path.join(selected_folder, path_parts[0], "compare_input")
                if not os.path.exists(compare_input_folder):
                    os.makedirs(compare_input_folder)

            test_number += 1

    # Копируем референсный файл в папку compare_input
    if compare_input_folder:
        reference_file_name = os.path.basename(reference_file_path)
        new_reference_path = os.path.join(compare_input_folder, reference_file_name)
        shutil.copy(reference_file_path, new_reference_path)

        print(f"Copied reference file to '{new_reference_path}'.")

        # Записываем веса в файл weight.txt в папке compare_input
        weights_file_path = os.path.join(compare_input_folder, "weight.txt")
        with open(weights_file_path, "w") as f:
            for test, weight in weights.items():
                if weight > 0:
                    f.write(f"{weight:.4f}\n")

        print(f"Weights file saved to '{weights_file_path}'.")

    print(f"Selected tests and their content have been copied to '{selected_folder}'.")


def create_reference_mapping(reference_file):
    """
    Создает отображение 16-ричных значений функции на их индексы из референсного файла.
    Индекс соответствует первой встреченной позиции функции, начиная с 0.
    Игнорируются строки с комментариями.
    :param reference_file: Путь к референсному файлу (например, compare_input/reference.histo).
    :return: Словарь с 16-ричными значениями как ключами и их позициями как значениями.
    """
    reference_mapping = {}
    real_index = 0  # Индекс, который будет отслеживать строку без учета комментариев

    try:
        # Парсим референсный файл
        with open(reference_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue  # Пропускаем пустые строки и комментарии

                # Разбираем строку
                parts = line.split()
                if len(parts) == 2 and parts[1].isdigit():
                    function_name = parts[0]
                    # Если функция еще не встречалась, сохраняем её реальный индекс
                    if function_name not in reference_mapping:
                        reference_mapping[function_name] = real_index

                    # Увеличиваем индекс только для строк, которые не являются комментариями
                    real_index += 1
                else:
                    # Если строка некорректна, выбрасываем исключение с указанием строки
                    raise ValueError(
                        f"Invalid line in the reference file '{reference_file}' at line {line_num}: {line}"
                    )
    except Exception as e:
        print(f"Error reading the reference file {reference_file}: {e}")
    return reference_mapping



def parse_file(file_path):
    """
    Парсит файл и возвращает словарь с функциями и их процентными значениями.
    Выбрасывает исключение, если в файле есть некорректные строки.
    :param file_path: Путь к файлу.
    :return: Словарь {функция: процентное значение}.
    """
    result = {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = []
            for line_num, line in enumerate(f, start=1):
                # Игнорируем строки с комментариями
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Разбираем строку: ожидается формат "<function> <number>"
                parts = line.split()
                if len(parts) == 2 and parts[1].isdigit():
                    function_name = parts[0]
                    number = int(parts[1])
                    data.append((function_name, number))
                else:
                    # Если строка некорректна, выбрасываем исключение с указанием строки
                    raise ValueError(f"Invalid line in the file '{file_path}' at line {line_num}: {line}")

            # Рассчитываем процентное соотношение
            total = sum(val for _, val in data)
            if total > 0:
                result = {func: (val / total) * 100 for func, val in data}
    except Exception as e:
        print(f"Error reading the file {file_path}: {e}")
    return result


def find_and_process_files(base_dir):
    """
    Обходит папки внутри указанной директории, ищет файлы reference.histo и trace.histo,
    и заполняет словарь словарей.
    :param base_dir: Базовая директория для поиска.
    :return: Словарь словарей {путь файла: {функция: процентное значение}}.
    """
    results = {}  # Основной словарь для хранения данных

    for root, dirs, files in os.walk(base_dir):
        # Проверяем наличие reference.histo
        reference_file = os.path.join(root, "compare_input", "reference.histo")
        if os.path.exists(reference_file):
            print(f"Found reference.histo: {reference_file}")

            # Парсим reference.histo и добавляем в словарь
            parsed_reference = parse_file(reference_file)
            results[reference_file] = parsed_reference

            # Ищем все trace.histo в подпапках
            for sub_dir in dirs:
                trace_file_path = os.path.join(root, sub_dir, "mode", "trace.histo")
                if os.path.exists(trace_file_path):
                    print(f"Found trace.histo: {trace_file_path}")

                    # Парсим trace.histo и добавляем в словарь
                    parsed_trace = parse_file(trace_file_path)
                    results[trace_file_path] = parsed_trace

    return results

def optimize_tests_continuous(times_tests, target_function, num_functions, max_sum_w):
    """
    Оптимизирует веса тестов для создания функции, максимально приближенной к таргетной гистограмме.
    """
    # Создание массивов s_i для всех тестов
    s_list = []
    test_indices = list(times_tests.keys())  # Получаем список имен тестов
    for test in times_tests:
        funcs = times_tests[test][0]
        s_i = np.zeros(num_functions)
        for func, value in funcs.items():
            func_index = int(func) # Используем числовое значение как индекс
            s_i[func_index] = value
        s_list.append(s_i)

    s_list = np.array(s_list)

    # Преобразование целевой функции в массив T
    T = np.zeros(num_functions)
    for func, value in target_function.items():
        func_index = int(func) # Используем числовое значение как индекс
        T[func_index] = value

    # Определение переменных
    w = cp.Variable(len(times_tests))
    z = cp.Variable(len(times_tests), boolean=True)  # Бинарные переменные

    # Ограничения
    constraints = [
        w >= 0,
        w <= z,  # w_i может быть положительным только если z_i = 1
        cp.sum(z) <= max_sum_w,  # Ограничение на количество выбранных тестов
        cp.sum(w) == 1  # Нормализуем веса
    ]

    # Определяем целевую функцию
    objective = cp.Minimize(
        cp.sum(cp.abs(cp.matmul(w, s_list) - T))  # Минимизация отклонений от целевой функции
    )

    # Проблема и решение
    problem = cp.Problem(objective, constraints)
    problem.solve(solver=cp.CBC)

    # Проверка результата
    if problem.status in [cp.OPTIMAL, cp.OPTIMAL_INACCURATE]:
        result_function = cp.matmul(w, s_list).value

        # Нормализация полученной функции
        if np.sum(result_function) > 0:
            normalized_function = (result_function / np.sum(result_function)) * 100
        else:
            normalized_function = np.zeros_like(result_function)

        # Вычисление метрики схожести
        min_sums = np.minimum(normalized_function, T)
        print(min_sums, normalized_function, T)
        overall_similarity = np.sum(min_sums)

        # Сохранение веса каждого теста
        result_weight = {}
        for i in range(len(times_tests)):
            result_weight[test_indices[i]] = w.value[i]

        return overall_similarity, result_weight
    else:
        print("Optimization failed.")
        return None, None

def replace_hex_keys_with_numerical(reference_data, swap_16):
    """
    Заменяет 16-ричные ключи на численные индексы.
    :param reference_data: Словарь, где ключи - 16-ричные значения.
    :param swap_16: Словарь для замены 16-ричных ключей на численные индексы.
    :return: Новый словарь с числовыми ключами.
    """
    return {
        str(swap_16.get(key, key)): value  # Заменяем 16-ричный ключ на численный, если он есть
        for key, value in reference_data.items()
    }

def replace_hex_keys_with_numerical_in_times_tests(times_tests, swap_16):
    """
    Заменяет все 16-ричные ключи на численные для всех элементов в словаре times_tests.
    Если ключ отсутствует в swap_16, удаляет строку из times_tests.
    :param times_tests: Словарь с данными тестов.
    :param swap_16: Словарь с отображением 16-ричных ключей на численные индексы.
    :return: Обновленный словарь times_tests с численными ключами.
    """
    # Создаем новый словарь с проверкой на наличие ключей в swap_16
    updated_times_tests = {}

    for key, value in times_tests.items():
        # Фильтруем ключи и сохраняем только те, что есть в swap_16
        updated_values = {swap_16[k]: v for k, v in value[0].items() if k in swap_16}

        # Добавляем только те записи, где после фильтрации остались данные
        if updated_values:
            updated_times_tests[key] = [updated_values, value[1]]

    return updated_times_tests



def process_reference(reference_key, parsed_data, base_directory, max_tests):
    """
    Обрабатывает оптимизацию и копирование данных для указанного референсного файла.
    :param reference_key: Путь к референсному файлу.
    :param parsed_data: Распарсенные данные из всех файлов.
    :param base_directory: Базовая директория поиска.
    :param max_tests: Максимальное количество тестов для оптимизации.
    """
    # Создаем отображение hex -> числовой индекс
    swap_16 = create_reference_mapping(reference_key)

    # Получаем данные для reference и удаляем из общего parsed_data
    reference_data = parsed_data.pop(reference_key)
    reference_data = replace_hex_keys_with_numerical(reference_data, swap_16)

    # Создаем times_tests с численными ключами
    times_tests = {key: [value, key] for key, value in parsed_data.items()}
    times_tests = replace_hex_keys_with_numerical_in_times_tests(times_tests, swap_16)

    # Определяем количество функций
    num_functions = len(reference_data)

    # Выполняем оптимизацию
    similarity, weights = optimize_tests_continuous(times_tests, reference_data, num_functions, max_tests)

    # Выполняем копирование файлов
    create_selected_folder_and_copy_files(times_tests, reference_key, weights, base_directory)

    # Вывод результата
    print(f"\n--- Results for {reference_key} ---")
    if similarity is not None:
        print(f"Overall similarity: {similarity:.2f}%")
        for test, weight in weights.items():
            print(f"{test}: Weight = {weight:.2f}")
    else:
        print("Optimization problem could not be solved.")


def solve_for_all_references(base_directory, max_tests):
    """
    Находит все референсы и обрабатывает их по очереди.
    :param base_directory: Базовая директория поиска.
    :param max_tests: Максимальное количество тестов для оптимизации.
    """
    # Находим все файлы reference.histo
    parsed_data = find_and_process_files(base_directory)
    reference_keys = [key for key in parsed_data if "reference.histo" in key]

    if not reference_keys:
        print("No reference.histo files found.")
        return

    # Обрабатываем каждый reference.histo отдельно
    for reference_key in reference_keys:
        process_reference(reference_key, parsed_data.copy(), base_directory, max_tests)


# Пример использования
if __name__ == "__main__":
    # Укажите базовую директорию поиска
    base_directory = "./test_folder"
    max_tests = 4  # Максимальное количество тестов для оптимизации

    # Запуск обработки всех референсов
    solve_for_all_references(base_directory, max_tests)