import requests
from config.config_base import model_data as md

def make_zap(messages: list, max_tokens = md['max_tokens']) -> str:
    # print(messages)
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
        # print(response.text)
        res = response.json()
        
        # print(res)
        r = res['result']['alternatives'][0]['message']['text']
        r = r.replace('*', '')

    except (IndexError, TypeError) as e:
        r = '-1'
    return r


def cards3(cards: str, reason: str) -> str:
    messages = [
        {
            "role": "system",
            "text": "Ты гадалка, которая специализируется на раскладах таро"
        },
        {
            "role": "user",
            "text": f'Я хочу сделать расклад таро на {reason}'
        },
        {
            "role": "assistant",
            "text": f"Вам выпали карты {cards}"
        },
        {
            "role": "user",
            "text": f"И что это значит? Что мне сулят эти карты? Напиши про каждую карту, что она значит в контексте {reason} и общую картину. Используй оригинальные формулировки, сохраняй налет загадочности. Не пиши ничего больше. Не делай предсказаний о будущем."
        }
    ]

    res = make_zap(messages)
    return res

def daycard(card: str) -> str:
    messages = [
        {
            "role": "system",
            "text": "Ты гадалка, которая специализируется на раскладах таро"
        },
        {
            "role": "user",
            "text": f'Я хочу сделать вытянуть карту дня'
        },
        {
            "role": "assistant",
            "text": f"Вам выпала карта {card}"
        },
        {
            "role": "user",
            "text": f"И что мне сулит эта карта? Опиши общую картину. Используй оригинальные формулировки, сохраняй налет загадочности. Не пиши ничего больше. Не делай предсказаний о будущем."
        }
    ]

    res = make_zap(messages)
    return res

def star7(cards: str) -> str:
    messages = [
        {
            "role": "system",
            "text": "Ты гадалка, которая специализируется на раскладах таро"
        },
        {
            "role": "user",
            "text": f'Я хочу сделать расклад на семь звезд'
        },
        {
            "role": "assistant",
            "text": cards
        },
        {
            "role": "user",
            "text": f"И что мне сулят эти карты? Расскажи о каждой карте в соответствии с ее толкованием. Если карта перевернута, это плохо, предсказание тревожное. Остальные предсказания оптимистичные. Используй оригинальные формулировки, сохраняй налет загадочности. Не пиши ничего больше. Не делай предсказаний о будущем."
        }
    ]

    res = make_zap(messages, 1000)
    return res

def crest5(cards: str) -> str:
    
    messages = [
        {
            "role": "system",
            "text": "Ты гадалка, которая специализируется на раскладах таро."
        },
        {
            "role": "user",
            "text": f'Я хочу сделать расклад пять карт.'
        },
        {
            "role": "assistant",
            "text": cards
        },
        {
            "role": "user",
            "text": f"И что мне сулят эти карты? Начни с главной, она важнее. затем расскажи об остальных. Опиши общую картину. Используй оригинальные формулировки, сохраняй налет загадочности. Не пиши ничего больше. Не делай предсказаний о будущем."
        }
    ]

    res = make_zap(messages)
    return res


def horse7(cards: str) -> str:
    messages = [
        {
            "role": "system",
            "text": "Ты гадалка, которая специализируется на раскладах таро"
        },
        {
            "role": "user",
            "text": f'Я хочу расклад подкова'
        },
        {
            "role": "assistant",
            "text": cards
        },
        {
            "role": "user",
            "text": f"И что мне сулят эти карты? Расскажи о каждой карте в соответствии с ее толкованием. Если карта перевернута, это плохо, предсказание тревожное. Остальные предсказания оптимистичные. Используй оригинальные формулировки, сохраняй налет загадочности. Не пиши ничего больше."
        }
    ]

    res = make_zap(messages, 1000)
    return res