import asyncio
import logging
from pathlib import Path
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from quiz_data import QUIZ_QUESTIONS, INTERMEDIATE_SCREEN, FINAL_SCREEN
from yandex_gpt import ask_yandex_gpt
from config import BOT_TOKEN

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Проверка наличия токена
if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
    raise ValueError("Необходимо указать BOT_TOKEN в файле env")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# Состояния FSM
class QuizState(StatesGroup):
    waiting_for_answer = State()
    asking_gpt = State()
    waiting_intermediate = State()  # Ожидание на промежуточном экране


# Хранилище результатов викторины для каждого пользователя
user_results = {}


def get_quiz_keyboard(question_num: int, options: list) -> InlineKeyboardMarkup:
    """Создает клавиатуру с вариантами ответов"""
    buttons = []
    for i, option in enumerate(options):
        buttons.append([
            InlineKeyboardButton(
                text=option,
                callback_data=f"answer_{question_num}_{i}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_start_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для начала викторины"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Поехали", callback_data="start_quiz")]
    ])
    return keyboard


def get_intermediate_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для промежуточного экрана"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Вопрос", callback_data="ask_gpt_intermediate")],
        [InlineKeyboardButton(text="Нет вопросов", callback_data="skip_intermediate")]
    ])
    return keyboard


def get_final_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для финального экрана"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Повторить викторину", callback_data="start_quiz")]
    ])
    return keyboard


async def send_photo(message_or_callback, photo_path: str, caption: str = "", reply_markup=None):
    """Отправляет фото с подписью"""
    photo_file = FSInputFile(photo_path)
    
    if isinstance(message_or_callback, CallbackQuery):
        try:
            await message_or_callback.message.answer_photo(
                photo=photo_file,
                caption=caption,
                reply_markup=reply_markup
            )
            await message_or_callback.answer()
        except Exception as e:
            logger.error(f"Ошибка при отправке фото: {e}")
            await message_or_callback.message.answer(
                caption,
                reply_markup=reply_markup
            )
            await message_or_callback.answer()
    else:
        await message_or_callback.answer_photo(
            photo=photo_file,
            caption=caption,
            reply_markup=reply_markup
        )


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Друг"
    
    user_results[user_id] = {
        "current_question": 0,
        "correct_answers": 0,
        "answers": []
    }
    
    greeting_text = (
        f"Приветствие:\n\n"
        f"{user_name}!\n\n"
        f"На Вашем пути 5 остановок с вопросами о легендарных заводах и их творениях.\n\n"
        f"Готовы к заезду? Запускаем двигатели!"
    )
    
    await message.answer(
        greeting_text,
        reply_markup=get_start_keyboard()
    )


@dp.callback_query(lambda c: c.data == "start_quiz")
async def start_quiz(callback: CallbackQuery, state: FSMContext):
    """Начало викторины"""
    user_id = callback.from_user.id
    user_results[user_id] = {
        "current_question": 0,
        "correct_answers": 0,
        "answers": []
    }
    
    await state.set_state(QuizState.waiting_for_answer)
    await show_question(callback, state)


async def show_question(callback: CallbackQuery, state: FSMContext):
    """Показывает текущий вопрос викторины"""
    user_id = callback.from_user.id
    current_q = user_results[user_id]["current_question"]
    
    # Проверяем, нужно ли показать промежуточный экран (после вопроса 2, индекс 1)
    # Промежуточный экран показываем после ответа на вопрос с индексом 1 (второй вопрос)
    if current_q == 2:  # После ответа на второй вопрос (индекс 1) показываем промежуточный экран
        await show_intermediate_screen(callback, state)
        return
    
    if current_q >= len(QUIZ_QUESTIONS):
        # Викторина завершена
        await show_final_screen(callback, state)
        return
    
    question_data = QUIZ_QUESTIONS[current_q]
    question_text = question_data['question']
    
    keyboard = get_quiz_keyboard(current_q, question_data['options'])
    
    try:
        # Если есть изображение, отправляем его с текстом вопроса
        if question_data.get('image'):
            photo_path = question_data['image']
            if Path(photo_path).exists():
                await send_photo(callback, photo_path, question_text, keyboard)
            else:
                await callback.message.edit_text(question_text, reply_markup=keyboard)
                await callback.answer()
        else:
            await callback.message.edit_text(question_text, reply_markup=keyboard)
            await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при показе вопроса: {e}")
        # Если не удалось отредактировать, отправляем новое сообщение
        if question_data.get('image'):
            photo_path = question_data['image']
            if Path(photo_path).exists():
                await send_photo(callback, photo_path, question_text, keyboard)
            else:
                await callback.message.answer(question_text, reply_markup=keyboard)
                await callback.answer()
        else:
            await callback.message.answer(question_text, reply_markup=keyboard)
            await callback.answer()


