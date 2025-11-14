import requests
from config import model_data as md

def make_zap(messages: list, max_tokens=None) -> str:
    if max_tokens is None:
        max_tokens = md['max_tokens']
    
    prompt = {
        "modelUri": md['model_uri'],
        "completionOptions": {
            "stream": False,
            "temperature": md['temperature'],
            "maxTokens": max_tokens
        },
        "messages": messages
    }

    url = md['url']
    headers = {
        "Content-Type": "application/json",
        "Authorization": md['authorization']
    }
    
    try:
        response = requests.post(url, headers=headers, json=prompt)
        res = response.json()
        r = res['result']['alternatives'][0]['message']['text']
        r = r.replace('*', '')
    except (IndexError, TypeError, KeyError) as e:
        r = 'Произошла ошибка при обращении к YandexGPT. Попробуйте позже.'
    return r

def ask_yandex_gpt(question: str) -> str:
    """Функция для задавания вопроса YandexGPT"""
    messages = [
        {
            "role": "system",
            "text": "Ты эксперт по заводам, локомотивам и железнодорожной технике. Отвечай кратко и по делу."
        },
        {
            "role": "user",
            "text": question
        }
    ]
    
    res = make_zap(messages)
    return res

