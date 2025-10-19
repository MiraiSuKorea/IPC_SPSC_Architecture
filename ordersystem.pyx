# ordersystem.pyx
# cython: language_level=3
# cython: boundscheck=False, wraparound=False, cdivision=True, nonecheck=False
import time, json, threading, hmac, base64, hashlib
cimport cython
import numpy as np
from websocket import WebSocketApp

from shm_ring import ShmRing
from layouts import ORDER_FLAG_DTYPE, ORDER_REPORT_DTYPE, FILL_REPORT_DTYPE, PRIVATE_EXEC_DTYPE

cdef inline long long _now_ms(): return <long long>(time.time()*1000)


cdef inline long long _to_ms():
    return <long long>(time.time()*1000)

cdef class Ordersystem:
    cdef dict cfg
    cdef str  symbol, inst_type, margin_mode, margin_coin
    cdef object r_flags, r_exec, r_orpt, r_frpt
    cdef dict orders
    cdef long long seq
    cdef bint running

    # WS 송신 전용
    cdef object _ws              # WebSocketApp
    cdef object _ws_lock         # send 보호용
    cdef bint   _ws_live
    cdef str    _api_key, _api_secret, _api_pass
    cdef int _ws_authed
    def __init__(self, dict cfg):
        self.cfg = cfg
        self.symbol     = <str>cfg.get("bitget_symbol", cfg.get("bitget_ticker","BTCUSDT"))
        self.inst_type  = <str>cfg.get("bitget_product_type","USDT-FUTURES")
        self.margin_mode= <str>cfg.get("bitget_margin_mode","crossed")
        self.margin_coin= (<str>cfg.get("bitget_margin_coin","USDT")).upper()

        self.r_flags = ShmRing(cfg.get("of_ring","RING_ORDER_FLAGS"), ORDER_FLAG_DTYPE, cfg.get("of_capacity",2048), create=False)
        self.r_exec  = ShmRing(cfg.get("bg_priv_ring","RING_BG_PRIV"), PRIVATE_EXEC_DTYPE, cfg.get("bg_priv_capacity",8192), create=False)
        self.r_orpt  = ShmRing(cfg.get("or_ring","RING_ORDER_REPORT"), ORDER_REPORT_DTYPE, cfg.get("or_capacity",4096), create=False)
        self.r_frpt  = ShmRing(cfg.get("fl_ring","RING_FILL_REPORT"),  FILL_REPORT_DTYPE,  cfg.get("fl_capacity",8192), create=False)


        self.orders = {}
        self.seq = (_now_ms() & 0x7fffffff)
        self.running = False
        self._ws_authed = False

        # ⚠️ 기본값은 비워두는 게 안전하지만, 기존 코드 호환
        #self._api_key    = <str>cfg.get("BITGET_API_KEY","bg_e06c596f7fb25fadf5bf491c026817ad")
        #self._api_secret = <str>cfg.get("BITGET_API_SECRET","ec5c829908079a8689793058e4107b8f2c4560721a59a9adce490f7cba00e5d2")
        self._api_key    = "bg_14f76b755786f092e1c10d5465cc99e1"
        self._api_secret = "0cf81f298b9abb8a7b561269a6313a8e314e0669ce167921d5c767f51292d742"
        self._api_pass   = "DavidLee"
        self._ws = None
        self._ws_lock = threading.Lock()
        self._ws_live = False

    cdef long long _oid(self):
        self.seq += 1
        return (_now_ms()<<20) | (self.seq & 0xfffff)

    # ===== WS helpers (sender) =====
    cdef str _ts_ms(self):
        return str(int(time.time()*1000))

    cdef str _sign(self, str ts, str method, str path):
        cdef str msg_str = ts + method + path
        cdef bytes key = self._api_secret.encode("utf-8")
        cdef bytes msg = msg_str.encode("utf-8")
        cdef bytes dig = hmac.new(key, msg, hashlib.sha256).digest()
        cdef str sig = base64.b64encode(dig).decode()
        return sig

    cdef void _ws_send_json(self, obj):
        # websocket-client는 스레드 세이프 아님 → send 보호
        try:
            msg = json.dumps(obj)
            with self._ws_lock:
                if self._ws is not None and self._ws_live:
                    self._ws.send(msg)

        except Exception as e:
            print(e)

    cdef void _ws_login(self):
        ts = self._ts_ms()
        payload = {
            "op":"login",
            "args":[{"apiKey":self._api_key,"passphrase":self._api_pass,"timestamp":ts,"sign":self._sign(ts,"GET","/user/verify")}]
        }


        self._ws_send_json(payload)

    cdef void _ws_place(self, int side, double size, double price, long long coid, bint is_limit, int force, bint reduce_only):
        cdef str side_s = "buy" if side>0 else "sell"
        cdef str order_type = "limit" if is_limit else "market"
        cdef dict params = {
            "orderType": order_type,
            "side": side_s,
            "size": str(size),
            "marginCoin": self.margin_coin,
            "force": {0:"gtc",1:"post_only",2:"fok",3:"ioc"}.get(force,"gtc"),
            "marginMode": self.margin_mode,

        }
        if is_limit:
            params["price"] = str(round(price,3))
        if reduce_only:
            params["reduceOnly"] = "YES"  # one-way-mode에서만 의미
        if coid > 0:
            params["clientOid"] = str(coid)

        pkt = {"op":"trade","args":[{
            "channel":"place-order",
            "id": str(coid),
            "instId": self.symbol,
            "instType": self.inst_type,
            "params": params
        }]}
        self._ws_send_json(pkt)

    cdef void _ws_cancel(self, long long coid):
        cdef dict params = {}
        params["clientOid"]= str(coid)
        pkt = {"op":"trade","args":[{
            "channel":"cancel-order",
            "id": str(coid),
            "instId": self.symbol,
            "instType": self.inst_type,
            "params": params
        }]}
        self._ws_send_json(pkt)

    # ===== WS 스레드 (재연결 + ping/pong) =====
    cdef object _mk_backoff(self):
        def _backoff_gen():
            t = 0.5
            while True:
                yield t
                t = t*2 if t < 12 else 12
        return _backoff_gen()

    cdef void _ws_thread_main(self):
        #cdef str url = "wss://ws.bitget.com/v2/ws/private"
        cdef str url = "wss://wspap.bitget.com/v2/ws/private"

        HEARTBEAT_INTERVAL = 10    # app ping
        HEARTBEAT_TIMEOUT  = 60    # ms 기준 환산은 아래에서
        CONTROL_PING_INT   = 10    # control frame ping

        # 가변 컨테이너들 (클로저에서 nonlocal 대체)
        bo_holder   = {"bo": self._mk_backoff()}
        last_pong   = {"ts": _to_ms()}   # 앱 레벨 pong 시각
        alive_flag  = {"alive": True}    # 스레드 생존 제어

        while self.running:
            self._ws_live = False

            def reset_backoff():
                bo_holder["bo"] = self._mk_backoff()

            def on_open(ws):



                # app-level ping loop ("ping" 문자열 송신 + pong 타임아웃 관리)
                def app_ping_loop():
                    while self.running and self._ws_live:
                        try:
                            if self._ws and getattr(self._ws, "sock", None) and self._ws.sock.connected:
                                # 문자열 ping
                                with self._ws_lock:
                                    if self._ws_live:
                                        self._ws.send("ping")
                            else:
                                break
                        except Exception:
                            break

                        # pong 타임아웃 → 연결 닫아서 재연결 유도
                        if (_to_ms() - <long long>last_pong["ts"]) > <long long>(HEARTBEAT_TIMEOUT*1000):
                            try:
                                self._ws.close()
                            except Exception:
                                pass
                            break
                        time.sleep(HEARTBEAT_INTERVAL)
                # 로그인
                self._ws_authed = False
                self._ws = ws
                self._ws_live = True
                last_pong["ts"] = _to_ms()
                reset_backoff()
                threading.Thread(target=app_ping_loop,  daemon=True).start()
                time.sleep(0.1)
                self._ws_login()


            def on_message(ws, message):
                # 문자열 pong

                print(message)
                if message == "pong":
                    last_pong["ts"] = _to_ms()
                    return
                # JSON
                try:
                    data = json.loads(message)
                except Exception:
                    return
                if isinstance(data, dict):
                    evt = data.get("event")
                    if evt == "login":
                        code = str(data.get("code",""))
                        # Bitget 성공코드: "0" 또는 "00000"
                        self._ws_authed = (code in ("0","00000"))
                        if not self._ws_authed:
                            print("WS LOGIN FAILED:", data)
                        return
                    if evt == "error":
                        return
                    elif evt == "pong":
                        last_pong["ts"] = _to_ms()
                        return
                    # login 이벤트는 송신 전용이므로 통과
                    # 필요 시 에러 로깅 등 확장 가능
                # 기타 메세지는 무시(주로 trade 응답, 에러 등)
            def on_error(ws, err):
                self._ws_live = False

            def on_close(ws, *a):
                self._ws_live = False

            ws = WebSocketApp(url, on_open=on_open, on_message=on_message,
                              on_error=on_error, on_close=on_close)
            try:
                ws.run_forever(ping_interval=0, ping_timeout=None)
            except Exception:
                pass

            if not self.running:
                break

            # 끊김 → 백오프 후 재시도
            try:
                dt = next(bo_holder["bo"])
            except Exception:
                dt = 1.0
            time.sleep(dt)

        # 종료 시 플래그 정리
        self._ws_live = False

    cdef void _ensure_ws(self):
        # 연결 없거나 죽었으면 WS 송신 스레드 보장
        if (self._ws is None) or (not self._ws_live):
            t = threading.Thread(target=self._ws_thread_main, daemon=True)
            t.start()
            # 로그인/오픈 약간의 유예
            time.sleep(0.05)

    # ===== 메인 루프 =====
    cpdef void start(self):
        self.running = True
        self._ensure_ws()
        BATCH=1024
        while self.running:
            # 1) 전략 → 주문플래그 수신 → WS place (post_only maker)
            chunk = self.r_flags.pop_many(BATCH)
            if chunk is not None:
                for rec in chunk: self._on_flag(rec)

            # 2) Private WS orders/fill 이벤트 소비
            execs = self.r_exec.pop_many(BATCH)
            if execs is not None:
                for e in execs:
                    print("실행되는주문 :",e)
                    self._on_exec(e)

            # 3) 타임아웃 스캔
            self._scan_timeouts()
            time.sleep(0.00001)

    cpdef void stop(self):
        self.running = False
        # run_forever는 내부에서 빠져나오고 _ws_live False로 정리됨
        try:
            if self._ws is not None:
                self._ws.close()
        except Exception:
            pass

    cdef void _on_flag(self, rec):
        cdef long long coid = int(rec["client_oid"]) or self._oid()
        cdef int side = int(rec["side"])
        cdef double qty = float(rec["qty"])
        cdef double exec_px = float(rec["exec_px"])
        cdef double exit_px = float(rec["exit_px"])

        try:
            # place: limit + post_only (maker)
            self._ws_place(side, qty, exec_px, coid,
                           is_limit=True, force=1, reduce_only=False)

            #self._push_orpt(coid, "", 0, exec_px, qty, 0.0, qty, side)
            #self.orders 에 전송한 내역 보관
            self.orders[coid] = {
                "side":side,"qty":qty,"exec_px":exec_px,"exit_px":exit_px,
                "order_id":"", "sent_ms":_now_ms(), "first_fill_ms":0, "filled_qty":0.0,
                "opp_sent":False, "opp_sent_ms":0, "opp_sent_coid" : coid+5000 , "done":False
            }
            print("최초주문!!")

        except Exception as e:
            print("[ERROR] _on_flag :  ",e)


    cdef void _on_exec(self, e):
        cdef long long coid = int(e["client_oid"]) #프로그램에서 나간 주문만 처리한다.
        try:
            st = self.orders.get(coid)

            # --- 반대(coid-5000) 체결 감지: 던진 수익주문의 체결 완료 체크 ---
            if st is None:
                dt = self.orders.get(coid - 5000)
                if dt is not None:
                    # 내가 보낸 반대주문(coid-5000 규칙)과 일치하고 아직 미완이면 완료 처리
                    if dt.get('opp_sent_coid') == coid and dt.get('done', False) is False:
                        dt["done"] = True
                        # 옵션: dt["opp_fill_ms"] = _now_ms()
                        print("반대주문체결완료")
                return  # 원 주문(coid) 기록이 없으면 여기서 종료

            # --- 공통 필드 파싱 ---
            side     = int(e["side"])
            status   = int(e["status"])
            acc      = float(e.get("acc_fill", 0.0))
            last_sz  = float(e.get("last_fill", 0.0))
            last_px  = float(e.get("last_price", 0.0))
            avg      = float(e.get("avg_price", 0.0))
            size0    = float(e.get("size", 0.0))

            # --- 스냅샷/상태 업데이트만 반영(orders 채널에 해당) ---
            # 힌트: fill 메시지는 last_fill>0, orders 메시지는 last_fill==0 로 구분 가능
            # 단, 어떤 거래소는 fill에도 acc만 주는 경우가 있어 Δ 로직이 더 안전.
            prev_acc = float(st.get("acc_fill_prev", 0.0))
            delta    = acc - prev_acc

            # 상태/평균가/누적갱신은 항상 반영
            st["avg"] = avg
            st["acc_fill_prev"] = acc
            # 필요하면 상태코드 기반으로 내부 상태도 업데이트
            # st["status_code"] = status

            # --- 트리거 조건: '누적 체결 증가(Δ>0)'일 때만 ---
            if delta <= 0.0:
                return

            # 여기서부터는 실제 "새 체결"로 간주
            # first_fill 마킹
            if st.get('first_fill_ms', 0) == 0:
                st["first_fill_ms"] = _now_ms()

            # Δ만큼 채워졌다고 보고 누적
            st["filled_qty"] = st.get("filled_qty", 0.0) + delta

            print("수익주문준비완료 (coid=%d, delta=%.4f, acc=%.4f)" % (coid, delta, acc))

            # --- idempotent 게이트: opp_sent=False 에서만 1회 발사 ---
            if (st.get('done') is False) and (st.get('opp_sent') is not True):
                try:
                    print("타겟수익주문 발사")
                    self._ws_place(
                        -st["side"],              # 반대방향
                        st["filled_qty"],         # 지금까지 체결된 수량만큼
                        st["exit_px"],
                        st["opp_sent_coid"],
                        is_limit=True, force=1, reduce_only=False
                    )
                    st["opp_sent"] = True
                    st["opp_sent_ms"] = _now_ms()
                    print("수익주문냈다", st)
                except Exception as ex:
                    print("수익주문에러:", ex)

        except Exception as ex:
            print("on_exec error:", ex)



    cdef void _scan_timeouts(self):
        now = _now_ms()
        if len(self.orders) != 0 :
            for coid, st in list(self.orders.items()):
                if st.get("done"): continue
                if st.get("first_fill_ms") == 0:
                    if now - st.get("sent_ms") > 2000:
                        self._ws_cancel(coid)
                        self.orders.get(coid)['done'] = True

                # 10초 경과 → exit 잔량 taker
                elif st.get("opp_sent") and not st.get("done"):
                    om = st.get("opp_sent_ms")
                    if om and now - om >= 30000:
                        remain = st.get("filled_qty", 0)
                        if remain>0.0:
                            try:
                                self._ws_cancel(st.get("opp_sent_coid"))
                                print("Cancel Unmatched Opposite Order")
                                self._ws_place(-st["side"], remain, 0.0, 0,is_limit=False, force=0, reduce_only=True)
                                print("Taker order for exit")

                            except Exception as e:
                                print(e)
                        self.orders.get(coid)["done"]=True

    # 리포트 push
    cdef void _push_orpt(self, long long coid, str ordid, int status, double px, double orig, double execq, double remain, int side):
        rec = np.zeros((), dtype=ORDER_REPORT_DTYPE)
        rec["ts"]=_now_ms(); rec["client_oid"]=coid; rec["order_id"]=ordid; rec["symbol"]=self.symbol
        rec["status"]=status; rec["price"]=px; rec["orig_qty"]=orig; rec["exec_qty"]=execq; rec["remain_qty"]=remain; rec["side"]=side
        self.r_orpt.push(rec)

    cdef void _push_frpt(self, long long coid, str ordid, double fq, double fp, int side, int liq):
        rec = np.zeros((), dtype=FILL_REPORT_DTYPE)
        rec["ts"]=_now_ms(); rec["client_oid"]=coid; rec["order_id"]=ordid; rec["symbol"]=self.symbol
        rec["fill_qty"]=fq; rec["fill_price"]=fp; rec["side"]=side; rec["liquidity"]=liq
        self.r_frpt.push(rec)
