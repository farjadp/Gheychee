#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для проверки переводов в файлах локализации.
Сравнивает значения переменных из messages_EN.py с остальными файлами messages_XX.py
и выводит список переменных, которые еще не переведены (имеют идентичные значения),
вместе с номерами строк, на которых они найдены.
"""

import sys
import importlib.util
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Путь к папке с файлами локализации
LANGUAGES_DIR = Path(__file__).parent / "CONFIG" / "LANGUAGES"
EN_FILE = LANGUAGES_DIR / "messages_EN.py"


class Tee:
    """Класс для дублирования вывода в консоль и файл."""
    def __init__(self, *files):
        self.files = files
    
    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()
    
    def flush(self):
        for f in self.files:
            f.flush()


def load_messages_class(file_path: Path) -> type:
    """Загружает класс Messages из файла."""
    try:
        spec = importlib.util.spec_from_file_location("messages_module", file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Не удалось загрузить модуль из {file_path}")
        
        module = importlib.util.module_from_spec(spec)
        sys.modules['messages_module'] = module
        spec.loader.exec_module(module)
        
        if not hasattr(module, 'Messages'):
            raise AttributeError(f"Класс Messages не найден в {file_path}")
        
        return module.Messages
    except Exception as e:
        print(f"❌ Ошибка при загрузке {file_path}: {e}", file=sys.stderr)
        return None


def get_class_attributes(cls: type) -> Dict[str, any]:
    """Извлекает все атрибуты класса (переменные), исключая методы и служебные."""
    attributes = {}
    for attr_name in dir(cls):
        # Пропускаем служебные атрибуты и методы
        if attr_name.startswith('_'):
            continue
        
        attr_value = getattr(cls, attr_name)
        # Пропускаем методы и функции
        if callable(attr_value):
            continue
        
        attributes[attr_name] = attr_value
    
    return attributes


def find_variable_lines(file_path: Path) -> Dict[str, int]:
    """Находит номера строк для всех переменных класса Messages в файле."""
    var_lines = {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        in_class = False
        class_indent = 0
        
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Проверяем начало класса Messages
            if 'class Messages' in stripped:
                in_class = True
                class_indent = len(line) - len(line.lstrip())
                continue
            
            # Если мы внутри класса
            if in_class:
                current_indent = len(line) - len(line.lstrip())
                
                # Если отступ меньше или равен отступу класса, значит мы вышли из класса
                if stripped and current_indent <= class_indent and not stripped.startswith('#'):
                    # Проверяем, не начинается ли новый класс
                    if stripped.startswith('class '):
                        break
                    # Если это не комментарий и не пустая строка, возможно мы вышли из класса
                    if not stripped.startswith('#'):
                        # Но может быть это просто метод на том же уровне
                        if 'def ' in stripped or 'class ' in stripped:
                            break
                
                # Ищем определения переменных (VAR_NAME = ...)
                # Паттерн: имя переменной (только заглавные буквы, цифры и подчеркивания) = значение
                match = re.match(r'^\s*([A-Z][A-Z0-9_]*)\s*=', stripped)
                if match:
                    var_name = match.group(1)
                    var_lines[var_name] = line_num
        
    except Exception as e:
        print(f"⚠️  Ошибка при чтении файла {file_path}: {e}", file=sys.stderr)
    
    return var_lines


def compare_messages_with_lines(
    en_attributes: Dict[str, any], 
    lang_attributes: Dict[str, any],
    lang_var_lines: Dict[str, int]
) -> List[Tuple[str, int]]:
    """Сравнивает атрибуты и возвращает список кортежей (имя_переменной, номер_строки) с идентичными значениями."""
    untranslated = []
    
    # Проверяем все переменные из английского файла
    for var_name, en_value in en_attributes.items():
        if var_name in lang_attributes:
            lang_value = lang_attributes[var_name]
            # Сравниваем значения
            if lang_value == en_value:
                line_num = lang_var_lines.get(var_name, 0)
                untranslated.append((var_name, line_num))
    
    return untranslated


def main():
    """Основная функция."""
    # Создаем файл для записи результатов
    script_dir = Path(__file__).parent
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = script_dir / f"translation_check_results_{timestamp}.txt"
    
    # Открываем файл для записи
    with open(output_file, 'w', encoding='utf-8') as f:
        # Создаем Tee для дублирования вывода
        tee = Tee(sys.stdout, f)
        
        # Перенаправляем print в Tee
        original_print = print
        def print_tee(*args, **kwargs):
            kwargs['file'] = tee
            original_print(*args, **kwargs)
        
        # Временно заменяем print
        import builtins
        builtins.print = print_tee
        
        try:
            _main_logic(output_file)
        finally:
            # Восстанавливаем оригинальный print
            builtins.print = original_print
    
    return 0


def _main_logic(output_file: Path):
    """Основная логика проверки переводов."""
    print("🔍 Проверка переводов в файлах локализации\n")
    print(f"📁 Папка: {LANGUAGES_DIR}\n")
    print("=" * 80)
    
    # Загружаем эталонный файл (английский)
    print(f"\n📖 Загрузка эталонного файла: {EN_FILE.name}")
    en_messages = load_messages_class(EN_FILE)
    if en_messages is None:
        print("❌ Не удалось загрузить эталонный файл. Выход.")
        return
    
    en_attributes = get_class_attributes(en_messages)
    print(f"✅ Загружено переменных из {EN_FILE.name}: {len(en_attributes)}")
    
    # Находим все файлы messages_XX.py
    lang_files = sorted(LANGUAGES_DIR.glob("messages_*.py"))
    lang_files = [f for f in lang_files if f.name != "messages_EN.py"]
    
    if not lang_files:
        print("\n❌ Не найдено файлов для сравнения.")
        return
    
    print(f"\n📚 Найдено файлов для проверки: {len(lang_files)}\n")
    print("=" * 80)
    
    # Результаты
    results = {}
    total_untranslated = {}
    
    # Проверяем каждый файл
    for lang_file in lang_files:
        lang_code = lang_file.stem.replace("messages_", "").upper()
        print(f"\n🌐 Проверка: {lang_file.name} ({lang_code})")
        
        lang_messages = load_messages_class(lang_file)
        if lang_messages is None:
            print(f"   ⚠️  Пропущен из-за ошибки загрузки")
            continue
        
        lang_attributes = get_class_attributes(lang_messages)
        lang_var_lines = find_variable_lines(lang_file)
        untranslated = compare_messages_with_lines(en_attributes, lang_attributes, lang_var_lines)
        
        results[lang_code] = {
            'file': lang_file.name,
            'total_vars': len(lang_attributes),
            'untranslated': untranslated,
            'untranslated_count': len(untranslated)
        }
        
        total_untranslated[lang_code] = len(untranslated)
        
        # Выводим статистику
        untranslated_count = len(untranslated)
        translated_count = len(lang_attributes) - untranslated_count
        translation_percent = (translated_count / len(en_attributes) * 100) if en_attributes else 0
        
        print(f"   📊 Всего переменных: {len(lang_attributes)}")
        print(f"   ✅ Переведено: {translated_count} ({translation_percent:.1f}%)")
        print(f"   ❌ Не переведено: {untranslated_count} ({100 - translation_percent:.1f}%)")
    
    # Выводим детальные результаты
    print("\n" + "=" * 80)
    print("\n📋 ДЕТАЛЬНЫЙ СПИСОК НЕПЕРЕВЕДЕННЫХ ПЕРЕМЕННЫХ С НОМЕРАМИ СТРОК\n")
    print("=" * 80)
    
    for lang_code in sorted(results.keys()):
        data = results[lang_code]
        if data['untranslated_count'] == 0:
            print(f"\n✅ {lang_code} ({data['file']}): Все переменные переведены!")
            continue
        
        print(f"\n❌ {lang_code} ({data['file']}): {data['untranslated_count']} непереведенных переменных")
        print("-" * 80)
        
        # Сортируем по номеру строки
        sorted_untranslated = sorted(data['untranslated'], key=lambda x: (x[1] if x[1] > 0 else 999999, x[0]))
        
        # Группируем по категориям (по префиксу)
        grouped = {}
        for var_name, line_num in sorted_untranslated:
            # Определяем категорию по префиксу
            prefix = var_name.split('_')[0] if '_' in var_name else 'OTHER'
            if prefix not in grouped:
                grouped[prefix] = []
            grouped[prefix].append((var_name, line_num))
        
        # Выводим сгруппированные переменные с номерами строк
        for prefix in sorted(grouped.keys()):
            vars_list = sorted(grouped[prefix], key=lambda x: (x[1] if x[1] > 0 else 999999, x[0]))
            print(f"\n  📌 {prefix}_* ({len(vars_list)} переменных):")
            # Выводим переменные с номерами строк
            for var_name, line_num in vars_list:
                line_info = f"строка {line_num}" if line_num and line_num > 0 else "строка не найдена"
                print(f"     {var_name:<50} ({line_info})")
    
    # Итоговая статистика
    print("\n" + "=" * 80)
    print("\n📊 ИТОГОВАЯ СТАТИСТИКА\n")
    print("=" * 80)
    
    print(f"{'Язык':<8} {'Файл':<25} {'Всего':<8} {'Переведено':<12} {'Не переведено':<15} {'%':<8}")
    print("-" * 80)
    
    for lang_code in sorted(results.keys()):
        data = results[lang_code]
        translated = data['total_vars'] - data['untranslated_count']
        percent = (translated / len(en_attributes) * 100) if en_attributes else 0
        print(f"{lang_code:<8} {data['file']:<25} {data['total_vars']:<8} {translated:<12} {data['untranslated_count']:<15} {percent:>6.1f}%")
    
    # Находим языки с наибольшим количеством непереведенных переменных
    if total_untranslated:
        max_untranslated = max(total_untranslated.values())
        if max_untranslated and max_untranslated > 0:
            worst_languages = [lang for lang, count in total_untranslated.items() if count == max_untranslated]
            print(f"\n⚠️  Наибольшее количество непереведенных переменных ({max_untranslated}): {', '.join(worst_languages)}")
    
    print("\n" + "=" * 80)
    print("✅ Проверка завершена!")
    print(f"\n💾 Результаты сохранены в файл: {output_file}")


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

