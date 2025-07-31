# builder/backend/builtin_tools/web_tools.py
"""
Web-related tools for the Agent-Builder application.
Provides web search, HTTP requests, and web scraping capabilities.
"""

import logging
from typing import Dict, Any, Union, List
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
        name="Web Search Tool",
        description="Search the web using DuckDuckGo API and return formatted results"
    )
    async def web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search the web and return structured results."""
        try:
            # Use DuckDuckGo Instant Answer API (no API key required)
            search_url = f"https://api.duckduckgo.com/?q={query}&format=json&no_redirect=1&no_html=1&skip_disambig=1"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        results = []
                        
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
                        
                        return {
                            "success": True,
                            "query": query,
                            "results": results,
                            "total_results": len(results)
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Search API returned status {response.status}",
                            "results": []
                        }
        except Exception as e:
            return {
                "success": False,
                "error": f"Search error: {str(e)}",
                "results": []
            }
    
    @tframex_app.tool(
        name="HTTP Request Tool",
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
                    except:
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
    
    tools_registered += 2
    
    # Web scraping tool (requires both aiohttp and beautifulsoup4)
    if HAS_BS4:
        @tframex_app.tool(
            name="Web Scraper Tool",
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