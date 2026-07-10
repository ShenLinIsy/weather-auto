import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import os

# ---------- 配置 ----------
API_BASE = "api.ztweather.com"
API_PATH = "/api/v1.1/forecast"
USERNAME = os.environ["API_USERNAME"]
PASSWORD = os.environ["API_PASSWORD"]

# 参数（10个，包含天气现象）
PARAMS = "t_10m:C,relative_humidity_10m:p,pressure_10m:hPa,wind_speed_10m:ms,wind_dir_10m:d,wind_gusts_10m_1h:ms,precip_15min:mm,global_rad:W,effective_cloud_cover:p,weather_symbol_1h:idx"
INTERVAL_MIN = 15
OUTPUT_DIR = "output"


# 🌍 坐标列表（可自由增减）
# 格式：{"name": "站点名", "lat_lon": "纬度,经度"}
LOCATIONS = [
    {"name": "慈溪舒能", "lat_lon": "30.2670096532924,121.116422748094"},
    {"name": "镇海岚能", "lat_lon": "30.0094265067896,121.63719375602"},
    {"name": "慈溪协能", "lat_lon": "30.0909739575981,121.592623310078"},
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

# 🈴 中文表头映射（根据实际返回的列名调整）
COLUMN_CN_MAP = {
    "time": "时间(北京时间)",
    "valid_time": "时间(北京时间)",
    "t_10m:C": "气温(℃)",
    "relative_humidity_10m:p": "相对湿度(%)",
    "pressure_10m:hPa": "气压(hPa)",
    "wind_speed_10m:ms": "风速(m/s)",
    "wind_dir_10m:d": "风向(°)",
    "wind_gusts_10m_1h:ms": "阵风(m/s)",
    "precip_15min:mm": "降水量(mm)",
    "global_rad:W": "总辐射(W/m²)",
    "effective_cloud_cover:p": "云量(%)",
    "weather_symbol_1h:idx": "天气现象(编码)",
    "天气现象": "天气现象"  # 我们手动添加的中文列，保持不变
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

def get_tomorrow_utc() -> str:
    # 获取明天北京时间 00:00 对应的 UTC 时间
    today = datetime.now(timezone(timedelta(hours=8)))  # 当前北京时间
    tomorrow = today.date() + timedelta(days=1)
    target_cst = datetime.combine(tomorrow, datetime.min.time(),
                                  tzinfo=timezone(timedelta(hours=8)))
    return target_cst.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def fetch_one_location(name, lat_lon):
    """获取单个坐标的数据，返回处理好的 DataFrame（已转换时间和中文表头）"""
    start_utc = get_tomorrow_utc()
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
    
    # 替换中文表头
    df.rename(columns=COLUMN_CN_MAP, inplace=True)
    
    return df

def fetch_and_save():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    today_str = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d")
    output_file = f"{OUTPUT_DIR}/光伏气象预报_{today_str}.xlsx"
    
    # 用 ExcelWriter 写入多个 Sheet
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        for loc in LOCATIONS:
            try:
                df = fetch_one_location(loc["name"], loc["lat_lon"])
                # Sheet 名称不能超过31字符，且不能包含 [ ] : * ? / \
                sheet_name = loc["name"][:31]
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"✓ {loc['name']} 写入成功")
            except Exception as e:
                print(f"✗ {loc['name']} 获取失败：{e}")
    
    print(f"汇总文件已保存至：{output_file}")

if __name__ == "__main__":
    fetch_and_save()


