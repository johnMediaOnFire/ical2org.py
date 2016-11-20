from setuptools import setup
import os

os.environ["PYTHONDONTWRITEBYTECODE"] = "YES"

setup(name="ical2org",
      version="1.0",
      description = "Convert ical to org-mode.",
      test_suite = "test.test_ical2org")
