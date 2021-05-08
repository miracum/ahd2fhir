#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pip._internal.req import parse_requirements
from setuptools import find_packages, setup


def load_requirements(fname):
    """Turn requirements.txt into a list"""
    reqs = parse_requirements(fname, session="test")
    return [r.requirement for r in reqs]


setup(
    name="ahd2fhir",
    description="Creates FHIR from text",
    version="0.0.1",
    url="https://github.com/miracum/ahd-to-fhir",
    # packages=["ahd2fhir", "."],
    package_dir={"ahd2fhir": "ahd2fhir"},
    packages=find_packages(exclude=["test*"]),
    include_package_data=True,
    install_requires=load_requirements("requirements.txt"),
    python_requires=">=3.9",
)
