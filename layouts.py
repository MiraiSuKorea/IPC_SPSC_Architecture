# layouts.py
import numpy as np

TRADE_DTYPE = np.dtype([
    ("ts",  "int64"),
    ("px",  "float64"),
    ("qty", "float64"),
    ("sell","uint8"),
    ("tid", "int64"),
])

BOOK_DTYPE = np.dtype([
    ("ts",   "int64"),
    ("bbid", "float64"),
    ("bqty", "float64"),
    ("bask", "float64"),
    ("aqty", "float64"),
])

# ====== 추가: 전략 → 주문엔진 (실행가/청산가를 전략이 산출해 넘김) ======
ORDER_FLAG_DTYPE = np.dtype([
    ("ts", "int64"),
    ("symbol", "U32"),      # 예: "SOLUSDT_UMCBL"
    ("side", "int8"),       # +1=BUY, -1=SELL
    ("exec_px", "float64"), # Bitget 선물에 낼 '실행 지정가'
    ("exit_px", "float64"), # 최초 체결 후 바로 내보낼 '반대 10틱 지정가'
    ("qty", "float64"),
    ("tick", "float64"),
    ("client_oid", "int64"),# 0이면 주문엔진이 생성해도 됨
])

# ====== 추가: 주문엔진 → 상위(상태) ======
ORDER_REPORT_DTYPE = np.dtype([
    ("ts", "int64"),
    ("client_oid", "int64"),
    ("order_id", "U48"),
    ("symbol", "U32"),
    ("status", "int8"),     # 0=newAck,1=filled,2=part,3=canceled,4=rejected,5=expired
    ("price", "float64"),
    ("orig_qty", "float64"),
    ("exec_qty", "float64"),
    ("remain_qty", "float64"),
    ("side", "int8"),
])

# ====== 추가: 주문엔진 → 상위(체결) ======
FILL_REPORT_DTYPE = np.dtype([
    ("ts", "int64"),
    ("client_oid", "int64"),
    ("order_id", "U48"),
    ("symbol", "U32"),
    ("fill_qty", "float64"),
    ("fill_price", "float64"),
    ("side", "int8"),
    ("liquidity", "int8"),   # 0=unknown,1=maker,2=taker
])


PRIVATE_EXEC_DTYPE = np.dtype([
    ("ts",        "int64"),
    ("client_oid","int64"),   # clientOid (없으면 0)
    ("order_id",  "U48"),
    ("side",      "int8"),    # +1 buy, -1 sell, 0 unknown
    ("status",    "int8"),    # 0=new,1=filled,2=part,3=canceled,4=rejected,5=expired
    ("size",      "float64"), # order size
    ("acc_fill",  "float64"), # 누적 체결
    ("last_fill", "float64"), # 이번 이벤트 체결
    ("last_price","float64"), # 이번 이벤트 체결가
    ("avg_price", "float64"), # 평균 체결가(있으면)
])
'''
self.orders[coid] = {
                "side":side,"qty":qty,"exec_px":exec_px,"exit_px":exit_px,
                "order_id":"", "sent_ms":_now_ms(), "first_fill_ms":0, "filled_qty":0.0,
                "opp_sent":False, "opp_sent_ms":0, "opp_sent_coid" : coid+50000 , "done":False
            }
            
            
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
            "clientOid": str(coid),
        }
        if is_limit: params["price"] = str(price)
        if reduce_only: params["reduceOnly"] = "yes"  # one-way-mode에서만 의미

        pkt = {"op":"trade","args":[{
            "channel":"place-order",
            "id": str(coid),
            "instId": self.symbol,
            "instType": self.inst_type,
            "params": params
        }]}
        self._ws_send_json(pkt)
'''


# Bitget Private WS로 보낼 커맨드(주문/취소)
# cmd: 1=place, 2=cancel
# order_type: 0=limit, 1=market
# force: 0=gtc, 1=post_only, 2=fok, 3=ioc
# trade_side: 0=ignore(one-way), 1=open, 2=close (hedge-mode에서만 사용)
BG_WS_CMD_DTYPE = np.dtype([
    ("ts",          "int64"),
    ("cmd",         "int8"),
    ("side",        "int8"),     # +1 buy, -1 sell
    ("order_type",  "int8"),     # 0/1
    ("force",       "int8"),     # 0..3
    ("reduce_only", "int8"),     # 0/1 (one-way에서만 의미)
    ("trade_side",  "int8"),     # 0/1/2 (hedge-mode)
    ("qty",         "float64"),
    ("price",       "float64"),
    ("client_oid",  "int64"),
    ("order_id",    "U48"),      # cancel 시 우선
])
