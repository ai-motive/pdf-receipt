from pathlib import Path


## Path options
ROOT_DIR = Path(__file__).resolve().parent

TGT_DATE = '220114 점심'

PDF_EXTENSIONS = ['pdf']
PDF_DIR = ROOT_DIR / 'pdf' / TGT_DATE

CSV_DIR = ROOT_DIR / 'csv'

HOMETAX_URL = "https://teht.hometax.go.kr/wqAction.do?actionId=ATTABZAA001R08&screenId=UTEABAAA13&popupYn=false&realScreenId="
HOMETAX_DATA = "<map id=\"ATTABZAA001R08\"><pubcUserNo/><mobYn>N</mobYn><inqrTrgtClCd>1</inqrTrgtClCd><txprDscmNo>\{CRN\}</txprDscmNo><dongCode>85</dongCode><psbSearch>Y</psbSearch><map id=\"userReqInfoVO\"/></map><nts<nts>nts>65AGfuvw27DVJrPbJ8pYRkgFW9OhjQJa3Y3FuhNj6ZlM5"
HOMETAX_HEADERS = {'Content-Type': 'text/xml'}

# 'https://www.hometax.go.kr/websquare/websquare.wq?w2xPath=/ui/pp/index_pp.xml'