async def show_intermediate_screen(callback: CallbackQuery, state: FSMContext):
    """Показывает промежуточный экран после вопроса 2"""
    await state.set_state(QuizState.waiting_intermediate)
    
    photo_path = INTERMEDIATE_SCREEN['image']
    text = INTERMEDIATE_SCREEN['text']
    keyboard = get_intermediate_keyboard()
    
    try:
        if Path(photo_path).exists():
            await send_photo(callback, photo_path, text, keyboard)
        else:
            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при показе промежуточного экрана: {e}")
        if Path(photo_path).exists():
            await send_photo(callback, photo_path, text, keyboard)
        else:
            await callback.message.answer(text, reply_markup=keyboard)
            await callback.answer()


async def show_final_screen(callback: CallbackQuery, state: FSMContext):
    """Показывает финальный экран"""
    await state.clear()
    
    photo_path = FINAL_SCREEN['image']
    text = FINAL_SCREEN['text']
    keyboard = get_final_keyboard()
    
    try:
        if Path(photo_path).exists():
            await send_photo(callback, photo_path, text, keyboard)
        else:
            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при показе финального экрана: {e}")
        if Path(photo_path).exists():
            await send_photo(callback, photo_path, text, keyboard)
        else:
            await callback.message.answer(text, reply_markup=keyboard)
            await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("answer_"))
async def process_answer(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа пользователя"""
    user_id = callback.from_user.id
    _, question_num, answer_num = callback.data.split("_")
    question_num = int(question_num)
    answer_num = int(answer_num)
    
    question_data = QUIZ_QUESTIONS[question_num]
    is_correct = answer_num == question_data['correct']
    
    # Сохраняем ответ
    user_results[user_id]["answers"].append({
        "question": question_num,
        "answer": answer_num,
        "correct": is_correct
    })
    
    if is_correct:
        user_results[user_id]["correct_answers"] += 1
    
    # Получаем текст ответа из responses
    response_text = question_data['responses'].get(answer_num, "Ответ обработан")
    
    # Отправляем ответ как сообщение вместо уведомления
    await callback.message.answer(response_text)
    await callback.answer()
    
    # Переходим к следующему вопросу
    user_results[user_id]["current_question"] += 1
    
    await asyncio.sleep(1)  # Небольшая задержка для показа результата
    await show_question(callback, state)


@dp.callback_query(lambda c: c.data == "skip_intermediate")
async def skip_intermediate(callback: CallbackQuery, state: FSMContext):
    """Пропуск промежуточного экрана и переход к следующему вопросу"""
    user_id = callback.from_user.id
    # Пропускаем промежуточный экран и переходим к вопросу с индексом 2 (третий вопрос)
    # current_q уже равен 2, поэтому просто показываем вопрос напрямую
    await state.set_state(QuizState.waiting_for_answer)
    
    # Показываем вопрос с индексом 2 напрямую, минуя проверку на промежуточный экран
    current_q = user_results[user_id]["current_question"]
    if current_q >= len(QUIZ_QUESTIONS):
        await show_final_screen(callback, state)
        return
    
    question_data = QUIZ_QUESTIONS[current_q]
    question_text = question_data['question']
    keyboard = get_quiz_keyboard(current_q, question_data['options'])
    
    try:
        if question_data.get('image'):
            photo_path = question_data['image']
            if Path(photo_path).exists():
                await send_photo(callback, photo_path, question_text, keyboard)
            else:
                await callback.message.answer(question_text, reply_markup=keyboard)
                await callback.answer()
        else:
            await callback.message.answer(question_text, reply_markup=keyboard)
            await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при показе вопроса: {e}")
        if question_data.get('image'):
            photo_path = question_data['image']
            if Path(photo_path).exists():
                await send_photo(callback, photo_path, question_text, keyboard)
            else:
                await callback.message.answer(question_text, reply_markup=keyboard)
                await callback.answer()
        else:
            await callback.message.answer(question_text, reply_markup=keyboard)
            await callback.answer()


@dp.callback_query(lambda c: c.data == "continue_quiz")
async def continue_quiz(callback: CallbackQuery, state: FSMContext):
    """Продолжение викторины после промежуточного экрана (возврат к промежуточному экрану)"""
    user_id = callback.from_user.id
    current_q = user_results.get(user_id, {}).get("current_question", 0)
    
    # Если мы на промежуточном экране (current_q == 2), показываем его снова
    if current_q == 2:
        await state.set_state(QuizState.waiting_intermediate)
        await show_intermediate_screen(callback, state)
    else:
        # Иначе продолжаем викторину
        await state.set_state(QuizState.waiting_for_answer)
        await show_question(callback, state)


@dp.callback_query(lambda c: c.data == "ask_gpt_intermediate")
async def ask_gpt_intermediate(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Вопрос' на промежуточном экране"""
    await state.set_state(QuizState.asking_gpt)
    # Отправляем новое сообщение вместо редактирования (т.к. предыдущее сообщение может быть с фото)
    await callback.message.answer(
        "💬 Задайте ваш вопрос о том, что нас везло:\n\n"
        "Напишите ваш вопрос в следующем сообщении.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="continue_quiz")]
        ])
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == "ask_gpt")
async def ask_gpt_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Задать вопрос YandexGPT'"""
    await state.set_state(QuizState.asking_gpt)
    # Отправляем новое сообщение вместо редактирования
    await callback.message.answer(
        "💬 Задайте ваш вопрос о заводах и локомотивах YandexGPT:\n\n"
        "Напишите ваш вопрос в следующем сообщении.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="cancel_gpt")]
        ])
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == "cancel_gpt")
async def cancel_gpt(callback: CallbackQuery, state: FSMContext):
    """Отмена вопроса к GPT"""
    await state.clear()
    # Отправляем новое сообщение вместо редактирования
    await callback.message.answer(
        "Действие отменено.",
        reply_markup=get_start_keyboard()
    )
    await callback.answer()


