import os
import logging
import time
import sys
from http import HTTPStatus

import requests
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
    """Отпраляет пользователю сообщение."""
    bot.send_message(TELEGRAM_CHAT_ID, message)
    if message is None:
        raise ValueError('Сообщение не может быть пустым')

def get_api_answer(current_timestamp):
    """Получается ответ от api."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response is requests.ConnectionError:
        raise requests.ConnectionError('Не удалось соединиться')
    if response.status_code != HTTPStatus.OK:
        raise ValueError('Ответ API не OK')
    return response.json()


def check_response(response):
    """Проверяет ответ api."""
    if type(response) != dict:
        raise TypeError('Ответ пришёл не в виде словаря')
    homeworks = response['homeworks']
    if 'homeworks' not in response:
        raise ValueError('В словаре нет homeworks')
    if 'current_date' not in response:
        raise ValueError('В данных нет даты')
    if type(homeworks) != list:
        raise TypeError('Список домашек не в виде списка')
    logger.debug('Ответ сервера успешно прошел проверку')
    return homeworks


def parse_status(homework):
    """Узнаёт статус домашней работы."""
    if type(homework) != dict:
        raise TypeError('Данные о домашке не в виде словаря')
    homework_name = homework['homework_name']
    if 'homework_name' not in homework:
        raise ValueError('Нет названия домашки')
    homework_status = homework['status']
    if 'status' not in homework:
        raise ValueError('В данных нет статуса')
    if homework_status in HOMEWORK_STATUSES:
        logging.info('Статус домашней работы захвачен, капитан')
        verdict = HOMEWORK_STATUSES[homework_status]
    else:
        raise ValueError('Неизвестный статус')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет наличие необходимых токенов."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True


def main():
    """Основная логика работы бота."""
    is_tokens_valid = check_tokens()
    if is_tokens_valid:
        logger.debug('Все токены на месте')
    else:
        logger.critical('Отсутствует токен')
        raise ValueError('Отсутствуют токены')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    last_status = ''
    while True:
        try:
            api_response = get_api_answer(current_timestamp)
            response = api_response
            checked_response = check_response(response)
            parsed_status = parse_status(checked_response[0])
            status = checked_response[0]['status']
            if status != last_status:
                send_message(bot, parsed_status)
                logger.info('Сообщение с новым статусом отправлено')
            else:
                logger.debug('Нет обновлений статуса')
            current_timestamp = response['current_date']
            last_status = status
            logger.info('Записан текущий статус проверки домашки')
        except IndexError:
            logger.info('Нет домашек')
        except ValueError:
            logger.error('Ошибка значения, проверьте ключи')
        except TypeError:
            logger.error('Что-то преедаётся в неверном типе')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        finally: 
            time.sleep(RETRY_TIME)

if __name__ == '__main__':
    main()
