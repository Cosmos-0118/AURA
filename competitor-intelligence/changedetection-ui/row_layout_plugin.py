from pathlib import Path

from flask import url_for

from changedetectionio.pluggy_interface import hookimpl


_STATIC_DIR = Path(__file__).with_name("static")


# The upstream loader also treats every module in this directory as a
# conditions plugin, so provide the no-op condition surface while using the
# global plugin hooks below for the stylesheet.
def register_operators() -> dict:
    return {}


def register_operator_choices() -> list:
    return []


def register_field_choices() -> list:
    return []


def add_data(current_watch_uuid, application_datastruct, ephemeral_data) -> dict:
    return {}


def ui_edit_stats_extras(watch) -> str:
    return ""


@hookimpl
def plugin_static_path() -> str:
    return str(_STATIC_DIR)


@hookimpl
def get_html_head_extras() -> str:
    stylesheet = url_for("static_content", group="plugin", filename="row-layout.css")
    return f'<link rel="stylesheet" href="{stylesheet}">'
