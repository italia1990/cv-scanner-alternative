import os
import pathlib

db_path = os.getcwd() + '/resume_scans.sqlite'
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + db_path
SQLALCHEMY_TRACK_MODIFICATIONS = False

ALLOWED_FILES_TYPES = ['pdf', 'docx', 'doc', 'html', 'xhtml',
                       'txt']  # based on the file processing functions in the resume scanner .py.

# AFFINDA_TOKEN = '8b740a87d3078cbab63c8354862c605ec671e900'
AFFINDA_TOKEN = '4f12bf14d4babecc03153d3c49823f3636f1c634'
# AFFINDA_TOKEN = 'f6163ae4e8f7507342c7881c8b1012d29c31781f'
# AFFINDA_TOKEN = '1fb65827595fbd558793fc312c565379f577d067'

# a reminder of why this folder is currently needed is in the resume_scanner.py where it's used
TEMP_FOLDER = os.getcwd() + '/temp/'

pathlib.Path(TEMP_FOLDER).mkdir(parents=True, exist_ok=True)  # create folder if doesn't exist