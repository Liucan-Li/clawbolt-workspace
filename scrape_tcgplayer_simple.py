#!/usr/bin/env python3
"""
尝试爬取 TCGplayer.com 的卡片信息 - 简化版
使用正则表达式和内置库
"""

import requests
import re
import json
import time
from html.parser import HTMLParser

class SimpleCardParser(HTMLParser):
    """简单的HTML解析器，用于提取卡片信息"""
    def __init__(self):
        super().__init__()
        self.cards = []
        self.current_card = {}
        self.in_card = False
        self.in_name = False
        self.in_price = False
        self.current_data = ""
    
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        classes = attrs_dict.get('class', '').lower()
        
        # 检测可能的卡片元素
        if tag == 'div' and any(x in classes for x in ['product', 'card', 'item', 'result']):
            self.in_card = True
            self.current_card = {}
            if 'href' in attrs_dict:
                href = attrs_dict['href']
                if href.startswith('/'):
                    href = 'https://www.tcgplayer.com' + href
                self.current_card['url'] = href
        
        # 检测名称元素
        elif self.in_card and tag in ['h2', 'h3', 'h4', 'a', 'span']:
            if any(x in classes for x in ['title', 'name', 'product', 'heading']):
                self.in_name = True
        
        # 检测价格元素
        elif self.in_card and tag in ['span', 'div', 'p']:
            if any(x in classes for x in ['price', 'cost', 'amount', 'money']):
                self.in_price = True
    
    def handle_data(self, data):
        if self.in_name:
            self.current_data += data
        elif self.in_price:
            if '$' in data or any(x in data.lower() for x in ['usd', 'price']):
                self.current_card['price_raw'] = data.strip()
    
    def handle_endtag(self, tag):
        if tag in ['h2', 'h3', 'h4', 'a', 'span'] and self.in_name:
            if self.current_data.strip():
                self.current_card['name'] = self.current_data.strip()
            self.in_name = False
            self.current_data = ""
        
        elif tag in ['span', 'div', 'p'] and self.in_price:
            self.in_price = False
        
        elif tag == 'div' and self.in_card:
            if self.current_card:
                self.cards.append(self.current_card.copy())
            self.in_card = False

