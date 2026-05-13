import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import os

# ---------- 配置 ----------
API_BASE = "api.ztweather.com"
API_PATH = "/api/v1.1/forecast"
USERNAME = os.environ["API_USERNAME"]
PASSWORD = os.environ["API_PASSWORD"]
LAT_LON = "30.01083,121.63147"
# 包含天气现象的核心参数（10个）
PARAMS = "t_10m:C,relative_humidity_10m:p,pressure_10m:hPa,wind_speed_10m:ms,wind_dir_10m:d,wind_gusts_10m_1h:ms,precip_15min:mm,global_rad:W,effective_cloud_cover:p,weather_symbol_1h:idx"
INTERVAL_MIN = 15
OUTPUT_DIR = "output"

# 天气现象编码表
WEATHER_MAP = {
    1: "晴天", 2: "少云", 3: "晴转多云", 4: "全天多云",
    5: "降雨", 6: "雨夹雪", 7: "雪", 8: "暴雨",
    9: "暴雪", 10: "雨夹雪较大", 11: "薄雾", 12: "浓雾",
    13: "冻雨", 14: "雷暴", 15: "毛毛雨", 16: "沙尘暴"
}

def decode_weather(val):
    """将数值转为中文含义，自动处理夜间标记"""
    if pd.isna(val):
        return ""
    try:
        v = int(val)
    except ValueError:
        return f"无效({val})"
    night = ""
    if v >= 100:
        night = "夜间"
        v -= 100
    return night + WEATHER_MAP.get(v, f"未知({v})")

# --------------------------

def get_day_after_tomorrow_utc() -> str:
    today = datetime.now(timezone(timedelta(hours=8)))
    day_after_tomorrow = today.date() + timedelta(days=2)
    target_cst = datetime.combine(
        day_after_tomorrow, datetime.min.time(),
        tzinfo=timezone(timedelta(hours=8))
    )
    return target_cst.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def fetch_and_save():
    start_utc = get_day_after_tomorrow_utc()
    time_segment = f"{start_utc}P1D:PT{INTERVAL_MIN}M"
    full_url = f"http://{API_BASE}{API_PATH}/{time_segment}/{PARAMS}/{LAT_LON}/csv"
    print(f"请求时间（UTC）：{start_utc}")
    print(f"坐标：{LAT_LON}")
    resp = requests.get(full_url, auth=(USERNAME, PASSWORD), timeout=60)
    resp.raise_for_status()
    
    df = pd.read_csv(pd.io.common.StringIO(resp.text))
    
    # ---------- 时间列 UTC→北京时间 ----------
    first_col = df.columns[0]
    df[first_col] = pd.to_datetime(df[first_col], utc=True)
    df[first_col] = df[first_col].dt.tz_convert('Asia/Shanghai')
    df[first_col] = df[first_col].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # ---------- 新增：天气现象含义列 ----------
    weather_col = "weather_symbol_1h:idx"
    if weather_col in df.columns:
        # 在天气现象数值列右边插入含义列
        col_idx = df.columns.get_loc(weather_col) + 1
        df.insert(col_idx, "天气现象", df[weather_col].apply(decode_weather))
    # -----------------------------------------
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    today_str = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d")
    output_file = f"{OUTPUT_DIR}/光伏气象预报_{today_str}.xlsx"
    df.to_excel(output_file, index=False)
    print(f"数据已保存至：{output_file}")

if __name__ == "__main__":
    fetch_and_save()
