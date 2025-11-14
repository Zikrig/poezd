import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла env (если он существует)
# В Docker переменные будут переданы через environment, поэтому файл не обязателен
if os.path.exists('env'):
    load_dotenv('env')

# Токен Telegram бота
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Данные для YandexGPT
model_data = {
    'model_uri': os.getenv('LLM_MODEL_URI'),
    'temperature': float(os.getenv('LLM_TEMPERATURE', '0.5')),
    'max_tokens': int(os.getenv('LLM_MAX_TOKENS', '500')),
    'url': os.getenv('LLM_URL'),
    'authorization': os.getenv('LLM_AUTHORIZATION')  # Должен быть установлен через переменные окружения
}

