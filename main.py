import os
import re
import time
import requests
from lxml import etree
from flask import Flask, render_template
from notion_client import Client


app = Flask(__name__, template_folder="templates")


NOTION_DATABASE_ID = os.environ.get("database","None")
NOTION_API_TOKEN= os.environ.get("api","None")
# Initialize the Notion client
notion = Client(auth=NOTION_API_TOKEN)

@app.route("/")
def index():
    return render_template("22.html")

@app.route("/in/<isbn>")
def get_book_info(isbn):
    url = f"https://douban.com/isbn/{isbn}"
    process_book_info(url, isbn)
    return "Book information processed."


@app.route("/out/<isbn>")
def book_out(isbn):
    # 查找匹配的图书
    query = {
        "database_id": NOTION_DATABASE_ID,
        "filter": {
            "and": [
                {
                    "property": "ISBN",
                    "rich_text": {
                        "contains": isbn
                    }
                },
                {
                    "property": "阅读状态",
                    "select": {
                        "does_not_equal": "出库"
                    }
                }
            ]
        }
    }

    try:
        response = notion.databases.query(**query)
        if response['results']:
            # 找到匹配的图书,更新阅读状态为"出库"
            page_id = response['results'][0]['id']
            update_reading_status(page_id, new_status="出库")
            return f"Book with ISBN {isbn} has been marked as '出库'."
        else:
            return f"No book found with ISBN {isbn} or it's already marked as '出库'."
    except Exception as e:
        print("Error querying or updating Notion database:")
        print(e)
        return "An error occurred while processing the request."

# 确保update_reading_status函数已定义,如果没有,可以使用之前提供的版本














