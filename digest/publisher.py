"""
Publish the weekly digest to the alpha-digest GitHub Pages repo.
Works both locally and in GitHub Actions (uses GITHUB_TOKEN for push).
"""
import os
import subprocess
import tempfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from digest.config import TEMPLATES_DIR, GITHUB_TOKEN


def publish_to_demo_repo(html_body: str, start_date: str, end_date: str, repo_slug: str = "utsapoddar/alpha-digest", web_html: str | None = None):
    """Clone the alpha-digest repo, update it, and push.

    Args:
        repo_slug: GitHub owner/repo (default: utsapoddar/alpha-digest)
    """
    if GITHUB_TOKEN:
        clone_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{repo_slug}.git"
    else:
        clone_url = f"https://github.com/{repo_slug}.git"

    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir) / "alpha-digest"

        try:
            subprocess.run(["git", "clone", clone_url, str(repo)], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"[publisher] Clone failed: {e.stderr.decode() if e.stderr else e}")
            return

        archive_dir = repo / "archive"
        archive_dir.mkdir(exist_ok=True)

        # Save this week's digest
        archive_file = archive_dir / f"{end_date}.html"
        archive_file.write_text(web_html if web_html else html_body, encoding="utf-8")

        # Build archive index
        archive_entries = sorted(
            [f.stem for f in archive_dir.glob("*.html") if f.stem != "index"],
            reverse=True,
        )

        # Render landing page
        env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
        template = env.get_template("landing_page.html.j2")
        landing_html = template.render(
            latest_digest=html_body,
            latest_date=end_date,
            archive_entries=archive_entries,
        )
        (repo / "index.html").write_text(landing_html, encoding="utf-8")

        # Render archive index
        archive_index = env.get_template("archive_index.html.j2")
        (archive_dir / "index.html").write_text(
            archive_index.render(archive_entries=archive_entries),
            encoding="utf-8",
        )

        # Git commit + push
        try:
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "97543305+utsapoddar@users.noreply.github.com"], capture_output=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "utsapoddar"], capture_output=True)
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)

            result = subprocess.run(
                ["git", "-C", str(repo), "diff", "--cached", "--quiet"],
                capture_output=True,
            )
            if result.returncode == 0:
                print("[publisher] No changes to publish.")
                return

            subprocess.run(
                ["git", "-C", str(repo), "commit", "-m", f"Weekly digest — {end_date}"],
                check=True, capture_output=True,
            )
            subprocess.run(["git", "-C", str(repo), "push"], check=True, capture_output=True)
            print(f"[publisher] Published digest for {end_date} to GitHub Pages.")
        except subprocess.CalledProcessError as e:
            print(f"[publisher] Git error: {e.stderr.decode() if e.stderr else e}")
