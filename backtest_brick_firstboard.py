#!/usr/bin/env python3
"""
砖型图 + 趋势 + 首板 回测策略
-------------------------------
选股逻辑（通达信）：
    VAR1A := (HHV(HIGH,4)-CLOSE)/(HHV(HIGH,4)-LLV(LOW,4))*100 - 90
    VAR2A := SMA(VAR1A,4,1) + 100
    VAR3A := (CLOSE-LLV(LOW,4))/(HHV(HIGH,4)-LLV(LOW,4))*100
    VAR4A := SMA(VAR3A,6,1)
    VAR5A := SMA(VAR4A,6,1) + 100
    VAR6A := VAR5A - VAR2A
    砖型图 := IF(VAR6A>4, VAR6A-4, 0)

    白线 := EMA(EMA(CLOSE,10),10)
    黄线 := (MA14+MA28+MA57+MA114)/4
    COND_TREND := 白线 > 黄线

    绿转红 := REF(砖型图 上升,1)=False AND 砖型图 上升
    BASE_COND := 绿转红 AND 红色量 > 前绿色量 * 2/3

    三连板 := COUNT(CLOSE>REF(CLOSE,1)*1.095, 3)=3
    断板日 := REF(三连板,1) AND CLOSE<=REF(CLOSE,1)*1.095
    断板天数 := BARSLAST(断板日)
    首板 := 断板天数∈[2,19] AND CLOSE>REF(CLOSE,1)*1.095

    选股 := BASE_COND AND COND_TREND AND 首板

交易规则：
    - 触发选股次日开盘买入，半仓（50% 可用资金）
    - 持仓第二日（买入后第一个交易日）开盘卖出（近似9:33）
    - 同日多信号：取 成交量/前日成交量 比值最大的一只

股票池：沪深两市市值 > 100亿，排除 ST、北交所
回测区间：2024-05-26 ~ 2026-05-26
"""

import argparse
import json
import math
import os
import pickle
import subprocess
import sys
import time
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# ── 导入 paper_trading 常量（只用 normalize_code 做兼容，主数据路径已重写）──
_PT_SKILL = Path.home() / ".claude/skills/a-share-paper-trading/scripts"
_AD_SKILL  = Path.home() / ".claude/skills/a-share-data/scripts"
sys.path.insert(0, str(_PT_SKILL))

# 当前 Python 可执行路径（anaconda）
_PYTHON = sys.executable

# ─────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────
BACKTEST_START = "2024-05-26"
BACKTEST_END   = "2026-05-26"
FETCH_START    = "2023-10-01"   # 多取 ~170 个交易日作为指标暖机期
INITIAL_CASH   = 1_000_000.0
POSITION_RATIO = 0.50           # 半仓
MAX_WORKERS    = 4    # 避免 Tencent/Sina API 限速
CACHE_DIR      = Path.home() / ".cache" / "backtest_brick"


# ─────────────────────────────────────────────
# 1. 股票池
# ─────────────────────────────────────────────

