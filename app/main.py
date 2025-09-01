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

