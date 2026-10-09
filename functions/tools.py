from langchain.tools import tool
from tavily import TavilyClient
from bs4 import BeautifulSoup
import requests

from layers.config import get_settings

tavily = TavilyClient(api_key=get_settings().tavily_api_key)

@tool
def get_search(query: str) -> str:
    '''Search the web for recent and reliable topic'''
    result = tavily.search(query=query, max_results=5)
    out = []
    for r in result['results']:
        out.append(
            f"URL: {r['url']}\nTitle: {r['title']}\nSnippet: {r['content'][:500]}"
        )
    return "\n\n".join(out)   
 
 
@tool
def get_information(url: str) -> str:
    """Extract the main text content from a webpage URL."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/138.0.0.0 Safari/537.36"
        )
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return text[:3000]
    except Exception as e:
        return f"Error: {str(e)}"