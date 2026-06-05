import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import os

# ---------- 配置 ----------
API_BASE = "api.ztweather.com"
API_PATH = "/api/v1.1/forecast"
USERNAME = os.environ["API_USERNAME"]
PASSWORD = os.environ["API_PASSWORD"]

# 参数设置（10个，含天气现象）
PARAMS = "t_10m:C,relative_humidity_10m:p,pressure_10m:hPa,wind_speed_10m:ms,wind_dir_10m:d,wind_gusts_10m_1h:ms,precip_15min:mm,global_rad:W,effective_cloud_cover:p,weather_symbol_1h:idx"
INTERVAL_MIN = 15
OUTPUT_DIR = "output"

# 🌍 坐标列表（可自由增减）
# 格式：{"name": "站点名", "lat_lon": "纬度,经度"}
LOCATIONS = [
    {"name": "慈溪舒能", "lat_lon": "30.2670096532924,121.116422748094"},
    {"name": "镇海岚能", "lat_lon": "30.0094265067896,121.63719375602"},
    {"name": "杭州舒能", "lat_lon": "30.2767248359807,120.695208299293"},
    {"name": "长兴公司", "lat_lon": "30.9193523361022,119.928042976362"},
    {"name": "夏湖光伏", "lat_lon": "30.9558830982346,120.80093313297"},
    {"name": "兰溪公司", "lat_lon": "29.26707531894,119.35926233301"}
    # 更多站点继续往下加即可，注意逗号隔开
]

# 天气现象编码表
WEATHER_MAP = {
    1: "晴天", 2: "少云", 3: "晴转多云", 4: "全天多云",
    5: "降雨", 6: "雨夹雪", 7: "雪", 8: "暴雨",
    9: "暴雪", 10: "雨夹雪较大", 11: "薄雾", 12: "浓雾",
    13: "冻雨", 14: "雷暴", 15: "毛毛雨", 16: "沙尘暴"
}

def decode_weather(val):
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

def fetch_one_location(name, lat_lon):
    """获取单个坐标的数据并返回 DataFrame（已处理时区和天气含义）"""
    start_utc = get_day_after_tomorrow_utc()
    time_segment = f"{start_utc}P1D:PT{INTERVAL_MIN}M"
    full_url = f"http://{API_BASE}{API_PATH}/{time_segment}/{PARAMS}/{lat_lon}/csv"
    print(f"请求 {name} ({lat_lon})...")
    resp = requests.get(full_url, auth=(USERNAME, PASSWORD), timeout=60)
    resp.raise_for_status()
    
    df = pd.read_csv(pd.io.common.StringIO(resp.text))
    
    # 时间列 UTC→北京时间
    first_col = df.columns[0]
    df[first_col] = pd.to_datetime(df[first_col], utc=True)
    df[first_col] = df[first_col].dt.tz_convert('Asia/Shanghai')
    df[first_col] = df[first_col].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # 添加天气现象含义列
    weather_col = "weather_symbol_1h:idx"
    if weather_col in df.columns:
        col_idx = df.columns.get_loc(weather_col) + 1
        df.insert(col_idx, "天气现象", df[weather_col].apply(decode_weather))
    
    return df

def fetch_and_save():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    today_str = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d")
    
    for loc in LOCATIONS:
        try:
            df = fetch_one_location(loc["name"], loc["lat_lon"])
            output_file = f"{OUTPUT_DIR}/{loc['name']}_气象预报_{today_str}.xlsx"
            df.to_excel(output_file, index=False)
            print(f"✓ {loc['name']} 保存成功：{output_file}")
        except Exception as e:
            print(f"✗ {loc['name']} 获取失败：{e}")

if __name__ == "__main__":
    fetch_and_save()
