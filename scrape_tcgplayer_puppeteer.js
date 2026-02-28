#!/usr/bin/env node

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function scrapeTCGplayer() {
    console.log('🚀 启动 Puppeteer 爬取 TCGplayer 卡片信息...');
    
    let browser;
    try {
        // 启动浏览器（无头模式）
        browser = await puppeteer.launch({
            headless: 'new',
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
                '--window-size=1920,1080'
            ],
            defaultViewport: { width: 1920, height: 1080 }
        });
        
        const page = await browser.newPage();
        
        // 设置用户代理
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
        
        // 导航到 TCGplayer 搜索页面
        const searchUrl = 'https://www.tcgplayer.com/search/all/product?q=magic&view=grid';
        console.log(`🌐 导航到: ${searchUrl}`);
        
        await page.goto(searchUrl, {
            waitUntil: 'networkidle2',
            timeout: 60000
        });
        
        // 等待页面加载
        console.log('⏳ 等待页面加载...');
        await new Promise(resolve => setTimeout(resolve, 5000));
        
        // 尝试等待搜索结果加载
        try {
            await page.waitForSelector('[data-testid="search-results"], .search-results, .product-grid, .product-card', {
                timeout: 15000
            });
            console.log('✅ 搜索结果已加载');
        } catch (e) {
            console.log('⚠️  未找到标准选择器，继续执行...');
        }
        
        // 获取页面内容用于调试
        const pageContent = await page.content();
        fs.writeFileSync(
            path.join(__dirname, 'tcgplayer_page.html'),
            pageContent.substring(0, 50000) // 只保存前5万字符
        );
        console.log('📄 页面HTML已保存到 tcgplayer_page.html');
        
        // 尝试多种方法提取卡片信息
        console.log('🔍 尝试提取卡片信息...');
        
        // 方法1：通过页面评估提取数据
        const cards = await page.evaluate(() => {
            const results = [];
            
            // 查找所有可能的卡片元素
            const cardSelectors = [
                '[data-testid*="product"]',
                '[data-testid*="card"]',
                '.product-card',
                '.search-result-item',
                '.product',
                '[class*="product"]',
                '[class*="card"]'
            ];
            
            // 尝试所有选择器
            for (const selector of cardSelectors) {
                const elements = document.querySelectorAll(selector);
                if (elements.length > 0) {
                    console.log(`找到 ${elements.length} 个元素，选择器: ${selector}`);
                    break;
                }
            }
            
            // 更通用的方法：查找包含价格信息的元素
            const allElements = document.querySelectorAll('div, article, section, li');
            
            allElements.forEach(element => {
                const card = {};
                
                // 检查元素是否包含价格信息
                const text = element.innerText || '';
                const html = element.innerHTML || '';
                
                // 查找卡片名称
                const nameSelectors = ['h2', 'h3', 'h4', '.product-name', '.title', '[class*="name"]'];
                let nameFound = false;
                
                for (const selector of nameSelectors) {
                    const nameElem = element.querySelector(selector);
                    if (nameElem && nameElem.innerText && nameElem.innerText.trim().length > 2) {
                        card.name = nameElem.innerText.trim();
                        nameFound = true;
                        break;
                    }
                }
                
                // 如果没有找到名称，尝试从文本中提取
                if (!nameFound && text.length > 10 && text.length < 200) {
                    // 可能是名称的行通常较短且不包含数字和特殊符号
                    const lines = text.split('\n').filter(line => line.trim().length > 3 && line.trim().length < 100);
                    if (lines.length > 0) {
                        card.name = lines[0].trim();
                    }
                }
                
                // 查找价格信息
                const priceRegex = /\$?\d+\.?\d*\s*(USD)?/g;
                const priceMatches = text.match(priceRegex);
                if (priceMatches && priceMatches.length > 0) {
                    card.price = priceMatches[0].trim();
                }
                
                // 查找链接
                const linkElem = element.querySelector('a[href]');
                if (linkElem) {
                    const href = linkElem.getAttribute('href');
                    if (href) {
                        card.url = href.startsWith('http') ? href : 'https://www.tcgplayer.com' + href;
                    }
                }
                
                // 如果找到了名称，添加到结果
                if (card.name && card.name.length > 2) {
                    results.push(card);
                }
            });
            
            // 去重
            const uniqueResults = [];
            const seenNames = new Set();
            
            results.forEach(card => {
                if (card.name && !seenNames.has(card.name)) {
                    seenNames.add(card.name);
                    uniqueResults.push(card);
                }
            });
            
            return uniqueResults;
        });
        
        console.log(`📊 找到 ${cards.length} 张卡片`);
        
        // 如果卡片太少，尝试其他页面
        if (cards.length < 10) {
            console.log('🔄 卡片数量较少，尝试访问其他页面...');
            
            // 尝试 Pokemon 页面
            await page.goto('https://www.tcgplayer.com/search/all/product?q=pokemon&view=grid', {
                waitUntil: 'networkidle2',
                timeout: 30000
            });
            
            await new Promise(resolve => setTimeout(resolve, 3000));
            
            const moreCards = await page.evaluate(() => {
                const additionalCards = [];
                const priceElements = document.querySelectorAll('[class*="price"], [class*="Price"]');
                
                priceElements.forEach(elem => {
                    const card = {};
                    const parent = elem.closest('div, article, li') || elem.parentElement;
                    
                    if (parent) {
                        // 查找名称
                        const nameElem = parent.querySelector('h2, h3, h4, [class*="name"], [class*="Name"]');
                        if (nameElem && nameElem.innerText) {
                            card.name = nameElem.innerText.trim();
                        }
                        
                        // 获取价格
                        card.price = elem.innerText.trim();
                        
                        // 查找链接
                        const link = parent.querySelector('a[href]');
                        if (link) {
                            const href = link.getAttribute('href');
                            card.url = href.startsWith('http') ? href : 'https://www.tcgplayer.com' + href;
                        }
                        
                        if (card.name) {
                            additionalCards.push(card);
                        }
                    }
                });
                
                return additionalCards;
            });
            
            cards.push(...moreCards);
            console.log(`📊 新增 ${moreCards.length} 张卡片，总计 ${cards.length} 张`);
        }
        
        // 去重最终结果
        const uniqueCards = [];
        const seen = new Set();
        
        cards.forEach(card => {
            if (card.name && !seen.has(card.name)) {
                seen.add(card.name);
                uniqueCards.push(card);
            }
        });
        
        console.log(`🎯 最终去重后卡片数: ${uniqueCards.length}`);
        
        // 保存结果
        if (uniqueCards.length > 0) {
            // JSON 格式
            const jsonPath = path.join(__dirname, 'tcgplayer_cards_puppeteer.json');
            fs.writeFileSync(jsonPath, JSON.stringify(uniqueCards.slice(0, 100), null, 2));
            console.log(`💾 JSON 数据已保存到: ${jsonPath}`);
            
            // 文本格式
            const txtPath = path.join(__dirname, 'tcgplayer_cards_puppeteer.txt');
            let textContent = 'TCGplayer 卡片信息汇总 (Puppeteer爬取)\n';
            textContent += '='.repeat(50) + '\n\n';
            textContent += `爬取时间: ${new Date().toLocaleString()}\n`;
            textContent += `总卡片数: ${Math.min(uniqueCards.length, 100)}\n\n`;
            
            uniqueCards.slice(0, 100).forEach((card, index) => {
                textContent += `${index + 1}. ${card.name}\n`;
                if (card.price) {
                    textContent += `   价格: ${card.price}\n`;
                }
                if (card.url) {
                    textContent += `   链接: ${card.url}\n`;
                }
                textContent += '\n';
            });
            
            fs.writeFileSync(txtPath, textContent);
            console.log(`📝 文本报告已保存到: ${txtPath}`);
            
            // 显示前5个结果
            console.log('\n📋 前5个结果:');
            uniqueCards.slice(0, 5).forEach((card, index) => {
                console.log(`${index + 1}. ${card.name} - ${card.price || '无价格信息'}`);
            });
        } else {
            console.log('❌ 未找到任何卡片信息');
            
            // 保存页面截图用于调试
            const screenshotPath = path.join(__dirname, 'tcgplayer_screenshot.png');
            await page.screenshot({ path: screenshotPath, fullPage: false });
            console.log(`📸 页面截图已保存到: ${screenshotPath}`);
        }
        
    } catch (error) {
        console.error('❌ 爬取过程中发生错误:', error);
    } finally {
        if (browser) {
            await browser.close();
            console.log('🔒 浏览器已关闭');
        }
    }
}

// 执行爬取
scrapeTCGplayer().catch(console.error);