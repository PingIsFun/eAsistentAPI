import logging
from dataclasses import dataclass
import datetime
import re
from typing import Callable, TypeVar

import bs4.element
import requests
from bs4 import BeautifulSoup

from structure import EventType, HourTime, Teacher, ClassHour, LimitedClassHour, LimitedHour, \
    LimitedEventHour, WeekData, RequestData, ClassSchedule, LimitedSchedule

PARSED_HOUR_RETURN = tuple[tuple[str, str | None], tuple[str, str], list[str], EventType | None]
LOGGER = logging.getLogger("eAsistentPY-scraper")


def request_ajax(request_data: RequestData) -> requests.Response:
    url = "https://www.easistent.com/urniki/ajax_urnik"

    payload = (f"id_sola={request_data.school_id}"
               f"&id_razred={request_data.class_id}"
               f"&id_profesor={request_data.professor_id}"
               f"&id_dijak={request_data.student_id}"
               f"&id_ucilnica={request_data.classroom_id}"
               f"&teden={request_data.school_week}"
               f"&id_interesna_dejavnost={request_data.interest_activity}")

    headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

    response = requests.request("POST", url, data=payload, headers=headers)

    if response.status_code != 200:
        raise ValueError("An error occurred.")
    return response


def get_html(request_data: RequestData) -> str:
    response = request_ajax(request_data)
    return response.text


def get_week_data(s: str) -> WeekData:
    s = s.strip().split("")
    week = int(s[0])
    date_format = "%d. %m. %Y"
    start_date = datetime.datetime.strptime(s[1], date_format).date()
    end_date = datetime.datetime.strptime(s[2], date_format).date()
    return WeekData(week, start_date, end_date)


def school_start_year() -> int:
    now = datetime.datetime.now().date()
    year = now.year
    if now.month < 7:
        year -= 1
    return year


def set_year(date: datetime.date) -> datetime.date:
    year = school_start_year()
    if date.month < 7:
        year += 1
    return datetime.date(year, date.month, date.day)


def get_day_dates(days: list[bs4.Tag]) -> list[datetime.date]:
    days.pop(0)
    res = []
    date_format = "%d. %m."
    for i in days:
        date = i.select("th > div")[1].text
        date = set_year(datetime.datetime.strptime(date, date_format).date())
        res.append(date)
    return res


def get_hours(hours: list[bs4.Tag]) -> list[HourTime]:
    time_format = "%H:%M"
    res = []
    for i in hours:
        name, time = [x.text.strip() for x in i.select("td > div")]
        start, end = [datetime.datetime.strptime(x, time_format).time() for x in time.split(" - ")]
        res.append(HourTime(name, start, end))
    return res


def parse_hour(data: bs4.Tag) -> PARSED_HOUR_RETURN:
    event = None
    try:
        event = EventType(data.find("img").attrs["title"])
    except AttributeError:
        pass

    if event == EventType.DOGODEK:
        # TODO
        text1 = data.select("table > tbody > tr > td")[0].text.strip()
        data = list(data)
        for x in data:
            if isinstance(x, bs4.Tag):
                data.remove(x)
                break
        description = "".join([x.text for x in data]).strip()
        return (text1, description), None, None, event

    if event == EventType.GOVORILNE_URE:
        data = data.select("table > tbody > tr > td")[0]
        title = data.find(string=True).strip()  # Individualne govorilne ure

        try:
            description = data.select("em")[0].text.strip()
        except IndexError:
            description = None

        data = data.select("span")
        teacher, classroom = [x.strip() for x in data[0].text.split("(")]
        classroom = classroom.removesuffix(")").strip()
        time_format = "%H:%M"
        # start, end = [datetime.datetime.strptime(x, time_format).time() for x in
        #               data[1].text.split(",")[0].strip().split(" - ")]

        return (description, None), (teacher, classroom), None, event

    res = []
    # Row 1 (subject/class name)
    row1_raw = data.select("table > tbody > tr > td")[0]
    span1_raw = row1_raw.find("span")
    span1 = None
    if span1_raw:
        span1 = span1_raw.attrs.get("title")
        span1 = span1.strip() if span1 is not None else None
    res.append((row1_raw.text.strip(), span1))

    divs = data.find_all("div")

    # Row 2 (teacher/(teacher, classroom))
    row2_raw = divs.pop(0)
    title2 = row2_raw.attrs.get("title")
    text2 = row2_raw.text.strip()
    res.append((title2, text2))

    # Row 3 (None/None|Group)
    res.append([])
    if len(divs) > 1:
        groups = [x.text.strip() for x in divs]
        res[2] = groups
    # Event
    res.append(event)
    return tuple(res)


def extract_tag_elements(data: list[bs4.PageElement]) -> list[bs4.Tag]:
    return [x for x in data if isinstance(x, bs4.element.Tag)]