def process_book_info(url, isbn):
    tag_pattern = re.compile(r"criteria = '(.+)'")
    brand_default = "无"
    publish_date = None

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.1 "
            "(KHTML, like Gecko) Chrome/14.0.835.163 Safari/535.1"
        )
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to retrieve data from {url}")
        return

    html = etree.HTML(response.content)

    # Extract data using XPath
    book_name = "".join(html.xpath("//*[@id='mainpic']/a/@title")).strip()
    book_img = "".join(html.xpath("//*[@id='mainpic']/a/img/@src")).strip()
    author_name = " ".join(html.xpath("//*[@id='info']/span[1]/a/text()")).strip()
    if not author_name:
        author_name = re.sub(r"[\s\n]", "", "".join(html.xpath('//span[text()="作者:"]/../a[1]/text()')))
    press = "".join(html.xpath('//span[./text()="出版社:"]/following::text()[2]')).strip()
    if not press:
        press = "".join(html.xpath('//span[./text()="出版社:"]/following::text()[1]')).strip()
    subtitle = "".join(html.xpath('//span[./text()="副标题:"]/following::text()[1]')).strip()
    press_year = "".join(html.xpath('//span[./text()="出版年:"]/following::text()[1]')).strip()
    pages = "".join(html.xpath('//span[./text()="页数:"]/following::text()[1]')).strip()
    price = "".join(html.xpath('//span[./text()="定价:"]/following::text()[1]')).strip()
    ISBN = "".join(html.xpath('//span[./text()="ISBN:"]/following::text()[1]')).strip()
    brand = "".join(html.xpath('//span[./text()="出品方:"]/following::text()[2]')).strip() or brand_default
    series = "".join(html.xpath('//span[./text()="丛书:"]/following::text()[2]')).strip() or "无"
    design = "".join(html.xpath('//span[./text()="装帧:"]/following::text()[1]')).strip() or "无"
    score = "".join(html.xpath("//*[@id='interest_sectl']/div/div[2]/strong/text()")).strip()
    translator = " ".join(html.xpath('//*[@id="info"]/span[contains(.,"译者")]/descendant::a/text()')).strip()

    # Extract tags
    tags = []
    tag_match = tag_pattern.findall(response.text)
    if tag_match:
        tags = [
            tag.replace("7:", "")
            for tag in filter(lambda tag: tag and tag.startswith("7:"), tag_match[0].split("|"))
        ][:5]  # Limit to first 5 tags

    # Data cleaning and type conversion
    try:
        price = float(re.search(r"\d+\.?\d*", price).group(0))
    except (AttributeError, ValueError):
        price = 0.0

    try:
        score = float(score)
    except ValueError:
        score = 0.0

    try:
        pages = int(re.findall(r"\d+", pages)[0])
    except (IndexError, ValueError):
        pages = 0

    # Format publish_date
    publish_date_list = re.findall(r"\d+", press_year)
    if len(publish_date_list) >= 2:
        publish_date = f"{publish_date_list[0]}-{publish_date_list[1].zfill(2)}-01"
    elif len(publish_date_list) == 1:
        publish_date = f"{publish_date_list[0]}-01-01"
    else:
        publish_date = "2023-01-01"  # Default date

    # Current date as purchase_date
    purchase_date = time.strftime("%Y-%m-%d", time.localtime())

    # Check if ISBN already exists in Notion database
    existing_page = find_page_by_isbn(ISBN)
    if existing_page:
        # Retrieve the current reading status
        current_status = existing_page['properties'].get('阅读状态', {}).get('select', {}).get('name', '')
        if current_status == "出库":
            # Update the Reading Status to '闲置'
            update_reading_status(existing_page['id'], new_status="闲置")
            print(f"ISBN {ISBN} already exists with 阅读状态 '出库'. Updated to '闲置'.")
        else:
            print(f"ISBN {ISBN} already exists with 阅读状态 '{current_status}'. No update performed.")
        return  # Exit the function since the ISBN already exists

    # Prepare properties for Notion
    properties = {
        "书名": {
            "title": [
                {
                    "type": "text",
                    "text": {"content": book_name}
                }
            ]
        },
        "副标题": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": subtitle}
                }
            ]
        },
        "出版社": {
            "select": {"name": press}
        },
        "作者": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": author_name}
                }
            ]
        },
        "译者": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": translator}
                }
            ]
        },
        "ISBN": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": ISBN}
                }
            ]
        },
        "丛书": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": series}
                }
            ]
        },
        "装帧": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": design}
                }
            ]
        },
        "出品方": {
            "select": {"name": brand}
        },
        "册数": {
            "number": 1
        },
        "定价": {
            "number": price
        },
        "页数": {
            "number": pages
        },
        "豆瓣评分": {
            "number": score
        },
        "豆瓣": {
            "url": response.url
        },
        "封面": {
            "files": [
                {
                    "name": "封面图片",
                    "type": "external",
                    "external": {"url": book_img},
                }
            ]
        },
        "出版日": {
            "date": {"start": publish_date}
        },
        "时间": {
            "date": {"start": purchase_date}
        },
        "标签": {
            "multi_select": [{"name": tag} for tag in tags]
        },
        "阅读状态": {  # Set the 阅读状态 property to '闲置' for new entries
            "select": {"name": "闲置"}
        },
    }

    # Create a new page in Notion
    try:
        notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties=properties
        )
        print("导入信息成功，图书信息为：")
        print(
            book_name,
            author_name,
            press,
            publish_date,
            pages,
            price,
            brand,
            series,
            design,
            ISBN,
            sep=" | ",
        )
        print("-------------------------------------------------------------------------------------------------")
    except Exception as e:
        print("导入失败，请检查错误信息：")
        print(e)

def find_page_by_isbn(isbn):
    """
    Search for a page in the Notion database by ISBN.
    Returns the page object if found, else None.
    """

    query = {
        "database_id": NOTION_DATABASE_ID,
        "filter": {
            "and": [
                {
                    "property": "ISBN",
                    "rich_text": {
                        "contains": isbn
                    }
                },
                {
                    "property": "阅读状态",
                    "select": {
                        "equals": "出库"
                    }
                }
            ]
        }
    }



    try:
        response = notion.databases.query(**query)
        if response['results']:
            return response['results'][0]  # Return the first matching page
        else:
            return None
    except Exception as e:
        print("Error querying Notion database:")
        print(e)
        return None

def update_reading_status(page_id, new_status="闲置"):
    """
    Update the '阅读状态' property of a page to the specified status.
    """
    update_data = {
        "properties": {
            "阅读状态": {
                "select": {"name": new_status}
            }
        }
    }
    try:
        notion.pages.update(page_id, **update_data)
        print(f"Successfully updated 阅读状态 to '{new_status}' for page ID {page_id}.")
    except Exception as e:
        print(f"Failed to update 阅读状态 for page {page_id}:")
        print(e)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=516)
