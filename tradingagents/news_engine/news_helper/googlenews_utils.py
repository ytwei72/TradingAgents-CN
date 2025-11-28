import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import random
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_result,
)

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')


def is_rate_limited(response):
    """Check if the response indicates rate limiting (status code 429)"""
    return response.status_code == 429


@retry(
    retry=(retry_if_result(is_rate_limited) | retry_if_exception_type(requests.exceptions.ConnectionError) | retry_if_exception_type(requests.exceptions.Timeout)),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5),
)
def make_request(url, headers):
    """Make a request with retry logic for rate limiting and connection issues"""
    # Random delay before each request to avoid detection
    time.sleep(random.uniform(2, 6))
    # 添加超时参数，设置连接超时和读取超时
    response = requests.get(url, headers=headers, timeout=(10, 30))  # 连接超时10秒，读取超时30秒
    return response


def getNewsData(query, start_date, end_date):
    """
    Scrape Google News search results for a given query and date range.
    query: str - search query
    start_date: str - start date in the format yyyy-mm-dd or mm/dd/yyyy
    end_date: str - end date in the format yyyy-mm-dd or mm/dd/yyyy
    """
    if "-" in start_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        start_date = start_date.strftime("%m/%d/%Y")
    if "-" in end_date:
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        end_date = end_date.strftime("%m/%d/%Y")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/101.0.4951.54 Safari/537.36"
        )
    }

    news_results = []
    page = 0
    while True:
        offset = page * 10
        url = (
            f"https://www.google.com/search?q={query}"
            f"&tbs=cdr:1,cd_min:{start_date},cd_max:{end_date}"
            f"&tbm=nws&start={offset}"
        )

        try:
            response = make_request(url, headers)
            logger.debug(f"Google News Status: {response.status_code}, URL: {url}")
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Try new selectors based on h3 tags
            h3_tags = soup.find_all("h3")
            logger.debug(f"Found {len(h3_tags)} h3 tags")
            
            if not h3_tags:
                 logger.warning("No h3 tags found in Google News response")
                 break

            for h3 in h3_tags:
                try:
                    # Title
                    title = h3.get_text()
                    
                    # Link
                    a_tag = h3.find_parent("a")
                    if not a_tag:
                        continue
                    link = a_tag.get("href")
                    
                    # Remove /url?q= prefix if present (Google redirection)
                    if link and link.startswith("/url?"):
                        import urllib.parse
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
                        if 'url' in parsed:
                            link = parsed['url'][0]
                        elif 'q' in parsed:
                            link = parsed['q'][0]
                            
                    # Container for source and date
                    container = a_tag
                    
                    # Source: .KogRLb or .BamJPe
                    source_tag = container.select_one(".KogRLb, .BamJPe")
                    source = source_tag.get_text() if source_tag else ""
                    
                    # Date: .UK5aid
                    date_tag = container.select_one(".UK5aid")
                    date = date_tag.get_text() if date_tag else ""
                    
                    # Snippet
                    snippet = ""
                    if date_tag:
                        snippet_div = date_tag.find_parent("div")
                        if snippet_div:
                            snippet = snippet_div.get_text().replace(date, "").strip()
                    
                    news_results.append({
                        "link": link,
                        "title": title,
                        "snippet": snippet,
                        "date": date,
                        "source": source
                    })
                except Exception as e:
                    logger.error(f"Error processing result: {e}")
                    continue

            # Check for the "Next" link (pagination)
            next_link = soup.find("a", id="pnnext")
            if not next_link:
                break

            page += 1

        except requests.exceptions.Timeout as e:
            logger.error(f"连接超时: {e}")
            # 不立即中断，记录错误后继续尝试下一页
            page += 1
            if page > 3:  # 如果连续多页都超时，则退出循环
                logger.error("多次连接超时，停止获取Google新闻")
                break
            continue
        except requests.exceptions.ConnectionError as e:
            logger.error(f"连接错误: {e}")
            # 不立即中断，记录错误后继续尝试下一页
            page += 1
            if page > 3:  # 如果连续多页都连接错误，则退出循环
                logger.error("多次连接错误，停止获取Google新闻")
                break
            continue
        except Exception as e:
            logger.error(f"获取Google新闻失败: {e}")
            break

    return news_results