def parse_hour_block(data: bs4.Tag) -> list[PARSED_HOUR_RETURN]:
    data = data.select("td > div")
    res = []
    if len(data) == 0:
        return []
    if len(data) == 1:
        try:
            res.append(parse_hour(data[0]))
        except BaseException as e:
            LOGGER.error("An error occurred while parsing an hour. "
                         "Please report this at https://github.com/PingIsFun/eAsistentAPI/issues.\n"
                         f"Error: {e}\n"
                         f"Hour html: \"{repr(data[0])}\"")
        return res
    main = data[0]
    others = data[1]
    data = extract_tag_elements(list(others.children))
    data.insert(0, main)

    for i in data:
        try:
            res.append(parse_hour(i))
        except BaseException as e:
            LOGGER.error("An error occurred while parsing an hour. "
                         "Please report this at https://github.com/PingIsFun/eAsistentAPI/issues.\n"
                         f"Error: {e}\n"
                         f"Hour html: \"{repr(i)}\"")

    return res


@dataclass
class ParsedData:
    data: list[list[PARSED_HOUR_RETURN]]
    hour_times: list[HourTime]
    dates: list[datetime.date]
    week_data: WeekData


def parse_html(html: str) -> ParsedData:
    soup = BeautifulSoup(html, "html5lib")
    week_data = get_week_data(soup.find(string=True))
    table = soup.select("html > body > table > tbody")[0]
    table = [[y for y in x if not isinstance(y, bs4.element.NavigableString)] for x in table if
             not isinstance(x, bs4.element.NavigableString)]
    dates = get_day_dates(table.pop(0))
    times = get_hours([x.pop(0) for x in table])
    # START MANUPULATE DATA
    # [table.pop(0) for _ in range(4)]
    # table = [x[2:] for x in table]
    # END MANUPULATE DATA
    res = []
    for tr in table:
        row_res = []
        for td in tr:
            row_res.append(parse_hour_block(td))
            # exit()
        res.append(row_res)
    return ParsedData(res, times, dates, week_data)


def parse_limited_hour(hour_data: PARSED_HOUR_RETURN) -> LimitedHour:
    event = hour_data[3]
    if event == EventType.DOGODEK:
        name, description = hour_data[0]
        return LimitedEventHour(teacher=Teacher("", ""), group=[], event=event, class_name="", name=name,
                                description=description)
    teacher = Teacher(*hour_data[1])
    group = hour_data[2]
    class_name = hour_data[0][0]
    return LimitedHour(teacher, group, event, class_name)


def parse_class_hour(hour_data: PARSED_HOUR_RETURN) -> ClassHour:
    event = hour_data[3]
    if event == EventType.DOGODEK:
        name, description = hour_data[0]
        return LimitedClassHour(teacher=Teacher("", ""), group=[], event=event, subject="", subject_short="",
                                classroom="",
                                name=name, description=description)
    teacher_full = hour_data[1][0]
    teacher_short, classroom = [x.strip() for x in hour_data[1][1].split(",")]
    teacher = Teacher(teacher_full, teacher_short)
    group = hour_data[2]
    subject_short, subject = hour_data[0]
    return ClassHour(teacher, group, event, subject, subject_short, classroom)


HT = TypeVar("HT", LimitedHour, ClassHour)


def parse(parsed_data: ParsedData, parse_func: Callable[[PARSED_HOUR_RETURN], HT]) \
        -> list[list[list[HT]]]:
    hours = parsed_data.data
    row_matrix = [[[parse_func(hour) for hour in block] for block in row] for row in hours]
    return [list(x) for x in zip(*row_matrix)]  # Rotate matrix for 90 deg


def get_limited_schedule(request_data: RequestData) -> LimitedSchedule:
    request_time = datetime.datetime.now()
    parsed_data = parse_html(get_html(request_data))
    limited_hours = parse(parsed_data, parse_limited_hour)
    return LimitedSchedule(parsed_data.hour_times, parsed_data.dates, parsed_data.week_data, request_time, request_data,
                           limited_hours)


def get_class_schedule(request_data: RequestData) -> ClassSchedule:
    request_time = datetime.datetime.now()
    parsed_data = parse_html(get_html(request_data))
    class_hours = parse(parsed_data, parse_class_hour)
    return ClassSchedule(parsed_data.hour_times, parsed_data.dates, parsed_data.week_data, request_time, request_data,
                         class_hours)


def get_url_request_data(url: str) -> RequestData:
    response = requests.get(url)
    regex = [r"var id_sola = '(\d+)';", r"var id_razred = '(\d+)';", r"var id_profesor = '(\d+)'",
             r"var id_ucilnica = '(\d+)'", r"var id_dijak = '(\d+)'", r"var id_interesna_dejavnost = '(\d+|vse)'",
             r"var teden = '(\d+)'"]
    matches = [re.findall(x, response.text)[0] for x in regex]
    matches[5] = 0 if matches[5] == "vse" else matches[5]
    matches = [int(x) for x in matches]
    request_data = RequestData(matches[0])
    request_data.class_id = matches[1]
    request_data.professor_id = matches[2]
    request_data.classroom_id = matches[3]
    request_data.student_id = matches[4]
    request_data.interest_activity = matches[5]
    request_data.school_week = matches[6]
    return request_data


def numeric_id_from_uuid(school_uuid: str):
    request_data = get_url_request_data(f"https://www.easistent.com/urniki/{school_uuid}")
    return request_data.school_id
