import os
import logging
import time
import sys
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()


class ApiAnswerError(Exception):
    """Ошибка ответа от API."""

    pass


class UnaviableApiError(Exception):
    """Ошибка недоступности API."""

    pass


class CantSendMessageError(Exception):
    """Ошибка отправки сообщения."""

    pass


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
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception:
        raise CantSendMessageError('Не удалось отправить сообщение')


def get_api_answer(current_timestamp):
    """Получается ответ от api."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception:
        raise UnaviableApiError('Эндпоинт недоступен')
    if response is requests.ConnectionError:
        raise requests.ConnectionError('Не удалось соединиться')
    if response.status_code != HTTPStatus.OK:
        logger.info(response)
        raise ApiAnswerError(f'Ответ API не OK: {response.status_code}.'
                             f'Использовалось: {ENDPOINT}, {HEADERS}, {params}'
                             )
    return response.json()


def check_response(response):
    """Проверяет ответ api."""
    if not isinstance(response, dict):
        raise TypeError('Ответ пришёл не в виде словаря')
    if 'homeworks' not in response:
        raise KeyError('В словаре нет homeworks')
    homeworks = response['homeworks']
    if 'current_date' not in response:
        raise KeyError('В данных нет даты')
    if not isinstance(homeworks, list):
        raise TypeError('Список домашек не в виде списка')
    logger.debug('Ответ сервера успешно прошел проверку')
    return homeworks


def parse_status(homework):
    """Узнаёт статус домашней работы."""
    if not isinstance(homework, dict):
        raise TypeError('Данные о домашке не в виде словаря')
    if 'homework_name' not in homework:
        raise KeyError('Нет названия домашки')
    homework_name = homework['homework_name']
    if 'status' not in homework:
        raise KeyError('В данных нет статуса')
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        raise KeyError(f'Неизвестный статус, {homework_status}')
    logging.info('Статус домашней работы захвачен, капитан')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет наличие необходимых токенов."""
    return PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID


def main():
    """Основная логика работы бота."""
    is_tokens_valid = check_tokens()
    if not is_tokens_valid:
        logger.critical('Отсутствует токен')
        raise ValueError('Отсутствуют токены')
    logger.debug('Все токены на месте')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    last_status = ''
    while True:
        try:
            api_response = get_api_answer(current_timestamp)
            checked_response = check_response(api_response)
            parsed_status = parse_status(checked_response[0])
            status = checked_response[0]['status']
            if status != last_status:
                send_message(bot, parsed_status)
                logger.info('Сообщение с новым статусом отправлено')
            else:
                logger.debug('Нет обновлений статуса')
            current_timestamp = api_response['current_date']
            last_status = status
            logger.info('Записан текущий статус проверки домашки')
        except IndexError:
            logger.info('Нет домашек')
        except ValueError as error:
            logger.critical('Неверное значение переменных')
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        except TypeError as error:
            logger.error('Что-то передаётся в неверном типе')
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        except ApiAnswerError as error:
            logger.error('Неверный ответ API')
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        except UnaviableApiError as error:
            logger.error('Эндпоинт недоступен')
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        except CantSendMessageError:
            logger.error('Отправка сообщения не удалась')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
