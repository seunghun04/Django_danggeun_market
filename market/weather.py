"""
기상청 단기예보 조회서비스(공공데이터포털)로 현재 날씨 가져오기

필요한 환경변수
- KMA_SERVICE_KEY : 공공데이터포털에서 발급받은 '일반 인증키 (Decoding)'
  (Encoding 키를 넣어도 동작하도록 처리)

사용하는 API
- 초단기실황(getUltraSrtNcst) : 현재 기온, 습도, 강수형태, 풍속
- 초단기예보(getUltraSrtFcst) : 하늘상태(맑음/구름많음/흐림)
"""

import json
import math
import os
import urllib.parse
import urllib.request
from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone

API_BASE = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"

CACHE_SECONDS = 10 * 60  # 같은 격자는 10분 동안 다시 묻지 않음

# GPS를 허용하지 않은 사용자에게 보여줄 기본 위치 (서울 중구)
DEFAULT_LOCATION = {"lat": 37.5636, "lon": 126.9976, "name": "서울"}

PTY_TEXT = {
    "0": None, "1": "비", "2": "비/눈", "3": "눈",
    "5": "빗방울", "6": "빗방울·눈날림", "7": "눈날림",
}
PTY_ICON = {
    "1": "🌧️", "2": "🌨️", "3": "❄️", "5": "🌦️", "6": "🌨️", "7": "🌨️",
}
SKY_TEXT = {"1": "맑음", "3": "구름많음", "4": "흐림"}
SKY_ICON = {"1": "☀️", "3": "⛅", "4": "☁️"}


class WeatherError(Exception):
    pass


def latlon_to_grid(lat, lon):
    """위도/경도 → 기상청 격자(nx, ny)  (기상청 제공 LCC 변환식)"""

    re_ = 6371.00877 / 5.0  # 지구 반경 / 격자 간격(km)
    slat1, slat2 = math.radians(30.0), math.radians(60.0)
    olon, olat = math.radians(126.0), math.radians(38.0)
    xo, yo = 43, 136

    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(
        math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    )
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5) ** sn * math.cos(slat1) / sn
    ro = re_ * sf / math.tan(math.pi * 0.25 + olat * 0.5) ** sn

    ra = re_ * sf / math.tan(math.pi * 0.25 + math.radians(lat) * 0.5) ** sn
    theta = math.radians(lon) - olon
    if theta > math.pi:
        theta -= 2 * math.pi
    if theta < -math.pi:
        theta += 2 * math.pi
    theta *= sn

    nx = int(ra * math.sin(theta) + xo + 0.5)
    ny = int(ro - ra * math.cos(theta) + yo + 0.5)
    return nx, ny


def _service_key():
    key = os.getenv("KMA_SERVICE_KEY", "").strip()
    if not key:
        raise WeatherError("날씨 API 키(KMA_SERVICE_KEY)가 설정되지 않았습니다.")
    # Encoding 키(%가 들어 있음)를 넣었다면 원래 값으로 되돌림
    if "%" in key:
        key = urllib.parse.unquote(key)
    return key


def _call(operation, base_date, base_time, nx, ny):
    params = urllib.parse.urlencode({
        "serviceKey": _service_key(),
        "pageNo": 1,
        "numOfRows": 100,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny,
    })

    url = f"{API_BASE}/{operation}?{params}"

    try:
        with urllib.request.urlopen(url, timeout=6) as response:
            raw = response.read().decode("utf-8")
    except Exception as exc:
        raise WeatherError("기상청 서버에 연결하지 못했습니다.") from exc

    try:
        data = json.loads(raw)
    except ValueError:
        # 키 오류 등은 JSON이 아닌 XML로 응답이 옴
        if "SERVICE_KEY" in raw:
            raise WeatherError("날씨 API 키가 올바르지 않거나 아직 활성화되지 않았습니다.")
        raise WeatherError("기상청 응답을 읽지 못했습니다.")

    header = data.get("response", {}).get("header", {})
    if header.get("resultCode") != "00":
        raise WeatherError(f"기상청 오류: {header.get('resultMsg', '알 수 없음')}")

    return data["response"]["body"]["items"]["item"]


def _comment(temp, pty, sky):
    """중고거래 사이트다운 한마디"""
    if pty in ("1", "2", "5"):
        return "비 소식이 있어요. 직거래는 실내에서, 우산 챙기세요 ☂️"
    if pty in ("3", "6", "7"):
        return "눈이 와요! 미끄럼 조심하며 거래하세요 ⛄"
    if temp is None:
        return "오늘도 좋은 거래 되세요!"
    if temp <= 0:
        return "많이 추워요. 따뜻하게 입고 나가세요 🧣"
    if temp <= 10:
        return "쌀쌀해요. 겉옷 꼭 챙기세요 🧥"
    if temp >= 30:
        return "무더워요. 시원한 곳에서 거래하세요 🥤"
    if sky == "1":
        return "맑은 날! 직거래하기 딱 좋은 날씨예요 😊"
    return "산책 겸 직거래하기 좋은 날이에요 🚶"


def get_current_weather(lat, lon):
    nx, ny = latlon_to_grid(lat, lon)

    cache_key = f"kma-weather-{nx}-{ny}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    now = timezone.localtime()

    # 초단기실황: 매시 정각 자료가 약 40분 뒤 제공
    ncst_time = now - timedelta(minutes=40)
    items = _call(
        "getUltraSrtNcst",
        ncst_time.strftime("%Y%m%d"),
        ncst_time.strftime("%H00"),
        nx, ny,
    )
    values = {item["category"]: item.get("obsrValue") for item in items}

    def to_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    temp = to_float(values.get("T1H"))
    pty = str(values.get("PTY", "0")).split(".")[0]

    # 하늘상태는 초단기예보에서 (실패해도 기온은 보여줌)
    sky = None
    try:
        fcst_time = now - timedelta(minutes=45)
        fcst_items = _call(
            "getUltraSrtFcst",
            fcst_time.strftime("%Y%m%d"),
            fcst_time.strftime("%H30"),
            nx, ny,
        )
        sky_items = sorted(
            (i for i in fcst_items if i["category"] == "SKY"),
            key=lambda i: (i["fcstDate"], i["fcstTime"]),
        )
        if sky_items:
            sky = str(sky_items[0]["fcstValue"])
    except WeatherError:
        pass

    if PTY_TEXT.get(pty):
        condition, icon = PTY_TEXT[pty], PTY_ICON.get(pty, "🌧️")
    else:
        condition, icon = SKY_TEXT.get(sky, "현재 날씨"), SKY_ICON.get(sky, "🌤️")

    result = {
        "ok": True,
        "temp": temp,
        "humidity": to_float(values.get("REH")),
        "wind": to_float(values.get("WSD")),
        "rain_1h": values.get("RN1"),
        "condition": condition,
        "icon": icon,
        "comment": _comment(temp, pty, sky),
        "grid": [nx, ny],
        "observed_at": ncst_time.strftime("%H:00"),
    }

    cache.set(cache_key, result, CACHE_SECONDS)
    return result
