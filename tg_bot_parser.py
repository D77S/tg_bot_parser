"""Docstring."""
import datetime
import logging
import os
import requests
import sys
import time
import telegram
from bs4 import BeautifulSoup, ResultSet, element
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
from pathlib import Path
from tenacity import (
    Retrying,
    # RetryError,
    stop_after_attempt,
    wait_exponential
)


# class TokensException(Exception):
#     """Кастомное исключение по отсутствию токенов."""
#     def __init__(self, message=None):
#         super().__init__(message)
#         print(message)


def get_response(url):
    """."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    response.encoding = 'utf-8'
    return response


def convert_site1(data_in: dict[str, list[dict[str, str]]]) -> str:  # noqa
    """."""
    data_out = ''
    if data_in == {}:
        return data_out
    for key, value in data_in.items():
        data_out += ' ' + os.getenv('SITE12_STR3') + ': ' + key + '\n'
        for vac in value:
            data_out += '  ' + os.getenv('SITE12_STR4') + ': ' + '\n'
            for key2, value2 in vac.items():
                data_out += '   ' + key2 + ': ' + value2 + '\n'
    return data_out


def site1(from_server: requests.Response):  # noqa
    """."""
    # Список интересующих констант данного сайта
    ITEMS_OF_INTEREST_NAMES = [  # noqa
        str(os.getenv('SITE12_STR1')),
        str(os.getenv('SITE12_STR2'))
    ]
    all_depts_vacs = {}
    soup2 = BeautifulSoup(from_server.text, features='lxml')
    temp2_1: element.Tag = soup2.find(name='div', attrs={'class': 'VacanciesSection VacanciesSpoilers SpoilerList _two-cols'})  # type: ignore # noqa
    temp2_2: ResultSet = temp2_1.find_all(name='div', attrs={'class': 'Spoiler js-spoiler'})  # type: ignore # noqa
    for dept in temp2_2:
        curr_dept_name: element.Tag = dept.find(name='div', attrs={'class': 'Spoiler__Title'})  # noqa
        items = curr_dept_name.find_all(name='span')
        for item in items:
            item.decompose()
        curr_dept_name_text = curr_dept_name.text.strip()
        curr_dept_vacancies_list = []
        curr_dept_vacs = dept.find_all(name='div', attrs={'class': 'VacanciesSpoilerBlock'})  # noqa
        for vacancy in curr_dept_vacs:
            curr_vac_div = vacancy.find(name='div', attrs={'class': 'VacanciesSpoilerBlock__Text'})  # noqa
            curr_vac_div = curr_vac_div.text.strip()
            curr_vac_pos = vacancy.find(name='div', attrs={'class': 'VacanciesSpoilerBlock__Title'})  # noqa
            curr_vac_pos = curr_vac_pos.text.strip()
            curr_vac_pub_date_raw = vacancy.find(name='div', attrs={'class': 'VacanciesSpoilerBlock__Caption'})  # noqa
            items = curr_vac_pub_date_raw.find_all(name='span')
            for item in items:
                item.decompose()
            curr_vac_pub_date = curr_vac_pub_date_raw.text.strip()
            curr_dept_vacancies_list.append({
                'division': curr_vac_div,
                'position': curr_vac_pos,
                'pub_date': curr_vac_pub_date,
            })
        if curr_dept_name_text in ITEMS_OF_INTEREST_NAMES:
            all_depts_vacs[curr_dept_name_text] = curr_dept_vacancies_list

    return convert_site1(all_depts_vacs)


def site2(from_server: requests.Response):  # noqa
    """."""
    soup4 = BeautifulSoup(from_server.text, features='lxml')
    temp4_1 = soup4.find(name='div', attrs={'class': 'VacanciesResultsTable__Row _heading'})  # noqa
    temp4_2 = temp4_1.next_siblings
    temp4_3 = None
    for item in temp4_2:
        if not (isinstance(item, element.Tag)):
            continue
        temp4_3 = item
        break
    order = temp4_3.find(name='div', attrs={'data-title': 'Приказ об открытии конкурса'})  # noqa
    order = order.text.strip()
    dept = temp4_3.find(name='div', attrs={'data-title': 'Департаменты'})  # noqa
    dept = dept.text.strip()
    pub_date = temp4_3.find(name='div', attrs={'data-title': 'Дата опубликования:'})  # noqa
    pub_date = pub_date.text.strip()

    return ','.join([order, dept, pub_date])


def site3(from_server: requests.Response):  # noqa
    """."""
    soup3 = BeautifulSoup(from_server.text, features='lxml')
    temp3_1 = soup3.find(name='select', attrs={'title': os.getenv('SITE3_STR1')})  # noqa
    return temp3_1.find().text  # type: ignore


def startup(SITES_ARRAY):
    """."""

    results_storage = {}
    for item in SITES_ARRAY:
        from_server = get_response(item[3])
        start_item = item[2](from_server)
        now_moment = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))  # noqa
        results_storage[item[1]] = {
            'moment': now_moment,
            'data': start_item
        }
    return results_storage


def configure_logging():
    """."""
    LOG_FORMAT = '"%(asctime)s - [%(levelname)s] - %(message)s"'
    DT_FORMAT = '%d.%m.%Y %H:%M:%S'
    BASE_DIR = Path(__file__).parent
    log_dir = BASE_DIR / 'logs'
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / 'parser.log'
    rotating_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 ** 6,
        backupCount=10,
        # encoding='utf-8'
    )
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=(
            rotating_handler, logging.StreamHandler()
        ),
        datefmt=DT_FORMAT,
    )


def main():
    """."""
    load_dotenv()
    configure_logging()
    info_msg = 'Парсер запущен!'
    logging.info(info_msg)
    try:
        if not all([
            os.getenv('BOT_TOKEN'),
            os.getenv('CHAT_ID')
        ]):
            raise Exception
    except Exception:
        error_msg = 'Ошибка, отсутствуют две переменные окружения по тг-боту'
        logging.error(error_msg)
        sys.exit()

    CHAT_ID = os.getenv('CHAT_ID')
    bot = telegram.Bot(token=os.getenv('BOT_TOKEN'))
    info_msg = 'Инициализация серверной части'
    bot.send_message(CHAT_ID, info_msg)
    logging.info(info_msg)

    try:
        if not all([
            os.getenv('SITE1_URL'),
            os.getenv('SITE1_LABEL'),
            os.getenv('SITE1_DELTA_H'),
            os.getenv('SITE1_DELTA_M'),
            os.getenv('SITE1_DELTA_S'),
            os.getenv('SITE1_NIGHT'),
            os.getenv('SITE2_URL'),
            os.getenv('SITE2_LABEL'),
            os.getenv('SITE2_DELTA_H'),
            os.getenv('SITE2_DELTA_M'),
            os.getenv('SITE2_DELTA_S'),
            os.getenv('SITE2_NIGHT'),
            os.getenv('SITE12_STR1'),
            os.getenv('SITE12_STR2'),
            os.getenv('SITE12_STR3'),
            os.getenv('SITE12_STR4'),
            os.getenv('SITE3_URL'),
            os.getenv('SITE3_LABEL'),
            os.getenv('SITE3_DELTA_S'),
            os.getenv('SITE3_DELTA_M'),
            os.getenv('SITE3_DELTA_S'),
            os.getenv('SITE3_NIGHT'),
            os.getenv('SITE3_STR1'),
        ]):
            raise Exception
    except Exception:
        error_msg = 'Ошибка, отсутствуют переменные окружения'
        bot.send_message(CHAT_ID, error_msg)
        logging.error(error_msg)
        sys.exit()

    SITES_ARRAY = [
        [
            datetime.timedelta(
                hours=int(os.getenv('SITE1_DELTA_H')),  # период проверки сайта1  # noqa
                minutes=int(os.getenv('SITE1_DELTA_M')),  # период проверки сайта1  # noqa
                seconds=int(os.getenv('SITE1_DELTA_S'))  # период проверки сайта1  # noqa
            ),
            os.getenv('SITE1_LABEL'),  # лабел сайта1
            site1,  # функция распарсивания по сайту1
            os.getenv('SITE1_URL'),  # URL сайта1
            os.getenv('SITE1_NIGHT').lower() == 'true',  # надо ли парсить сайт1 ночью  # noqa
            ],
        [
            datetime.timedelta(
                hours=int(os.getenv('SITE2_DELTA_H')),  # период проверки сайта2  # noqa
                minutes=int(os.getenv('SITE2_DELTA_M')),  # период проверки сайта2  # noqa
                seconds=int(os.getenv('SITE2_DELTA_S'))  # период проверки сайта2  # noqa
            ),
            os.getenv('SITE2_LABEL'),  # лабел сайта2
            site2,  # функция распарсивания по сайту2
            os.getenv('SITE2_URL'),  # URL сайта2
            os.getenv('SITE2_NIGHT').lower() == 'true',  # надо ли парсить сайт2 ночью  # noqa
            ],
        # [
        #    datetime.timedelta(
        #        hours=int(os.getenv('SITE3_DELTA_H')),  # период проверки сайта3  # noqa
        #        minutes=int(os.getenv('SITE3_DELTA_M')),  # период проверки сайта3  # noqa
        #        seconds=int(os.getenv('SITE3_DELTA_S'))  # период проверки сайта3  # noqa
        #    ),
        #    os.getenv('SITE3_LABEL'),  # лабел сайта3
        #    site3,  # функция распарсивания по сайту3
        #    os.getenv('SITE3_URL'),  # URL сайта3
        #    os.getenv('SITE3_NIGHT').lower() == 'true',  # надо ли парсить сайт3 ночью  # noqa
        # ],
    ]

    try:
        results_storage = startup(SITES_ARRAY)
    except Exception:
        error_msg = 'Ошибка инициализации, по ответу какого-то из всех сайтов'  # noqa
        logging.error(error_msg)
        sys.exit()

    msg = 'Старт бесконечного цикла серверной части'
    logging.info(msg)
    bot.send_message(CHAT_ID, msg)

    while True:
        for item in SITES_ARRAY:
            now_moment = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))  # noqa

            if (5 <= now_moment.weekday() <= 6 or
                datetime.time(9, 0, 0) <= now_moment.time() <= datetime.time(18, 0, 0)):  # noqa
                is_night_or_weekend = True
            else:
                is_night_or_weekend = False
            if is_night_or_weekend and not item[4]:
                time.sleep(1)
                continue
            # logging.info(f'Очередной момент времени {now_moment=}')
            if now_moment >= results_storage[item[1]]['moment'] + item[0]:  # noqa
                logging.info(f'Начаты действия с сайтом {item[1]}')
                result_old_data = results_storage[item[1]]['data']

                try:
                    for attempt in Retrying(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=5)):  # noqa
                        with attempt:
                            logging.info(f'Начаты попытки получить ответ сервера сайта {item[1]}')  # noqa
                            from_server = get_response(item[3])
                except Exception:
                    error_msg = f'Ошибка по ответу сайта {item[1]}'
                    bot.send_message(CHAT_ID, error_msg)
                    logging.error(error_msg)
                    results_storage[item[1]]['moment'] = now_moment
                    continue

                logging.info(f'Ответ сайта {item[1]} успешен')

                try:
                    result_new_data = item[2](from_server)
                except Exception:
                    error_msg = f'Ошибка распарсинга сайта {item[1]}'
                    bot.send_message(CHAT_ID, error_msg)
                    logging.exception(error_msg)
                    results_storage[item[1]]['moment'] = now_moment
                    continue
                else:
                    logging.info(f'Распарсинг сайта {item[1]} успешен')
                    data_out = '\n'.join([
                        f'{item[1]} проверка прошла.',
                        'Результат предыдущий:',
                        result_old_data,
                        'Результат крайний:',
                        result_new_data,
                    ])
                    if result_new_data == result_old_data:
                        data_out += '\n Изменений нет.'
                        logging.info(f'По сайту {item[1]} изменений нет')
                    else:
                        data_out += '\n Есть изменения!'
                        bot.send_message(CHAT_ID, data_out)
                        logging.info(f'По сайту {item[1]} изменения есть')
                        results_storage[item[1]]['data'] = result_new_data

                    results_storage[item[1]]['moment'] = now_moment

            time.sleep(1)


if __name__ == '__main__':
    main()
