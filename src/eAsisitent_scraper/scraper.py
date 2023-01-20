import bs4.element
import datetime
import re
import requests
import time
from dataclasses import dataclass

from bs4 import BeautifulSoup

EVENT_MAP = {
    "Odpadla ura": "cancelled",
    "Dogodek": "event",
    "Nadomeščanje": "substitute",
    "Polovična ura": "half_hour",
    "Videokonferenca": "video_call",
    "Interesna dejavnost": "activity",
    "Zaposlitev": "occupation",
    "Neopravljena ura": "unfinished_hour",
    "Govorilne ure": "office hours",
    "Izpiti": "exams",
}


@dataclass()
class Formatting:
    SUBJECT_CLASS = "text14"
    RAW_GROUP_CLASS = "text11 gray bold"
    TEACHER_CLASSROOM_CLASS = "text11"
    EVENT_CLASS = "text14"
    EVENT_STYLE = "border:none"


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
    debug: str = None


@dataclass()
class Hour:
    name: str
    blocks: list[HourBlock]


@dataclass()
class SchoolDay:
    date: datetime
    hours: list[Hour]


@dataclass()
class Schedule:
    days: list[SchoolDay]
    hour_times: list[str]
    dates: list[datetime.date]
    class_name: str
    request_week: int
    request_epoch: int
    used_data: dict


def get_hour_data(section: bs4.element.Tag) -> tuple[str, str, str]:
    subject = section.find(class_=Formatting.SUBJECT_CLASS).text.replace("\n", "").replace("\t", "")
    group_raw = section.find_all(class_=Formatting.RAW_GROUP_CLASS)
    try:
        teacher_classroom = (
            section.find(class_=Formatting.TEACHER_CLASSROOM_CLASS)
            .text.replace("\n", "")
            .replace("\t", "")
            .replace("\r", "")
            .split(", ")
        )
    except AttributeError:
        subject = section.find(class_=Formatting.EVENT_CLASS).text.replace("\n", "").replace("\t", "")
        teacher_classroom = [None, None]
    # print("--------------")
    # print(section)
    # print(repr(event))
    return subject, group_raw, teacher_classroom


def make_data_out(
        date: datetime.date,
        subject: str = None,
        teacher: str = None,
        classroom: str = None,
        group: list = None,
        event: str = None,
        hour_name: str = None,
        week_day: str = None,
        hour_in_block: int = None
) -> dict:
    return {
        "subject": subject,
        "teacher": teacher,
        "classroom": classroom,
        "group": group,
        "event": event,
        "hour": hour_name,
        "week_day": int(week_day),
        "hour_in_block": hour_in_block,
        "date": format_date(date),
    }


def make_data_out_v2(
        date: datetime.date,
        subject: str = None,
        teacher: str = None,
        classroom: str = None,
        group: list = None,
        event: str = None,
        hour_name: str = None,
        week_day: str = None,
        hour_in_block: int = None,
        debug=None
) -> HourBlock:
    return HourBlock(subject, teacher, classroom, group, event, hour_name, hour_in_block, date, debug)


def format_date(date: datetime.date) -> str:
    return str(date.strftime("%Y-%m-%d"))


def get_dates(table_row: bs4.element.Tag) -> list[datetime.date]:
    dates: list = []
    for days in table_row:
        if type(days) == bs4.element.Tag:
            day = days.select("div")
            if day[0].text != "Ura":
                temp_date = re.findall(r"[^A-z,. ]+", day[1].text)
                temp_datetime = datetime.date(
                    day=int(temp_date[0]),
                    month=int(temp_date[1]),
                    year=today.year,
                )
                dates.append(temp_datetime)
    return dates


def get_hours_time_data(row: bs4.element.ResultSet) -> tuple[str, str]:
    hour_name = str(row[0].find(class_="text14").text)
    hour_time = str(row[0].find(class_="text10").text.replace(" ", ""))
    return hour_name, hour_time


def request_schedule(
        school_id: str,
        class_id=0,
        professor=0,
        classroom=0,
        interest_activity=0,
        school_week=0,
        student_id=0,
        soup=False,
) -> requests.models.Response:
    """
    It requests schedule from easistent.com and returns it as a response

    :param school_id: The ID of the school you want to get data for
    :type school_id: str
    :param class_id: The ID of the class you want to get data for, 0 is all classes, defaults to 0 (optional)
    :param professor: The ID of the professor you want to get data for,  0 is all professors, defaults to 0 (optional)
    :param classroom: The classroom you want to get data for,  0 is all classrooms, defaults to 0 (optional)
    :param interest_activity: The activity you want to get data for, 0 is all interest activities, defaults to 0 (optional)
    :param school_week: school week that you want to get the data for, 0 is the current week, defaults to 0 (optional)
    :param student_id: The ID of the student you want to get the schedule for,0 is all students, defaults to 0 (optional)
    :param soup: Return a BeautifulSoup object (optional)
    :return: A response object is a requests.models.Response object.


    """

    url = f"https://www.easistent.com/urniki/izpis/{school_id}/{class_id}/{professor}/{classroom}/{interest_activity}/{school_week}/{student_id}"

    response = requests.get(url)

    if response.text == "Šola ni veljavna!" or response.text == "Šola ni izbrana!":
        raise ValueError("This school does not exist. school_id is invalid")
    if soup:
        return BeautifulSoup(response.text, "html5lib")
    return response


