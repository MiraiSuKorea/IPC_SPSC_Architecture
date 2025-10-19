# cython: language_level=3
# cython: boundscheck=False, wraparound=False, cdivision=True, nonecheck=False
"""
Binance Spot (orderbook L1 + trades) + Bitget Futures trades(price) 를 입력받아
신호가 나올 때 Bitget 선물에 낼 실행가(exec_px)와 청산가(exit_px)를 계산해서
ORDER_FLAGS 링에 push한다.

- 실행가: maker 유지 위해 Binance L1 기준 ±5tick
- 청산가: 최초 체결 즉시 반대 10tick (실행엔진이 exit_px 그대로 사용)
- 속도우선: 예외/검증 최소화 (예외 발생 시 조용히 skip)
"""

import os
from libc.math cimport floor
cimport cython
import numpy as np

from shm_ring import ShmRing
from layouts import ORDER_FLAG_DTYPE

cdef inline double qtick(double x, double tick) nogil:
    if tick <= 0.0:
        return x
    return floor(x/tick + 0.5) * tick




cdef class Avellaneda_Stoikov_marketmaking:
    # 외부 파라미터
    cdef public str ticker, base, settle, interval, bitget_ticker
    cdef public int magic, minqty, numOrders
    cdef public double bet_amount

    # 내부 상태
    cdef double last_bid, last_ask
    cdef double tick
    cdef object of_ring
    cdef long long seq
    cdef int last_signal_side

    def __init__(self, str ticker, str base, str settle, int magic,
                 str interval, double bet_amount, int minqty, int numOrders,
                 str bitget_ticker):
        self.ticker = ticker
        self.base = base
        self.settle = settle
        self.magic = magic
        self.interval = interval
        self.bet_amount = bet_amount
        self.minqty = minqty
        self.numOrders = numOrders
        self.bitget_ticker = bitget_ticker

        self.last_bid = 0.0
        self.last_ask = 0.0
        self.tick = float(os.getenv("BITGET_TICK_SIZE", "0.001"))
        self.seq = 490000
        self.last_signal_side = 0

        self.of_ring = ShmRing(
            os.getenv("ORDER_FLAGS_RING", "RING_ORDER_FLAGS"),
            ORDER_FLAG_DTYPE,
            capacity=int(os.getenv("OF_CAP", "2048")),
            create=False
        )

    cdef inline long long _next_oid(self) nogil:
        self.seq += 1
        return self.seq & 0x7fffffff

    cpdef void feed_trade(
        self,
        double price, double qty, bint is_sell, long long t_ms,
        object bid_px, object bid_qty, object ask_px, object ask_qty,
        object bg_bid_px, object bg_bid_qty, object bg_ask_px, object bg_ask_qty,

    ):
        """
        Parameters
        ----------
        price       : Binance trade price
        qty         : Binance trade qty
        is_sell     : Binance trade aggressor (1=sell, 0=buy)
        t_ms        : trade timestamp (ms)
        bid_px[0]   : Binance L1 best bid
        ask_px[0]   : Binance L1 best ask
        bg big/as : Bitget Futures 마지막 체결가 (직접 인자)  ← NEW
        """
        cdef object rec
        cdef double exec_px
        cdef double exit_px

        # L1 업데이트(리스트 1원소)
        try:
            if bid_px is not None and len(bid_px) > 0:
                self.last_bid = float(bid_px[0])
            if ask_px is not None and len(ask_px) > 0:
                self.last_ask = float(ask_px[0])
        except:
            return

        cdef double bb = self.last_bid
        cdef double aa = self.last_ask
        if bb <= 0.0 or aa <= 0.0:
            return

        # ===== 초경량 신호 (예시) =====
        # - 매수: 체결가가 bid보다 충분히 낮게 찍힐 때
        # - 매도: 체결가가 ask보다 충분히 높게 찍힐 때
        # - Bitget 체결가가 Binance mid와 너무 동떨어져 있으면 skip (체결 레짐 불일치 방지)
                # ===== 신호 판단 =====
        cdef double band = self.tick * 50.0
        cdef double mid_bi = 0.5 * (bb + aa)
        cdef int side = 0

        # Bitget L1 (필수: 길이 체크)
        if bg_bid_px is None or bg_ask_px is None or len(bg_bid_px) == 0 or len(bg_ask_px) == 0:
            return
        cdef double bg_bid = float(bg_bid_px[0])
        cdef double bg_ask = float(bg_ask_px[0])
        if bg_bid <= 0.0 or bg_ask <= 0.0:
            return
        cdef double mid_bg = 0.5 * (bg_bid + bg_ask)

        # (선택) 거래소 괴리 sanity
        if mid_bg > 0.0:
            if mid_bg > mid_bi * 1.01 or mid_bg < mid_bi * 0.99:
                pass  # 필요시 return



        # ===== Avellaneda-Stoikov 변형: 총스프레드 100틱 고정 + 스큐로 중심 이동 =====
        # 파라미터
        cdef double tau = self.tick
        cdef double S_ticks = 100.0
        cdef double H = S_ticks / 2.0           # 반 스프레드(틱)
        cdef double eps = 1.0                   # 교차 방지 여유 틱
        # 민감도 (필요시 self에서 빼오거나 상수로 시작)
        cdef double mu = 20.0
        cdef double kappa = 30.0
        cdef double zeta = 10.0
        cdef double Qmax = 100.0

        # 재고(q)와 임밸런스(I) 추정
        cdef double q = 0.0
        try:
            q = float(self.inventory)  # 네 클래스의 재고 변수명에 맞춰주면 좋음
        except:
            q = 0.0
        cdef double B = 0.0
        cdef double A = 0.0
        if bid_qty is not None and len(bid_qty) > 0:
            B = float(bid_qty[0])
        if ask_qty is not None and len(ask_qty) > 0:
            A = float(ask_qty[0])
        cdef double I = 0.0
        if B + A > 0.0:
            I = (B - A) / (B + A)       # -1 ~ +1

        cdef double s = float(side)     # 신호 -1/0/+1

        # 스큐 k = mu*I - kappa*(q/Qmax) - zeta*s   (틱 단위)
        cdef double k = mu*I - kappa*(q / Qmax) - zeta*s
        if k > (H - eps):
            k = H - eps
        elif k < -(H - eps):
            k = -(H - eps)

        # 호가 중심(base) 계산 (Bitget 미드 기준)
        # p_bid = m - (H - k)*tau, p_ask = m + (H + k)*tau
        cdef double base_bid = mid_bg - (H - k) * tau
        cdef double base_ask = mid_bg + (H + k) * tau

        # 메이커(post_only) 보장 clip
        if base_bid > bg_bid:
            base_bid = bg_bid
        if base_ask < bg_ask:
            base_ask = bg_ask

        # ===== 주문 사다리 생성 (여러 장 리스트) =====
        # 예) (0,20,40) 틱 오프셋 → 3장
        cdef list ladder_levels = getattr(self, "ladder_levels", None)
        if ladder_levels is None:
            ladder_levels = [0, 20, 40]   # 기본값

        cdef double qty1 = self.minqty if self.minqty > 0 else 1.0

        # 안전: price 0 방지
        if price == 0.0:
            return

        # 로컬 보관(원하면 반환/로그)
        cdef list orders = []

        # 내부 헬퍼: 한 장 push (목표수익 100틱 고정)
        # 매수: exit = exec + 100*tau, 매도: exit = exec - 100*tau
        def _push(int pside, double px_exec, double qtty):
            cdef object rec
            cdef double exit_px = px_exec + (S_ticks * tau if pside > 0 else -S_ticks * tau)
            rec = np.zeros((), dtype=ORDER_FLAG_DTYPE)
            rec["ts"]         = <long long>t_ms
            rec["symbol"]     = self.bitget_ticker if self.bitget_ticker else "BTCUSDT_UMCBL"
            rec["side"]       = <int>pside           # +1 매수 / -1 매도
            rec["exec_px"]    = <double>px_exec      # ★ 스칼라
            rec["exit_px"]    = <double>exit_px      # ★ 스칼라 (목표수익 100틱)
            rec["qty"]        = <double>qtty
            rec["tick"]       = <double>tau
            rec["client_oid"] = <long long>self._next_oid()
            self.of_ring.push(rec)
            orders.append(rec)

        try:
            if side == 0:
                # 양방향 스프레드: ladder_levels 만큼 대칭
                for off in ladder_levels:
                    # 매수측(더 안쪽으로 붙일수록 off를 작게)
                    exec_px = base_bid - off * tau
                    if exec_px > bg_bid:
                        exec_px = bg_bid
                    _push(+1, exec_px, qty1)

                    # 매도측
                    exec_px = base_ask + off * tau
                    if exec_px < bg_ask:
                        exec_px = bg_ask
                    _push(-1, exec_px, qty1)

            elif side > 0:
                # 롱 모드: 매수만 여러 장
                for off in ladder_levels:
                    exec_px = base_bid - off * tau
                    if exec_px > bg_bid:
                        exec_px = bg_bid
                    _push(+1, exec_px, qty1)

            else:
                # 숏 모드: 매도만 여러 장
                for off in ladder_levels:
                    exec_px = base_ask + off * tau
                    if exec_px < bg_ask:
                        exec_px = bg_ask
                    _push(-1, exec_px, qty1)

        except Exception as _:
            # 속도우선: 실패 시 조용히 무시
            return

