import os
import shutil
import numpy as np
import cvxpy as cp
import argparse

def create_selected_folder_and_copy_files(times_tests, reference_file_path, weights, base_directory):
    """
    Создает папку test_folder_selected вне base_directory, копирует выбранные тесты с новыми именами,
    сохраняет reference.histo и весовой файл в compare_input рядом с первым тестом.
    :param times_tests: Словарь тестов, содержащий пути и данные
                        Ключ: Имя теста (например, "test1", "test2").
                        Значение: Список из двух элементов:
                            1)  Словарь, где:
                                    Ключ: Числовой индекс функции (например, "0", "1").
                                    Значение: Процентное значение функции в гистограмме (вещественное число).
                            2)  Строка, представляющая путь к файлу (например, путь к trace.histo).
    :param reference_file_path: Путь к референсному файлу.
    :param weights: Словарь с весами для каждого теста.
                    Ключ: Имя теста (например, "test1", "test2").
                    Значение: Вес теста (вещественное число от 0 до 1), указывающий на его значимость.
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

            # Получаем путь до директории теста
            test_dir_path = os.path.dirname(os.path.dirname(test_file_path))
            rel_path = os.path.relpath(test_dir_path, base_directory)
            path_parts = rel_path.split(os.sep)

            # Проверяем длину path_parts
            if len(path_parts) <= 1:
                print(f"Skipping test '{test}' due to unexpected path structure: '{rel_path}'")
                continue

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
    """
    Ключ: 16-ричное значение функции (например, "0x1a2b").
    Значение: Индекс этой функции (целое число, начиная с 0), 
              который соответствует порядку её первой встречи в референсном файле.
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
    и заполняет словарь словарей с дополнительным ключом <x>.
    :param base_dir: Базовая директория для поиска.
    :return: Словарь словарей {<x>: {путь файла: {функция: процентное значение}}}.
    """
    results = {}  # Основной словарь для хранения данных

    for root, dirs, files in os.walk(base_dir):
        # Определяем текущую папку (уровень <x>)
        relative_path = os.path.relpath(root, base_dir)
        top_level_folder = relative_path.split(os.sep)[0] if relative_path != '.' else os.path.basename(base_dir)

        if top_level_folder not in results:
            results[top_level_folder] = {}

        # Проверяем наличие reference.histo
        reference_file = os.path.join(root, "compare_input", "reference.histo")
        if os.path.exists(reference_file):
            print(f"Found reference.histo: {reference_file}")

            # Парсим reference.histo и добавляем в словарь
            parsed_reference = parse_file(reference_file)
            results[top_level_folder][reference_file] = parsed_reference

            # Ищем все trace.histo в подпапках
            for sub_dir in dirs:
                trace_file_path = os.path.join(root, sub_dir, "mode", "trace.histo")
                if os.path.exists(trace_file_path):
                    print(f"Found trace.histo: {trace_file_path}")

                    # Парсим trace.histo и добавляем в словарь
                    parsed_trace = parse_file(trace_file_path)
                    results[top_level_folder][trace_file_path] = parsed_trace

    return results


def optimize_tests(times_tests, target_function, num_tests, num_functions, max_sum_w):
    # Создание массивов s_i для всех тестов
    s_list = []
    test_indices = list(times_tests.keys())  # Получаем список имен тестов
    for test in times_tests:
        funcs = times_tests[test][0]
        s_i = np.zeros(num_functions)
        for func, value in funcs.items():
            func_index = int(func)  # Используем числовое значение как индекс
            s_i[func_index] = value
        s_list.append(s_i)
    s_list = np.array(s_list)

    # Преобразование целевой функции в массив T
    T = np.zeros(num_functions)
    for func, value in target_function.items():
        func_index = int(func)  # Используем числовое значение как индекс
        T[func_index] = value

    # Определение переменных
    w = cp.Variable(num_tests, integer=True)

    # Определяем ограничения
    constraints = [
        cp.sum(w) == max_sum_w,  # Ограничение: сумма всех тестов должна быть не больше max_sum_w
        w >= 0,
        w <= max_sum_w
    ]

    # Определение целевой функции: минимизация суммы отклонений от T
    objective = cp.Minimize(
        cp.sum(cp.abs(cp.matmul(w, s_list) / max_sum_w - T))
    )

    # Определяем проблему и решаем
    problem = cp.Problem(objective, constraints)
    problem.solve(solver=cp.CBC)

    # Выводим результаты
    if problem.status == cp.OPTIMAL or problem.status == cp.OPTIMAL_INACCURATE:
        # Нормализуем получившуюся функцию
        result_function = cp.matmul(w, s_list).value
        normalized_function = (result_function / np.sum(result_function)) * 100

        # Вычисляем метрику схожести
        min_sums = np.minimum(normalized_function, T)
        overall_similarity = np.sum(min_sums)

        # Выбираем тесты
        selected_tests = [test_indices[i] for i in range(num_tests) if w.value[i] > 0]

        for i in range(len(times_tests)):
            print(f"{test_indices[i]} -> {w.value[i]}")
        print(f"ILP similarity {overall_similarity}")

        return overall_similarity, selected_tests
    else:
        return None, None


def optimize_tests_continuous_selected(times_tests, target_function, selected_tests, num_functions, max_sum_w):
    # Создание массивов s_i для всех тестов
    s_list = []
    test_indices = selected_tests
    for test in selected_tests:
        funcs = times_tests[test][0]
        s_i = np.zeros(num_functions)
        for func, value in funcs.items():
            func_index = int(func)   # Используем числовое значение как индекс
            s_i[func_index] = value
        s_list.append(s_i)

    s_list = np.array(s_list)

    # Преобразование целевой функции в массив T
    T = np.zeros(num_functions)
    for func, value in target_function.items():
        func_index = int(func)  # Используем числовое значение как индекс
        T[func_index] = value

    # Определение переменных
    w = cp.Variable(len(selected_tests))

    # Определяем ограничения
    constraints = [w >= 0, cp.sum(w) == 1]

    # Определение целевой функции: минимизация суммы отклонений от T
    objective = cp.Minimize(
        cp.sum(cp.abs(cp.matmul(w, s_list) - T))
    )

    # Определяем проблему и решаем
    problem = cp.Problem(objective, constraints)
    problem.solve()

    # Выводим результаты
    if problem.status == cp.OPTIMAL or problem.status == cp.OPTIMAL_INACCURATE:
        # Нормализуем получившуюся функцию
        result_function = cp.matmul(w, s_list).value
        normalized_function = (result_function / np.sum(result_function)) * 100

        # Вычисляем метрику схожести
        min_sums = np.minimum(normalized_function, T)
        overall_similarity = np.sum(min_sums)

        result_weight = {}
        for i in range(len(selected_tests)):
            result_weight[test_indices[i]] = w.value[i]

        return overall_similarity, result_weight
    else:
        return None, None

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
            func_index = int(func)  # Используем числовое значение как индекс
            s_i[func_index] = value
        s_list.append(s_i)
    s_list = np.array(s_list)
    print(s_list)
    # Преобразование целевой функции в массив T
    T = np.zeros(num_functions)
    for func, value in target_function.items():
        func_index = int(func)  # Используем числовое значение как индекс
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
        """
        Ключ: Имя теста (например, "test1", "test2").
        Значение: Оптимизированный вес для этого теста (вещественное число от 0 до 1).
        """
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
    Если ключ отсутствует в swap_16, добавляет его и приписывает новый порядковый номер.
    :param times_tests: Словарь с данными тестов.
    :param swap_16: Словарь с отображением 16-ричных ключей на численные индексы.
    :return: Обновленный словарь times_tests с численными ключами.
    """
    """
    Ключ: Имя теста (например, "test1", "test2").
    Значение: Список из двух элементов:
        1)  Словарь, где:
                Ключ: Числовой индекс функции (например, "0", "1").
                Значение: Процентное значение функции в гистограмме (вещественное число).
        2)  Строка, представляющая путь к файлу (например, путь к trace.histo).
    """
    updated_times_tests = {}

    # Порядковый номер для новых значений
    next_index = len(swap_16)

    for key, value in times_tests.items():
        updated_values = {}

        for hex_key, v in value[0].items():
            # Если 16-ричный ключ не найден в swap_16, добавляем его с новым индексом
            if hex_key not in swap_16:
                swap_16[hex_key] = next_index
                next_index += 1

            # Заменяем 16-ричный ключ на численный
            updated_values[str(swap_16[hex_key])] = v

        # Добавляем обновленные значения в новый словарь
        updated_times_tests[key] = [updated_values, value[1]]

    return updated_times_tests