today = datetime.date.today()


def get_schedule_data(
        school_id: str,
        class_id=0,
        professor=0,
        classroom=0,
        interest_activity=0,
        school_week=0,
        student_id=0,
) -> Schedule:
    """
    Date format is: YYYY-MM-DD
    If school id is invalid ValueError is raised

    :param school_id: The ID of the school you want to get data for
    :type school_id: str
    :param class_id: The ID of the class you want to get data for, 0 is all classes, defaults to 0 (optional)
    :param professor: The ID of the professor you want to get data for,  0 is all professors, defaults to 0 (optional)
    :param classroom: The classroom you want to get data for,  0 is all classrooms, defaults to 0 (optional)
    :param interest_activity: The activity you want to get data for, 0 is all interest activities, defaults to 0 (optional)
    :param school_week: school week that you want to get the data for, 0 is the current week, defaults to 0 (optional)
    :param student_id: The ID of the student you want to get the schedule for,0 is all students, defaults to 0 (optional)
    :return: A dictionary with the data.
    """

    # TODO: reduce complexity of the function,
    #  better naming of variables,
    response = request_schedule(
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
    scraped_data: dict = {}

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
    finla_bundle_pre_turn = []
    for count, table_row in enumerate(table_rows):
        bundle_hour: list[Hour] = []
        if count == 0:
            dates = get_dates(table_row)
            continue

        row = table_row.find_all("td",
                                 class_="ednevnik-seznam_ur_teden-td")
        hour_name, hour_time = get_hours_time_data(row)
        hour_times.append(hour_time)
        for count2, row_part in enumerate(row):
            if count2 != 0:
                bundle_hour_block = Hour(hour_name, [])
                """Pass the first collum that contains hour times"""
                date = dates[count2 - 1]
                day_num = str(date.weekday())
                if day_num not in scraped_data.keys():
                    scraped_data.update({str(day_num): []})
                scraped_data[day_num].append(Hour(hour_name, []))

                if "style" not in row_part.attrs:  # Detect empty hours
                    data_out = make_data_out_v2(date, hour_name=hour_name, week_day=day_num, hour_in_block=0)
                    # scraped_data[day_num][count - 1].blocks.append(data_out)
                    bundle_hour_block.blocks.append(data_out)
                else:
                    classes_in_hour = 0
                    for section in row_part:
                        if type(section) != bs4.element.Tag:
                            continue
                        event = None
                        group = []
                        for img in section.select("img"):
                            try:
                                event = EVENT_MAP[img.attrs["title"]]
                            except KeyError:
                                event = "unknown_event"
                        subject, group_raw, teacher_classroom = get_hour_data(section)
                        teacher = teacher_classroom[0]
                        hour_classroom = teacher_classroom[1]
                        if group_raw:
                            for gr in group_raw:
                                group.append(gr.text)
                        is_block_hour = ("id" in section.attrs) and bool(
                            re.match(
                                r"ednevnik-seznam_ur_teden-blok"
                                r"-\d\d\d\d\d\d-\d\d\d\d-\d\d-\d\d",
                                section.attrs["id"],
                            )
                        )

                        if is_block_hour:
                            # Check for blocks
                            for block in section:
                                if type(block) == bs4.element.Tag:
                                    event = None
                                    group = []
                                    for img in block.select("img"):
                                        try:
                                            event = EVENT_MAP[
                                                img.attrs["title"]
                                            ]
                                        except KeyError:
                                            event = "unknown_event"
                                    subject, group_raw, teacher_classroom = get_hour_data(section)
                                    teacher = teacher_classroom[0]
                                    hour_classroom = teacher_classroom[1]
                                    if group_raw:
                                        for gr in group_raw:
                                            group.append(gr.text)
                                    data_out = make_data_out_v2(
                                        date, subject, teacher, hour_classroom, group, event, hour_name, day_num, classes_in_hour
                                    )
                                    bundle_hour_block.blocks.append(data_out)

                                    # print(data_out)

                                    # scraped_data[day_num][count - 1].blocks.append(data_out)
                                    classes_in_hour += 1
                        else:
                            data_out = make_data_out_v2(
                                date, subject, teacher, hour_classroom, group, event, hour_name, day_num, classes_in_hour
                            )
                            # print(data_out)
                            # scraped_data[day_num][count - 1].blocks.append(data_out)
                            bundle_hour_block.blocks.append(data_out)

                            classes_in_hour += 1
                bundle_hour.append(bundle_hour_block)
        finla_bundle_pre_turn.append(bundle_hour)
    r = [SchoolDay(None, list(x)) for x in list(zip(*finla_bundle_pre_turn))]
    used_data = {
            "school_id": school_id,
            "class_id": class_id,
            "professor": professor,
            "classroom": classroom,
            "interest_activity": interest_activity,
            "school_week": school_week,
            "student_id": student_id
        }
    return Schedule(r, hour_times, dates, class_name, current_week, request_time, used_data)
