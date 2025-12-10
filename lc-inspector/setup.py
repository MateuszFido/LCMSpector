from setuptools import setup
from Cython.Build import cythonize

setup(
    name="LCMSpector",
    ext_modules=cythonize("utils/loading.pyx"),
)
