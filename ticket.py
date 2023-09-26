import requests
import time
import random
import yaml
from config import global_config
from logger import logger
from timer import Timer
from datetime import datetime
import os
from collections import defaultdict
import qrcode


BASE_URL = "https://api.pyiffestival.com/app/api/v1"
ORIGIN = "https://www.pyiffestival.com"
REFERER = "https://www.pyiffestival.com"

Headers = {
    "User-Agent": global_config["user_agent"],
    "Origin": ORIGIN,
    "Referer": REFERER,
}

AVAIlABLE_SEAT_TYPE_ID = "09ffe644-40cd-42fe-889c-46e0b940f8bc"


class TicketHelper(object):
    def __init__(self):
        self.config = global_config
        self.activity_id = self.config["activity_id"]
        self.session = requests.Session()
        self.session.headers.update(Headers)
        self.timer = Timer()

    def start(self):
        if "token" not in self.config or not self.config["token"]:
            self.send_push("请先登录", "请先登录并配置token")
        else:
            self.session.headers.update(
                {"Authorization": f'Bearer {self.config["token"]}'}
            )
            self.buy_ticket()

    def wait_some_time(self):
        time.sleep(random.randint(3200, 7400) / 1000)

    def send_push(self, title, content):
        requests.get(
            f'https://api.day.app/{self.config["bark_key"]}/{title}/{content}?isArchive=1'
        )

    def validate_user(self, activity_id):
        res = self.session.get(
            url=BASE_URL + "/TenantUser",
            params={"activityId": activity_id},
        )
        self.handle_response("验证用户", res)

    def get_categories(self):
        if os.path.exists("categories.yaml"):
            return yaml.load(open("categories.yaml", "r"), Loader=yaml.FullLoader)
        res = self.session.get(
            url=BASE_URL + f"/Activity/{self.activity_id}/ActivityFilmCategories",
        )
        result = self.handle_response("获取分类", res)
        if not result:
            raise LookupError("获取分类失败")
        else:
            categories = []
            for item in result:
                category = {
                    "id": item["id"],
                    "name": item["categoryName"],
                    "nameEn": item["categoryNameEN"],
                    "activityId": item["activityId"],
                    "children": [],
                }
                for subCat in item["children"]:
                    category["children"].append(
                        {
                            "id": subCat["id"],
                            "name": subCat["categoryName"],
                            "nameEn": subCat["categoryNameEN"],
                            "activityId": subCat["activityId"],
                            "projectId": subCat["projectFilmCategoryId"],
                        }
                    )
                categories.append(category)
            return categories

    def get_movie_list(
        self,
        category_id="d4c82f14-4dfc-4fb6-a91e-9fd1876956ea",
        date="",
        search_text="",
        pageSize=10,
        pageIndex=1,
    ):
        params = {
            "ActivityFilmCategoryId": category_id,
            "Language": 0,
            "pageIndex": pageIndex,
            "pageSize": pageSize,
            "Date": date,
            "SearchText": search_text,
        }
        res = self.session.get(
            url=BASE_URL + f"/Activity/{self.activity_id}/ActivityFilms",
            params=params,
        )
        return self.handle_response("获取电影列表", res)

    def get_movie_detail(self, movie_id):
        res = self.session.get(
            url=BASE_URL + f"/ActivityFilm/{movie_id}",
        )
        return self.handle_response("获取电影详情", res)

    def create_order(self, seat_ids=[], plan_id=""):
        self.validate_user(self.activity_id)
        self.session.headers.update({"Content-Type": "application/json"})
        data = {
            "activityFilmPlanSeats": seat_ids,
        }
        res = self.session.post(
            f"{BASE_URL}/ActivityFilmPlan/{plan_id}/ActivityFilmPlanOrder",
            data=str(data),
        )
        return self.handle_response("创建订单", res)

    def get_film_plan_detail(self, film_plan_id):
        res = self.session.get(
            url=BASE_URL + f"/ActivityFilmPlan/{film_plan_id}",
        )
        return self.handle_response("获取场次详情", res)

    def get_seats_for_film_plan(self, film_plan_id):
        res = self.session.get(
            url=BASE_URL + f"/ActivityFilmPlan/{film_plan_id}/ActivityFilmPlanSeats",
        )
        return self.handle_response("获取座位", res)

    def create_pay_qr_code(self, order_ids):
        self.session.headers.update({"Content-Type": "application/json"})
        for id in order_ids:
            data = {
                "couponCode": "",
            }
            res = self.session.post(
                url=BASE_URL + f"/ActivityFilmPlanOrder/{id}/InitiatePayPc",
                data=str(data),
            )
            result = self.handle_response("生成支付二维码", res)
            if "codeUrl" in result:
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_H,
                    box_size=5,
                    border=4,
                )
                qr.add_data(result["codeUrl"])
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                if not os.path.exists("pay"):
                    os.makedirs("pay")
                with open(f"pay/{id}.png", "wb") as f:
                    img.save(f)

    def handle_response(self, func_name, res):
        if res.status_code == 200 or res.status_code == 201:
            result = res.json()
            return result
        else:
            raise requests.exceptions.RequestException(
                f"{func_name}失败:{res.status_code},{res.reason}"
            )

    def find_all_the_films(self):
        self.validate_user(self.activity_id)
        categories = self.get_categories()
        if not os.path.exists("categories.yaml"):
            with open("categories.yaml", "w") as f:
                yaml.dump(categories, f, allow_unicode=True)
        film_screening_activities = [
            category
            for category in categories
            if category["nameEn"] == "FILM SCREENING"
        ]
        result = {}
        for category in film_screening_activities[0]["children"]:
            movies = []
            movie_list = self.get_movie_list(category["id"], pageSize=20)
            for movie in movie_list["items"]:
                movie_detail = self.get_movie_detail(movie["id"])
                plans = []
                for plan in movie_detail["activityFilmPlans"]:
                    plans.append(
                        {
                            "id": plan["id"],
                            "cinemaHallId": plan["activityCinemaHallId"],
                            "cinemaHallName": plan["activityCinemaHall"],
                            "date": plan["date"],
                            "startTime": plan["startTime"],
                            "endTime": plan["endTime"],
                            "price": plan["price"],
                        }
                    )
                movies.append(
                    {
                        "id": movie["id"],
                        "name": movie["activityFilmName"],
                        "category": movie["activityFilmCategoryName"],
                        "hasTickets": movie["hasTickets"],
                        "plans": plans,
                    }
                )
            result[category["name"]] = movies
        return result

    def search_movie_and_place_order(self):
        if os.path.exists("all_movies.yaml"):
            with open("all_movies.yaml", "r") as f:
                all_movies = yaml.load(f, Loader=yaml.FullLoader)
        else:
            all_movies = self.find_all_the_films()
            with open("all_movies.yaml", "w") as f:
                yaml.dump(all_movies, f, allow_unicode=True)
        if "movies" not in self.config or not self.config["movies"]:
            raise Exception("配置错误：请配置电影")
        movies = self.config["movies"]
        order_ids = []
        for movie in movies:
            if "category" not in movie:
                raise Exception("配置错误：请配置分类")
            if "date" not in movie:
                raise Exception("配置错误：请配置日期")
            if "count" not in movie:
                raise Exception("配置错误：请配置购票数量")
            if movie["count"] > 5:
                raise Exception("配置错误：购票数量不能超过5张")
            categoryList = all_movies[movie["category"]]
            [found_movie] = (
                [item for item in categoryList if item["name"] == movie["name"]]
                if any(item["name"] == movie["name"] for item in categoryList)
                else [{}]
            )
            if not found_movie:
                raise LookupError(f"未找到「{movie['name']}」")
            plans = []
            movie_detail = self.get_movie_detail(found_movie["id"])
            for plan in movie_detail["activityFilmPlans"]:
                plans.append(
                    {
                        "id": plan["id"],
                        "cinemaHallId": plan["activityCinemaHallId"],
                        "cinemaHallName": plan["activityCinemaHall"],
                        "date": plan["date"],
                        "startTime": plan["startTime"],
                        "endTime": plan["endTime"],
                        "price": plan["price"],
                        "canSell": plan["canSell"],
                        "hasTickets": plan["hasTickets"],
                    }
                )
            [plan] = (
                [
                    item
                    for item in plans
                    if datetime.strptime(movie["date"], "%Y-%m-%d")
                    == datetime.strptime(item["date"], "%Y-%m-%d %H:%M:%S")
                ]
                if any(
                    datetime.strptime(movie["date"], "%Y-%m-%d")
                    == datetime.strptime(item["date"], "%Y-%m-%d %H:%M:%S")
                    for item in found_movie["plans"]
                )
                else [{}]
            )
            if not plan:
                raise LookupError(f"未找到「{movie['name']}」指定时间{movie['date']}的场次")
            if not plan["canSell"]:
                raise Exception(f"「{movie['name']}」指定时间{movie['date']}的场次不可售")
            if not plan["hasTickets"]:
                raise Exception(f"「{movie['name']}」指定时间{movie['date']}的场次已售罄")
            plan_detail = self.get_film_plan_detail(plan["id"])
            if not plan_detail["canSell"]:
                raise Exception(f"「{movie['name']}」指定时间{movie['date']}的场次不可售")
            if not plan_detail["hasTickets"]:
                raise Exception(f"「{movie['name']}」指定时间{movie['date']}的场次已售罄")
            seats = self.get_seats_for_film_plan(plan["id"])
            seat_ids = self.choose_seat(seats, movie)
            if not seat_ids:
                raise Exception(f"「{movie['name']}」'+指定时间{movie['date']}的场次未找到可用座位")
            result = self.create_order(seat_ids, plan["id"])
            if "id" in result:
                order_ids.append(result["id"])
            else:
                raise Exception(f"{movie['name']}指定时间{movie['date']}的场次下单失败")
        return order_ids

    def choose_seat(self, seats, movie_config):
        num_seats_needed = movie_config["count"]
        seats_by_row = defaultdict(list)
        seats_number_by_row = defaultdict(list)
        for seat in seats:
            seats_number_by_row[seat["row"]].append(seat["number"])
            area_condition = True
            if "area" in movie_config:
                area_condition = seat["area"] == movie_config["area"]
            if seat["stateTypeId"] == AVAIlABLE_SEAT_TYPE_ID and area_condition:
                seats_by_row[seat["row"]].append(
                    {"number": seat["number"], "id": seat["id"]}
                )
            else:
                continue
        best_score = float("inf")
        best_seats = []
        best_seat_row_number = []
        mid_row = max(seats_number_by_row.keys()) // 2  # 计算中间排

        for row, seats in seats_by_row.items():
            seats.sort(key=lambda x: x["number"])
            if len(seats) < num_seats_needed:  # 如果该排空座位数不够，跳过
                continue
            if row <= 2:
                continue
            mid_point = max(seats_number_by_row[row]) // 2  # 计算中间位置
            for i in range(len(seats) - num_seats_needed + 1):
                selected_seats = seats[i : i + num_seats_needed]
                # 计算得分（越低越好）
                score = sum(abs(mid_point - x["number"]) for x in selected_seats) + (
                    abs(row - mid_row)
                )
                if score < best_score:
                    best_score = score
                    best_seats = []
                    best_seat_row_number = []
                    for seat in selected_seats:
                        best_seat_row_number.append((row, seat["number"]))
                        best_seats.append(seat["id"])
        logger.info(f"最优座位:{best_seat_row_number}")
        if not best_seats or len(best_seats) < 1:  # 如果没有找到“最优”座位，尝试选择任何可用座位
            for row, seat_numbers in sorted(seats_by_row.items()):
                if len(seat_numbers) >= num_seats_needed:
                    return [x["id"] for x in seat_numbers[:num_seats_needed]]
                else:
                    return [x["id"] for x in seat_numbers]
        return best_seats

    def buy_ticket(self):
        self.timer.start()
        while True:
            try:
                self.validate_user(self.activity_id)
                order_ids = self.search_movie_and_place_order()
                if len(order_ids) > 0:
                    logger.info(f"购票成功:{(',').join(order_ids)}")
                    self.send_push("购票成功，请马上付款", {(",").join(order_ids)})
                    self.create_pay_qr_code(order_ids)
                    break
            except requests.exceptions.RequestException as e:
                logger.error(e)
                self.send_push("请求失败", e)
                if "验证用户失败" in str(e):
                    break
            except LookupError as e:
                logger.error(e)
                if "指定时间" in str(e):
                    break
            except Exception as e:
                logger.error("购票失败:" + str(e))
                if "配置错误" in str(e):
                    break
            self.wait_some_time()
