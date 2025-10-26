# bitget_private_ws.py  (RECV-ONLY)
import os, time, json, hmac, base64, hashlib, threading
import numpy as np
from websocket import WebSocketApp
from shm_ring import ShmRing
from layouts import PRIVATE_EXEC_DTYPE

#PRV_URL = "wss://ws.bitget.com/v2/ws/private"
PRV_URL ="wss://wspap.bitget.com/v2/ws/private" #Demo
#API_KEY        = os.getenv('BITGET_API_KEY',        '')
#API_SECRET     = os.getenv('BITGET_API_SECRET',     '')
API_PASSPHRASE = os.getenv('BITGET_PASSPHRASE',     '')
API_KEY = '' #Demo
API_SECRET = '' #Demo
HEARTBEAT_INTERVAL = 20  
HEARTBEAT_TIMEOUT  = 70  
def _ts_ms_str(): return str(int(time.time() * 1000))

def _sign(ts, method, path):
    msg = ts + method + path
    d = hmac.new(API_SECRET.encode(), msg.encode(), hashlib.sha256).digest()
    return base64.b64encode(d).decode()

def _status_to_code(s: str) -> int:
    s = (s or "").lower()
    if s in ("live","new","open","created","accepted"): return 0
    if s in ("filled","done"): return 1
    if s in ("partially_filled","partial-fill","part"): return 2
    if s in ("canceled","cancelled"): return 3
    if s in ("rejected","reject"): return 4
    if s in ("expired","ioc_exhaust"): return 5
    return 0

def _side_to_int(s: str) -> int:
    s = (s or "").lower()
    if s == "buy": return +1
    if s == "sell": return -1
    return 0



def _start_app_heartbeat(ws, last_pong: dict):
    def _loop():
        while True:
            time.sleep(HEARTBEAT_INTERVAL)
            try:
                if not (ws.sock and ws.sock.connected):
                    break
                ws.send("ping")  # Bitget 문자열 핑 받음 좀 이상함..자체 ping 보내면 반응없음
            except Exception:
                break
            # pong 타임아웃 체크
            if int(time.time()*1000) - last_pong["ts"] > HEARTBEAT_TIMEOUT*1000:
                try: ws.close()  # run_forever 루프 종료 -> 바깥에서 재연결
                except: pass
                break
    threading.Thread(target=_loop, daemon=True).start()

def bitget_private_ws_worker(cfg, shm_name_exec: str, capacity: int, shared):
    ring_exec = ShmRing(shm_name_exec, PRIVATE_EXEC_DTYPE, capacity, create=False)

    inst_type  = str(cfg.get("bitget_product_type", "USDT-FUTURES"))
    inst_id    = "default" 
    shared["bg_priv_state"] = "starting"
    last_pong = {"ts": int(time.time() * 1000)}

    # ----- backoff generator (로컬) -----
    def _backoff_gen():
        t = 0.5
        while True:
            yield t
            t = min(t * 2, 12)
    bo = _backoff_gen()

    def reset_backoff():
        nonlocal bo
        bo = _backoff_gen()
    # ------------------------------------

    def on_open(ws):
        reset_backoff()                # 연결 성공 시 백오프 리셋
        _start_app_heartbeat(ws, last_pong)  
        ts = _ts_ms_str()

        print(_sign(ts,"GET","/user/verify"))
        ws.send(json.dumps({
            "op":"login",
            "args":[{"apiKey":API_KEY,"passphrase":API_PASSPHRASE,"timestamp":ts,"sign":_sign(ts,"GET","/user/verify")}]
        }))
        shared["bg_priv_state"] = "login_sent"

    def on_message(ws, message):
        # 1) 핑/퐁 처리
        if message == "pong":
            last_pong["ts"] = int(time.time() * 1000)
            return
        try:
            data = json.loads(message)
        except Exception:
            return
        if isinstance(data, dict) and data.get("event") == "pong":

            last_pong["ts"] = int(time.time() * 1000)
            return

        evt = data.get("event")
        if evt == "login":
            if data.get("code") in (0,"0",None):
                shared["bg_priv_state"] = "login_ok"
                ws.send(json.dumps({
                    "op":"subscribe",
                    "args":[
                        {"instType":inst_type,"channel":"orders","instId":inst_id},
                        {"instType":inst_type,"channel":"fill","instId":inst_id},
                    ]
                }))
            else:
                shared["bg_priv_state"] = f"login_fail:{data.get('code')}"
            return

        if evt == "subscribe":
            shared["bg_priv_state"] = "live"
            return

        arg = data.get("arg", {})
        ch = (arg.get("channel") or "").lower()
        rows = data.get("data") or []
        ts = int(data.get("ts") or int(time.time() * 1000))
        print(data)
        if ch in ("fill"):
            for d in rows:
                order_id = d.get("orderId") or ""
                client_oid = d.get("clientOId") or d.get("clientOid") or "0"
                try:
                    coid = int(client_oid)
                except:
                    coid = 0

                # 공통값
                side = _side_to_int(d.get("side"))
                size0 = float(d.get("size") or 0)

                # --- 채널별로 역할 분리 ---
                if ch == "fill":
                    # 체결 이벤트만: 이번 체결분을 last_fill로!
                    last_fill = float(d.get("baseVolume") or 0)
                    last_px = float(d.get("price") or d.get("fillPrice") or 0)
                    # 누적 체결은 fill에도 있을 수 있지만, 확실한 건 orders 쪽
                    acc_fill = float(d.get("accBaseVolume") or 0)
                    # 상태는 fill엔 없거나 불명확 
                    status = 1

                else:  # ch == "orders"
                    # 상태/누적/평균가 업데이트 역할
                    status = _status_to_code(d.get("status"))
                    acc_fill = float(d.get("accBaseVolume") or d.get("baseVolume") or 0)
                    
                    last_fill = 0.0
                    last_px = float(d.get("fillPrice") or d.get("price") or 0)

                avg_px = float(d.get("priceAvg") or d.get("price") or 0)

                rec = np.zeros((), dtype=PRIVATE_EXEC_DTYPE)
                rec["ts"] = ts
                rec["client_oid"] = coid
                rec["order_id"] = order_id
                rec["side"] = side
                rec["status"] = status
                rec["size"] = size0
                rec["acc_fill"] = acc_fill
                rec["last_fill"] = last_fill  #  fill에서만 >0, orders는 0
                rec["last_price"] = last_px
                rec["avg_price"] = avg_px

                ring_exec.push(rec)
                # print(rec)  

    def on_error(ws, err): shared["bg_priv_state"] = f"error:{err}"
    def on_close(ws, *a):  shared["bg_priv_state"] = "closed"

    while True:
        ws = WebSocketApp(PRV_URL, on_open=on_open, on_message=on_message,
                          on_error=on_error, on_close=on_close)
        try:
            ws.run_forever(ping_interval=0, ping_timeout=None)  # control ping/pong
        except Exception as e:
            shared["bg_priv_state"] = f"crashed:{e}"
        # 실패/종료 후 지수 백오프 슬립
        try:
            time.sleep(next(bo))
        except StopIteration:
            bo = _backoff_gen()
            time.sleep(next(bo))
