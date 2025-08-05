# builder/backend/builtin_tools/web_tools.py
"""
Web-related tools for the Agent-Builder application.
Provides web search, HTTP requests, and web scraping capabilities.
"""

import logging
from typing import Dict, Any, Union
from urllib.parse import urljoin

# Optional imports - tools will be disabled if dependencies are missing
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

logger = logging.getLogger(__name__)


def register_web_tools(tframex_app):
    """Register web tools with the TFrameXApp instance."""
    tools_registered = 0
    
    if not HAS_AIOHTTP:
        logger.warning("aiohttp not available - web tools will be disabled")
        return tools_registered
    
    @tframex_app.tool(
        name="web_search_tool",
        description="Search the web using multiple search methods and return formatted results with web scraping fallback"
    )
    async def web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search the web and return structured results with multiple fallback methods."""
        results = []
        
        # Method 1: Try DuckDuckGo Instant Answer API first
        try:
            search_url = f"https://api.duckduckgo.com/?q={query}&format=json&no_redirect=1&no_html=1&skip_disambig=1"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Abstract (direct answer)
                        if data.get('Abstract'):
                            results.append({
                                "type": "abstract",
                                "title": data.get('AbstractText', 'Direct Answer'),
                                "content": data['Abstract'],
                                "url": data.get('AbstractURL', ''),
                                "source": data.get('AbstractSource', 'DuckDuckGo')
                            })
                        
                        # Related topics
                        for topic in data.get('RelatedTopics', [])[:max_results-len(results)]:
                            if isinstance(topic, dict) and 'Text' in topic:
                                results.append({
                                    "type": "related_topic",
                                    "title": topic.get('FirstURL', {}).get('text', 'Related Topic'),
                                    "content": topic['Text'],
                                    "url": topic.get('FirstURL', {}).get('url', ''),
                                    "source": "DuckDuckGo"
                                })
        except Exception as e:
            logger.warning(f"DuckDuckGo API failed: {str(e)}")
        
        # Method 2: If no results, try scraping DuckDuckGo search results page
        if len(results) < max_results:
            try:
                search_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(search_url, headers=headers, timeout=15) as response:
                        if response.status == 200 and HAS_BS4:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Find search result divs
                            search_results = soup.find_all('div', class_='result')
                            
                            for result_div in search_results[:max_results-len(results)]:
                                title_elem = result_div.find('a', class_='result__a')
                                snippet_elem = result_div.find('a', class_='result__snippet')
                                
                                if title_elem:
                                    title = title_elem.get_text(strip=True)
                                    url = title_elem.get('href', '')
                                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                                    
                                    results.append({
                                        "type": "search_result",
                                        "title": title,
                                        "content": snippet,
                                        "url": url,
                                        "source": "DuckDuckGo Search"
                                    })
            except Exception as e:
                logger.warning(f"DuckDuckGo scraping failed: {str(e)}")
        
        # Method 3: If still no results, try alternative news sources for news queries
        if len(results) < max_results and any(word in query.lower() for word in ['news', 'today', 'latest', 'current', 'breaking']):
            try:
                # Try BBC News RSS feed for general news
                news_url = "https://feeds.bbci.co.uk/news/rss.xml"
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(news_url, timeout=10) as response:
                        if response.status == 200:
                            xml_content = await response.text()
                            # Simple XML parsing for RSS
                            import re
                            
                            # Extract titles and descriptions
                            title_pattern = r'<title><!\[CDATA\[(.*?)\]\]></title>'
                            desc_pattern = r'<description><!\[CDATA\[(.*?)\]\]></description>'
                            link_pattern = r'<link>(.*?)</link>'
                            
                            titles = re.findall(title_pattern, xml_content)
                            descriptions = re.findall(desc_pattern, xml_content)
                            links = re.findall(link_pattern, xml_content)
                            
                            # Skip first item (usually the feed title)
                            for i, (title, desc, link) in enumerate(zip(titles[1:], descriptions[1:], links[1:])):
                                if i >= max_results - len(results):
                                    break
                                
                                results.append({
                                    "type": "news_item",
                                    "title": title.strip(),
                                    "content": desc.strip(),
                                    "url": link.strip(),
                                    "source": "BBC News"
                                })
            except Exception as e:
                logger.warning(f"News feed fallback failed: {str(e)}")
        
        # If still no results, provide a helpful message
        if not results:
            results.append({
                "type": "no_results",
                "title": "No Results Found",
                "content": f"Unable to find search results for '{query}'. This could be due to network issues or API limitations. Try rephrasing your query or being more specific.",
                "url": "",
                "source": "Search System"
            })
        
        return {
            "success": len(results) > 0,
            "query": query,
            "results": results,
            "total_results": len(results),
            "methods_used": ["DuckDuckGo API", "DuckDuckGo Scraping", "News Feeds"] if len(results) > 1 else ["Fallback"]
        }
    
    @tframex_app.tool(
        name="http_request_tool",
        description="Make HTTP requests with support for different methods and headers"
    )
    async def http_request(
        url: str,
        method: str = "GET",
        headers: Dict[str, str] = None,
        data: Union[str, Dict] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Make HTTP requests with full control over parameters."""
        try:
            async with aiohttp.ClientSession() as session:
                kwargs = {
                    'headers': headers or {},
                    'timeout': aiohttp.ClientTimeout(total=timeout)
                }
                
                if data:
                    if isinstance(data, dict):
                        kwargs['json'] = data
                    else:
                        kwargs['data'] = data
                
                async with session.request(method.upper(), url, **kwargs) as response:
                    content = await response.text()
                    
                    # Try to parse JSON if possible
                    try:
                        json_content = await response.json()
                    except (ValueError, TypeError):
                        json_content = None
                    
                    return {
                        "success": response.status < 400,
                        "status_code": response.status,
                        "headers": dict(response.headers),
                        "content": content,
                        "json": json_content,
                        "url": str(response.url)
                    }
        except Exception as e:
            return {
                "success": False,
                "error": f"HTTP request error: {str(e)}",
                "status_code": 0
            }
    
    @tframex_app.tool(
        name="news_search_tool",
        description="Search for current news and headlines from multiple reliable news sources"
    )
    async def news_search(query: str = "latest news", max_results: int = 5) -> Dict[str, Any]:
        """Search for current news from reliable sources."""
        results = []
        sources_tried = []
        
        # List of RSS feeds to try
        news_feeds = [
            {"name": "BBC World News", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
            {"name": "BBC Technology", "url": "https://feeds.bbci.co.uk/news/technology/rss.xml"},
            {"name": "Reuters World", "url": "https://www.reuters.com/news/world/rss"},
            {"name": "AP News", "url": "https://apnews.com/apf-topnews"}
        ]
        
        # Try each news source
        for feed in news_feeds:
            if len(results) >= max_results:
                break
                
            try:
                sources_tried.append(feed["name"])
                
                async with aiohttp.ClientSession() as session:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (compatible; NewsBot/1.0)',
                        'Accept': 'application/rss+xml, application/xml, text/xml'
                    }
                    async with session.get(feed["url"], headers=headers, timeout=10) as response:
                        if response.status == 200:
                            xml_content = await response.text()
                            import re
                            
                            # Extract RSS items
                            title_pattern = r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>'
                            desc_pattern = r'<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>'
                            link_pattern = r'<link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>'
                            pubdate_pattern = r'<pubDate>(.*?)</pubDate>'
                            
                            titles = re.findall(title_pattern, xml_content, re.DOTALL)
                            descriptions = re.findall(desc_pattern, xml_content, re.DOTALL)
                            links = re.findall(link_pattern, xml_content, re.DOTALL)
                            pubdates = re.findall(pubdate_pattern, xml_content, re.DOTALL)
                            
                            # Skip first items (usually feed metadata)
                            for i, (title, desc, link) in enumerate(zip(titles[1:], descriptions[1:], links[1:])):
                                if len(results) >= max_results:
                                    break
                                
                                # Clean up content
                                title = re.sub(r'<[^>]+>', '', title).strip()
                                desc = re.sub(r'<[^>]+>', '', desc).strip()
                                link = re.sub(r'<[^>]+>', '', link).strip()
                                
                                # Skip if empty
                                if not title or not link:
                                    continue
                                
                                # Get publish date if available
                                pubdate = pubdates[i+1] if i+1 < len(pubdates) else "Recently"
                                
                                # Filter by query if specific
                                if query.lower() not in "latest news today current" and query.lower() not in title.lower() and query.lower() not in desc.lower():
                                    continue
                                
                                results.append({
                                    "type": "news_article",
                                    "title": title,
                                    "content": desc,
                                    "url": link,
                                    "source": feed["name"],
                                    "published": pubdate.strip()
                                })
                        
            except Exception as e:
                logger.warning(f"Failed to fetch from {feed['name']}: {str(e)}")
                continue
        
        # If no results from RSS feeds, try web scraping news sites
        if not results:
            try:
                # Try BBC News homepage
                url = "https://www.bbc.com/news"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, timeout=15) as response:
                        if response.status == 200 and HAS_BS4:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Find headlines
                            headline_selectors = [
                                'h3[data-testid="card-headline"]',
                                'h2[data-testid="card-headline"]',
                                '.gs-c-promo-heading__title',
                                '.media__title a'
                            ]
                            
                            for selector in headline_selectors:
                                headlines = soup.select(selector)
                                for headline in headlines[:max_results]:
                                    if isinstance(headline, str):
                                        continue
                                        
                                    title = headline.get_text(strip=True)
                                    link_elem = headline if headline.name == 'a' else headline.find('a')
                                    link = link_elem.get('href', '') if link_elem else ''
                                    
                                    if link and not link.startswith('http'):
                                        link = f"https://www.bbc.com{link}"
                                    
                                    if title and link:
                                        results.append({
                                            "type": "news_headline",
                                            "title": title,
                                            "content": "Latest news from BBC",
                                            "url": link,
                                            "source": "BBC News",
                                            "published": "Today"
                                        })
                                
                                if results:
                                    break
                            
                            sources_tried.append("BBC News Scrape")
                            
            except Exception as e:
                logger.warning(f"News scraping failed: {str(e)}")
        
        # Provide fallback if no results
        if not results:
            results.append({
                "type": "no_news",
                "title": "News Search Unavailable",
                "content": f"Unable to retrieve current news for '{query}'. This could be due to network restrictions or RSS feed unavailability. Try checking news websites directly.",
                "url": "https://www.bbc.com/news",
                "source": "System Message",
                "published": "N/A"
            })
        
        return {
            "success": len([r for r in results if r["type"] != "no_news"]) > 0,
            "query": query,
            "results": results,
            "total_results": len(results),
            "sources_tried": sources_tried
        }

    tools_registered += 3
    
    # Web scraping tool (requires both aiohttp and beautifulsoup4)
    if HAS_BS4:
        @tframex_app.tool(
            name="web_scraper_tool",
            description="Extract content from web pages with customizable selectors"
        )
        async def web_scrape(
            url: str, 
            selector: str = None, 
            extract_links: bool = False,
            max_content_length: int = 10000
        ) -> Dict[str, Any]:
            """Scrape content from a web page."""
            import re
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    async with session.get(url, headers=headers, timeout=30) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            result = {
                                "success": True,
                                "url": url,
                                "title": soup.title.string if soup.title else "No title",
                                "content": "",
                                "links": [] if extract_links else None
                            }
                            
                            # Extract content based on selector or default
                            if selector:
                                elements = soup.select(selector)
                                content = ' '.join([elem.get_text(strip=True) for elem in elements])
                            else:
                                # Remove script and style elements
                                for script in soup(["script", "style"]):
                                    script.decompose()
                                content = soup.get_text()
                            
                            # Clean and limit content
                            content = re.sub(r'\s+', ' ', content).strip()
                            if len(content) > max_content_length:
                                content = content[:max_content_length] + "..."
                            
                            result["content"] = content
                            
                            # Extract links if requested
                            if extract_links:
                                links = []
                                for link in soup.find_all('a', href=True):
                                    href = link['href']
                                    if href.startswith(('http://', 'https://')):
                                        full_url = href
                                    else:
                                        full_url = urljoin(url, href)
                                    
                                    links.append({
                                        "text": link.get_text(strip=True),
                                        "url": full_url
                                    })
                                
                                result["links"] = links[:50]  # Limit to 50 links
                            
                            return result
                        else:
                            return {
                                "success": False,
                                "error": f"HTTP {response.status}: {response.reason}",
                                "url": url
                            }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Scraping error: {str(e)}",
                    "url": url
                }
        
        tools_registered += 1
    else:
        logger.warning("beautifulsoup4 not available - web scraping tool will be disabled")
    
    return tools_registered