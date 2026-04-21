# ЧЕРНОВИК И ПРАКТИКА РАБОТЫ С МОДУЛЯМИ И БИБЛИОТЕКАМИ

import argparse
import os
import shutil
import pathlib
import json
import logging


# В теории это отдельный файл для работы с модулем ОС, правильно разделить на функции
# Рекурсировать (Ну или продумать что то лучше дабы не заполнять стеки памяти)
def work_os(path):
    while True:
        print(f"\nТекущая директория: {path}")
        try:
            user_input = int(input(
                "\n1. Вывести содержимое текущей директории\n" \
                "2. Перейти в директорию\n" \
                "3. Подняться на уровень выше\n" \
                "4. Завершить режим\n" \
                "Выберите действие: "
            ))
            if not (1 <= user_input <= 4):
                    raise ValueError
        except ValueError:
            print("\nОшибка ввода! Принимаются только цифры в указанном диапозоне (пока что)\n")

        if user_input == 1:
            print(f"\nСодержимое каталога: {path}")
            for elem in os.listdir(path):
                print(f"    {elem}")

        elif user_input == 2:
            name_direct = input("\nВведите название директории: ")
            if name_direct in os.listdir(path):
                work_os(os.path.abspath(os.path.join(path, name_direct)))
            else:
                print("\nУказанной директории нету в текущем каталоге.")

        elif user_input == 3:
            work_os(os.path.abspath(os.path.join(path, "../..")))

        elif user_input == 4:
            print("\nЗавершение режима перемещения...")
            break


def work_file_with_os(path):
    print("\nСоздание (пока что тестого каталога)...")
    os.makedirs(os.path.join(path,"HackLab", "Test_Folder"))
    new_path = os.path.join(path,"HackLab", "Test_Folder")
    
    while True: 
        print(f"\nТекущая директория: {new_path}\n" \
              f"Содержимое тестовой папки:")
        
        for elem in os.listdir(new_path):
            print(elem)
        try:
            user_input = int(input(
                "\n1. Создать файл\n" \
                "2. Переименовать файл\n" \
                "3. Удалить файл\n"
                "4. Создать каталог\n"
                "5. Перейти в каталог\n" \
                "6. Вернуться назад\n" \
                "7. Завершить режим\n" \
                "Выберите действие: "
            
            ))
        except ValueError:
            print("\nОшибка ввода! Принимаются только цифры в указанном диапозоне (пока что)\n")
        
        if user_input == 1:
            new_file = input("\nВведите название файла: ")
            with open(os.path.join(new_path, new_file), "a") as file:
                print("\nФайл создан...")

        elif user_input == 2:
            name_file = input("\nВведите имя файла: ")
            if os.path.exists(os.path.join(new_path, name_file)):
                new_name_file = input("\nПереименовать: ")
                os.rename(os.path.join(new_path, name_file), os.path.join(new_path, new_name_file))
            else:
                print("\nДанного файла нету в директории")

        elif user_input == 3:
            name_file = input("\nВведите имя файла: ")
            if os.path.exists(os.path.join(new_path, name_file)):
                os.remove(os.path.join(new_path, name_file))
            else:
                print("\nДанного файла нету в директории")

        elif user_input == 7:
            print("\nЗавершение режима работы с файлами...")
            os.rmdir(new_path)
            break
                

def main(path):
    print("Утилита для работы с файлами.\n")
    while True:
        try:
            user_input = int(input(
            "\n1. Режим для работы с пермещением по файлам и директориям\n" \
            "2. Зайти в доп режим для работы с файлами и каталогами (Удалить, Переимновать и тд)\n" \
            "3. Создать объект Path из библиотеки, и пройти по этой директории\n" \
            "4. Прочесть json-файл и вывести содержимое\n" \
            "5. Завершить работу программы.\n" \
            "Выберите действие: "
            )) 
            if not (1 <= user_input <= 5):
                raise ValueError
        except ValueError:
            print("\nОшибка ввода! Принимаются только цифры в указанном диапозоне (пока что)\n")
        
        if user_input == 1:
            work_os(path)
        
        elif user_input == 2:
            work_file_with_os(path)

        elif user_input == 5:
            print("\nПрограмма завершается...")
            break

main(os.path.abspath(os.path.join("../.."))) # путь начала хоум/имя пользователя


