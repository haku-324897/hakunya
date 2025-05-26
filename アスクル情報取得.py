import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import time

# 商品情報を取得する関数
def get_product_info(url, df):
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    # 商品名（titleタグから取得し、「 - アスクル」を除去）
    if res.status_code != 200:
        name = ""
    elif soup.title:
        name = soup.title.string.strip()
        if name == "Not Found":
            name = ""
        elif name.endswith(" - アスクル"):
            name = name.removesuffix(" - アスクル")
    else:
        name = ""

    # 値段
    price = ""
    price_tag = soup.find("span", class_="item-price-value")
    if not price_tag:
        price_tag = soup.find("span", class_="item-price-taxin")
    if price_tag:
        price = price_tag.get_text(strip=True)
    else:
        price_candidates = soup.find_all(string=re.compile("￥"))
        for candidate in price_candidates:
            text = candidate.strip()
            if re.match(r"^￥[0-9,]+", text):
                price = text
                break
    if not price:
        price = ""

    # 販売単位
    quantity = ""
    for tag in soup.find_all(string=re.compile("販売単位")):
        quantity = tag.strip()
        break
    if not quantity:
        quantity = ""

    # JANコード
    jan = ""
    for tag in soup.find_all(string=re.compile("JANコード")):
        m = re.search(r"JANコード[:：]?\s*([0-9]+)", tag)
        if m:
            jan = f"JANコード：{m.group(1)}"
        else:
            jan = tag.strip()
        break
    if not jan:
        jan = ""
    jan_code = jan.replace("JANコード：", "").strip()
    sheet_info = search_xlsx_by_jan(jan_code, df)

    # F列に一致しない場合のURL_シートを修正
    if jan_code == "":
        sheet_info["URL_シート"] = ""
    elif sheet_info["同一商品判定"] == "類似商品":
        sheet_info["URL_シート"] = f"https://www.ntps-shop.com/search/res/{jan_code}/"

    return {
        "アスクル品名": name,
        "個数": quantity,
        "JANコード": jan_code,
        "値段": price,
        "URL": url,
        **sheet_info
    }

# xlsxファイルのURL
XLSX_URL = "https://github.com/haku-324897/hakunya/raw/refs/heads/main/%E3%82%A2%E3%82%B9%E3%82%AF%E3%83%AB%E3%83%8A%E3%83%93%E3%83%AA%E3%82%AA%E3%83%B3githab%E7%94%A8.xlsx"

# xlsxを一度だけ読み込む
@st.cache_data
def load_xlsx():
    return pd.read_excel(XLSX_URL)

def search_xlsx_by_jan(jan_code, df):
    # F列（JANコード列）で検索
    match = df[df.iloc[:, 5].astype(str) == str(jan_code)]
    if match.empty:
        return {
            "同一商品判定": "類似商品",
            "製品": "",
            "個数_シート": "",
            "申し込み番号": "",
            "NV小売価格": "",
            "URL_シート": ""
        }
    else:
        row = match.iloc[0]
        return {
            "同一商品判定": "同一商品",
            "製品": row[2],         # C列
            "個数_シート": row[3],  # D列
            "申し込み番号": row[1],  # B列
            "NV小売価格": row[4],   # E列
            "URL_シート": row[6]    # G列
        }

st.title("アスクル商品情報取得ツール")
st.write("商品番号またはURLを1行ずつ入力してください。商品番号のみでもOKです。")

input_text = st.text_area("商品番号またはURL（1行に1つ）", height=200)

if st.button("情報取得"):
    df_sheet = load_xlsx()
    lines = [line.strip() for line in input_text.splitlines() if line.strip()]
    urls = []
    for line in lines:
        if line.startswith("http"):
            urls.append(line)
        else:
            # 商品番号のみの場合
            urls.append(f"https://www.askul.co.jp/p/{line}/")

    results = []
    progress = st.progress(0)
    for i, url in enumerate(urls):
        info = get_product_info(url, df_sheet)
        results.append(info)
        progress.progress((i + 1) / len(urls))
        time.sleep(0.5)
    progress.empty()
    df = pd.DataFrame(results)
    st.dataframe(df)
