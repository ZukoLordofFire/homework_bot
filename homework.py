import requests
import os
import logging
import time
import sys

import telegram
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('TOKEN_YP')
TELEGRAM_TOKEN = os.getenv('TOKEN_TG')
TELEGRAM_CHAT_ID = os.getenv('TOKEN_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    text = message
    bot.send_message(TELEGRAM_CHAT_ID, text)


def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        logger.error('API Практикума не отвечает')
        raise ConnectionError()
    return response.json()


def check_response(response):
    homeworks = response['homeworks']
    if type(homeworks) != list:
        logger.error('Тип данных в ответе не соответствует ожидаемому')
        raise ValueError()
    elif homeworks == []:
        logger.debug('Нет домашек для отслеживания статуса')
        raise ValueError('На сервере нет домашек на проверке')
    logger.debug('Ответ сервера успешно прошел проверку')
    return homeworks


def parse_status(homework):
    homework_name = homework['homework_name']
    print(homework_name)
    if homework_name is None:
        logging.error('Не удалось получить данные домашки, homework_name is None')
        return f'Название клада не получено, homework_name is None'
    homework_status = homework['status']
    if homework_status is None:
        logging.error('Не удалось получить данные домашки, homework_status is None')
        return f'Статус клада не получен, homework_status is None'
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
        logging.info('Статус домашней работы захвачен, капитан')
    except Exception as error:
        logging.error(f'Захватывать нечего, там пусто! Быть может мы не вовремя? Ошибка: {error}')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        logger.debug('Все токены на месте, можно работать!')
        return True
    logger.error('Не хватает токенов для работы программы')
    return False


def main():
    """Основная логика работы бота."""

    ...

    is_tokens_valid = check_tokens()
    if not is_tokens_valid:
        print('Выполнение программы прервано')
        logger.error('Выполнение программы прервано из-за отсутствия токена')
        return
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    api_response = get_api_answer(current_timestamp)
    last_status = ''

    ...

    while True:
        try:
            response = api_response
            checked_response = check_response(response)
            parsed_status = parse_status(checked_response[0])
            status = checked_response[0]['status']
            if status != last_status:
                send_message(bot, parsed_status)
                print('Сообщение с новым статусом отправлено')
            current_timestamp = response['current_date']
            last_status = status
            print('Записан текущий статус проверки домашки')
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        else:
            ...


if __name__ == '__main__':
    main()
