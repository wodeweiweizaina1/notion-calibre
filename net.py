from lxml import etree
import json
import requests
import time
import re
import datetime
from flask import Flask, render_template
import os

app = Flask(__name__, template_folder="templates")

notion_database_id = os.environ.get("database","None")
notion_api_token = os.environ.get("api","None")




@app.route("/")
def index():
    # decodedText = request.form.get('decodedText')
    return render_template("22.html")


@app.route("/isbn/<isbn>")
def get_book_info(isbn):
    getResqutes("https://douban.com/isbn/" + isbn)



def getResqutes(url):
    tag_pattern = re.compile("criteria = '(.+)'")
    brand = "无"

    pubilishDate = None

    # 设置请求头信息
    # headers = {'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36'}
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.1 (KHTML, like Gecko) Chrome/14.0.835.163 Safari/535.1"
    }

    data = requests.get(url, headers=headers)  # 此处是请求
    html = etree.HTML(data.content)  # 网页的解析

    # 书名
    book_name = html.xpath("//*[@id='mainpic']/a/@title")
    # 图片url
    book_img = html.xpath("//*[@id='mainpic']/a/img/@src")
    # 作者
    author_name = html.xpath("//*[@id='info']/span[1]/a/text()")
    if "".join(author_name) == "":
        author_name = html.xpath('//span[text()="作者:"]/../a[1]/text()')
        author_name = re.sub(r"[(\s)*(\n)*]", "", "".join(author_name))
    # 出版社
    press = html.xpath('//span[./text()="出版社:"]/following::text()[2]')
    if "".join(press).lstrip() == "":
        press = html.xpath('//span[./text()="出版社:"]/following::text()[1]')
    # 副标题
    substitle = html.xpath('//span[./text()="副标题:"]/following::text()[1]')
    # 出版日期
    press_year = html.xpath('//span[./text()="出版年:"]/following::text()[1]')
    # 页数
    pages = html.xpath('//span[./text()="页数:"]/following::text()[1]')
    # 价格
    price = html.xpath('//span[./text()="定价:"]/following::text()[1]')
    # 图书ISBN
    ISBN = html.xpath('//span[./text()="ISBN:"]/following::text()[1]')
    # 出品方
    brand = html.xpath('//span[./text()="出品方:"]/following::text()[2]')
    # 丛书
    series = html.xpath('//span[./text()="丛书:"]/following::text()[2]')
    # 装帧
    design = html.xpath('//span[./text()="装帧:"]/following::text()[1]')
    # 评分
    score = html.xpath("//*[@id='interest_sectl']/div/div[2]/strong/text()")
    # # 评价人数
    # number_reviewers = html.xpath("//*[@id='interest_sectl']/div/div[2]/div/div[2]/span/a/span/text()")
    # # 图书简介
    # introduction = html.xpath(u'//span[text()="内容简介"]/../following::div[1]//div[@class="intro"]/p/text()')
    # # 作者简介
    # introduction = html.xpath(u'//span[text()="作者简介"]/../following::div[1]//div[@class="intro"]/p/text()')
    # # 译者
    translator = html.xpath(
        '//*[@id="info"]/span[contains(.,"译者")]/descendant::a/text()'
    )

    # 提取标签,默认提取前3个标签
    tag_match = tag_pattern.findall(data.text)
    if len(tag_match):
        tags = [
            tag.replace("7:", "")
            for tag in filter(
                lambda tag: tag and tag.startswith("7:"), tag_match[0].split("|")
            )
        ]

    # list转成string,并清除 author、press_year、design、ISBN 等字段的前后空格
    book_name = "".join(book_name)
    author_name = " ".join(author_name).lstrip()  # 如果由多位作者，用空格分隔
    translator = " ".join(translator).lstrip()  # 如果由多位译者，用空格分隔
    book_img = "".join(book_img)
    press = "".join(press).strip()
    press_year = "".join(press_year).lstrip()
    pages = "".join(pages)
    price = "".join(price).lstrip()
    ISBN = "".join(ISBN).lstrip()
    brand = "".join(brand).lstrip()
    series = "".join(series).lstrip()
    design = "".join(design).lstrip()
    substitle = "".join(substitle).lstrip()
    score = "".join(score).lstrip()

    # 正则处理price字段，并将 price、pages 转换成Num
    priceMatch = re.search(r"\d+\.?\d*", price, re.I)
    if priceMatch:
        price = priceMatch.group(0)
    else:
        price = 0

    price = float(price)

    score = float(score)

    pages = re.findall(r"\d+", pages)
    if pages != '':
        pages = int(pages [0])
    else:
        pages = 0


    # 当豆瓣图书页面没有出品方、丛书、装帧信息时，默认填「无」
    if brand == "":
        brand = "无"
    if series == "":
        series = "无"
    if design == "":
        design = "无"

    # series = re.sub(u"([^\u4e00-\u9fa5\u0030-\u0039\u0041-\u005a\u0061-\u007a])","",series)

    # 将press_year格式化为标准日期格式（到月)。如果有年月，出版日期为当年当月的1号，如果只有年，出版日期为当年的1月1日，如果都没有则使用默认日期。
    pubilishDateList = re.findall(r"\d+", press_year)
    if len(pubilishDateList) >= 2:
        pubilishDate = pubilishDateList[0] + "-" + pubilishDateList[1].zfill(2) + "-01"
    elif len(pubilishDateList) == 1:
        pubilishDate = pubilishDateList[0] + "-" + "01-01"
    else:
        pubilishDate = "2023-01-01"

    # 购买日期字段，默认为当天日期
    purchase_date = time.strftime("%Y-%m-%d", time.localtime())

    body = {
        "parent": {"type": "database_id", "database_id": notion_database_id},
        "properties": {
            "书名": {"title": [{"type": "text", "text": {"content": book_name}}]},
            "副标题": {"rich_text": [{"type": "text", "text": {"content": substitle}}]},
            "出版社": {"select": {"name": press}},
            "作者": {"rich_text": [{"type": "text", "text": {"content": author_name}}]},
            "译者": {"rich_text": [{"type": "text", "text": {"content": translator}}]},
            "ISBN": {"rich_text": [{"type": "text", "text": {"content": ISBN}}]},
            "丛书": {"rich_text": [{"type": "text", "text": {"content": series}}]},
            "装帧": {"rich_text": [{"type": "text", "text": {"content": design}}]},
            "出品方": {"select": {"name": brand}},
            "册数": {"number": 1},
            "定价": {"number": price},
            "页数": {"number": pages},
            "豆瓣评分": {"number": score},
            "豆瓣": {"url": data.url},
            "封面": {"url": book_img},
            "出版日": {"date": {"start": pubilishDate, "end": None}},
            "时间": {"date": {"start": purchase_date, "end": None}},
            "封面": {
                "files": [
                    {
                        "name": "testname",
                        "type": "external",
                        "external": {"url": book_img},
                    }
                ]
            },
            "标签": {
                "multi_select": [
                    {"name": tags[0]},
                    {"name": tags[1]},
                    {"name": tags[2]},
                    {"name": tags[3]},
                    {"name": tags[4]},
                ]
            },
        },
    }

    # 向 Notion API 发送HTTP请求
    NotionData = requests.request(
        "POST",
        # API 链接
        "https://api.notion.com/v1/pages",
        # 读取消息体，消息体需要另行编辑，后文再说
        json=body,
        # 消息头，内有必要信息
        headers={
            # 设置机器人令牌，即 Notion 的机器人码
            "Authorization": "Bearer " + notion_api_token,
            # 设置 Notion 版本，目前不用改
            "Notion-Version": "2021-05-13",
        },
    )

    # 根据POST返回结构打印信息
    if str(NotionData.status_code) == "200":
        print("导入信息成功，图书信息为：")
        print(
            book_name,
            author_name,
            press,
            pubilishDate,
            pages,
            price,
            brand,
            series,
            design,
            ISBN,
            sep=" | ",
        )
        print(
            "-------------------------------------------------------------------------------------------------"
        )
    else:
        print("导入失败，换本书试试，或检查脚本内Body内容与Notion书库字段：")
        print(NotionData.text)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=516,

    )
    # server = pywsgi.WSGIServer(('0.0.0.0',8080),app,keyfile='./static/cert/localhost+3.pem',certfile='./static/cert/localhost+3-key.pem')
    # server.serve_forever()
