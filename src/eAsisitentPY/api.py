import time
import scraper
from structure import Schedule, RequestData, LimitedSchedule, CacheEnum


class API:
    cache_seconds: int
    school_uuid: str
    school_id: int
    cache: dict[CacheEnum, dict[int, (int, Schedule)]] = {x: {} for x in CacheEnum}

    def __init__(self, school_uuid: str, cache_seconds: int = 300):
        if not isinstance(school_uuid, str):
            raise TypeError(f"Invalid type for school_uuid. Expected {str}, got {type(school_uuid)}")
        self.school_uuid = school_uuid
        self.school_id = scraper.numeric_id_from_uuid(school_uuid)
        self.cache_seconds = cache_seconds

    def get_school_data(self, school_week: int = 0, recache=False) -> LimitedSchedule:
        request_data = RequestData(self.school_id, school_week=school_week)
        func_cache = self.cache[CacheEnum.CLASSROOM]
        request_data_hash = (self.school_id, school_week).__hash__()
        cache_data = func_cache.get(request_data_hash)
        if cache_data and not recache:
            cache_expired = cache_data[0] + self.cache_seconds * (10 ** 9) - time.time_ns() < 0
            if not cache_expired:
                return cache_data[1]

        res = scraper.get_limited_schedule(request_data)
        func_cache[request_data_hash] = (time.time_ns(), res)
        return res

    def get_classroom_data(self, classroom_uuid: int, school_week: int = 0, recache=False) -> LimitedSchedule:
        if not isinstance(classroom_uuid, int):
            raise TypeError(f"Invalid type for classroom_uuid. Expected {int}, got {type(classroom_uuid)}")

        func_cache = self.cache[CacheEnum.CLASSROOM]
        request_data_hash = (self.school_id, classroom_uuid, school_week).__hash__()
        cache_data = func_cache.get(request_data_hash)
        if cache_data and not recache:
            cache_expired = cache_data[0] + self.cache_seconds * (10 ** 9) - time.time_ns() < 0
            if not cache_expired:
                return cache_data[1]

        url = f"https://www.easistent.com/urniki/{self.school_uuid}/ucilnice/{classroom_uuid}"
        classroom_id = scraper.get_url_request_data(url).classroom_id
        request_data = RequestData(self.school_id, classroom_id=classroom_id, school_week=school_week)

        res = scraper.get_limited_schedule(request_data)
        func_cache[request_data_hash] = (time.time_ns(), res)
        return res

    def get_class_data(self, class_uuid: int, school_week: int = 0, recache=False):
        if not isinstance(class_uuid, int):
            raise TypeError(f"Invalid type for class_uuid. Expected {int}, got {type(class_uuid)}")

        func_cache = self.cache[CacheEnum.CLASS]
        request_data_hash = (self.school_id, class_uuid, school_week).__hash__()
        cache_data = func_cache.get(request_data_hash)
        if cache_data and not recache:
            cache_expired = cache_data[0] + self.cache_seconds * (10 ** 9) - time.time_ns() < 0
            if not cache_expired:
                return cache_data[1]

        url = f"https://www.easistent.com/urniki/{self.school_uuid}/razredi/{class_uuid}"
        class_id = scraper.get_url_request_data(url).class_id
        request_data = RequestData(self.school_id, class_id=class_id, school_week=school_week)

        res = scraper.get_class_schedule(request_data)
        func_cache[request_data_hash] = (time.time_ns(), res)
        return res
