from pathlib import Path


## Path options
ROOT_DIR = Path(__file__).resolve().parent

TGT_DATE = '220114 점심'

PDF_EXTENSIONS = ['pdf']
PDF_DIR = ROOT_DIR / 'pdf' / TGT_DATE

CSV_DIR = ROOT_DIR / 'csv'