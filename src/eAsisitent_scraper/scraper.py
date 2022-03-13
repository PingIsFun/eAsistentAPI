import bs4
import datetime
import re
import requests

from bs4 import BeautifulSoup


def request_schedule(school_id: str, class_id: str, professor=0, classroom=0, school_week=0, student_id=0):
    """
    Requests schedule from: https://www.easistent.com/urniki/izpis/school_id/class_id/professor/classroom/0/school_week/student_id
    :param school_id: id of school
    :param class_id: id of class
    :param professor: id of professor
    :param classroom:
    :param school_week: week of school from what you have
    :param student_id: id of student that you want to have schedule returned from
    :return: class 'requests.models.Response'

    """
    # TODO: find out what does the 5th part of the url do
    url = f"https://www.easistent.com/urniki/izpis/{school_id}/{class_id}/{professor}/{classroom}/0/{school_week}/{student_id}"

    response = requests.get(url)

    if response.text == "Šola ni veljavna!" or response.text == "Šola ni izbrana!":
        return None

    return response


today = datetime.date.today()


def date_to_datetime(var_day=today.day, var_month=today.month, var_year=today.year):
    return datetime.datetime(var_year, month=var_month, day=var_day)


def hour_to_num(hour: str):
    """Convert hour name to integer"""
    if hour == "predura":
        return int(0)
    else:
        return int(hour.split(". ura")[0])


