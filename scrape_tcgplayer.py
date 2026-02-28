#!/usr/bin/env python3
"""
尝试爬取 TCGplayer.com 的卡片信息
"""

import requests
from bs4 import BeautifulSoup
import time
import json
import re

def get_page(url):
    """获取页面内容"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"获取页面失败: {e}")
        return None

def parse_search_results(html):
    """解析搜索结果页面"""
    soup = BeautifulSoup(html, 'html.parser')
    cards = []
    
    # 尝试查找卡片元素 - 这取决于网站的实际HTML结构
    # 可能需要根据实际页面调整选择器
    
    # 查找可能的卡片容器
    card_elements = soup.find_all(['div', 'article'], class_=re.compile(r'product|card|item', re.I))
    
    if not card_elements:
        # 尝试其他选择器
        card_elements = soup.select('[data-testid*="product"], [class*="product-card"], .search-result-item')
    
    print(f"找到 {len(card_elements)} 个可能的卡片元素")
    
    for i, element in enumerate(card_elements[:20]):  # 先测试前20个
        card_info = {}
        
        # 尝试提取卡片名称
        name_elem = element.find(['h2', 'h3', 'h4', 'a'], class_=re.compile(r'title|name|product-name', re.I))
        if name_elem:
            card_info['name'] = name_elem.get_text(strip=True)
        
        # 尝试提取价格
        price_elem = element.find(class_=re.compile(r'price|cost|amount', re.I))
        if price_elem:
            card_info['price'] = price_elem.get_text(strip=True)
        
        # 尝试提取链接
        link_elem = element.find('a', href=True)
        if link_elem:
            href = link_elem['href']
            if href.startswith('/'):
                href = 'https://www.tcgplayer.com' + href
            card_info['url'] = href
        
        if card_info:
            cards.append(card_info)
            print(f"  卡片 {i+1}: {card_info.get('name', '未命名')} - {card_info.get('price', '无价格')}")
    
    return cards

def main():
    print("开始爬取 TCGplayer 卡片信息...")
    
    # 搜索页面 - 尝试搜索Magic卡牌
    search_url = "https://www.tcgplayer.com/search/all/product?q=magic+the+gathering&view=grid"
    
    print(f"访问页面: {search_url}")
    html = get_page(search_url)
    
    if not html:
        print("无法获取页面内容")
        return
    
    # 保存原始HTML以供调试
    with open('/home/liliucan/.openclaw/workspace/tcgplayer_raw.html', 'w', encoding='utf-8') as f:
        f.write(html[:50000])  # 只保存前50000字符
    
    print("页面获取成功，开始解析...")
    
    cards = parse_search_results(html)
    
    print(f"\n总共解析到 {len(cards)} 张卡片")
    
    # 保存结果到JSON文件
    if cards:
        output_file = '/home/liliucan/.openclaw/workspace/tcgplayer_cards.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(cards, f, indent=2, ensure_ascii=False)
        
        print(f"\n数据已保存到: {output_file}")
        
        # 生成简明的文本报告
        report_file = '/home/liliucan/.openclaw/workspace/tcgplayer_report.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("TCGplayer 卡片信息汇总\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"爬取时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总卡片数: {len(cards)}\n\n")
            
            for i, card in enumerate(cards, 1):
                f.write(f"{i}. {card.get('name', '未知名称')}\n")
                f.write(f"   价格: {card.get('price', '未知')}\n")
                if 'url' in card:
                    f.write(f"   链接: {card.get('url')}\n")
                f.write("\n")
        
        print(f"报告已保存到: {report_file}")
        
        # 显示前5个结果
        print("\n前5个结果:")
        for i, card in enumerate(cards[:5], 1):
            print(f"{i}. {card.get('name', '未知名称')} - {card.get('price', '未知')}")
    else:
        print("未找到卡片信息，可能需要调整解析逻辑")

if __name__ == "__main__":
    main()