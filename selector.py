import os
import shutil
import numpy as np
import cvxpy as cp
import argparse
from typing import Dict, List


def create_selected_folder_and_copy_files(
    reference_file_path: str,
    weights: Dict[str, float],
    base_directory: str
):
    """
    Создает папку test_folder_selected вне base_directory, копирует выбранные тесты с новыми именами,
    сохраняет reference.histo и весовой файл в compare_input рядом с первым тестом.
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
            test_file_path = test  # Путь к файлу trace.histop

            # Получаем путь до директории теста
            test_dir_path = os.path.dirname(os.path.dirname(test_file_path))
            rel_path = os.path.relpath(test_dir_path, base_directory)
            path_parts = rel_path.split(os.sep)

            # Определяем новый путь для переноса
            original_test_folder = path_parts[-1]  # Исходное имя папки после <x>
            path_parts[-1] = f"trace_{test_number:02d}"  # Переименовываем в trace_01, trace_02 и т.д.
            new_test_dir_path = os.path.join(selected_folder, os.path.join(*path_parts))

            # Копируем всю директорию теста
            if not os.path.exists(new_test_dir_path):
                shutil.copytree(test_dir_path, new_test_dir_path)

            print(f"Copied folder '{original_test_folder}' to '{os.path.basename(new_test_dir_path)}'.")

            # Устанавливаем папку compare_input рядом с trace_01
            if test_number == 1:
                if len(path_parts) > 1:
                    compare_input_folder = os.path.join(selected_folder, path_parts[0], "compare_input")
                else:
                    compare_input_folder = os.path.join(selected_folder, "compare_input")
                if not os.path.exists(compare_input_folder):
                    os.makedirs(compare_input_folder)

            test_number += 1

    # Копируем референсный файл в папку compare_input
    if compare_input_folder:
        reference_file_name = os.path.basename(reference_file_path)
        new_reference_path = os.path.join(compare_input_folder, reference_file_name)
        shutil.copy(reference_file_path, new_reference_path)

        print(f"Copied reference file to '{new_reference_path}'.")

        # Записываем веса в файл weights в папке compare_input
        weights_file_path = os.path.join(compare_input_folder, "weights")
        with open(weights_file_path, "w") as f:
            for test, weight in weights.items():
                if weight > 0:
                    f.write(f"{weight:.4f}\n")

        print(f"Weights file saved to '{weights_file_path}'.")

    print(f"Selected tests and their content have been copied to '{selected_folder}'.")


def create_reference_mapping(reference_file: str) -> Dict[str, int]:
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

                # Разбираем строку и берем только первые два токена
                parts = line.split(maxsplit=2)  # Ограничиваем разбиение на два токена
                if len(parts) >= 2:
                    try:
                        function_name = parts[0]
                        int(parts[1])  # Проверяем, что второй токен можно преобразовать в число

                        # Если функция еще не встречалась, сохраняем её реальный индекс
                        if function_name not in reference_mapping:
                            reference_mapping[function_name] = real_index

                        # Увеличиваем индекс только для строк, которые не являются комментариями
                        real_index += 1
                    except ValueError:
                        print(f"Skipping invalid number in file '{reference_file}' at line {line_num}: {line}")
                else:
                    # Если строка не содержит двух токенов, пропускаем её
                    print(f"Skipping invalid line in file '{reference_file}' at line {line_num}: {line}")
    except Exception as e:
        print(f"Error reading the reference file {reference_file}: {e}")
    return reference_mapping



def parse_file(file_path: str) -> Dict[str, float]:
    """
    Парсит файл и возвращает словарь с функциями и их процентными значениями.
    Игнорирует некорректные строки, извлекая только первые два токена.
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

                # Разбираем строку и извлекаем первые два токена
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        function_name = parts[0]
                        number = int(parts[1])  # Пытаемся преобразовать второй токен в число
                        data.append((function_name, number))
                    except ValueError:
                        print(f"Invalid number format in file '{file_path}' at line {line_num}: {line}")
                        continue
                else:
                    print(f"Skipping invalid line in file '{file_path}' at line {line_num}: {line}")

            # Рассчитываем процентное соотношение
            total = sum(val for _, val in data)
            if total > 0:
                result = {func: (val / total) * 100 for func, val in data}
    except Exception as e:
        print(f"Error reading the file {file_path}: {e}")
    return result


