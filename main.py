import argparse
import collections
import pandas as pd
pd.set_option('display.max_row', 500)
pd.set_option('display.max_columns', 500), pd.set_option('display.width', 1000)
import pdfplumber
import re
import sys
from typing import OrderedDict

from config import *
from python_utils.common import general as cg


TITLE_COLUMNS = [
    '승인번호', '카드종류', '카드번호', '결제일자', '판매자 상호', '대표자명', '사업자등록번호',
]
PRICE_COLUMNS = [
    '금액', '부가세', '합계'
]
TOTAL_COLUMNS = TITLE_COLUMNS + PRICE_COLUMNS
SKIP_COLUMNS = ['금액'] * 2


def parse_data_from_pdf(path) -> OrderedDict:
    total_dict = collections.OrderedDict()
    total_dict['파일명'] = Path(path).name

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split('\n')

            for l_idx, line in enumerate(lines):
                # 대상열 이름 포함여부 확인
                title_line_ = any(name in line for name in TOTAL_COLUMNS)
                if title_line_:
                    parse_dict = parse_line(line, lines[l_idx + 1])
                    total_dict.update(parse_dict)
                    continue

    return total_dict


def parse_line(title_line, val_line):
    titles = split_str_from_words(title_line, TOTAL_COLUMNS)

    skip_title_ = (titles == SKIP_COLUMNS)
    skip_val_ = (''.join(val_line.replace(' ', '').split('\xa0')) == '백천원백천원')
    skip_line_ = (skip_title_ and skip_val_)
    if skip_line_:
        return {}

    # 열이름 인덱스 저장
    col_indices = []
    for tgt_col in TOTAL_COLUMNS:
        if tgt_col in titles:
            if tgt_col in TITLE_COLUMNS:
                col_idx = titles.index(tgt_col)
                col_indices.append(col_idx)
            elif tgt_col in PRICE_COLUMNS:
                col_idx = titles.index(tgt_col)
                col_indices.append(col_idx)

    # 값 추출 (열이름 기반)
    parse_dict = {}
    for col_idx in col_indices:
        col_name = titles[col_idx]

        # 소제목
        if col_name in TITLE_COLUMNS:
            tmp_vals = val_line.split(' ')

            if col_name == '결제일자':
                vals = re.findall(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', val_line)
            else:
                even_ = (len(tmp_vals) % 2 == 0)
                if even_:
                    vals = tmp_vals
                else:
                    first_val = tmp_vals.pop(0)
                    tmp_vals[0] = first_val + ' ' + tmp_vals[0]
                    vals = tmp_vals

        # 금액
        elif col_name in PRICE_COLUMNS[0]:
            tmp_vals = [line for line in val_line.replace(' ', '').split('\xa0') if len(line) > 0]
            vals = tmp_vals

        # 부가세, 합계
        elif col_name in PRICE_COLUMNS[1:]:
            tmp_vals = title_line.replace(' ', '').split(col_name)[1:]
            vals = tmp_vals

        if col_name in PRICE_COLUMNS:
            parse_dict[col_name] = vals
        else:
            parse_dict[col_name] = vals[col_idx]

    return parse_dict


def split_str_from_words(string, words):
    parts = re.split(rf"({'|'.join(words)})", string)
    return [part for part in parts if len(part) > 1]


def main(args):
    # 데이터 입력
    pdf_paths = sorted(cg.get_filepaths(str(PDF_DIR), extensions=PDF_EXTENSIONS), key=lambda x : int(Path(x).name.replace('.pdf', '')))

    df = pd.DataFrame(columns=['파일명'] + TOTAL_COLUMNS)
    for idx, path in enumerate(pdf_paths):
        total_dict = parse_data_from_pdf(path)

        df = df.append(total_dict, ignore_index=True)
        print(f" [PDF-RECEIPT] # ({idx+1}/{len(pdf_paths)}) 번째 파일이 처리중입니다.")

    # # 파일명 기반 정렬
    # df = df.sort_values(by=['파일명'], ascending=[True])

    # list -> rows 변환
    df = df.explode(PRICE_COLUMNS).reset_index(drop=True)

    # 결과 파일 저장
    csv_path = str(Path(f"{args.csv_dir}/{TGT_DATE}.csv"))
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')

    print(f" [PDF-RECEIPT] # 결과 파일이 {csv_path}에 저장되었습니다.")

    return True

def parse_arguments(argv):
    parser = argparse.ArgumentParser()

    parser.add_argument("--pdf_dir", required=True, type=str, help="Input pdf directory path")
    parser.add_argument("--csv_dir", default=".", help="Output csv directory path")

    args = parser.parse_args(argv)

    return args


SELF_TEST_ = True


if __name__ == "__main__":
    if len(sys.argv) == 1:
        if SELF_TEST_:
            sys.argv.extend(["--pdf_dir", str(PDF_DIR)])
            sys.argv.extend(["--csv_dir", str(CSV_DIR)])
        else:
            sys.argv.extend(["--help"])

    main(parse_arguments(sys.argv[1:]))
