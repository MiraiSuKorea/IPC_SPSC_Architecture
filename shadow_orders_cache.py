# orders_cache.py

import os, json, time
from threading import Thread

class ShadowOrdersCache:
    def __init__(self,  hang_orders_file, flush_interval=0.1):
        self.hang_orders_file = hang_orders_file
        self.hang_orders = self._load_file(self.hang_orders_file)
        # Flags to track if the in-memory data was modified
        self._hang_orders_modified = False
        self.flush_interval = flush_interval
        # Start a background flush thread as a daemon
        #Thread(target=self._flush_loop, daemon=True).start()

    def _load_file(self, filename):
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                return json.load(f)
        return []  # Return an empty list if file does not exist


    def load_hang_orders(self):
        self.hang_orders = self._load_file(self.hang_orders_file)
        return self.hang_orders

    def mark_hang_orders_modified(self):
        self.flush_hang_orders()

    def flush_hang_orders(self):
        print("FLUSH HANG_ORDERS")
        with open(self.hang_orders_file, 'w') as f:
            json.dump(self.hang_orders, f)
        self._hang_orders_modified = False
        print("FLUSH HANG_ORDERS DONE")

    def _flush_loop(self):
        while True:
            time.sleep(self.flush_interval)
            if self._hang_orders_modified:
                self.flush_hang_orders()

    def flush_immediately(self):
        # Call this if you need to force an immediate flush
        self.flush_hang_orders()
