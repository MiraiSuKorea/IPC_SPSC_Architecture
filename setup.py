# setup.py
from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy as np
import os, sys, platform

BASE_DIR = os.path.dirname(__file__)

def ext(name, rel_src):
    src = os.path.join(BASE_DIR, rel_src)
    is_msvc = platform.system().lower().startswith("win") and \
              ("msvc" in getattr(sys, "argv", []) or True)  # 대체로 Windows=MSVC

    extra_compile_args = ["/O2", "/DNDEBUG"] if is_msvc else ["-O3", "-ffast-math"]
    extra_link_args    = [] if is_msvc else []

    return Extension(
        name=name,
        sources=[src],
        include_dirs=[np.get_include()],
        language="c++",                 # C++로 컴파일
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args,
    )

extensions = [
    # 전략 엔진 (feed_trade 포함)
    ext("qty_based_leverage_trading", "qty_based_leverage_trading.pyx"),
    # 오더 실행/관리 엔진 (REST 발주 + Private 이벤트 소비)
    ext("ordersystem", "ordersystem.pyx"),
]

setup(
    name="lowlat_hft_modules",
    ext_modules=cythonize(
        extensions,
        language_level=3,
        compiler_directives={
            "boundscheck": False,
            "wraparound": False,
            "cdivision": True,
            "nonecheck": False,
        },
        annotate=False,   # True로 두면 HTML 최적화 리포트 생성
    ),
    zip_safe=False,
)
