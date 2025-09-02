# app/main.py
from fastapi import FastAPI, HTTPException
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()  # upload variables from .env

app = FastAPI(title='Hacker News Scraper API')

cache: Dict[int, List[Dict[str, Any]]] = {}  # save cache by page number

BASE_URL = 'https://news.ycombinator.com'

async def fetch_page(page: int) -> List[Dict[str, Any]]:
    url = f'{BASE_URL}/news?p={page}'  # create page url
    async with httpx.AsyncClient() as client:
        response = await client.get(url)  # get the page asynchronously
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail='Error while loading Hacker News')  # if Hacker news does not respond

    soup = BeautifulSoup(response.text, 'html.parser')  #  HTML parser

    stories = []
    items = soup.select('.athing')  # select all the news on the page
    for item in items:
        title_tag = item.select_one('.titleline a')
        subtext = item.find_next_sibling('tr').select_one('.subtext')
        if not title_tag or not subtext:
            continue  # skip if no title

        points_tag = subtext.select_one('.score')
        if points_tag:
            points_text = points_tag.get_text(strip=True).replace(' points', '').strip()
            points = int(points_text) if points_text.isdigit() else 0  # transform to the number
        else:
            points = 0

        story = {
            'title': title_tag.text,
            'url': title_tag['href'],
            'points': points,
            'sent_by': (subtext.select_one('.hnuser') or {}).get_text(strip=True) if subtext.select_one('.hnuser') else None,  # extract author
            'published': subtext.select('span')[-1].get_text(strip=True) if subtext.select('span') else None,  # posted, time
        }

        comments_text = subtext.find_all('a')[-1].text
        if 'comment' in comments_text:
            comments_clean = comments_text.replace('comments', '').replace('comment', '').replace('\xa0', '').strip()
            story['comments'] = int(comments_clean) if comments_clean.isdigit() else 0  # umber of comments
        else:
            story['comments'] = 0

        stories.append(story)  # add the news to the list

    return stories

async def get_pages(n: int) -> List[Dict[str, Any]]:
    tasks = []
    results = []
    for i in range(1, n+1):
        if i in cache:
            results.extend(cache[i])  # use cached news if exists
        else:
            tasks.append(fetch_page(i))  # otherwise add to processing

    if tasks:
        new_results = await asyncio.gather(*tasks)  # simultaneous processing
        for idx, res in enumerate(new_results, start=1):
            page_index = list(set(range(1, n+1)) - set(cache.keys()))[idx-1]  # determine page's number
            cache[page_index] = res
            results.extend(res)  # add new resuls

    return results

@app.get('/')
async def root():
    return await get_pages(1)  # return 1 page

@app.get('/{number}')
async def get_number(number: int):
    return await get_pages(number)  # return {number} amount of pages

from openai import AsyncOpenAI
client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))  # create OpenAI client

@app.get('/ai/classify/{pages}')
async def classify(pages: int):
    stories = await get_pages(pages)
    sample = stories[:5]  # 5 entries to classify
    prompt = [{'role': 'system', 'content': 'Classify Hacker News articles by category.'}]

    for idx, s in enumerate(sample):
        prompt.append({
            'role': 'user',
            'content': str({
                'index': idx,
                'title': s['title'],
                'url': s['url'],
                'points': s['points'],
                'comments': s['comments']
            })  # create model's prompt 
        })

    response = await client.chat.completions.create(
        model='gpt-4o-mini',  # use selected model
        messages=prompt,
        temperature=0.3  # use lower temperature for more precise responses
    )

    return {
        'model': 'gpt-4o-mini',
        'total': len(sample),
        'schema_version': 1,
        'items': response.choices[0].message  # return model's response
    }
