from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import httpx
import os
import json
from bs4 import BeautifulSoup

load_dotenv()
mcp = FastMCP("docs")

USER_AGENT = "docs-app/1.0"
SERPER_URL = "https://google.serper.dev/search"

docs_urls = {
    "langchain": "python.langchain.com/docs",
    "llama-index": "docs.llamaindex.ai/en/stable",
    "openai": "platform.openai.com/docs",
}

"""
Our agent is going to first search the web using the Serper API key for Google search, for the given query, and then use those search results to access the URLs returned in the search results and get the contents of the page from the URL 
"""

async def search_web(query: str) -> dict | None:
    """
    Search the web using the Serper API key for Google search, for the given query.
    """
    payload = json.dumps({"q": query, "num": 2})
    headers = {
        "X-API-KEY": os.getenv("SERPER_API_KEY"),
        "Content-Type": "application/json",       
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url=SERPER_URL, headers=headers, 
                                         data=payload, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            print("Timeout occurred while searching the web.")
            return {"organic": []}        


async def fetch_url(url: str):
    """
    Fetch the content in the page of the URL using the Serper API key for Google search, 
    for the given query.
    """
    async with httpx.AsyncClient() as client:        
        try:
            response = await client.get(url=url, timeout=30.0)
            soup = BeautifulSoup(response.text, "html.parser")
            # text = soup.get_text()
            # return text
            # Target main content areas instead of all text
            main_content = soup.find("main") or soup.find("article") or soup
            text = main_content.get_text(separator="\n\n", strip=True)
            return text
        except httpx.TimeoutException:
            return "Timeout occurred while fetching the URL."

@mcp.tool()
async def get_docs(query: str, library: str, max_chars: int = 1000):
    """
    Search the docs for a given query and library.
    Supports langchain, llama-index, and openai.

    Args:
        query: The query to search for (e.g.: "Chroma DB").
        library: The library to search in. One of langchain, llama-index, openai.
        max_chars: Maximum characters to return (default: 1000 for free tier).

    Returns:
        Text from the documentation.
    """
    if library not in docs_urls:
        raise ValueError(f"Library {library} not supported. Supported libraries are: {', '.join(docs_urls.keys())}")

    url = f"site:{docs_urls[library]} {query}"
    results = await search_web(url)
    if len(results["organic"]) == 0:
        return "No results found."
    text = ""
    for result in results["organic"]:
        text += await fetch_url(result["link"])
    return text[:max_chars]  # Limit to max_chars characters




if __name__ == "__main__":
    mcp.run(transport="stdio")
