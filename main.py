# -*- coding: utf-8 -*-
import argparse
import collections
import pandas as pd
import requests
import threading
import time
import xml.etree.ElementTree as ElementTree

pd.set_option('display.max_row', 500)
pd.set_option('display.max_columns', 500), pd.set_option('display.width', 1000)
import pdfplumber
import re
import sys
from typing import OrderedDict, List

from config import *
from python_utils.common import general as cg

TITLE_COLUMNS = [
    '승인번호', '카드종류', '카드번호', '결제일자', '판매자 상호', '대표자명', '사업자등록번호', '사업자등록상태',
]
PRICE_COLUMNS = [
    '금액', '부가세', '합계'
]
TOTAL_COLUMNS = TITLE_COLUMNS + PRICE_COLUMNS
SKIP_COLUMNS = ['금액'] * 2


def parse_data_from_pdf(path) -> List[dict]:
    total_dicts = []
    with pdfplumber.open(path) as pdf:
        # 좌, 우 영역 순차처리
        for i in range(2):
            total_dict = collections.OrderedDict()
            total_dict['파일명'] = Path(path).name

            for page in pdf.pages:
                w, h = page.width, page.height
                half_w = (w / 2)
                page_x, page_w = (half_w * i), (half_w * (i + 1))
                crop_page = page.crop(bbox=(page_x, 0, page_w, h))

                text = crop_page.extract_text()
                lines = text.split('\n')

                if len(lines) <= 2:
                    continue

                for l_idx, line in enumerate(lines):
                    # 대상열 이름 포함여부 확인
                    title_line_ = any(name in line for name in TOTAL_COLUMNS)
                    if title_line_:
                        parse_dict = parse_line(line, lines[l_idx + 1])
                        total_dict.update(parse_dict)
                        continue

            if len(total_dict) > 1:
                total_dicts.append(total_dict)

    return total_dicts


def parse_line(title_line, val_line):
    titles = split_str_from_words(title_line, TOTAL_COLUMNS)
    raw_vals = val_line.split(' ')

    skip_title_ = (titles == SKIP_COLUMNS)
    skip_val_ = (''.join(raw_vals).split('\xa0') == '백천원백천원')
    skip_line_ = (skip_title_ and skip_val_)
    if skip_line_:
        return {}

    # 열이름 인덱스 저장
    col_indices = extract_column_indices(tgt_columns=titles, ref_columns=TOTAL_COLUMNS)

    # 값 추출 (열이름 기반)
    parse_dict = {}
    for col_idx in col_indices:
        col_name = titles[col_idx]
        refine_vals = refine_values_by_column_name(raw_vals, titles, col_name)

        if col_name in PRICE_COLUMNS:
            parse_dict[col_name] = refine_vals
        else:
            parse_dict[col_name] = refine_vals[col_idx]

    return parse_dict


def extract_column_indices(tgt_columns, ref_columns=TOTAL_COLUMNS):
    col_indices = []
    for ref_col in ref_columns:
        if ref_col in tgt_columns:
            if ref_col in TITLE_COLUMNS:
                col_idx = tgt_columns.index(ref_col)
                col_indices.append(col_idx)
            elif ref_col in PRICE_COLUMNS:
                col_idx = tgt_columns.index(ref_col)
                col_indices.append(col_idx)

    return col_indices


def refine_values_by_column_name(vals, titles, col_name):
    # 소제목
    if col_name in TITLE_COLUMNS:
        if col_name == '결제일자':
            refine_vals = re.findall(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', ' '.join(vals))
        elif col_name in ['대표자명','판매자 상호']:
            text = ' '.join(vals)
            if ',' in text:
                comma_cnt = text.count(',')
                agent_names = text.split(' ')[-(comma_cnt+1):]
                agent_idx = text.index(agent_names[0])
                store_name, agent_name = text[:agent_idx].strip(), ' '.join(agent_names).replace(',', '')
            else:
                store_name, agent_name = (' '.join(vals)[:-3], ' '.join(vals)[-3:])

            refine_vals = [store_name, agent_name]
        else:
            refine_vals = vals

    # 금액
    elif col_name in [PRICE_COLUMNS[0]]:
        tmp_vals = [line for line in ''.join(vals).split('\xa0') if len(line) > 0]
        refine_vals = tmp_vals[0]

    # 부가세, 합계
    elif col_name in PRICE_COLUMNS[1:]:
        tmp_vals = titles[-1].replace(' ', '')
        refine_vals = tmp_vals

    return refine_vals


def split_str_from_words(string, words):
    parts = re.split(rf"({'|'.join(words)})", string)
    return [part for part in parts if len(part) > 1]


# 각 스레드에 생성되는 객체(독립적)
thread_local = threading.local()

# 세션 제공
def get_session():
    if not hasattr(thread_local, "session"):
        thread_local.session = requests.Session()
    return thread_local.session

def get_business_registration_status(url, data, crn):
    # 세션 획득
    session = get_session()

    req_data = data.replace('\{CRN\}', crn)
    with session.post(url, data=req_data, headers=HOMETAX_HEADERS, timeout=60) as resp:
        try:
            status = ElementTree.fromstring(resp.text).findtext('trtCntn')  # 결과 부분에서 사업자등록상태 부분만 파싱
        except Exception as e:
            status = resp.text

        return status.replace('\n', '')


def main(args):
    # 데이터 입력
    pdf_paths = sorted(cg.get_filepaths(str(PDF_DIR), extensions=PDF_EXTENSIONS), key=lambda x: int(Path(x).name.replace('.pdf', '')))

    df = pd.DataFrame(columns=['파일명'] + TOTAL_COLUMNS)
    for idx, path in enumerate(pdf_paths):
        # if '19.pdf' != path[-6:]:
        #     continue
        total_dicts = parse_data_from_pdf(path)

        for total_dict in total_dicts:
            df = df.append(total_dict, ignore_index=True)

        print(f" [PDF-RECEIPT] # ({idx + 1}/{len(pdf_paths)}) 번째 파일이 처리중입니다.")

    # 홈택스 데이터 추출
    for idx, row in df.iterrows():
        crn = row['사업자등록번호']

        time.sleep(0.2)  # 0.2초 대기후 접근
        status = get_business_registration_status(HOMETAX_URL, HOMETAX_DATA, crn)
        df.at[idx, '사업자등록상태'] = status
        print(f" [PDF-RECEIPT] # ({idx + 1}/{len(df)}) 번째 URL이 처리중입니다.")

    # 결과 파일 저장
    cg.directory_exists(args.csv_dir, create_=True)
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
