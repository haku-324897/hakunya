import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import time

# 商品情報を取得する関数
def get_product_info(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    # 商品名（titleタグから取得し、「 - アスクル」を除去）
    if soup.title:
        name = soup.title.string.strip()
        if name.endswith(" - アスクル"):
            name = name.removesuffix(" - アスクル")  # Python 3.9以降
        # もしPython 3.8以前なら
        # if name.endswith(" - アスクル"):
        #     name = name[:-len(" - アスクル")]
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

    return {
        "商品名": name,
        "値段": price,
        "個数": quantity,
        "JANコード": jan
    }

st.title("アスクル商品情報取得ツール")
st.write("商品番号またはURLを1行ずつ入力してください。商品番号のみでもOKです。")

input_text = st.text_area("商品番号またはURL（1行に1つ）", height=200)

if st.button("情報取得"):
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
        info = get_product_info(url)
        # 「販売単位：」を消す
        if info["個数"].startswith("販売単位："):
            info["個数"] = info["個数"].replace("販売単位：", "", 1)
        # 「JANコード：」を消す
        if info["JANコード"].startswith("JANコード："):
            info["JANコード"] = info["JANコード"].replace("JANコード：", "", 1)
        results.append(info)
        progress.progress((i + 1) / len(urls))
        time.sleep(0.5)
    progress.empty()

    df = pd.DataFrame(results)
    st.dataframe(df)
