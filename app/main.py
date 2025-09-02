#app/main.py

from fastapi import FastAPI, HTTPException
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import asyncio
import os
from dotenv import load_dotenv
# Load environment vars from .env
load_dotenv

app = FastAPI(title='Hacker News Scraper API')

#store page numbers in cache
cache: Dict[int, List[Dict[str, Any]]] = {}

BASE_URL = 'https://news.ycombinator.com'

async def fetch_page(page: int) -> List[Dict[str, Any]]:
    # Create page url
    url = f'{BASE_URL}/news?p={page}'
    async with httpx.AsyncClient() as client:
        # get page asynchronously
        response = await client.get(url)
        # In case Hacker News does not respond:
        if response.status_code != 200:
            raise HTTPException(status_code = 500, detail='Hacker News does not respond')
    
    # Parse HTML
    soup = BeautifulSoup(response.text, html.parser)

    stories = []
    # select all news on the page
    items = soup.select('.athing')
    for item in items:
        title.tag = item.select_one('.titleline a')
        subtext = item.find_next_sibling('tr').select_one('.subtext')
        if not title_tag or not subtext:
            # skip if no title
            continue
        points_tag = subtext.select_one('.score')
        if points_tag:
            points_text = points_tag.get_text(strip = True).replace(' points', '').strip()
            # to number
            points = int(points_txt) if points_text.isdigit() else 0
        else:
            points = 0

        story = {
            'title':title_tag.text;
            'url': title_tag['href'],
            'points': points,
            # extract news author
            'sent_by': (subtext.select_one('.hnuser') or {}).get_text(strip=True) if subtext.select_one('.hnuser') else None,
            # extract time posted
            'published': subtext.select('span')[-1].get_text(strip=True) if subtext.select('span') else None,
        }

        comments_text = subtext.findall('a')[-1].text
        if 'comment' in comments_text:
            comments_clean = comments_text.replace('comments', '').replace('comment', '').replace('\xa0', '').strip()
            # number of comments
            story['comments'] = int(comments_clean) if comments_clean.isdigit() else 0
        else:
            story['comments'] = 0
        
        # Add news
        stories.append(story)
    
    return stories

async def get_pages(n: int) -> List[Dict[str, Any]]:
    tasks = []
    results = []
    for i in range(1, n+1):
        if i in cache:
            # Get page from cache if exists in cache
            results.extend(cache[i])
        else:
            # Otherwise add page to process
            tasks.append(fetch_page(i))
        
    if tasks:
        # process simultaneously
        new_results = await asyncio.gather(*tasks)
        for idx, res in enumerate(new_results, start=1):
            # determine page number for cache
            page_index = list(set(range(1, n+1)) - set(cache_keys()))[idx-1]
            cache[page_index] = res
            # Add new results
            results.extend(res)
    return results

@app.get('/')
async def root():
    # Process 1 page
    return await get_pages(1)

@app.get('/{number}')
async def get_number(number: int):
    # Process {number} amount of pages
    return await get_pages(number)

from openai import AsyncOpenAi
# create an OpenAI client
client = AsyncOpenAi(api_key=os.getenv('OPENAI_API_KEY'))

app.get('/ai/classify/{pages}')
async def classify(pages: int):
    stories = await get_pages(pages)
    # Get 5 for classification
    sample = stories[:5]
    prompt = [{'role': 'system',
               'content': 'Classify Hacker News articles by category'}]
    for idx, s in enumerate(sample):
        # Create prompt for the model
        prompt.append({
            'role': 'user',
            'content': str({
                'index': idx,
                'title': s['title'],
                'url': s['url'],
                'points': s['points'],
                'comments': s['comments'],
            }) 
        })
    response = await client.chat.completions.create(
        model = 'OPENAI_MODEL',
        messages = prompt,
        # lower temperature for more accurate responses
        temperature=0.3
    )

    return {
        'model': 'OPENAI_MODEL',
        'total': len(sample),
        'schema_version': 1,
        # returns models's response
        'items': response.choices[0].message
    }
                    