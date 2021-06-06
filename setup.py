import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("install_requirements.txt", "r", encoding="utf-8") as fh:
    install_requirements = fh.read()

setuptools.setup(
    name="e3lm",
    version="0.1.1",
    author="Kenan Masri",
    author_email="kenanmasri@outlook.com",
    description="e3lm CLI tool (3lm language) for managing .3lm projects and files.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/e3lm/e3lm",
    project_urls={
        "Bug Tracker": "https://github.com/e3lm/e3lm/issues",
    },
    entry_points='''
        [console_scripts]
        e3lm=cli:main
    ''',
    install_requires=[install_requirements],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
)