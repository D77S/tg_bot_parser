"""Docstring."""
from datetime import datetime, timedelta, time
from logging import (error,
                     info,
                     basicConfig,
                     INFO,
                     StreamHandler,
                     disable,
                     critical,
                     exception)
from os import getenv
from requests import Response, get, session
from sys import exit
from time import sleep
from telegram import Bot
from bs4 import BeautifulSoup, ResultSet, element, Tag
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
from pathlib import Path
from tenacity import (
    Retrying,
    # RetryError,
    stop_after_attempt,
    wait_exponential
)

#  !!!!!!!!!!!!!!!!!!!!
TG_ON: bool = True
LOG_ON: bool = False
#  !!!!!!!!!!!!!!!!!!!


def get_response(url):
    """."""
    response = get(url, timeout=30)
    response.raise_for_status()
    response.encoding = 'utf-8'
    return response


def site1(from_server: Response):  # noqa
    """."""
    # Список интересующих констант данного сайта
    ITEMS_OF_INTEREST_NAMES = [  # noqa
        str(getenv('SITE12_STR1')),
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

    data_out = ''
    if all_depts_vacs == {}:
        return data_out
    for key, value in all_depts_vacs.items():
        data_out += ' ' + getenv('SITE12_STR3') + ': ' + key + '\n'
        for vac in value:
            data_out += '  ' + getenv('SITE12_STR4') + ': ' + '\n'
            for key2, value2 in vac.items():
                data_out += '   ' + key2 + ': ' + value2 + '\n'

    return data_out


def site2(from_server: Response):  # noqa
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


def site3(from_server: Response):  # noqa
    """."""
    soup3 = BeautifulSoup(from_server.text, features='lxml')
    temp3_1 = soup3.find(name='select', attrs={'title': getenv('SITE3_STR1')})  # noqa
    return temp3_1.find().text  # type: ignore


def startup(SITES_ARRAY):
    """."""

    results_storage = {}
    for item in SITES_ARRAY:
        from_server = get_response(item[3])
        start_item = item[2](from_server)
        now_moment = datetime.now().astimezone()  # noqa
        results_storage[item[1]] = {
            'moment': now_moment,
            'data': start_item,
            'counter': 1,
            'counter_erase': now_moment
        }
    return results_storage


def site33(TG_ON, bot: Bot, CHAT_ID, item):
    """Выполняет действия, к-е надо сделать по обнаружении
    изменения по сайт3."""
    MAIN_URL = getenv('SITE3_URL')
    USER1_EMAIL = getenv('SITE3_USER1_EMAIL')
    USER1_PASS = getenv('SITE3_USER1_PASS')
    post_data = {
        'Login': USER1_EMAIL,
        'Password': USER1_PASS,
        'action': 'UserLogin',
        'view': 'MainPage',
        'RegisterButton': 'Вход'
    }
    curr_session = session()
    #  логинимся на site3
    try:
        response = curr_session.post(url=MAIN_URL, data=post_data)
    except Exception:
        error_msg = f'Ахтунг, ошибка по ответу сайта {item[1]} при залогинивании, пытаемся ещё'  # noqa
        if TG_ON:
            bot.send_message(CHAT_ID, error_msg)
        error(error_msg)
    #  получаем крайний м-бросок
    response = curr_session.get(url=MAIN_URL)
    soup = BeautifulSoup(response.text, features='lxml')
    mb_table: Tag = soup.find(name='td', string='Марш-бросок').parent.parent  # noqa
    curr_mb_link_part: str = str(mb_table.find_all(name='a')[1].get('href'))

    counter_command = 0
    init_moment = datetime.now().astimezone()
    now_moment = init_moment

    while counter_command < 1 or now_moment.time() < (init_moment.time() + timedelta(hours=23)):  # Повторяем запрос, пока не вернется, что есть хотя бы одна команда уже чья-то, или прошло 23ч  # noqa
        params = {
            'RaidId': curr_mb_link_part.split('=')[1],
        }
        response_currmmb = curr_session.get(url=MAIN_URL, params=params)
        soup = BeautifulSoup(response_currmmb.text, features='lxml')
        try:
            temp3: Tag = soup.find(string='Участники').parent.parent.parent
            temp4 = temp3.find_all(name='a')[0]
            counter_command = int(temp4.get('name'))
        except Exception:
            counter_command = 0
        now_moment = datetime.now().astimezone()
        sleep(3)

    post_data = {
        'action': 'RegisterNewTeam',
        'view': 'ViewRaidTeams',
        'DistanceId': '0',
        'RaidId': curr_mb_link_part.split('=')[1],
        'TeamNum': 'Номер команды'
    }
    response_currcommand = curr_session.post(url=MAIN_URL, data=post_data)
    soup = BeautifulSoup(response_currcommand.text, features='lxml')
    dist_id = str(soup.find(name='select', attrs={'name': 'DistanceId'}).find(name='option').get('value'))  # noqa
    post_data = {
        'action': 'AddTeam',
        'TeamId': '0',
        'RaidId': curr_mb_link_part.split('=')[1],
        'HideTeamUserId': '0',
        'UserOutLevelId': '0',
        'UserNotInLevelPointId': '0',
        'UserId': '0',
        'NewTeamUserEmail': USER1_EMAIL,
        'TeamNum': '0',
        'DistanceId': dist_id,
        'TeamName': 'aсhtung',
        'TeamUseGPS': 'on',
        'TeamMapsCount': '2',
        'Confirmation': 'on',
        'view': 'ViewTeamData'
    }
    params = {
        'RaidId': curr_mb_link_part.split('=')[1],
    }
    # Главный запрос!!!!!!!!!!!!
    try:
        response_currcommand = curr_session.post(url=MAIN_URL, data=post_data, params=params)  # noqa
    except Exception:
        error_msg = f'Ахтунг, ошибка в {item[1]} при попытке реги команды.'  # noqa
        if TG_ON:
            bot.send_message(CHAT_ID, error_msg)
        error(error_msg)
    if response_currcommand.status_code == 200:
        msg = f'Команда зарегана. И перед её регой было других команд: {counter_command}'  # noqa
        if TG_ON:
            bot.send_message(CHAT_ID, msg)
        error(msg)
    else:
        msg = f'Команду зарегать почему-то не удалось, дальше вручную только.'  # noqa
        if TG_ON:
            bot.send_message(CHAT_ID, msg)
        error(msg)
    return None


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
        maxBytes=10 ** 5,
        backupCount=3,
        # encoding='utf-8'
    )
    basicConfig(
        level=INFO,
        format=LOG_FORMAT,
        handlers=(
            rotating_handler, StreamHandler()
        ),
        datefmt=DT_FORMAT,
    )


