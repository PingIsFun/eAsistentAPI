import datetime
import re
import requests
import bs4.element

from bs4 import BeautifulSoup


def request_schedule(
        school_id: str,
        class_id=0,
        professor=0,
        classroom=0,
        interest_activity=0,
        school_week=0,
        student_id=0,
        soup=False
):
    """
    It requests schedule from easistent.com and returns it as a response

    :param school_id: The ID of the school you want to get data for
    :type school_id: str
    :param class_id: The ID of the class you want to get data for, defaults to 0 (optional), defaults to 0 (optional)
    :param professor: The ID of the professor you want to get data for, defaults to 0 (optional), defaults to 0 (optional)
    :param classroom: The classroom you want to get data for, defaults to 0 (optional), defaults to 0 (optional)
    :param interest_activity: The activity you want to get data for, defaults to 0 (optional)
    :param school_week: 0 is the current week, 1 is the next week, 2 is the week after that, etc, defaults to 0 (optional)
    :param student_id: The ID of the student you want to get the schedule for, defaults to 0 (optional)
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


def hour_to_num(hour: str):
    """
    Convert hour name to integer

    :param hour: the hour that you want to be converted to int
    :type hour: str
    :return: The hour as an integer.
    """
    if hour == "predura":
        return int(0)
    else:
        return int(hour.split(". ura")[0])


def get_schedule_data(
        school_id: str,
        class_id=0,
        professor=0,
        classroom=0,
        interest_activity=0,
        school_week=0,
        student_id=0,
):
    """
    Date format is: YYYY-MM-DD
    If school id is invalid ValueError is raised

    :param school_id: The ID of the school you want to get data for
    :type school_id: str
    :param class_id: The ID of the class you want to get data for, defaults to 0 (optional), defaults to 0 (optional)
    :param professor: The ID of the professor you want to get data for, defaults to 0 (optional), defaults to 0 (optional)
    :param classroom: The classroom you want to get data for, defaults to 0 (optional), defaults to 0 (optional)
    :param interest_activity: The activity you want to get data for, defaults to 0 (optional)
    :param school_week: 0 is the current week, 1 is the next week, 2 is the week after that, etc, defaults to 0 (optional)
    :param student_id: The ID of the student you want to get the schedule for, defaults to 0 (optional)
    :return: A dictionary with the data.
    """

    # TODO: reduce complexity of the function,
    #  better naming of variables,
    #  get template for scraped_data from template.json
    response = request_schedule(school_id=school_id,
                                class_id=class_id,
                                professor=professor,
                                classroom=classroom,
                                interest_activity=interest_activity,
                                school_week=school_week,
                                student_id=student_id)
    soup = BeautifulSoup(response.text, "html5lib")
    seznam_ur_teden = soup.select("body > table > tbody > tr")

    count: int = -1

    dates: list = []
    dates_formatted: list = []
    hour_times: list = []

    scraped_data: dict = {str(i): {str(j): {} for j in range(15)} for i in range(7)}
    scraped_data["week_data"] = {"hour_times": [], "dates": [], "current_week": "", "class": ""}

    current_week = int("".join(re.findall("[0-9]", [item.text.split(",")[0] for item in soup.select("body > div > span")][0])))
    current_class = str([item.text.strip() for item in soup.select("body > div > strong")][0])

    for i in seznam_ur_teden:
        if count == -1:
            for days in i:
                if type(days) == bs4.element.Tag:
                    day = days.select("div")
                    if day[0].text != "Ura":
                        temp_date = re.findall(r"[^A-z,. ]+", day[1].text)
                        temp_datetime = datetime.datetime(
                                day=int(temp_date[0]),
                                month=int(temp_date[1]),
                                year=today.year,
                            )
                        dates_formatted.append(str(temp_datetime.strftime("%Y-%m-%d")))
                        dates.append(temp_datetime)
        if count >= 0:
            row = i.find_all("td", class_="ednevnik-seznam_ur_teden-td")
            hour_name = row[0].find(class_="text14").text
            hour_time = row[0].find(class_="text10").text
            hour_times.append(hour_time)
            hour_num = str(hour_to_num(hour_name))
            hour_num = str(hour_num)
            count2: int = 0
            for block in row:
                if count2 != 0:
                    """Pass the first collum that contains hour times"""
                    date = dates[count2 - 1]
                    day_num = str(date.weekday())
                    date_formatted = str(date.strftime("%Y-%m-%d"))
                    if "style" not in block.attrs:
                        data_out = {
                            "subject": None,
                            "teacher": None,
                            "classroom": None,
                            "group": None,
                            "event": None,
                            "hour": int(hour_num),
                            "week_day": int(day_num),
                            "hour_in_block": 0,
                            "date": date_formatted,
                        }
                        scraped_data[day_num][hour_num]["0"] = data_out
                    else:
                        classes_in_hour = 0
                        for section in block:
                            if type(section) == bs4.element.Tag:
                                event = None
                                subject = None
                                group_raw = None
                                group = []
                                teacher = None
                                classroom = None
                                teacher_classroom = None
                                for img in section.select("img"):
                                    events_list = {
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
                                    try:
                                        event = events_list[img.attrs["title"]]
                                    except KeyError:
                                        event = "unknown_event"

                                try:
                                    subject = (
                                        section.find(class_="text14")
                                            .text.replace("\n", "")
                                            .replace("\t", "")
                                    )
                                    group_raw = section.find_all(
                                        class_="text11 gray bold"
                                    )
                                    teacher_classroom = (
                                        section.find(class_="text11")
                                            .text.replace("\n", "")
                                            .replace("\t", "")
                                            .replace("\r", "")
                                            .split(", ")
                                    )
                                    teacher = teacher_classroom[0]
                                    classroom = teacher_classroom[1]
                                except IndexError:
                                    pass
                                except AttributeError:
                                    """Makes it so empty strings don't crash the program"""
                                    pass
                                if group_raw:
                                    for gr in group_raw:
                                        group.append(gr.text)
                                if ("id" in section.attrs) and bool(
                                        re.match(
                                            r"ednevnik-seznam_ur_teden-blok-\d\d\d\d\d\d-\d\d\d\d-\d\d-\d\d",
                                            section.attrs["id"],
                                        )
                                ):
                                    """Check for blocks"""
                                    for block_part in section:
                                        if type(block_part) == bs4.element.Tag:
                                            event = None
                                            subject = None
                                            group_raw = None
                                            group = []
                                            teacher = None
                                            classroom = None
                                            teacher_classroom = None
                                            for img in block_part.select("img"):
                                                events_list = {
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
                                                try:
                                                    event = events_list[
                                                        img.attrs["title"]
                                                    ]
                                                except KeyError:
                                                    event = "unknown_event"
                                            try:
                                                subject = (
                                                    block_part.find(class_="text14")
                                                        .text.replace("\n", "")
                                                        .replace("\t", "")
                                                )
                                                group_raw = block_part.find_all(
                                                    class_="text11 gray bold"
                                                )
                                                teacher_classroom = (
                                                    block_part.find(class_="text11")
                                                        .text.replace("\n", "")
                                                        .replace("\t", "")
                                                        .replace("\r", "")
                                                        .split(", ")
                                                )
                                                teacher = teacher_classroom[0]
                                                classroom = teacher_classroom[1]
                                            except IndexError:
                                                pass
                                            except AttributeError:
                                                """Makes it so empty strings don't crash the program"""
                                                pass
                                            if group_raw:
                                                for gr in group_raw:
                                                    group.append(gr.text)
                                            data_out = {
                                                "subject": subject,
                                                "teacher": teacher,
                                                "classroom": classroom,
                                                "group": group,
                                                "event": event,
                                                "hour": int(hour_num),
                                                "week_day": int(day_num),
                                                "hour_in_block": int(classes_in_hour),
                                                "date": date_formatted,
                                            }
                                            scraped_data[day_num][hour_num][
                                                classes_in_hour
                                            ] = data_out
                                            classes_in_hour += 1

                                else:
                                    data_out = {
                                        "subject": subject,
                                        "teacher": teacher,
                                        "classroom": classroom,
                                        "group": group,
                                        "event": event,
                                        "hour": int(hour_num),
                                        "week_day": int(day_num),
                                        "hour_in_block": int(classes_in_hour),
                                        "date": date_formatted,
                                    }
                                    scraped_data[day_num][hour_num][
                                        classes_in_hour
                                    ] = data_out
                                    classes_in_hour += 1
                count2 += 1
        count += 1
    scraped_data["week_data"]["hour_times"] = hour_times
    scraped_data["week_data"]["dates"] = dates_formatted
    scraped_data["week_data"]["current_week"] = current_week
    scraped_data["week_data"]["class"] = current_class

    return scraped_data
