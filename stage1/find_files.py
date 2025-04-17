import os
import fnmatch
import json
import shutil

STAGES_DIR = "stages"
REFERENCE_DIR = ""
SAMPLE_DIR = ""


def ensure_stages_dir():
    if os.path.exists(STAGES_DIR):
        shutil.rmtree(STAGES_DIR)  # Удаляет всю папку со всем содержимым
    os.makedirs(STAGES_DIR)         # Создаёт папку заново


def write_intermediate_json(file_type: str, file_path: str, index: int):
    """
    Создаёт промежуточный JSON-файл в папке stages/.
    """
    data = {
        "type": file_type,
        "source_file": file_path
    }
    filename = f"{file_type}_{index:03}.json"
    output_path = os.path.join(STAGES_DIR, filename)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[+] Saved {file_type} file: {output_path}")


def find_and_store_artifacts(base_dir: str, mask: str):
    """
    Ищет файлы по маске и сохраняет информацию о них как промежуточные артефакты.
    """
    sample_count = 0

    for root, _, files in os.walk(base_dir):
        for filename in files:
            if fnmatch.fnmatch(filename, mask):
                full_path = os.path.abspath(os.path.join(root, filename))

                if REFERENCE_DIR in full_path:
                    write_intermediate_json("reference", full_path, 0)
                elif SAMPLE_DIR in full_path:
                    write_intermediate_json("sample", full_path, sample_count)
                    sample_count += 1


def main():
    run_dir = os.environ.get("RUN_DIR")
    reference_dir = os.environ.get("REFERENCE_DIR", os.path.join(run_dir, "compare_input"))
    sample_dir = os.environ.get("SAMPLE_DIR", run_dir)
    lookup_mask = os.environ.get("LOOKUP_MASK", "*.jfr")

    if not run_dir or not os.path.exists(run_dir):
        raise FileNotFoundError("RUN_DIR is not set or does not exist.")

    global REFERENCE_DIR, SAMPLE_DIR
    REFERENCE_DIR = os.path.abspath(reference_dir)
    SAMPLE_DIR = os.path.abspath(sample_dir)

    print(f"RUN_DIR: {run_dir}")
    print(f"REFERENCE_DIR: {REFERENCE_DIR}")
    print(f"SAMPLE_DIR: {SAMPLE_DIR}")
    print(f"LOOKUP_MASK: {lookup_mask}")

    ensure_stages_dir()
    find_and_store_artifacts(run_dir, lookup_mask)


if __name__ == "__main__":
    main()
