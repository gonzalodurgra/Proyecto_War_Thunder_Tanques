import sys
import os

# Permitir que Python encuentre main.py en la carpeta padre
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
