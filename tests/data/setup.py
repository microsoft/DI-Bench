from pathlib import Path

from setuptools import find_packages, setup

# Reading the long description from the README.md file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

dependencies = [
    "cryptography",
    "freezegun",
    "installer",
    "pytest",
    "pytest-cov",
    "pytest-rerunfailures",
    "pytest-xdist",
    "scripttest",
    "setuptools",
    'virtualenv<20.0;python_version<"3.10" and (sys_platform!="darwin" or platform_machine!="arm64")',
    'virtualenv>=20.0;python_version>="3.10" or (sys_platform=="darwin" and platform_machine=="arm64")',
    "werkzeug",
    "wheel",
    "tomli-w",
    "proxy.py",
    "coverage>=4.4",
    "setuptools>=40.8.0,!=60.6.0",
    "wheel",
]

useless = ["a", "b"]
usefull = useless

setup(
    name="data",
    version="0.1.0",
    description="",
    author="Junhao Wang <junhaoo.wang@gmail.com>",
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.10",
    install_requires=dependencies,
    packages=find_packages(),
    package_data={"": ["README.md"]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    include_package_data=True,
    zip_safe=False,
)
