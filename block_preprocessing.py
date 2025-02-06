def merge_with_base_dict(base_dict: dict, data_dict: dict, swap_16: dict) -> dict:
    """
    Объединяет данные из base_dict с данными из data_dict, используя swap_16 для преобразования ключей.
    :param base_dict: Словарь с базовыми значениями.
    :param data_dict: Словарь с дополнительными данными.
    :param swap_16: Словарь для замены 16-ричных ключей на числовые индексы.
    :return: Объединенный словарь.
    """
    result = {str(key): [0] * (1 + len(data_dict)) for key in swap_16.values()}

    for key, base_value in base_dict.items():
        if key in result:
            result[key][0] = base_value  # Заполняем значением из base_dict

    for index, (path, values) in enumerate(data_dict.items()):
        hist_values = values[0]
        for key, value in hist_values.items():
            if key in result:
                result[key][index + 1] = value  # Добавляем данные из data_dict

    return result


def merge_keys_with_sum(data: dict) -> dict:
    """
    Объединяет ключи с одинаковыми значениями, суммируя их.
    :param data: Словарь с функциями и их значениями.
    :return: Словарь с суммированными значениями для одинаковых ключей.
    """
    value_to_keys = {}

    for key, values in data.items():
        value_tuple = tuple(values)  # Преобразуем в tuple для использования в качестве ключа
        if value_tuple not in value_to_keys:
            value_to_keys[value_tuple] = []
        value_to_keys[value_tuple].append(key)

    result = {}
    for value_tuple, keys in value_to_keys.items():
        main_key = keys[0]  # Основной ключ для группы
        summed_values = [sum(data[k][i] for k in keys) for i in range(len(data[main_key]))]
        result[main_key] = summed_values

    return result


def update_reference_and_times(reference_data: dict, times_tests: dict, result: dict) -> tuple:
    """
    Обновляет данные референса и тестов с использованием объединенных данных.
    :param reference_data: Данные референса.
    :param times_tests: Данные тестов.
    :param result: Результат объединения данных.
    :return: Обновленные данные референса и тестов.
    """
    updated_reference_data = {key: values[0] for key, values in result.items() if values[0] > 0}

    index = 1
    updated_times_tests = {}
    for test_path, data in times_tests.items():
        updated_values = {key: values[index] for key, values in result.items() if values[index] > 0}
        updated_times_tests[test_path] = [updated_values, data[1]]
        index += 1

    return updated_reference_data, updated_times_tests


def calculate_percentages(data: dict) -> dict:
    """
    Вычисляет процентное соотношение значений относительно их суммы.
    :param data: Словарь с данными.
    :return: Словарь с процентными значениями.
    """
    total = sum(data.values())
    if total == 0:
        return {key: 0 for key in data}
    return {key: (value / total) * 100 for key, value in data.items()}


def calculate_nested_percentages(data: dict) -> dict:
    """
    Вычисляет процентное соотношение значений в каждой папке относительно их суммы.
    :param data: Словарь с данными для каждой папки.
    :return: Обновленный словарь с процентами для каждой папки.
    """
    updated_data = {}
    for folder, (values_dict, path) in data.items():
        total = sum(values_dict.values())
        if total == 0:
            percentages = {key: 0 for key in values_dict}
        else:
            percentages = {key: (value / total) * 100 for key, value in values_dict.items()}
        updated_data[folder] = [percentages, path]
    return updated_data
