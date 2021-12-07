import time

import logging
import os

import requests
from requests import RequestException
from dotenv import load_dotenv
from telegram import Bot
from http import HTTPStatus

from logging.handlers import RotatingFileHandler

load_dotenv()

logging.basicConfig(level=logging.DEBUG,
                    encoding='utf-8',
                    filename='main.log',
                    filemode='a',
                    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    'my_logger.log', maxBytes=50000000, backupCount=5
)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение отправлено')
    except Exception as error:
        logging.error(f'Сообщение не отправлено {error}')


def get_api_answer(current_timestamp):
    """Возвращаем ответ API, преобразовав его к типам данных Python."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except ValueError:
        logging.error('ENDPOINT недоступен')
    if homework_statuses.status_code != HTTPStatus.OK:
        error_message = 'Ошибка Request'
        logging.error(error_message)
        raise RequestException(error_message)
    try:
        response = homework_statuses.json()
    except Exception as error:
        logging.error(f'Нет ожидаемого ответа сервера {error}')
    return response


def check_response(response):
    """
    Проверяет ответ API на корректность.
    В случае успеха, выводит список домашних работ.
    """
    if not isinstance(response, dict):
        error_message = 'Не верный тип ответа API'
        logging.error(error_message)
        raise TypeError(error_message)
    if 'homeworks' not in response:
        error_message = 'Ключ homeworks отсутствует'
        logging.error(error_message)
        raise KeyError(error_message)
    if len(response) == 0:
        error_message = 'Пустой список домашних работ'
        logging.error(error_message)
        raise ValueError(error_message)
    homeworks = response.get('homeworks')
    return homeworks[0]


def parse_status(homework):
    """Возвращает статус домашней работы."""
    if 'homework_name' not in homework:
        error_message = 'Ключ homework_name отсутствует'
        logging.error(error_message)
        raise KeyError(error_message)
    if 'status' not in homework:
        error_message = 'Ключ status отсутствует'
        logging.error(error_message)
        raise KeyError(error_message)
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None or homework_status is None:
        return 'Работа не сдана на проверку'
    if homework_status not in HOMEWORK_STATUSES:
        error_message = 'Неизвестный статус домашней работы'
        logging.error(error_message)
        raise Exception(error_message)
    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return not (
        not PRACTICUM_TOKEN
        or not TELEGRAM_TOKEN
        or not TELEGRAM_CHAT_ID
    )


def main():
    """Основная логика работы бота."""
    print(check_tokens())
    if not check_tokens():
        error_message = 'Токены недоступны'
        logging.error(error_message)
        raise Exception(error_message)
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 0  # int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            if response:
                homework = check_response(response)
                logger.info('Есть новости')
                message = parse_status(homework)
                send_message(bot, message)
            current_timestamp = response.get('current_date')
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
