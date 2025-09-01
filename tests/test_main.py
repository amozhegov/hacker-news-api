import pytest
from httpx import AsyncClient
from app.main import app
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
# test '/'
async def test_root_endpoint(): 
    async with AsyncClient(base_url='http://127.0.0.1:8000') as client:
        response = await client.get('/')
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
# async test of '/ai/classify/1' endpoint with a Mock
async def test_classify_endpoint():
    # create Mock response
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(message={'role': 'assistant',
                                                'content': 'Mocked Classification'})]
    
    # patch for client.chat.completions.create from app.main
    with patch('app.main.client.chat.completions.create', return_value=mock_response):
        async with AsyncClient(base_url='http://127.0.0.1:8000') as client:
            response = await client.get('ai/classify/1')
    
    assert response.status_code == 200
    data = response.json()
    assert data['model'] == 'OPENAI_MODEL'
    assert data['total'] == 5
    assert 'items' in data
    assert data['items']['content'] == 'Mocked classification'