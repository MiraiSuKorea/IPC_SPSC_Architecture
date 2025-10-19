# run_lowlat.py
import os, time, signal
from multiprocessing import Process, Manager, set_start_method

from shm_ring import ShmRing
from layouts import (
    TRADE_DTYPE, BOOK_DTYPE,
    ORDER_FLAG_DTYPE, ORDER_REPORT_DTYPE, FILL_REPORT_DTYPE,
    PRIVATE_EXEC_DTYPE,BG_WS_CMD_DTYPE
)
from ws_workers import trade_ws_worker, book_ws_worker
from bitget_ws_workers import bitget_futures_book_ws_worker
from bitget_private_ws import bitget_private_ws_worker
from strategy_worker import strategy_worker
# Bitget



# ---------- NEW: top-level order process target (픽클 가능) ----------
def order_main(cfg):
    # Cython ordersystem 모듈 import 는 child 프로세스에서
    from ordersystem import Ordersystem
    o = Ordersystem({
        **cfg,
        "of_ring": cfg["ring_of"],
        "or_ring": cfg["ring_or"],
        "fl_ring": cfg["ring_fl"],
        "bg_priv_ring": cfg["ring_bg_priv"],
    })
    o.start()


def build_cfg():
    return {
        "ticker": "SOLUSDT",
        "base": "SOL",
        "settle": "USDT",
        "depth_levels": 5,
        "depth_speed_ms": 100,

        "bitget_ticker": "SOLUSDT", ##주문 넣을때
        "bitget_symbol": "SOLUSDT", ##웹소켓 사용시

        "BITGET_API_KEY": os.getenv("BITGET_API_KEY", ""),
        "BITGET_API_SECRET": os.getenv("BITGET_API_SECRET", ""),
        "BITGET_PASSPHRASE": os.getenv("BITGET_PASSPHRASE", ""),

        "bitget_product_type": "USDT-FUTURES",
        "bitget_margin_mode": "crossed",
        "bitget_margin_coin": "usdt",
        "rest_base": "https://api.bitget.com",

        "magic": 1, "interval": "1s",
        "bet_amount": 1.0, "minqty": 1, "numOrders": 5,

        "tr_capacity": 4096, "ob_capacity": 2048,
        "bg_ob_capacity": 2048,
        "of_capacity": 2048, "or_capacity": 4096, "fl_capacity": 8192,
        "bg_priv_capacity": 8192,

        "ring_tr_bi": "RING_TR_BI",
        "ring_ob_bi": "RING_OB_BI",
        "ring_ob_bg": "RING_OB_BG",
        "ring_of":    "RING_ORDER_FLAGS",
        "ring_or":    "RING_ORDER_REPORT",
        "ring_fl":    "RING_FILL_REPORT",
        "ring_bg_priv": "RING_BG_PRIV",
        "ring_bg_cmd": "RING_BG_CMD",
    }


def create_rings(cfg):
    rings = {}
    rings["TR_BI"] = ShmRing(cfg["ring_tr_bi"], TRADE_DTYPE, cfg["tr_capacity"], create=True) #Trade Binance
    rings["OB_BI"] = ShmRing(cfg["ring_ob_bi"], BOOK_DTYPE,  cfg["ob_capacity"], create=True) #Orderbook Binance
    rings["OB_BG"] = ShmRing(cfg["ring_ob_bg"], BOOK_DTYPE, cfg["bg_ob_capacity"], create=True) #Orderbook Bitget
    rings["OF"]    = ShmRing(cfg["ring_of"],    ORDER_FLAG_DTYPE,   cfg["of_capacity"], create=True) #OrderFlag
    rings["OR"]    = ShmRing(cfg["ring_or"],    ORDER_REPORT_DTYPE, cfg["or_capacity"], create=True) #OrderReport
    rings["FL"]    = ShmRing(cfg["ring_fl"],    FILL_REPORT_DTYPE,  cfg["fl_capacity"], create=True) #FillReport
    rings["BGPRV"] = ShmRing(cfg["ring_bg_priv"], PRIVATE_EXEC_DTYPE, cfg["bg_priv_capacity"], create=True)
    rings["BG_CMD"] = ShmRing(cfg["ring_bg_cmd"], BG_WS_CMD_DTYPE, cfg["bg_priv_capacity"], create=True)

    return rings


# ---------- NEW: 안전 정리 (뷰 먼저 해제) ----------
def close_and_unlink_all(rings):
    # memoryview/ndarray 참조 먼저 해제
    for r in rings.values():
        try:
            # ShmRing 내부 속성 해제 (있을 때만)
            if hasattr(r, "arr"):     del r.arr
            if hasattr(r, "data_mv"): del r.data_mv
        except Exception:
            pass

    # close
    for r in rings.values():
        try: r.close()
        except Exception: pass

    time.sleep(0.05)  # 잠깐 대기 (윈도우에서 도움 됨)

    # unlink
    for r in rings.values():
        try: r.unlink()
        except Exception: pass


def main():
    try:
        set_start_method("spawn")
    except RuntimeError:
        pass

    cfg = build_cfg()
    rings = create_rings(cfg)
    mgr = Manager()
    shared = mgr.dict()

    procs = []

    procs.append(Process(target=trade_ws_worker,
                         args=(cfg, cfg["ring_tr_bi"], cfg["tr_capacity"], shared),
                         daemon=True))
    procs.append(Process(target=book_ws_worker,
                         args=(cfg, cfg["ring_ob_bi"], cfg["ob_capacity"], shared),
                         daemon=True))
    procs.append(Process(target=bitget_futures_book_ws_worker,
                         args=(cfg, cfg["ring_ob_bg"], cfg["bg_ob_capacity"], shared),
                         daemon=True))
    procs.append(Process(target=bitget_private_ws_worker,
                         args=(cfg, cfg["ring_bg_priv"],  cfg["bg_priv_capacity"], shared),
                         daemon=True))

    # strategy: Binance OB/Trades + Bitget Orderbook 전달
    procs.append(Process(target=strategy_worker,
                         args=(cfg, shared, cfg["ring_tr_bi"], cfg["ring_ob_bi"], cfg["ring_ob_bg"]),
                         daemon=True))

    # ---------- CHANGED: order_main 은 top-level 함수 ----------
    procs.append(Process(target=order_main, args=(cfg,), daemon=True))

    for p in procs:
        p.start()
    print("[main] started. Ctrl+C to stop.", flush=True)

    stopping = False

    def handle_sigint(signum, frame):
        nonlocal stopping
        if stopping: return
        stopping = True
        print("\n[main] stopping…", flush=True)

    signal.signal(signal.SIGINT, handle_sigint)

    try:
        while not stopping:
            time.sleep(1.0)
            print(
                f"BINANCE tr={shared.get('tr_ws_state')} "
                f"ob={shared.get('ob_ws_state')} | "
                f"BITGET pub-tr={shared.get('bg_books_state')} priv={shared.get('bg_priv_state')} | "
                f"last BiT={shared.get('last_trade_ts')} BiOB={shared.get('last_book_ts')} "
                f"BgOB={shared.get('last_bg_books_ts')} BgPriv={shared.get('bg_priv_last_ts')}",
                flush=True
            )
    finally:
        for p in procs:
            try: p.terminate()
            except Exception: pass
        close_and_unlink_all(rings)
        print("[main] cleaned. bye.", flush=True)


if __name__ == "__main__":
    main()