def build_universe() -> list[dict]:
    """
    调用 a-share-data fetch_realtime.py --all-quote 获取全市场行情，
    过滤市值 > 100亿、沪深、非ST。
    """
    print("正在获取全市场行情（市值过滤）...")
    result = subprocess.run(
        [_PYTHON, str(_AD_SKILL / "fetch_realtime.py"),
         "--all-quote", "--top", "6000", "--sort", "change_pct_desc", "--json"],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        print("  警告：fetch_realtime.py 返回错误，stderr:", result.stderr[:200])
    try:
        data = json.loads(result.stdout)
    except Exception:
        sys.exit("无法解析全市场行情，请检查 a-share-data skill 配置")

    # data 可能是 list 或 {"data": [...]}
    stocks = data if isinstance(data, list) else data.get("data", data.get("stocks", []))
    if not stocks:
        sys.exit("全市场行情为空")

    universe = []
    for s in stocks:
        raw_code = str(s.get("code", s.get("代码", ""))).strip()
        # 去掉 sh/sz 前缀，只保留6位数字
        code = raw_code[-6:] if len(raw_code) > 6 else raw_code.zfill(6)
        name    = s.get("name", s.get("名称", s.get("stock_name", "")))
        # market_cap 单位：亿元
        mktcap  = s.get("market_cap", s.get("总市值", s.get("mktcap", 0)))
        try:
            mktcap = float(mktcap) if mktcap else 0.0
        except (ValueError, TypeError):
            mktcap = 0.0

        if not code or not name:
            continue
        if not code[0] in ("0", "3", "6"):   # 排除北交所(8xx)、科创板特殊代码等
            continue
        if "ST" in name or "退" in name:
            continue
        if mktcap > 0 and mktcap < 100:      # market_cap 单位亿元，>100亿
            continue
        universe.append({"code": code, "name": name, "mktcap": mktcap})

    # 若全部 mktcap=0（字段名不匹配），则不按市值过滤（降级）
    has_mktcap = sum(1 for u in universe if u["mktcap"] > 0)
    if len(universe) > 0 and has_mktcap < len(universe) * 0.5:
        print(f"  警告：{len(universe)-has_mktcap} 只市值字段为0，跳过市值过滤（降级）")
        universe = [u for u in universe if u["code"][0] in ("0","3","6") and "ST" not in u["name"]]
    else:
        universe = [u for u in universe if u["mktcap"] >= 100]  # 保留市值>100亿

    print(f"  股票池：{len(universe)} 只（市值>100亿 沪深非ST）")
    return universe


# ─────────────────────────────────────────────
# 2. 历史数据获取与缓存
# ─────────────────────────────────────────────

import threading as _threading
import requests as _requests
from requests.adapters import HTTPAdapter as _HTTPAdapter
from urllib3.util.retry import Retry as _Retry

_thread_local = _threading.local()

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer":    "https://finance.eastmoney.com",
}
_SINA_URL    = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
_TENCENT_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"


def _make_session() -> _requests.Session:
    s = _requests.Session()
    s.headers.update(_HEADERS)
    s.trust_env = False   # 绕过系统代理
    retry = _Retry(total=3, connect=3, read=3, backoff_factor=0.3,
                   status_forcelist=(429, 500, 502, 503, 504),
                   allowed_methods=("GET",), raise_on_status=False)
    adapter = _HTTPAdapter(max_retries=retry)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


def _get_session():
    if not hasattr(_thread_local, "session"):
        _thread_local.session = _make_session()
    return _thread_local.session


