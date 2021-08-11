import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    install_requires = [require for require in fh.readlines()]

setuptools.setup(
    name="autosub-baidu",
    version="0.2.0",
    author="RyouMon",
    author_email="wenslife@outlook.com",
    description="Auto-generates subtitles for any video or audio file. (Using Baidu AIP)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/RyouMon/autosub-baidu",
    project_urls={
        "Bug Tracker": "https://github.com/RyouMon/autosub-baidu/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
    install_requires=install_requires,
)
