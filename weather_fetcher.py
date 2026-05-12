import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import os

# ---------- 配置 ----------
API_BASE = "api.ztweather.com"
API_PATH = "/api/v1.1/forecast"
USERNAME = os.environ["API_USERNAME"]
PASSWORD = os.environ["API_PASSWORD"]
LAT_LON = "39.940833,112.869167"
PARAMS = "t_2m:C,relative_humidity_2m:p,wind_speed_10m:ms,wind_dir_10m:d,precip_1h:mm,global_rad:W,direct_rad:W,diffuse_rad:W"
INTERVAL_MIN = 15
OUTPUT_DIR = "output"

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
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    today_str = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d")
    output_file = f"{OUTPUT_DIR}/光伏气象预报_{today_str}.xlsx"
    df.to_excel(output_file, index=False)
    print(f"数据已保存至：{output_file}")

if __name__ == "__main__":
    fetch_and_save()
