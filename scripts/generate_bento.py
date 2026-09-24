"""
Entry point: fetch stats -> render SVG -> write it -> splice it into README.md.
Run daily by .github/workflows/update-readme.yml
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from fetch_stats import collect_all
from render_svg import render

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "config.json")

START_MARK = "<!--BENTO:START-->"
END_MARK = "<!--BENTO:END-->"


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def splice_readme(readme_path, svg_path):
    if not os.path.exists(readme_path):
        content = f"{START_MARK}\n![bento]({os.path.basename(svg_path)})\n{END_MARK}\n"
        with open(readme_path, "w") as f:
            f.write(content)
        return

    with open(readme_path) as f:
        text = f.read()

    block = f"{START_MARK}\n![bento]({os.path.basename(svg_path)})\n{END_MARK}"

    if START_MARK in text and END_MARK in text:
        text = re.sub(
            re.escape(START_MARK) + r".*?" + re.escape(END_MARK),
            block,
            text,
            flags=re.DOTALL,
        )
    else:
        text = block + "\n\n" + text

    with open(readme_path, "w") as f:
        f.write(text)


def main():
    config = load_config()
    login = config["github_login"]

    print(f"Fetching stats for {login} ...")
    stats = collect_all(login)

    print("Rendering SVG ...")
    svg = render(stats, config)

    svg_path = os.path.join(ROOT, config["output_svg_path"])
    with open(svg_path, "w") as f:
        f.write(svg)
    print(f"Wrote {svg_path}")

    readme_path = os.path.join(ROOT, config["readme_path"])
    splice_readme(readme_path, svg_path)
    print(f"Updated {readme_path}")


if __name__ == "__main__":
    main()