def process_reference(reference_key, parsed_data, base_directory, max_tests, flag_zlp_cont):
    """
    Обрабатывает оптимизацию и копирование данных для указанного референсного файла.
    :param reference_key: Путь к референсному файлу.
    :param parsed_data: Распарсенные данные из всех файлов, разделенные по <x>.
    :param base_directory: Базовая директория поиска.
    :param max_tests: Максимальное количество тестов для оптимизации.
    """
    # Извлекаем уровень <x> и данные для этого ключа
    folder_key = os.path.dirname(reference_key).split(os.sep)[-2] # Получаем <x> из пути
    print(folder_key)
    folder_data = parsed_data[folder_key]

    # Создаем отображение hex -> числовой индекс
    """
    Ключ: 16-ричное значение функции (например, "0x1a2b").
    Значение: Числовой индекс функции (целое число, начиная с 0), 
    который был сгенерирован при создании отображения из референсного файла.
    """
    swap_16 = create_reference_mapping(reference_key)

    # Получаем данные для reference и удаляем из общего folder_data
    reference_data = folder_data.pop(reference_key)
    """
    Ключ: Числовой индекс функции (например, "0", "1", "2").
    Значение: Процентное значение функции из референсной гистограммы (вещественное число).
    """
    reference_data = replace_hex_keys_with_numerical(reference_data, swap_16)

    # Создаем times_tests с численными ключами
    times_tests = {key: [value, key] for key, value in folder_data.items()}
    times_tests = replace_hex_keys_with_numerical_in_times_tests(times_tests, swap_16)

    # Определяем количество функций
    num_functions = len(swap_16)
    # Выполняем оптимизацию
    if(flag_zlp_cont):
        zlp_similarity, selected_tests = optimize_tests(times_tests, reference_data, num_tests=len(times_tests),
                                                        num_functions=num_functions, max_sum_w=max_tests)
        similarity, weights = optimize_tests_continuous_selected(times_tests, reference_data,
                                                                      selected_tests=selected_tests,
                                                                      num_functions=num_functions, max_sum_w=max_tests)
    else:
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


