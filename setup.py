#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pathlib

import pkg_resources
from setuptools import find_packages, setup

with pathlib.Path("requirements.txt").open() as requirements_txt:
    install_requires = [
        str(requirement)
        for requirement in pkg_resources.parse_requirements(requirements_txt)
    ]

setup(
    name="ahd2fhir",
    description="Creates FHIR from text",
    version="0.0.1",
    url="https://github.com/miracum/ahd2fhir",
    # packages=["ahd2fhir", "."],
    package_dir={"ahd2fhir": "ahd2fhir"},
    packages=find_packages(exclude=["test*"]),
    include_package_data=True,
    install_requires=install_requires,
    python_requires=">=3.9",
)
