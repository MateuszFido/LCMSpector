from setuptools import setup, Extension, find_packages
import numpy as np
import sys
import os

# Define the extension module to be built in the utils package
loading_accelerator = Extension(
    'lc_inspector.utils.loading_accelerator',
    sources=['lc-inspector/utils/loading_accelerator.c'],
    include_dirs=[np.get_include()],
    extra_compile_args=['-O3', '-ffast-math'] if sys.platform != 'win32' else ['/O2'],
    extra_link_args=['-lm'] if sys.platform != 'win32' else []
)

setup(
    name='lc-inspector-accelerator',
    version='1.0.0',
    description='C extensions for LC-Inspector performance optimization',
    packages=['lc_inspector', 'lc_inspector.utils'],
    package_dir={'lc_inspector': 'lc-inspector'},
    ext_modules=[loading_accelerator],
    setup_requires=['numpy'],
    install_requires=['numpy'],
    zip_safe=False,
    python_requires='>=3.7',
)