@dp.message(QuizState.asking_gpt)
async def process_gpt_question(message: types.Message, state: FSMContext):
    """Обработка вопроса к YandexGPT"""
    question = message.text
    
    if not question or len(question.strip()) == 0:
        await message.answer("Пожалуйста, задайте вопрос текстом.")
        return
    
    # Показываем, что обрабатываем запрос
    processing_msg = await message.answer("⏳ Обрабатываю ваш вопрос...")
    
    try:
        # Запрашиваем ответ у YandexGPT
        answer = ask_yandex_gpt(question)
        
        user_id = message.from_user.id
        current_q = user_results.get(user_id, {}).get("current_question", 0)
        
        # Определяем, на каком этапе мы находимся
        if current_q == 2:
            # Мы на промежуточном экране, возвращаемся к нему
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Вернуться", callback_data="continue_quiz")]
            ])
            await state.set_state(QuizState.waiting_intermediate)
        else:
            # Обычный вопрос GPT
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="В начало", callback_data="start_quiz")]
            ])
            await state.clear()
        
        await processing_msg.edit_text(
            f"❓ Ваш вопрос: {question}\n\n"
            f"🤖 Ответ YandexGPT:\n{answer}",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Ошибка при обращении к YandexGPT: {e}")
        user_id = message.from_user.id
        current_q = user_results.get(user_id, {}).get("current_question", 0)
        
        if current_q == 2:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Вернуться", callback_data="continue_quiz")]
            ])
            await state.set_state(QuizState.waiting_intermediate)
        else:
            keyboard = get_start_keyboard()
            await state.clear()
        
        await processing_msg.edit_text(
            "❌ Произошла ошибка при обращении к YandexGPT. Попробуйте позже.",
            reply_markup=keyboard
        )


@dp.message()
async def handle_other_messages(message: types.Message):
    """Обработка прочих сообщений"""
    await message.answer(
        "Используйте команду /start для начала работы с ботом.",
        reply_markup=get_start_keyboard()
    )


async def main():
    """Главная функция запуска бота"""
    logger.info("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