def get_schedule_data(school_id, class_id):
    """
    :param school_id: id of school
    :param class_id: id of class
    :return: dict of scraped data. If school is not found returns None.
    """

    # TODO: reduce complexity of the function,
    #  fix crash if class is "0",
    #  better naming of variables,
    #  get template for scraped_data from template.json
    response = request_schedule(school_id=school_id, class_id=class_id)
    if response is None:
        return None
    soup = BeautifulSoup(response.text, "html5lib")
    seznam_ur_teden = soup.select("body > table > tbody > tr")

    count = -1

    dates = []
    dates_formatted = []
    hour_times = []

    scraped_data = {
        "0": {
            "0": {},
            "1": {},
            "2": {},
            "3": {},
            "4": {},
            "5": {},
            "6": {},
            "7": {},
            "8": {},
            "9": {},
            "10": {},
            "11": {},
            "12": {},
            "13": {},
            "14": {},
        },
        "1": {
            "0": {},
            "1": {},
            "2": {},
            "3": {},
            "4": {},
            "5": {},
            "6": {},
            "7": {},
            "8": {},
            "9": {},
            "10": {},
            "11": {},
            "12": {},
            "13": {},
            "14": {},
        },
        "2": {
            "0": {},
            "1": {},
            "2": {},
            "3": {},
            "4": {},
            "5": {},
            "6": {},
            "7": {},
            "8": {},
            "9": {},
            "10": {},
            "11": {},
            "12": {},
            "13": {},
            "14": {},
        },
        "3": {
            "0": {},
            "1": {},
            "2": {},
            "3": {},
            "4": {},
            "5": {},
            "6": {},
            "7": {},
            "8": {},
            "9": {},
            "10": {},
            "11": {},
            "12": {},
            "13": {},
            "14": {},
        },
        "4": {
            "0": {},
            "1": {},
            "2": {},
            "3": {},
            "4": {},
            "5": {},
            "6": {},
            "7": {},
            "8": {},
            "9": {},
            "10": {},
            "11": {},
            "12": {},
            "13": {},
            "14": {},
        },
        "5": {
            "0": {},
            "1": {},
            "2": {},
            "3": {},
            "4": {},
            "5": {},
            "6": {},
            "7": {},
            "8": {},
            "9": {},
            "10": {},
            "11": {},
            "12": {},
            "13": {},
            "14": {},
        },
        "6": {
            "0": {},
            "1": {},
            "2": {},
            "3": {},
            "4": {},
            "5": {},
            "6": {},
            "7": {},
            "8": {},
            "9": {},
            "10": {},
            "11": {},
            "12": {},
            "13": {},
            "14": {},
        },
        "week_data": {
            "hour_times": [],
            "dates": []
        }

    }

    for i in seznam_ur_teden:
        if count == -1:
            for days in i:
                if type(days) == bs4.Tag:
                    day = days.select("div")
                    if day[0].text != "Ura":
                        temp_date = re.findall(r"[^A-z,. ]+", day[1].text)
                        dates_formatted.append(f"{today.year}-{temp_date[1]}-{temp_date[0]}")
                        dates.append(date_to_datetime(var_day=int(temp_date[0]), var_month=int(temp_date[1]), var_year=today.year))
        if count >= 0:
            row = i.find_all("td", class_="ednevnik-seznam_ur_teden-td")
            hour_name = row[0].find(class_="text14").text
            hour_time = row[0].find(class_="text10").text
            hour_times.append(hour_time)
            hour_num = str(hour_to_num(hour_name))
            hour_num = str(hour_num)
            count2 = 0
            for block in row:
                if count2 != 0:
                    """Pass the first collum that contains hour times"""
                    date = dates[count2 - 1]
                    day_num = str(date.weekday())
                    date_formatted = str(date.strftime("%Y-%m-%d"))
                    if "style" not in block.attrs:
                        data_out = \
                            {
                                "subject": None,
                                "teacher": None,
                                "classroom": None,
                                "group": None,
                                "event": None,
                                "hour": int(hour_num),
                                "week_day": int(day_num),
                                "hour_in_block": 0,
                                "date": date_formatted
                            }
                        print("--------------------------\n", data_out, "\n--------------------------")
                        scraped_data[day_num][hour_num]["0"] = data_out
                    else:
                        classes_in_hour = 0
                        for section in block:
                            if type(section) == bs4.Tag:
                                event = None
                                subject = None
                                group_raw = None
                                group = []
                                teacher = None
                                classroom = None
                                teacher_classroom = None
                                for img in section.select("img"):
                                    events_list = {"Odpadla ura": "cancelled", "Dogodek": "event", "Nadomeščanje": "substitute", "Polovična ura": "half_hour",
                                                   "Videokonferenca": "video_call", "Interesna dejavnost": "activity", "Zaposlitev": "occupation",
                                                   "Neopravljena ura": "unfinished_hour", "Govorilne ure": "office hours", "Izpiti": "exams"}
                                    try:
                                        event = events_list[img.attrs["title"]]
                                    except KeyError:
                                        event = "unknown_event"

                                try:
                                    subject = section.find(class_="text14").text.replace("\n", "").replace("\t", "")
                                    group_raw = section.find_all(class_="text11 gray bold")
                                    teacher_classroom = section.find(class_="text11").text.replace("\n", "").replace("\t", "").replace("\r", "").split(", ")
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
                                        re.match(r"ednevnik-seznam_ur_teden-blok-\d\d\d\d\d\d-\d\d\d\d-\d\d-\d\d", section.attrs["id"])):
                                    """Check for blocks"""
                                    for block_part in section:
                                        if type(block_part) == bs4.Tag:
                                            event = None
                                            subject = None
                                            group_raw = None
                                            group = []
                                            teacher = None
                                            classroom = None
                                            teacher_classroom = None
                                            for img in block_part.select("img"):
                                                events_list = {"Odpadla ura": "cancelled", "Dogodek": "event", "Nadomeščanje": "substitute",
                                                               "Polovična ura": "half_hour",
                                                               "Videokonferenca": "video_call", "Interesna dejavnost": "activity", "Zaposlitev": "occupation",
                                                               "Neopravljena ura": "unfinished_hour", "Govorilne ure": "office hours", "Izpiti": "exams"}
                                                try:
                                                    event = events_list[img.attrs["title"]]
                                                except KeyError:
                                                    event = "unknown_event"
                                            try:
                                                subject = block_part.find(class_="text14").text.replace("\n", "").replace("\t", "")
                                                group_raw = block_part.find_all(class_="text11 gray bold")
                                                teacher_classroom = block_part.find(class_="text11").text \
                                                    .replace("\n", "").replace("\t", "").replace("\r", "").split(", ")
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
                                            data_out = \
                                                {
                                                    "subject": subject,
                                                    "teacher": teacher,
                                                    "classroom": classroom,
                                                    "group": group,
                                                    "event": event,
                                                    "hour": int(hour_num),
                                                    "week_day": int(day_num),
                                                    "hour_in_block": int(classes_in_hour),
                                                    "date": date_formatted
                                                }
                                            print("--------------------------\n", data_out, "\n--------------------------")
                                            scraped_data[day_num][hour_num][classes_in_hour] = data_out
                                            classes_in_hour += 1
                                else:
                                    data_out = \
                                        {
                                            "subject": subject,
                                            "teacher": teacher,
                                            "classroom": classroom,
                                            "group": group,
                                            "event": event,
                                            "hour": int(hour_num),
                                            "week_day": int(day_num),
                                            "hour_in_block": int(classes_in_hour),
                                            "date": date_formatted
                                        }
                                    print("--------------------------\n", data_out, "\n--------------------------")
                                    scraped_data[day_num][hour_num][classes_in_hour] = data_out
                count2 += 1
        count += 1
    scraped_data["week_data"]["hour_times"] = hour_times
    scraped_data["week_data"]["dates"] = dates_formatted

    return scraped_data
