# note the ordering of imports matters
import email

from pyqt_distutils.build_ui import build_ui
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need
# fine tuning.
build_options = {
    'excludes': ['email', 'tkinter', 'pyqt5_tools', 'unittest', 'xml', 'distutils',
                 'ssl', 'lzma', 'bz2', 'socket', 'http', 'html'],
    'packages': ['generated'],
    'build_exe': 'R:/TEMP',
    'zip_include_packages': ['PySide2', 'shiboken2']
}

import sys

base = 'Win32GUI' if sys.platform == 'win32' else None

executables = [
    Executable('src/main/python/main.py',
               base=base,
               targetName='tafels.exe',
               icon="src/main/icons/app.ico"
               )
]

setup(name='tafels',
      version='1.0',
      description='',
      options={'build_exe': build_options},
      cmdclass={'build_ui': build_ui},
      executables=executables)
