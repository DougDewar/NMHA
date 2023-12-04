"""A script to create a .bat file used to autorun nmha.py at startup.
"""

import os
import sys

NMHA_FILE_NAME = 'nmha.py'
BAT_FILE_NAME = 'nmha.bat'

def get_nmha_absolute_path():
    """Determines the absolute path to the nmha.py file.

    Returns:
        String: The path to the nmha.py file.
    """
    utilities_directory_path = os.path.dirname(__file__)
    nmha_directory_path = os.path.dirname(utilities_directory_path)
    nmha_file_path = f'{nmha_directory_path}\\{NMHA_FILE_NAME}'
    return nmha_file_path

def main():
    """Using the path to the nmha.py file and the path to the python
    executable, creates a bat file to be added to the Windows Startup folder
    or scheduled using the Task Scheduler.
    """
    nmha_file_path = get_nmha_absolute_path()
    python_path = sys.executable
    if os.path.isfile(nmha_file_path):
        bat_text = f'@echo off\n"{python_path}" "{nmha_file_path}"\npause'
        utilities_directory_path = os.path.dirname(__file__)
        bat_file_path = f'{utilities_directory_path}\\{BAT_FILE_NAME}'
        print(bat_file_path)
        with open(bat_file_path, 'w', encoding='utf-8') as bat_file:
            bat_file.write(bat_text)
        print(f'Path to bat file: {bat_file_path}')
    input('Press any key to quit.')

if __name__ == '__main__':
    main()
