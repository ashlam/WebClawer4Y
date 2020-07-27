import os
import random
from datetime import datetime
import time
import csv
import requests
from lxml import etree

"""
这个sample是通过访问
http://gk.chengdu.gov.cn/govInfo/
的部分网站内容(http://gk.chengdu.gov.cn/govInfoPub/list.action?classId=07170201020202&tn=2&p=1)
而编写的，可对照sample的代码与该网站的网页源码来加深理解。

每个网站的设计、结构、元素都不尽相同，写此类程序的核心便是去寻找该网站资源的存放规律，然后再根据这个规律来写具体的解析/获取功能。
"""

"""
整体思路：
先找到所需信息的列表页做为入口
爬第一遍：遍历列表页中每一页的内容，得到列表页记录的所有的链接地址
爬第二遍：根据链接地址遍历每一个地址对应的详情页面，并筛选详情页内容中是否包含关键字
将符合关键字的相关合适内容记录到最终结果中
将结果写入文件保存
"""

# 入口信息
class _ArticleEntryInfo:
    content_url: str
    title: str
    datetime: str

    def __init__(self, url, title, datetime) -> None:
        self.content_url = url
        self.title = title
        self.datetime = datetime

# 结果信息
class _ArticleResultInfo:
    url: str
    title: str
    datetime: str
    summary: str

    def __init__(self, url, title, datetime, summary) -> None:
        self.url = url
        self.title = title
        self.datetime = datetime
        self.summary = summary
        

# 将数据写成tsv文件的类
class TsvWriter:
    def __init__(self, filename, header, rows):
        self.filename = filename
        self.header = header
        self.rows = rows

    def write_to_file(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            tsv_w = csv.writer(f, delimiter='\t')
            tsv_w.writerow(self.header)  
            tsv_w.writerows(self.rows)  # 多行写入

    def get_result_filename(self):
        return self.filename



# 随机使用一个用户标识，用于伪装访问信息，防止一些反爬虫手段
def get_random_user_agent():
    USER_AGENTS = [
        "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; AcooBrowser; .NET CLR 1.1.4322; .NET CLR 2.0.50727)",
        "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0; Acoo Browser; SLCC1; .NET CLR 2.0.50727; Media Center PC 5.0; .NET CLR 3.0.04506)",
        "Mozilla/4.0 (compatible; MSIE 7.0; AOL 9.5; AOLBuild 4337.35; Windows NT 5.1; .NET CLR 1.1.4322; .NET CLR 2.0.50727)",
        "Mozilla/5.0 (Windows; U; MSIE 9.0; Windows NT 9.0; en-US)",
        "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Win64; x64; Trident/5.0; .NET CLR 3.5.30729; .NET CLR 3.0.30729; .NET CLR 2.0.50727; Media Center PC 6.0)",
        "Mozilla/5.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0; WOW64; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; .NET CLR 1.0.3705; .NET CLR 1.1.4322)",
        "Mozilla/4.0 (compatible; MSIE 7.0b; Windows NT 5.2; .NET CLR 1.1.4322; .NET CLR 2.0.50727; InfoPath.2; .NET CLR 3.0.04506.30)",
        "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN) AppleWebKit/523.15 (KHTML, like Gecko, Safari/419.3) Arora/0.3 (Change: 287 c9dfb30)",
        "Mozilla/5.0 (X11; U; Linux; en-US) AppleWebKit/527+ (KHTML, like Gecko, Safari/419.3) Arora/0.6",
        "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.2pre) Gecko/20070215 K-Ninja/2.1.1",
        "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.9) Gecko/20080705 Firefox/3.0 Kapiko/3.0",
        "Mozilla/5.0 (X11; Linux i686; U;) Gecko/20070322 Kazehakase/0.4.5",
        "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.8) Gecko Fedora/1.9.0.8-1.fc10 Kazehakase/0.5.6",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/535.20 (KHTML, like Gecko) Chrome/19.0.1036.7 Safari/535.20",
        "Opera/9.80 (Macintosh; Intel Mac OS X 10.6.8; U; fr) Presto/2.9.168 Version/11.52",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.11 TaoBrowser/2.0 Safari/536.11",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.71 Safari/537.1 LBBROWSER",
        "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E; LBBROWSER)",
        "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; QQDownload 732; .NET4.0C; .NET4.0E; LBBROWSER)",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.84 Safari/535.11 LBBROWSER",
        "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)",
        "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E; QQBrowser/7.0.3698.400)",
        "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; QQDownload 732; .NET4.0C; .NET4.0E)",
        "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Trident/4.0; SV1; QQDownload 732; .NET4.0C; .NET4.0E; 360SE)",
        "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; QQDownload 732; .NET4.0C; .NET4.0E)",
        "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)",
        "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.89 Safari/537.1",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.89 Safari/537.1",
        "Mozilla/5.0 (iPad; U; CPU OS 4_2_1 like Mac OS X; zh-cn) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8C148 Safari/6533.18.5",
        "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:2.0b13pre) Gecko/20110307 Firefox/4.0b13pre",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:16.0) Gecko/20100101 Firefox/16.0",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11",
        "Mozilla/5.0 (X11; U; Linux x86_64; zh-CN; rv:1.9.2.10) Gecko/20100922 Ubuntu/10.10 (maverick) Firefox/3.6.10"
    ]
    return random.choice(USER_AGENTS)