def solve_for_all_references(base_directory, max_tests, flag_zlp_cont):
    """
    Находит все референсы и обрабатывает их по очереди.
    :param base_directory: Базовая директория поиска.
    :param max_tests: Максимальное количество тестов для оптимизации.
    """
    """
    Ключ: Имя папки уровня <x> (например, "x1", "x2").
    Значение: Словарь, где:
        Ключ: Путь к файлу (например, "/path/to/reference.histo").
        Значение: Словарь, где:
            Ключ: Функция (например, "0x1a2b").
            Значение: Процентное значение функции (вещественное число).
    """
    if not os.path.exists(base_directory):
        raise FileNotFoundError(f"The specified folder '{base_directory}' does not exist.")
    # Находим все файлы reference.histo
    parsed_data = find_and_process_files(base_directory)
    no_keys = True
    # Перебираем ключи <x>
    for folder_key, folder_data in parsed_data.items():
        reference_keys = [key for key in folder_data if "reference.histo" in key]

        # Обрабатываем каждый reference.histo отдельно
        for reference_key in reference_keys:
            process_reference(reference_key, parsed_data, base_directory, max_tests, flag_zlp_cont)
            no_keys = False

    if no_keys:
        print(f"No reference.histo files found in {base_directory}.")

def main():
    parser = argparse.ArgumentParser(description="Скрипт максимальное кол-во тестов")

    # Добавляем аргументы
    parser.add_argument("--max-tests", type=int, default=100, help="Максимальное количество тестов (по умолчанию 100)")
    parser.add_argument("--min-similarity", type=int, default=0, help="Минимальная схожесть (по умолчанию 0)")
    parser.add_argument("--flag-zlp-cont", type=int, default=0, help="Включить ЦЛП+ЗЛП(по умолчанию 0(бинарное))")
    parser.add_argument("folder", type=str, help="Папка где хранятся наши тесты")
    # Парсим аргументы
    args = parser.parse_args()

    print(f"Folder path: {args.folder}")
    print(f"Maximum number of tests: {args.max_tests}")
    print(f"Minimum similarity: {args.min_similarity}")
    print(f"Flag zlp+cont: {args.flag_zlp_cont}")

    try:
        solve_for_all_references(args.folder, args.max_tests, args.flag_zlp_cont)
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()


"""
В гистограммах есть совпадающие числа, по разным адресам, одни и те же числа
Можно делить на блоки. 

    0x80000428              3
    0x80000464              3
    0x80000468              3
    0x8000046a              3
    СУЩНОСТЬ А (3)
    0xffffffff80003c10      20
    0xffffffff80003c12      20
    0xffffffff80003c14      20
    0xffffffff80003c16      20
    СУЩНОСТЬ Б (20)
    Последовательность можно заменить на другие сущности
    Сделать из трейсов сущности в виде блоков

    trace1
    0xffffffff80003c12      20
    0xffffffff80003c14      20
    0xffffffff80003c16      20

    trace2
    0x80000428              3
    0x80000464              3
    0x80000468              3

    Следующая двойстсвенная задача - 
    0x80000428-468          3
    0x8000046a              3
    0xffffffff80003c10      20
    0xffffffff80003c12-16   20

    trace1
    0xffffffff80003c12-16   20

    trace2
    0x80000428-468          3

    Блок если есть полностью в трейсе, либо нет совсем.
    Ориг файл, пока число такое-же - формирую блок (появляется некоторый блок) Потом смотрим в другом этот блок или хотя бы точка внутри него
    Пока числа такие-же - один блок (может получится подмножество). Прогоняем через все трейсы. Блок который представлен одинаковым.
    В отдельный файлик препроцессинга.

    Мин симиларити просто перебор по кол-ву тестов (или бин поиском - лучше бин поиском)
    
    ЦЛП+ЗЛП
    
    Есть filepath можно хранить, как folder
    
    Добавить обозначение типов для того чтобы было человекочитаемо
"""

