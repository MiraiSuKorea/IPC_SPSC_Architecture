# shm_ring.py
import time
import struct
import numpy as np
from multiprocessing import shared_memory

class ShmRing:
    """
    단일 생산자-단일 소비자(SPSC) 링버퍼
    헤더(24B): [int64 head][int64 tail][int64 cap]
    데이터 영역: cap * item_bytes
    """
    HEADER_FMT = "<qqq"  # head, tail, cap (int64)
    HEADER_SIZE = struct.calcsize(HEADER_FMT)

    def __init__(self, name: str, item_dtype: np.dtype, capacity: int, create: bool):
        self.item_dtype = np.dtype(item_dtype)
        self.item_size  = self.item_dtype.itemsize
        self.capacity   = int(capacity)
        self.total_size = self.HEADER_SIZE + self.capacity * self.item_size

        if create:
            self.shm = shared_memory.SharedMemory(create=True, size=self.total_size, name=name)
            buf = self.shm.buf
            struct.pack_into(self.HEADER_FMT, buf, 0, 0, 0, self.capacity)
        else:
            self.shm = shared_memory.SharedMemory(name=name, create=False)
            buf = self.shm.buf
            _h, _t, cap = struct.unpack_from(self.HEADER_FMT, buf, 0)
            self.capacity = cap
            self.total_size = self.HEADER_SIZE + self.capacity * self.item_size

        self.buf = self.shm.buf
        self.data_mv = memoryview(self.buf)[self.HEADER_SIZE:]
        self.arr = np.ndarray((self.capacity,), dtype=self.item_dtype, buffer=self.data_mv)

    # --- header helpers
    def _get_head_tail(self):
        return struct.unpack_from(self.HEADER_FMT, self.buf, 0)[:2]

    def _set_head(self, v: int):
        struct.pack_into("<q", self.buf, 0, v)

    def _set_tail(self, v: int):
        struct.pack_into("<q", self.buf, 8, v)

    # --- API
    def push(self, rec):
        """
        rec: dtype과 호환되는 단일 튜플/배열(스칼라 레코드). 1-엘리먼트 ndarray 말고 '튜플' 추천.
        """
        head, tail = self._get_head_tail()
        nxt = (head + 1) % self.capacity
        if nxt == tail:
            # 풀 → 가장 오래된 것 드랍(저지연 우선)
            tail = (tail + 1) % self.capacity
            self._set_tail(tail)
        self.arr[head] = rec
        self._set_head(nxt)

    def pop_many(self, maxn: int):
        head, tail = self._get_head_tail()
        if head == tail:
            return None  # empty

        if head > tail:
            n = min(maxn, head - tail)
            view = self.arr[tail:tail+n]
            self._set_tail((tail + n) % self.capacity)
            return view
        else:
            # wrap
            left = self.capacity - tail
            n = min(maxn, left)
            view = self.arr[tail:tail+n]
            self._set_tail((tail + n) % self.capacity)
            return view

    def latest(self):
        head, tail = self._get_head_tail()
        if head == tail:
            return None
        idx = (head - 1) % self.capacity
        return self.arr[idx]

    def close(self):
        self.shm.close()

    def unlink(self):
        self.shm.unlink()