def _tencent_kline(session, norm: str, count: int) -> pd.DataFrame:
    """从腾讯接口拉日K线，兼容含分红的7字段行"""
    url = f"{_TENCENT_URL}?param={norm},day,,,{count},qfq"
    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
        block = payload.get("data", {}).get(norm, {})
        arr = block.get("qfqday") or block.get("day") or []
        if not arr:
            return pd.DataFrame()
        rows = []
        for item in arr:
            if len(item) < 6:
                continue
            rows.append({
                "time":   item[0],
                "open":   item[1],
                "close":  item[2],   # 腾讯字段顺序: open, close, high, low
                "high":   item[3],
                "low":    item[4],
                "volume": item[5],
            })
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        df["time"]   = pd.to_datetime(df["time"])
        for c in ["open", "close", "high", "low", "volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        # 腾讯 open/close/high/low 顺序与标准不同，修正
        df = df.rename(columns={"close": "close_raw", "high": "high_raw", "low": "low_raw"})
        df = df.rename(columns={"close_raw": "close", "high_raw": "high", "low_raw": "low"})
        return df.sort_values("time").reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def _sina_kline(session, code: str, count: int) -> pd.DataFrame:
    """从新浪接口拉日K线，code 格式如 sh600519"""
    params = {"symbol": code, "scale": 240, "ma": 5, "datalen": count}
    try:
        resp = session.get(_SINA_URL, params=params, timeout=10)
        resp.raise_for_status()
        import json as _json
        data = _json.loads(resp.text)
        if not data or isinstance(data, dict):
            return pd.DataFrame()
        df = pd.DataFrame(data)
        if "day" in df.columns:
            df = df.rename(columns={"day": "time"})
        df["time"] = pd.to_datetime(df["time"])
        for c in ["open", "high", "low", "close", "volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return df[["time", "open", "high", "low", "close", "volume"]].sort_values("time").reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def _fetch_one(code: str) -> tuple[str, pd.DataFrame]:
    """用自定义 Tencent/Sina 请求获取单只股票日线（前复权），约 700 根"""
    # 腾讯使用 sh/sz 前缀，新浪也一样
    prefix = "sh" if code.startswith("6") else "sz"
    norm   = f"{prefix}{code}"
    session = _get_session()
    count  = 700

    try:
        df = _tencent_kline(session, norm, count)
        if df.empty:
            df = _sina_kline(session, norm, count)
        if df is None or df.empty:
            return code, pd.DataFrame()

        for c in ["open", "high", "low", "close", "volume"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.dropna(subset=["close"]).sort_values("time").reset_index(drop=True)
        df = df[(df["time"] >= pd.Timestamp(FETCH_START)) &
                (df["time"] <= pd.Timestamp(BACKTEST_END))]
        return code, df
    except Exception as _e:
        return code, pd.DataFrame()


def load_all_data(universe: list[dict], force_refresh: bool = False) -> dict[str, pd.DataFrame]:
    """并行获取所有股票数据，使用本地缓存（当天有效）"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    cache_file = CACHE_DIR / f"data_{today}.pkl"

    if not force_refresh and cache_file.exists():
        print(f"命中缓存：{cache_file}")
        with open(cache_file, "rb") as f:
            return pickle.load(f)

    codes = [r["code"] for r in universe]
    total = len(codes)
    print(f"开始并行拉取 {total} 只股票数据（workers={MAX_WORKERS}）...")

    all_data: dict[str, pd.DataFrame] = {}
    failed: list[str] = []
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {ex.submit(_fetch_one, code): code for code in codes}
        done = 0
        for fut in as_completed(futs):
            code, df = fut.result()
            done += 1
            if not df.empty:
                all_data[code] = df
            else:
                failed.append(code)
            if done % 100 == 0:
                elapsed = time.time() - t0
                print(f"  进度：{done}/{total}，成功：{len(all_data)}，失败：{len(failed)}，耗时：{elapsed:.0f}s")

    elapsed = time.time() - t0
    print(f"数据拉取完毕：成功 {len(all_data)} 只，失败 {len(failed)} 只，总耗时 {elapsed:.0f}s")
    if failed:
        print(f"  失败代码（前20）：{failed[:20]}")

    with open(cache_file, "wb") as f:
        pickle.dump(all_data, f)
    print(f"数据已缓存至 {cache_file}")
    return all_data


# ─────────────────────────────────────────────
# 3. 指标计算
# ─────────────────────────────────────────────

def _tdx_sma(series: pd.Series, n: int, m: int) -> pd.Series:
    """通达信 SMA(X, N, M) = M/N * X + (1-M/N) * SMA_prev"""
    alpha = m / n
    return series.ewm(alpha=alpha, adjust=False).mean()


def _barslast(cond: pd.Series) -> pd.Series:
    """BARSLAST(cond)：距上次 cond 为 True 经过的 bar 数，首次为 True 前返回 NaN"""
    result = []
    last = np.nan
    for v in cond:
        if bool(v):
            last = 0
        elif last == last:   # not nan
            last += 1
        result.append(last)
    return pd.Series(result, index=cond.index, dtype=float)


def calc_signals(df: pd.DataFrame) -> pd.Series:
    """
    对单只股票的 OHLCV DataFrame 计算选股信号。
    返回 bool Series（index 与 df 对齐）。
    同时返回 volume_ratio 供外部排序。
    """
    close  = df["close"]
    high   = df["high"]
    low    = df["low"]
    volume = df["volume"]

    # ── 砖型图 ──────────────────────────────
    hhv4 = high.rolling(4).max()
    llv4 = low.rolling(4).min()
    rng4 = (hhv4 - llv4).replace(0, np.nan)

    var1a = (hhv4 - close) / rng4 * 100 - 90
    var2a = _tdx_sma(var1a, 4, 1) + 100

    var3a = (close - llv4) / rng4 * 100
    var4a = _tdx_sma(var3a, 6, 1)
    var5a = _tdx_sma(var4a, 6, 1) + 100

    var6a = var5a - var2a
    brick = np.where(var6a > 4, var6a - 4, 0.0)
    brick = pd.Series(brick, index=df.index)

    # ── 砖型图信号 ────────────────────────────
    brick_prev1 = brick.shift(1)
    brick_prev2 = brick.shift(2)

    rising_now  = brick > brick_prev1          # 当前在涨
    rising_prev = brick_prev1 > brick_prev2    # 前一根也在涨

    # 绿转红：前一根没有上升（或下降/平），当前上升
    lv_zhuan_hong = (~rising_prev) & rising_now

    red_vol   = np.where(brick > brick_prev1, brick - brick_prev1, 0.0)
    green_vol = np.where(brick_prev1 > brick, brick_prev1 - brick, 0.0)
    red_vol   = pd.Series(red_vol,   index=df.index)
    green_vol = pd.Series(green_vol, index=df.index)
    qian_green = green_vol.shift(1)

    base_cond = lv_zhuan_hong & (red_vol > qian_green * (2 / 3))

    # ── 趋势 ──────────────────────────────────
    white = close.ewm(span=10, adjust=False).mean()
    white = white.ewm(span=10, adjust=False).mean()

    m1, m2, m3, m4 = 14, 28, 57, 114
    yellow = (
        close.rolling(m1).mean() +
        close.rolling(m2).mean() +
        close.rolling(m3).mean() +
        close.rolling(m4).mean()
    ) / 4

    cond_trend = white > yellow

    # ── 连板断板首板 ─────────────────────────
    limit_up = close > close.shift(1) * 1.095

    san_lian_ban = limit_up.rolling(3).sum() == 3

    duan_ban_day = san_lian_ban.shift(1).fillna(False).astype(bool) & (~limit_up)
    duan_ban_tian = _barslast(duan_ban_day)

    shou_ban = (
        (duan_ban_tian >= 2) &
        (duan_ban_tian <= 19) &
        limit_up
    )

    signal = base_cond & cond_trend & shou_ban
    return signal


def calc_signals_with_volratio(df: pd.DataFrame) -> pd.DataFrame:
    """返回含 signal(bool) 和 vol_ratio(float) 的 DataFrame，index 为 df.index"""
    sig = calc_signals(df)
    vol_ratio = df["volume"] / df["volume"].shift(1).replace(0, np.nan)
    return pd.DataFrame({"signal": sig, "vol_ratio": vol_ratio}, index=df.index)


# ─────────────────────────────────────────────
# 4. 费用模型
# ─────────────────────────────────────────────

def _is_sh(code: str) -> bool:
    return code.startswith("6") or code.startswith("9")


def calc_cost(code: str, amount: float, side: str) -> float:
    """返回总费用（佣金 + 过户费 + 印花税）"""
    commission  = max(5.0, round(amount * 0.0003, 2))
    transfer    = round(amount * 0.00001, 2) if _is_sh(code) else 0.0
    stamp_tax   = round(amount * 0.001, 2) if side == "sell" else 0.0
    return commission + transfer + stamp_tax


# ─────────────────────────────────────────────
# 5. 回测模拟
# ─────────────────────────────────────────────

def run_backtest(
    all_data:  dict[str, pd.DataFrame],
    code_name: dict[str, str],
    start:     str = BACKTEST_START,
    end:       str = BACKTEST_END,
    init_cash: float = INITIAL_CASH,
    dry_run:   bool = False,
) -> dict:
    """
    主回测循环。
    dry_run=True 时只打印前5条信号，不模拟交易。
    """
    start_dt = pd.Timestamp(start)
    end_dt   = pd.Timestamp(end)

    # ── 预计算所有股票的信号表 ────────────────
    print("计算各股票信号...")
    t0 = time.time()
    sig_tables: dict[str, pd.DataFrame] = {}
    for code, df in all_data.items():
        if len(df) < 120:
            continue
        try:
            s = calc_signals_with_volratio(df)
            s = s.copy()
            s["date"] = df["time"].values
            s.set_index("date", inplace=True)
            sig_tables[code] = s
        except Exception:
            pass
    print(f"  完成 {len(sig_tables)} 只，耗时 {time.time()-t0:.1f}s")

    # ── 取出全部交易日（回测区间） ────────────
    # 用某只数据量最大的股票的时间轴
    biggest = max(sig_tables.values(), key=len)
    trading_days = sorted(
        d for d in biggest.index
        if start_dt <= d <= end_dt
    )
    print(f"交易日数：{len(trading_days)}（{start} ~ {end}）")

    if dry_run:
        print("\n=== DRY-RUN：前10条选股信号 ===")
        count = 0
        for day in trading_days:
            hits = []
            for code, stbl in sig_tables.items():
                if day not in stbl.index:
                    continue
                row = stbl.loc[day]
                if row["signal"]:
                    hits.append((code, float(row["vol_ratio"]) if not pd.isna(row["vol_ratio"]) else 0.0))
            if hits:
                hits.sort(key=lambda x: -x[1])
                best = hits[0]
                name = code_name.get(best[0], "")
                df_s = all_data.get(best[0], pd.DataFrame())
                close_price = df_s.loc[df_s["time"] == day, "close"].values
                cp = close_price[0] if len(close_price) else "?"
                print(f"  {day.date()}  {best[0]} {name}  量比={best[1]:.2f}  收={cp}")
                count += 1
            if count >= 10:
                break
        return {}

    # ── 主循环 ─────────────────────────────────
    cash          = init_cash
    pending_buy   = None   # {"code", "name", "signal_date"}
    holding       = None   # {"code", "name", "qty", "buy_price", "buy_date", "sell_date"}
    trades        = []
    equity_curve  = []

    for i, day in enumerate(trading_days):
        day_str = day.strftime("%Y-%m-%d")

        # 1. 卖出（持仓第二日开盘，即 buy_date + 1 交易日 = 当天）
        if holding and holding["sell_date"] == day:
            code = holding["code"]
            df_s = all_data.get(code, pd.DataFrame())
            day_row = df_s[df_s["time"] == day]
            if not day_row.empty:
                sell_price = float(day_row["open"].values[0])
                qty        = holding["qty"]
                amount     = sell_price * qty
                cost       = calc_cost(code, amount, "sell")
                pnl        = amount - cost - holding["buy_price"] * qty - calc_cost(code, holding["buy_price"] * qty, "buy")
                cash       += amount - cost
                trades.append({
                    "signal_date": holding["signal_date"],
                    "code":        code,
                    "name":        holding["name"],
                    "buy_date":    holding["buy_date"].strftime("%Y-%m-%d"),
                    "buy_price":   round(holding["buy_price"], 3),
                    "sell_date":   day_str,
                    "sell_price":  round(sell_price, 3),
                    "qty":         qty,
                    "pnl":         round(pnl, 2),
                    "pnl_pct":     round(pnl / (holding["buy_price"] * qty) * 100, 2),
                    "vol_ratio":   holding.get("vol_ratio", None),
                })
                holding = None

        # 2. 买入（选股次日开盘）
        if pending_buy and pending_buy["buy_date"] == day and holding is None:
            code = pending_buy["code"]
            df_s = all_data.get(code, pd.DataFrame())
            day_row = df_s[df_s["time"] == day]
            if not day_row.empty:
                buy_price = float(day_row["open"].values[0])
                target    = cash * POSITION_RATIO
                qty       = int(target / buy_price // 100) * 100
                if qty >= 100:
                    cost   = calc_cost(code, buy_price * qty, "buy")
                    cash  -= buy_price * qty + cost
                    # 确定卖出日（下一个交易日）
                    sell_date = trading_days[i + 1] if i + 1 < len(trading_days) else None
                    if sell_date:
                        holding = {
                            "code":        code,
                            "name":        pending_buy["name"],
                            "qty":         qty,
                            "buy_price":   buy_price,
                            "buy_date":    day,
                            "sell_date":   sell_date,
                            "signal_date": pending_buy["signal_date"],
                            "vol_ratio":   pending_buy.get("vol_ratio"),
                        }
            pending_buy = None

        # 3. 今日持仓市值
        holding_mv = 0.0
        if holding:
            code  = holding["code"]
            df_s  = all_data.get(code, pd.DataFrame())
            row_c = df_s[df_s["time"] == day]
            if not row_c.empty:
                holding_mv = float(row_c["close"].values[0]) * holding["qty"]

        equity_curve.append({"date": day_str, "equity": round(cash + holding_mv, 2)})

        # 4. 今日选股（为下一个交易日准备买单），跳过已有挂单或持仓时
        if pending_buy is None and holding is None:
            hits = []
            for code, stbl in sig_tables.items():
                if day not in stbl.index:
                    continue
                row = stbl.loc[day]
                if row["signal"]:
                    vr = float(row["vol_ratio"]) if not pd.isna(row["vol_ratio"]) else 0.0
                    hits.append((code, vr))
            if hits:
                hits.sort(key=lambda x: -x[1])
                best_code, best_vr = hits[0]
                next_day = trading_days[i + 1] if i + 1 < len(trading_days) else None
                if next_day:
                    pending_buy = {
                        "code":        best_code,
                        "name":        code_name.get(best_code, ""),
                        "buy_date":    next_day,
                        "signal_date": day_str,
                        "vol_ratio":   best_vr,
                    }

    # 若还有持仓，用最后一日收盘计算未实现盈亏（不计入已完结交易）
    final_equity = equity_curve[-1]["equity"] if equity_curve else init_cash

    return {
        "trades":       trades,
        "equity_curve": equity_curve,
        "final_equity": final_equity,
        "init_cash":    init_cash,
    }


# ─────────────────────────────────────────────
# 6. 结果统计与输出
# ─────────────────────────────────────────────

def print_results(result: dict):
    trades       = result["trades"]
    equity_curve = result["equity_curve"]
    init_cash    = result["init_cash"]
    final_equity = result["final_equity"]

    total_return  = (final_equity - init_cash) / init_cash * 100
    years         = len(equity_curve) / 250
    annual_return = ((final_equity / init_cash) ** (1 / max(years, 0.1)) - 1) * 100

    # 最大回撤
    peak = init_cash
    max_dd = 0.0
    for pt in equity_curve:
        eq = pt["equity"]
        if eq > peak:
            peak = eq
        if peak > 0:
            dd = (peak - eq) / peak
            if dd > max_dd:
                max_dd = dd

    # 夏普（简化，无风险利率=3%）
    eq_series = pd.Series([p["equity"] for p in equity_curve])
    daily_ret = eq_series.pct_change().dropna()
    rf_daily  = 0.03 / 250
    sharpe    = ((daily_ret - rf_daily).mean() / daily_ret.std() * math.sqrt(250)) if daily_ret.std() > 0 else 0.0

    # 胜率
    sell_trades = [t for t in trades if "sell_date" in t]
    win_trades  = [t for t in sell_trades if t["pnl"] > 0]
    win_rate    = len(win_trades) / len(sell_trades) * 100 if sell_trades else 0.0
    avg_pnl_pct = sum(t["pnl_pct"] for t in sell_trades) / len(sell_trades) if sell_trades else 0.0

    print("\n" + "=" * 60)
    print("  砖型图·首板策略 回测结果")
    print("=" * 60)
    print(f"  初始资金：{init_cash:>12,.0f} 元")
    print(f"  最终净值：{final_equity:>12,.0f} 元")
    print(f"  总收益率：{total_return:>11.2f} %")
    print(f"  年化收益率：{annual_return:>9.2f} %")
    print(f"  最大回撤：{max_dd*100:>11.2f} %")
    print(f"  夏普比率：{sharpe:>11.2f}")
    print(f"  总交易笔数：{len(sell_trades):>8}")
    print(f"  胜率：{win_rate:>15.1f} %")
    print(f"  平均单笔盈亏：{avg_pnl_pct:>8.2f} %")
    print("=" * 60)

    # 交易明细（最近20笔）
    if sell_trades:
        print("\n── 交易明细（最新20笔）─────────────────────────")
        print(f"{'触发日':10} {'代码':6} {'名称':8} {'买入日':10} {'买价':>7} {'卖出日':10} {'卖价':>7} {'手数':>5} {'盈亏%':>7} {'量比':>5}")
        print("-" * 85)
        for t in sell_trades[-20:]:
            name = t["name"][:4] if t["name"] else ""
            vr   = f"{t['vol_ratio']:.2f}" if t.get("vol_ratio") else "  -"
            sign = "+" if t["pnl_pct"] >= 0 else ""
            print(
                f"{t['signal_date']:10} {t['code']:6} {name:4} "
                f"{t['buy_date']:10} {t['buy_price']:>7.2f} "
                f"{t['sell_date']:10} {t['sell_price']:>7.2f} "
                f"{t['qty']:>5} {sign}{t['pnl_pct']:>6.2f}% {vr:>5}"
            )

    # ASCII 净值曲线（月频）
    if equity_curve:
        print("\n── 月度净值曲线 ────────────────────────────────")
        monthly = {}
        for pt in equity_curve:
            ym = pt["date"][:7]
            monthly[ym] = pt["equity"]
        months = sorted(monthly.keys())
        if months:
            min_eq = min(monthly[m] for m in months)
            max_eq = max(monthly[m] for m in months)
            rng    = max_eq - min_eq or 1
            width  = 40
            print(f"  {'日期':7}  净值(万)  {'':30}")
            for m in months:
                eq   = monthly[m]
                bar  = int((eq - min_eq) / rng * width)
                ret  = (eq - init_cash) / init_cash * 100
                sign = "+" if ret >= 0 else ""
                print(f"  {m}  {eq/10000:>7.1f}  {'█' * bar}  ({sign}{ret:.1f}%)")


# ─────────────────────────────────────────────
# 7. 入口
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="砖型图·首板 A股回测")
    parser.add_argument("--start",         default=BACKTEST_START, help="回测开始日期 YYYY-MM-DD")
    parser.add_argument("--end",           default=BACKTEST_END,   help="回测结束日期 YYYY-MM-DD")
    parser.add_argument("--cash",          type=float, default=INITIAL_CASH, help="初始资金（元）")
    parser.add_argument("--refresh",       action="store_true",    help="强制重新拉取数据（忽略缓存）")
    parser.add_argument("--dry-run",       action="store_true",    help="只打印前10条信号，不模拟交易")
    args = parser.parse_args()

    print(f"砖型图·首板回测  {args.start} ~ {args.end}")
    print(f"初始资金：{args.cash:,.0f} 元，仓位：{POSITION_RATIO*100:.0f}%")

    # 1. 股票池
    universe  = build_universe()
    code_name = {r["code"]: r["name"] for r in universe}

    # 2. 数据获取
    all_data = load_all_data(universe, force_refresh=args.refresh)

    # 3. 回测
    result = run_backtest(
        all_data, code_name,
        start=args.start, end=args.end,
        init_cash=args.cash,
        dry_run=args.dry_run,
    )

    # 4. 输出
    if not args.dry_run:
        print_results(result)


if __name__ == "__main__":
    main()