# 得到url的访问返回结果
def get_response(url, **kwargs):
    if 'headers' not in kwargs:
        kwargs['headers'] = {
            'User-Agent': get_random_user_agent(),
        }
    r = requests.get(url, **kwargs)
    dom = etree.HTML(r.text)
    return dom


# 设置搜索的一些参数
def get_filter_parameters():
    filter_params = {
        'EntryPageUrl' : 'http://gk.chengdu.gov.cn/govInfoPub/list.action?classId=07170201020202&tn={0}&p={1}',
        'DetailUrl' : 'http://gk.chengdu.gov.cn/govInfo/',
        'MaxInfoCountPerPage' : 20,
        'MaxInfoCount' : 97,
        'TagNumber' : 2,
        # 关键字，可以通过一些关键字来过滤掉无用的文章
        'ContentKeyWords' : [
            '疫情',
            '经济',
        ],
        "SummaryLimit" : 50,
    }
    return filter_params


# 得到入口信息
def get_list_page_info(filter_params):
    article_num = filter_params['MaxInfoCount']
    per_page = filter_params['MaxInfoCountPerPage']
    max_page = article_num / per_page if (article_num % per_page) == 0 else int (article_num / per_page) + 1
    entries = {}

    # 第一次爬行，得到列表的内容
    for i in range(1, max_page):
        dom = get_response(filter_params['EntryPageUrl'].format(filter_params['TagNumber'], i))
        # 拉每一页的列表信息
        items = dom.xpath('//div[@id="part_02"]/div[@class="blk01"]/div/ul/li')
        # item是每一大段包含下列要用到信息的内容
        for item in items:
            # 对每个li进行再提取
            details_xpath = {
                'link' : './a/@href',
                'article_id' : './a/span[@class="b1"]/text()',
                'title' : './a/span[@class="b2"]/text()',
                'datetime' : './a/span[@class="b4"]/text()',
            }

            # 得到将item通过xpath转化后的link，将有用信息存进一个列表
            detail = {}
            key_and_path = details_xpath.items()
            for key, path in key_and_path:
                detail[key] = ''.join(item.xpath(path)).strip()
            
            if not (detail['link'] in entries.keys()):
                entries[detail['link']] = _ArticleEntryInfo(detail['link'], detail['title'], detail['datetime'])
    return entries


# 得到文章的内容信息
def get_article_details(filter_params, entries):
    results = []
    for k, entry in entries.items():
        article_url = filter_params['DetailUrl'] + (entry.content_url)
        content_keywords = filter_params['ContentKeyWords']
        summary_limit = filter_params['SummaryLimit']
        # 得到文章的内容
        dom = get_response(article_url)
        # 根据文章页面的结构和元素，解析文章内容:
        items = dom.xpath('//table[@id="myTable"]/tr/td/p/span/text()')
        # 看看内容里有没有想要的关键字，有的话将检索结果（的一部分）保存下来
        if content_keywords and len(content_keywords) > 0:
            has_found = False
            for item in items:
                for keyword in content_keywords:
                    if (keyword in item):
                        summary = item[0 : min(summary_limit, len(item))]
                        summary = summary if len(item) < summary_limit else summary + ".."
                        info = _ArticleResultInfo(article_url, entry.title, entry.datetime, summary)
                        results.append(info)
                        has_found = True
                        break
                if has_found:
                    break
        else:
            info = _ArticleResultInfo(article_url, entry.title, entry.datetime, '')
            results.append(info)

    return results


# 将结果写入文件
def write_result_to_file(scaned_params, scaned_results):
    header = ['link', 'title', 'datetime', 'summary']
    rows = []
    for info in scaned_results:
        print('url = {0}, title = {1}, summary = {2}'.format(info.url, info.title, info.summary))
        row = [info.url, info.title, info.datetime, info.summary]
        rows.append(row)

    # 写文件
    writer = TsvWriter('m_result.tsv', header, rows)
    writer.write_to_file()
    return writer.get_result_filename()


def main():
    last_time = datetime.now()
    scaned_params = get_filter_parameters()
    print('当前检索关键字为:{0}'.format(scaned_params['ContentKeyWords']))
    print('可能要花一些时间，按[Ctrl+C]中止检索..')
    scaned_entries = get_list_page_info(scaned_params)
    scaned_results = get_article_details(scaned_params, scaned_entries)
    file_name = write_result_to_file(scaned_params, scaned_results)
    # 看看用了多久
    now = datetime.now()
    print('共用时{0}秒，结果保存在{1}'.format((now - last_time).seconds, file_name))
    print('done.')

# 走起！
main()