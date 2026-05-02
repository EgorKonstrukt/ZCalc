import sys
from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy as np

if len(sys.argv) == 1:
    sys.argv.append("build_ext")
    sys.argv.append("--inplace")

ext = Extension(
    name="_math_core",
    sources=["_math_core.pyx"],
    include_dirs=[np.get_include()],
    extra_compile_args=["-O3", "-march=native", "-ffast-math", "-funroll-loops"],
    define_macros=[("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")],
)

setup(
    name="_math_core",
    ext_modules=cythonize(
        [ext],
        compiler_directives={
            "language_level": 3,
            "boundscheck": False,
            "wraparound": False,
            "cdivision": True,
            "nonecheck": False,
            "initializedcheck": False,
            "infer_types": True,
            "profile": False,
        },
        annotate=False,
    ),
)