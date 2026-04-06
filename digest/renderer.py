"""Render the digest summary into HTML using Jinja2."""
from jinja2 import Environment, FileSystemLoader
from digest.config import TEMPLATES_DIR


def _render(template_name: str, summary: dict, commodities: dict, start_date: str, end_date: str) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    return env.get_template(template_name).render(
        entity_summaries=summary.get("entity_summaries", []),
        macro_note=summary.get("macro_note", ""),
        commodities=commodities,
        start_date=start_date,
        end_date=end_date,
    )


def render_html(summary: dict, commodities: dict, start_date: str, end_date: str) -> str:
    return _render("digest_email.html.j2", summary, commodities, start_date, end_date)


def render_web_html(summary: dict, commodities: dict, start_date: str, end_date: str) -> str:
    return _render("digest_web.html.j2", summary, commodities, start_date, end_date)
