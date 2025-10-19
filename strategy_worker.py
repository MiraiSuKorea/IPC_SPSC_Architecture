# strategy_worker.py
import time, traceback, numpy as np
from shm_ring import ShmRing
from layouts import TRADE_DTYPE, BOOK_DTYPE

def strategy_worker(cfg, shared, shm_trades: str, shm_book: str, shm_bg_books: str):
    print("[strat] importing cython bot…", flush=True)
    try:
        from qty_based_leverage_trading import Avellaneda_Stoikov_marketmaking as Bot
    except Exception:
        print("[strat] import failed:\n", traceback.format_exc(), flush=True)
        return

    bot = Bot(
        ticker=str(cfg["ticker"]),
        base=str(cfg["base"]),
        settle=str(cfg["settle"]),
        magic=int(cfg["magic"]),
        interval=str(cfg.get("interval", "1s")),
        bet_amount=float(cfg["bet_amount"]),
        minqty=int(cfg["minqty"]),
        numOrders=int(cfg["numOrders"]),
        bitget_ticker=str(cfg["bitget_ticker"])
    )

    ring_tr = ShmRing(shm_trades, TRADE_DTYPE, capacity=cfg.get("tr_capacity", 1_000), create=False)
    ring_ob = ShmRing(shm_book,   BOOK_DTYPE,  capacity=cfg.get("ob_capacity",    1_000), create=False)
    ring_bg = ShmRing(shm_bg_books, BOOK_DTYPE, capacity=cfg.get("bg_ob_capacity", 1_000), create=False)

    BATCH = 1024
    last_bg_px = 0.0

    while True:
        try:
            # 최신 북 1장
            ob = ring_ob.latest()
            if ob is not None:
                ob_ts, bbid, bqty, bask, aqty = ob
                best_bid = bbid; best_ask = bask
                best_bqty = bqty; best_aqty = aqty
            else:
                best_bid = best_ask = 0.0
                best_bqty = best_aqty = 0.0

            # 최신 Bitget book 가격
            bg = ring_bg.latest()
            if bg is not None:
                bg_ob_ts, bg_bbid, bg_bqty, bg_bask, bg_aqty = bg
                bg_best_bid = bg_bbid; bg_best_ask = bg_bask
                bg_best_bqty = bg_bqty; bg_best_aqty = bg_aqty
            else:
                bg_best_bid = bg_best_ask = 0.0
                bg_best_bqty = bg_best_aqty = 0.0

            # Binance 트레이드 벌크 소비
            chunk = ring_tr.pop_many(BATCH)
            if chunk is None:
                # 바쁜 대기 최소화
                time.sleep(0.0001)
                continue


            for ts, px, qty, sell, tid in chunk:
                bot.feed_trade(
                    float(px), float(qty), bool(sell), int(ts),
                    [best_bid], [best_bqty], [best_ask], [best_aqty],
                    [bg_best_bid], [bg_best_bqty], [bg_best_ask], [bg_best_aqty],  # ← NEW: Bitget futures last trade price
                )

        except KeyboardInterrupt:
            print("[strat] ^C, exit.")
            break
        except Exception:
            print("[strat] loop err:\n", traceback.format_exc(), flush=True)
            time.sleep(0.01)
