import bs4.element
import datetime
import re
import requests
import time
from dataclasses import dataclass

from bs4 import BeautifulSoup
from requests import Response


@dataclass()
class Formatting:
    SUBJECT_CLASS = "text14"
    RAW_GROUP_CLASS = "text11 gray bold"
    TEACHER_CLASSROOM_CLASS = "text11"
    EVENT_CLASS = "text14"
    CLASS_NAME_CLASS = "text20"


@dataclass()
class HourBlock:
    subject: str
    teacher: str
    classroom: str
    group: list[str]
    event: str
    hour: str
    hour_in_block: int
    date: datetime.date


@dataclass()
class Hour:
    name: str
    hour_blocks: list[HourBlock]


@dataclass()
class SchoolDay:
    date: datetime
    hours: list[Hour]


@dataclass()
class UsedData:
    school_id: str
    class_id: int
    professor: int
    classroom: int
    interest_activity: int
    school_week: int
    student_id: int


@dataclass()
class Schedule:
    days: list[SchoolDay]
    hour_times: list[str]
    dates: list[datetime.date]
    class_name: str
    request_week: int
    request_epoch: int
    used_data: UsedData


def __get_hour_data(section: bs4.element.Tag) -> tuple[str, list, str, str]:
    subject = section.find(class_=Formatting.SUBJECT_CLASS).text.replace("\n", "").replace("\t", "")
    group_raw = section.find_all(class_=Formatting.RAW_GROUP_CLASS)
    try:
        teacher_classroom = list(
            section.find(class_=Formatting.TEACHER_CLASSROOM_CLASS)
            .text.replace("\n", "")
            .replace("\t", "")
            .replace("\r", "")
            .split(", ")
        )
    except AttributeError:
        subject = section.find(class_=Formatting.EVENT_CLASS).text.replace("\n", "").replace("\t", "")
        teacher_classroom = [None, None]
    group = [x.text for x in group_raw]
    group = None if group == [] else group
    return subject, group, teacher_classroom[0], teacher_classroom[1]


def __get_event(section: bs4.element.Tag) -> str:
    for img in section.select("img"):
        return img.attrs["title"]


def __make_data_out(
        date: datetime.date,
        subject: str = None,
        teacher: str = None,
        classroom: str = None,
        group: list = None,
        event: str = None,
        hour_name: str = None,
        week_day: str = None,
        hour_in_block: int = None,
) -> HourBlock:
    return HourBlock(subject, teacher, classroom, group, event, hour_name, hour_in_block, date)


def __format_date(date: datetime.date) -> str:
    return str(date.strftime("%Y-%m-%d"))


def __get_dates(table_row: bs4.element.Tag) -> list[datetime.date]:
    dates: list = []
    for days in table_row:
        if type(days) == bs4.element.Tag:
            day = days.select("div")
            if day[0].text != "Ura":
                temp_date = re.findall(r"[^A-z,. ]+", day[1].text)
                temp_datetime = datetime.date(
                    day=int(temp_date[0]),
                    month=int(temp_date[1]),
                    year=datetime.date.today().year,
                )
                dates.append(temp_datetime)
    return dates


def __get_hours_time_data(row: bs4.element.ResultSet) -> tuple[str, str]:
    hour_name = str(row[0].find(class_="text14").text)
    hour_time = str(row[0].find(class_="text10").text.replace(" ", ""))
    return hour_name, hour_time


def __request_schedule(
        school_id: str,
        class_id=0,
        professor=0,
        classroom=0,
        interest_activity=0,
        school_week=0,
        student_id=0,
) -> Response:
    url = f"https://www.easistent.com/urniki/izpis/{school_id}/{class_id}/{professor}/{classroom}/{interest_activity}/{school_week}/{student_id}"

    response = requests.get(url)

    if response.text == "Šola ni veljavna!" or response.text == "Šola ni izbrana!":
        raise ValueError("This school does not exist. school_id is invalid")
    return response


def get_schedule(
        school_id: str,
        class_id=0,
        professor=0,
        classroom=0,
        interest_activity=0,
        school_week=0,
        student_id=0,
) -> Schedule:
    response = __request_schedule(
        school_id=school_id,
        class_id=class_id,
        professor=professor,
        classroom=classroom,
        interest_activity=interest_activity,
        school_week=school_week,
        student_id=student_id,
    )

    request_time = int(time.time())

    soup = BeautifulSoup(response.text, "html5lib")
    table_rows = soup.select("body > table > tbody > tr")

    hour_times: list = []
    dates: list[datetime.date] = []

    current_week = int(
        "".join(
            re.findall(
                "[0-9]",
                [item.text.split(",")[0] for item in
                 soup.select("body > div > span")][
                    0
                ],
            )
        )
    )
    class_name = str(
        [item.text.strip() for item in soup.select("body > div > strong")][0]
    )
    final_bundle_pre_turn = []
    for count, table_row in enumerate(table_rows):
        bundle_hour: list[Hour] = []
        if count == 0:
            dates = __get_dates(table_row)
            continue

        row = table_row.find_all("td",
                                 class_="ednevnik-seznam_ur_teden-td")
        hour_name, hour_time = __get_hours_time_data(row)
        hour_times.append(hour_time)
        for count2, row_part in enumerate(row):
            if count2 == 0:
                continue
            bundle_hour_block = Hour(hour_name, [])
            """Pass the first column that contains hour times"""
            date = dates[count2 - 1]
            day_num = str(date.weekday())
            if "style" not in row_part.attrs:  # Detect empty hours
                data_out = __make_data_out(date, hour_name=hour_name, week_day=day_num, hour_in_block=0)
                bundle_hour_block.hour_blocks.append(data_out)
            else:
                classes_in_hour = 0
                for section in row_part:
                    if type(section) != bs4.element.Tag:
                        continue
                    event = __get_event(section)
                    subject, group, teacher, hour_classroom = __get_hour_data(section)

                    is_block_hour = ("id" in section.attrs) and bool(
                        re.match(
                            r"ednevnik-seznam_ur_teden-blok"
                            r"-\d\d\d\d\d\d-\d\d\d\d-\d\d-\d\d",
                            section.attrs["id"],
                        )
                    )

                    if not is_block_hour:
                        data_out = __make_data_out(
                            date, subject, teacher, hour_classroom, group, event, hour_name, day_num, classes_in_hour
                        )
                        bundle_hour_block.hour_blocks.append(data_out)
                        classes_in_hour += 1
                        continue

                    for block in section:
                        if type(block) != bs4.element.Tag:
                            continue
                        event = __get_event(section)
                        subject, group, teacher, hour_classroom = __get_hour_data(section)
                        data_out = __make_data_out(
                            date, subject, teacher, hour_classroom, group, event, hour_name, day_num, classes_in_hour
                        )
                        bundle_hour_block.hour_blocks.append(data_out)
                        classes_in_hour += 1

            bundle_hour.append(bundle_hour_block)
        final_bundle_pre_turn.append(bundle_hour)
    school_days_list = [SchoolDay(dates[index], list(x)) for index, x in enumerate(list(zip(*final_bundle_pre_turn)))]
    used_data = UsedData(school_id, class_id, professor, classroom, interest_activity, school_week, student_id)
    return Schedule(school_days_list, hour_times, dates, class_name, current_week, request_time, used_data)