def find_and_process_files(base_dir: str) -> Dict[str, Dict[str, Dict[str, float]]]:
    """
    Обходит папки внутри указанной директории, ищет файлы reference.histop и trace.histop,
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

        # Проверяем наличие reference.histop
        reference_file = os.path.join(root, "compare_input", "reference.histop")
        if os.path.exists(reference_file):
            print(f"Found reference.histop: {reference_file}")

            # Парсим reference.histop и добавляем в словарь
            parsed_reference = parse_file(reference_file)
            results[top_level_folder][reference_file] = parsed_reference

            # Ищем все trace.histop на глубине 2
            for sub_dir in dirs:
                trace_dir_path = os.path.join(root, sub_dir)
                if os.path.isdir(trace_dir_path):  # Проверяем, что это директория
                    # Ищем во втором уровне вложенности
                    for sub_sub_dir in os.listdir(trace_dir_path):
                        sub_sub_dir_path = os.path.join(trace_dir_path, sub_sub_dir)
                        if os.path.isdir(sub_sub_dir_path):
                            # Ищем trace.histop в подкаталоге второго уровня
                            trace_file_path = os.path.join(sub_sub_dir_path, "trace.histop")
                            if os.path.exists(trace_file_path):
                                print(f"Found trace.histop: {trace_file_path}")

                                # Парсим trace.histop и добавляем в словарь
                                parsed_trace = parse_file(trace_file_path)
                                results[top_level_folder][trace_file_path] = parsed_trace

    return results



def optimize_tests_continuous(times_tests: dict, target_function: dict, num_functions: int, max_sum_w: int) -> tuple:
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
    t = np.zeros(num_functions)
    for func, value in target_function.items():
        func_index = int(func)  # Используем числовое значение как индекс
        t[func_index] = value

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
        cp.sum(cp.abs(cp.matmul(w, s_list) - t))  # Минимизация отклонений от целевой функции
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
        min_sums = np.minimum(normalized_function, t)
        print(min_sums, normalized_function, t)
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


def replace_hex_keys_with_numerical(reference_data: dict, swap_16: dict) -> dict:
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


def replace_hex_keys_with_numerical_in_times_tests(times_tests: dict, swap_16: dict) -> dict:
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


def process_reference(reference_key: str, parsed_data: dict, base_directory: str, max_tests: int, min_similarity: int):
    """
    Обрабатывает оптимизацию и копирование данных для указанного референсного файла.
    :param reference_key: Путь к референсному файлу.
    :param parsed_data: Распарсенные данные из всех файлов, разделенные по <x>.
    :param base_directory: Базовая директория поиска.
    :param max_tests: Максимальное количество тестов для оптимизации.
    :param min_similarity: Минимально требуемая схожесть
    """
    # Извлекаем уровень <x> и данные для этого ключа
    folder_key = os.path.dirname(reference_key).split(os.sep)[-2]  # Получаем <x> из пути
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

    num_functions = len(swap_16)

    if min_similarity:
        # Определение диапазона для бинарного поиска
        min_tests = 1
        max_tests = len(times_tests)  # Максимальное количество тестов (например, длина times_tests)

        # Инициализация переменных для хранения результата
        result_similarity = 0
        result_weights = None

        # Начинаем бинарный поиск
        while min_tests <= max_tests:
            # Вычисляем среднее значение для max_tests
            mid_tests = (min_tests + max_tests) // 2

            # Вызываем функцию оптимизации с количеством тестов = mid_tests
            similarity, weights = optimize_tests_continuous(times_tests, reference_data, num_functions, mid_tests)

            # Если похожесть больше или равна min_similarity, сохраняем результаты
            if similarity >= min_similarity:
                # Сохраняем текущие результаты
                result_similarity = similarity
                result_weights = weights
                # Пытаемся уменьшить количество тестов, чтобы найти минимальное значение
                max_tests = mid_tests - 1
            else:
                # Если похожесть меньше min_similarity, увеличиваем количество тестов
                min_tests = mid_tests + 1

        # После завершения бинарного поиска, result_similarity и result_weights содержат нужные значения
        similarity = result_similarity
        weights = result_weights
    else:
        # Выполняем оптимизацию
        similarity, weights = optimize_tests_continuous(times_tests, reference_data, num_functions, max_tests)
    # Проверяем, если similarity равно 0, выбрасываем исключение
    if similarity == 0:
        raise ValueError("Unable to achieve the required similarity value.")
    # Выполняем копирование файлов
    create_selected_folder_and_copy_files(reference_key, weights, base_directory)

    # Вывод результата
    print(f"\n--- Results for {reference_key} ---")
    if similarity is not None:
        print(f"Overall similarity: {similarity:.2f}%")
        for test, weight in weights.items():
            print(f"{test}: Weight = {weight:.2f}")
    else:
        print("Optimization problem could not be solved.")


def solve_for_all_references(base_directory: str, max_tests: int, min_similarity: int):
    """
    Находит все референсы и обрабатывает их по очереди.
    :param base_directory: Базовая директория поиска.
    :param max_tests: Максимальное количество тестов для оптимизации.
    :param min_similarity: Минимальная требуемая схожесть
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
    normalized_path = base_directory.replace('/', '\\')
    parsed_data = find_and_process_files(normalized_path)
    no_keys = True
    # Перебираем ключи <x>
    for folder_key, folder_data in parsed_data.items():
        reference_keys = [key for key in folder_data if "reference.histo" in key]

        # Обрабатываем каждый reference.histo отдельно
        for reference_key in reference_keys:
            process_reference(reference_key, parsed_data, base_directory, max_tests, min_similarity)
            no_keys = False

    if no_keys:
        print(f"No reference.histo files found in {base_directory}.")


def main():
    parser = argparse.ArgumentParser(description="Скрипт максимальное кол-во тестов")

    # Добавляем аргументы
    parser.add_argument("--max-tests", type=int, default=100, help="Максимальное количество тестов (по умолчанию 100)")
    parser.add_argument("--min-similarity", type=int, default=0, help="Минимальная схожесть (по умолчанию 0)")
    parser.add_argument("folder", type=str, help="Папка где хранятся наши тесты")
    # Парсим аргументы
    args = parser.parse_args()

    print(f"Folder path: {args.folder}")
    print(f"Maximum number of tests: {args.max_tests}")
    print(f"Minimum similarity: {args.min_similarity}")

    try:
        solve_for_all_references(args.folder, args.max_tests, args.min_similarity)
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()