def main():
    """."""
    load_dotenv()
    configure_logging()
    if LOG_ON is False:
        disable(INFO)
    try:
        if not all([
            getenv('BOT_TOKEN'),
            getenv('CHAT_ID')
        ]):
            raise Exception
    except Exception:
        error_msg = 'Критическая ошибка, отсутствуют две переменные окружения по тг-боту, выход'  # noqa
        error(error_msg)
        exit()

    CHAT_ID = getenv('CHAT_ID')
    if TG_ON:
        bot = Bot(token=getenv('BOT_TOKEN'))
    critical('Парсер запущен')
    if TG_ON:
        bot.send_message(CHAT_ID, 'Парсер запущен')
    critical('Инициализация серверной части')
    if TG_ON:
        bot.send_message(CHAT_ID, 'Инициализация серверной части')

    try:
        if not all([
            getenv('SITE1_URL'),
            getenv('SITE1_LABEL'),
            getenv('SITE1_DELTA_H'),
            getenv('SITE1_DELTA_M'),
            getenv('SITE1_DELTA_S'),
            getenv('SITE1_NIGHT'),
            getenv('SITE1_ALARM'),
            getenv('SITE1_SWITCH'),
            getenv('SITE2_URL'),
            getenv('SITE2_LABEL'),
            getenv('SITE2_DELTA_H'),
            getenv('SITE2_DELTA_M'),
            getenv('SITE2_DELTA_S'),
            getenv('SITE2_NIGHT'),
            getenv('SITE2_ALARM'),
            getenv('SITE2_SWITCH'),
            getenv('SITE12_STR1'),
            # getenv('SITE12_STR2'),
            getenv('SITE12_STR3'),
            getenv('SITE12_STR4'),
            getenv('SITE3_URL'),
            getenv('SITE3_LABEL'),
            getenv('SITE3_DELTA_S'),
            getenv('SITE3_DELTA_M'),
            getenv('SITE3_DELTA_S'),
            getenv('SITE3_NIGHT'),
            getenv('SITE3_ALARM'),
            getenv('SITE3_SWITCH'),
            getenv('SITE3_STR1'),
            getenv('SITE3_USER1_EMAIL'),
            getenv('SITE3_USER1_PASS'),
            getenv('SITE3_USER2_EMAIL'),
            getenv('SITE3_USER2_PASS'),

        ]):
            raise Exception
    except Exception:
        error_msg = 'Критическая ошибка, отсутствуют какие-то переменные окружения, выход'  # noqa
        if TG_ON:
            bot.send_message(CHAT_ID, error_msg)
        error(error_msg)
        exit()

    SITES_ARRAY = [
        [
            #  [0]
            timedelta(
                hours=int(getenv('SITE1_DELTA_H')),  # периодичность работы с сайт1  # noqa
                minutes=int(getenv('SITE1_DELTA_M')),  # периодичность работы с сайт1  # noqa
                seconds=int(getenv('SITE1_DELTA_S'))  # периодичность работы с сайт1  # noqa
            ),
            #  [1]
            getenv('SITE1_LABEL'),  # лабел сайт1
            #  [2]
            site1,  # функция работы по сайт1
            #  [3]
            getenv('SITE1_URL'),  # URL сайт1
            #  [4]
            getenv('SITE1_NIGHT').lower() == 'true',  # надо ли работать с сайт1 ночью  # noqa
            #  [5]
            getenv('SITE1_SWITCH').lower() == 'true',  # надо ли вообще работать с сайт1  # noqa
            #  [6]
            getenv('SITE1_ALARM').lower() == 'true',  # надо ли что-то делать по обнаружении изменений сайт1, кроме сигнала в бот  # noqa
            #  [7]
            None,
        ],
        [
            #  [0]
            timedelta(
                hours=int(getenv('SITE2_DELTA_H')),  # периодичность работы с сайт2  # noqa
                minutes=int(getenv('SITE2_DELTA_M')),  # периодичность работы с сайт2  # noqa
                seconds=int(getenv('SITE2_DELTA_S'))  # периодичность работы с сайт2  # noqa
            ),
            # [1]
            getenv('SITE2_LABEL'),  # лабел сайт2
            #  [2]
            site2,  # функция работы по сайт2
            #  [3]
            getenv('SITE2_URL'),  # URL сайт2
            #  [4]
            getenv('SITE2_NIGHT').lower() == 'true',  # надо ли работать с сайт2 ночью  # noqa
            #  [5]
            getenv('SITE2_SWITCH').lower() == 'true',  # надо ли вообще работать с сайт2  # noqa
            #  [6]
            getenv('SITE2_ALARM').lower() == 'true',  # надо ли что-то делать по обнаружении изменений сайт2, кроме сигнала в бот  # noqa
            #  [7]
            None,
        ],
        [
            #  [0]
            timedelta(
                hours=int(getenv('SITE3_DELTA_H')),  # периодичность работы с сайт3  # noqa
                minutes=int(getenv('SITE3_DELTA_M')),  # периодичность работы с сайт3  # noqa
                seconds=int(getenv('SITE3_DELTA_S'))  # периодичность работы с сайт3  # noqa
            ),
            #  [1]
            getenv('SITE3_LABEL'),  # лабел сайт3
            #  [2]
            site3,  # функция работы по сайт3
            #  [3]
            getenv('SITE3_URL'),  # URL сайт3
            #  [4]
            getenv('SITE3_NIGHT').lower() == 'true',  # надо ли работать с сайт3 ночью  # noqa
            #  [5]
            getenv('SITE3_SWITCH').lower() == 'true',  # надо ли вообще работать с сайт3  # noqa
            #  [6]
            getenv('SITE3_ALARM').lower() == 'true',  # надо ли что-то делать по обнаружении изменений сайт3, кроме сигнала в бот  # noqa
            #  [7]
            site33,
        ],
    ]

    try:
        results_storage = startup(SITES_ARRAY)
    except Exception:
        error_msg = 'Ошибка инициализации, по ответу какого-то из всех сайтов'  # noqa
        if TG_ON:
            bot.send_message(CHAT_ID, error_msg)
        error(error_msg)
        exit()

    msg = 'Старт бесконечного цикла серверной части'
    critical(msg)
    if TG_ON:
        bot.send_message(CHAT_ID, msg)

    while True:
        for item in SITES_ARRAY:

            sleep(5)
            now_moment = datetime.now().astimezone()
            info(f'Очередной момент времени {now_moment=}')

            #  если текущий сайт вообще пока не надо проверять - переходим к следующему  # noqa
            if item[5] is False:
                continue

            #  если выходной день или ночное время,
            if (5 <= now_moment.weekday() <= 6) or (time(9, 0, 0) <= now_moment.time() <= time(18, 0, 0)):  # noqa
                is_night_or_weekend = True
            else:
                is_night_or_weekend = False

            #  ... и текущий сайт не надо проверять ночью или в выходной, то переходим к следующему  # noqa
            if is_night_or_weekend and item[4] is False:
                continue

            info(f'Начало работы с сайтом {item[1]}, смотрим, не устарели ли ещё результаты')  # noqa

            if now_moment >= results_storage[item[1]]['moment'] + item[0]:  # noqa
                info(f'Устарели, начаты действия с сайтом {item[1]}')
                # подгрузка из буфера предыдущих результатов парсинга сайта
                result_old_data = results_storage[item[1]]['data']

                try:
                    for attempt in Retrying(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=5)):  # noqa
                        with attempt:
                            info(f'Начаты попытки получить ответ сайта {item[1]}')  # noqa
                            from_server = get_response(item[3])
                except Exception:
                    error_msg = f'Ахтунг, ошибка по ответу сайта {item[1]}, переходим к следующему'  # noqa
                    if TG_ON:
                        bot.send_message(CHAT_ID, error_msg)
                    error(error_msg)
                    results_storage[item[1]]['moment'] = now_moment
                    continue

                info(f'Ответ сайта {item[1]} успешен')

                try:
                    result_new_data = item[2](from_server)
                except Exception:
                    error_msg = f'Ахтунг, ошибка распарсинга сайта {item[1]}, переходим к следующему'  # noqa
                    if TG_ON:
                        bot.send_message(CHAT_ID, error_msg)
                    exception(error_msg)
                    results_storage[item[1]]['moment'] = now_moment
                    continue
                else:
                    info(f'Распарсинг сайта {item[1]} успешен')
                    data_out = '\n'.join([
                        f'Сайт {item[1]} только что должен был быть проверен, и был успешно проверен и распарсен.',  # noqa
                        'Результат предыдущий:',
                        result_old_data,
                        'Результат крайний:',
                        result_new_data,
                    ])
                    if result_new_data == result_old_data:
                        data_out += '\n Изменений нет.'
                        info(f'По сайту {item[1]} изменений нет')
                        results_storage[item[1]]['counter'] += 1
                    else:
                        data_out += '\n Есть изменения!'
                        if TG_ON:
                            bot.send_message(CHAT_ID, data_out)
                        info(f'По сайту {item[1]} изменения есть')
                        results_storage[item[1]]['data'] = result_new_data
                        #  Если поднят соотв.флаг, то надо выполнить то, что по обнаружении изменений  # noqa
                        if item[6]:
                            item[7](TG_ON=TG_ON, bot=bot, CHAT_ID=CHAT_ID, item=item)  # noqa
                        # По сайт3, при изменениях его далее отслеживать не надо, до след.перезапуска программы  # noqa
                        if item[1] == getenv('SITE3_LABEL'):
                            item[5] = False

                    # Если site3 проверяется уже непрерывно сутки, и изменений нет, доложим об этом  # noqa
                    if item[1] == getenv('SITE3_LABEL') and now_moment >= results_storage[item[1]]['counter_erase'] + timedelta(hours=24):  # noqa
                        counter = results_storage[item[1]]['counter']
                        msg = f'По сайту {item[1]} за последние сутки изменений нет, успешно загружен и распарсен {counter} раз'  # noqa
                        if TG_ON:
                            bot.send_message(CHAT_ID, msg)
                        info(msg)
                        results_storage[item[1]]['counter_erase'] = now_moment
                        results_storage[item[1]]['counter'] = 0

                    results_storage[item[1]]['moment'] = now_moment
            else:
                info('Ещё не устарели')


if __name__ == '__main__':
    main()