def get_page(url):
    """获取页面内容"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"获取页面失败: {e}")
        return None

def extract_json_data(html):
    """尝试从HTML中提取JSON数据"""
    # 查找可能的JSON数据块
    json_patterns = [
        r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
        r'window\.__PRELOADED_STATE__\s*=\s*({.*?});',
        r'var\s+productData\s*=\s*({.*?});',
        r'"products":\s*(\[.*?\]),',
        r'"items":\s*(\[.*?\]),'
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, html, re.DOTALL)
        for match in matches:
            try:
                data = json.loads(match)
                print(f"找到JSON数据: {type(data)}")
                if isinstance(data, dict):
                    # 尝试查找产品数据
                    for key in ['products', 'items', 'results', 'data']:
                        if key in data and isinstance(data[key], list):
                            return data[key]
                elif isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                continue
    
    return None

def extract_cards_from_json(json_data):
    """从JSON数据中提取卡片信息"""
    cards = []
    
    if not isinstance(json_data, list):
        return cards
    
    for item in json_data:
        if isinstance(item, dict):
            card = {}
            
            # 提取名称
            for key in ['name', 'title', 'productName', 'displayName']:
                if key in item and item[key]:
                    card['name'] = str(item[key])
                    break
            
            # 提取价格
            for key in ['price', 'marketPrice', 'lowPrice', 'avgPrice', 'amount']:
                if key in item:
                    price_val = item[key]
                    if isinstance(price_val, (int, float)):
                        card['price'] = f"${price_val:.2f}"
                    elif isinstance(price_val, str):
                        card['price'] = price_val
                    break
            
            # 提取URL
            for key in ['url', 'productUrl', 'link', 'detailUrl']:
                if key in item and item[key]:
                    url = str(item[key])
                    if not url.startswith('http'):
                        url = 'https://www.tcgplayer.com' + url
                    card['url'] = url
                    break
            
            if 'name' in card:
                cards.append(card)
    
    return cards

def main():
    print("开始爬取 TCGplayer 卡片信息...")
    
    # 尝试几个不同的搜索URL
    search_urls = [
        "https://www.tcgplayer.com/search/all/product?q=magic",
        "https://www.tcgplayer.com/search/all/product?q=magic+the+gathering",
        "https://www.tcgplayer.com/search/all/product?q=pokemon",
        "https://www.tcgplayer.com/search/magic/product?q=island"
    ]
    
    all_cards = []
    
    for search_url in search_urls:
        print(f"\n访问页面: {search_url}")
        html = get_page(search_url)
        
        if not html:
            print("无法获取页面内容")
            continue
        
        # 保存原始HTML以供调试
        with open(f'/home/liliucan/.openclaw/workspace/tcgplayer_{time.time()}.html', 'w', encoding='utf-8') as f:
            f.write(html[:100000])  # 只保存前100000字符
        
        print(f"页面大小: {len(html)} 字符")
        
        # 方法1：尝试提取JSON数据
        print("尝试提取JSON数据...")
        json_data = extract_json_data(html)
        
        if json_data:
            print(f"从JSON中找到 {len(json_data) if isinstance(json_data, list) else '一些'} 个数据项")
            cards = extract_cards_from_json(json_data)
            print(f"从JSON中解析出 {len(cards)} 张卡片")
            all_cards.extend(cards)
        
        # 方法2：使用简单的HTML解析
        print("尝试HTML解析...")
        parser = SimpleCardParser()
        parser.feed(html[:500000])  # 只解析前500k字符以避免内存问题
        print(f"从HTML中解析出 {len(parser.cards)} 张卡片")
        all_cards.extend(parser.cards)
        
        # 方法3：使用正则表达式查找产品信息
        print("尝试正则表达式匹配...")
        
        # 查找可能的卡片名称
        name_patterns = [
            r'<h[2-4][^>]*>(.*?)</h[2-4]>',
            r'class="[^"]*name[^"]*"[^>]*>(.*?)<',
            r'data-testid="[^"]*name[^"]*"[^>]*>(.*?)<',
            r'product-name[^>]*>(.*?)<'
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
            if matches:
                print(f"找到 {len(matches)} 个可能的名称")
                for match in matches[:10]:
                    name = re.sub(r'<[^>]+>', '', match).strip()
                    if name and len(name) > 3:
                        card = {'name': name[:200]}
                        all_cards.append(card)
                break
        
        # 去重
        unique_cards = []
        seen_names = set()
        for card in all_cards:
            name = card.get('name', '')
            if name and name not in seen_names:
                seen_names.add(name)
                unique_cards.append(card)
        
        all_cards = unique_cards
        
        if len(all_cards) >= 30:  # 如果已经有足够的数据
            print(f"已收集 {len(all_cards)} 张卡片，停止进一步爬取")
            break
        
        # 避免请求过快
        time.sleep(2)
    
    # 最终结果处理
    print(f"\n总共收集到 {len(all_cards)} 张卡片")
    
    # 保存结果到JSON文件
    if all_cards:
        output_file = '/home/liliucan/.openclaw/workspace/tcgplayer_cards.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_cards[:100], f, indent=2, ensure_ascii=False)  # 最多保存100条
        
        print(f"\n数据已保存到: {output_file}")
        
        # 生成简明的文本报告
        report_file = '/home/liliucan/.openclaw/workspace/tcgplayer_report.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("TCGplayer 卡片信息汇总\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"爬取时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总卡片数: {len(all_cards[:100])}\n\n")
            
            for i, card in enumerate(all_cards[:100], 1):
                f.write(f"{i}. {card.get('name', '未知名称')}\n")
                if 'price' in card:
                    f.write(f"   价格: {card.get('price')}\n")
                if 'price_raw' in card:
                    f.write(f"   价格(原始): {card.get('price_raw')}\n")
                if 'url' in card:
                    f.write(f"   链接: {card.get('url')}\n")
                f.write("\n")
        
        print(f"报告已保存到: {report_file}")
        
        # 显示前10个结果
        print("\n前10个结果:")
        for i, card in enumerate(all_cards[:10], 1):
            name = card.get('name', '未知名称')
            price = card.get('price', card.get('price_raw', '未知'))
            print(f"{i}. {name[:50]} - {price}")
    else:
        print("未找到卡片信息")

if __name__ == "__main__":
    main()