import re
import os
import shutil
import logging
import pandas as pd

from pathlib import Path
from src.config import settings

'''
The FileHandler module is used to check the input directory path
for new files. If new files are found, essential data is extracted
and the files are reanmed and moved to the destination directory as specified.
'''
class FileHandler:
    def __init__(self, log: logging.Logger):
        self.log = log

    def get_file_list(self, dir: str) -> list[str]:
        '''
        Checks a given directory and returns a list of all files found there.
        Can be used to check for new files in the input directory or a list of
        already processed files in the destination directory.
        '''
        pdf_files = [str(file) for file in os.listdir(dir)\
                        if (file != '.DS_Store') and file.lower().endswith('.pdf')]
        return pdf_files
    
    def get_destination_directory(self) -> str:
        '''
        Extracts destination directory path from the configuration
        and verifies its existence.
        '''
        dest_dir = settings.data_dir
        if not dest_dir:
            raise ValueError("Destination directory path is not specified in the\
                             configuration.")
        if not dest_dir.exists() or not dest_dir.is_dir():
            raise FileNotFoundError(f"Destination directory does not exist:\
                                    {dest_dir}") 
        return dest_dir

    def get_input_directory(self) -> str:
        '''
        Extracts input directory path from the configuration
        and verifies its existence.
        '''
        input_dir = settings.invoice_dir
        if not input_dir:
            raise ValueError("Input directory path is not specified in the\
                             configuration.")
        if not input_dir.exists() or not input_dir.is_dir():
            raise FileNotFoundError(f"Input directory does not exist:\
                                    {input_dir}")
        return input_dir
    
    def get_new_file_name(self, option: str, date: str, name: str) -> str:
        return f"{option}_{name}_{date}.pdf"
    
    def build_path(self, path: str, filename: str) -> os.path:
        return os.path.join(path, filename)
