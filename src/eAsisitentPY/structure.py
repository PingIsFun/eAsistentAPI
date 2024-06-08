import datetime
import logging
from dataclasses import dataclass, fields
from enum import Enum, auto


class ScheduleType(Enum):
    SCHOOL = 0
    CLASS = 1
    CLASSROOM = 2


class EventType(Enum):
    NADOMESCANJE = "Nadomeščanje"
    ZAPOSLITEV = "Zaposlitev"
    ODPADLA_URA = "Odpadla ura"
    NEOPRAVLJENA_URA = "Neopravljena ura"
    VEC_SKUPIN = "Več skupin"
    DOGODEK = "Dogodek"
    GOVORILNE_URE = "Govorilne ure"
    POLOVICNA_URA = "Polovična ura"
    INTERESNA_DEJAVNOST = "Interesna dejavnost"
    VIDEOKONFERENCA = "Videokonferenca"
    IZPITI = "Izpiti"
    UNKNOWN = -1

    @classmethod
    def _missing_(cls, value):
        logging.getLogger("eAsistentPY").warning(f"Unknown event type: {value}")
        return cls.UNKNOWN


@dataclass
class HourTime:
    name: str
    start: datetime.time
    end: datetime.time


@dataclass
class Teacher:
    name: str
    short_name: str


@dataclass
class Hour:
    teacher: Teacher
    group: list[str]
    event: EventType


@dataclass
class ClassHour(Hour):
    subject: str
    subject_short: str
    classroom: str


@dataclass
class LimitedClassHour(ClassHour):
    name: str
    description: str


@dataclass
class LimitedHour(Hour):
    class_name: str


@dataclass
class LimitedEventHour(LimitedHour):
    name: str
    description: str


@dataclass
class WeekData:
    school_week: int
    start: datetime.date
    end: datetime.date


@dataclass
class RequestData:
    school_id: int
    class_id: int = 0
    professor_id: int = 0
    classroom_id: int = 0
    interest_activity: int = 0
    school_week: int = 0
    student_id: int = 0

    def __hash__(self):
        return hash(tuple([getattr(self, x.name) for x in fields(RequestData)]))


@dataclass
class Schedule:
    hour_times: list[HourTime]
    dates: list[datetime.date]
    week_data: WeekData
    request_time: datetime.datetime
    used_data: RequestData
    data_matrix: list[list[list[Hour]]]

    def diff(self, schedule: 'Schedule'): pass


@dataclass
class ClassSchedule(Schedule):
    data_matrix: list[list[list[ClassHour]]]


@dataclass
class LimitedSchedule(Schedule):
    data_matrix: list[list[list[LimitedHour]]]


class CacheEnum(Enum):
    CLASS = auto()
    CLASSROOM = auto()
    SCHOOL = auto()
