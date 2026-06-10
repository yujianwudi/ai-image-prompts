import json
import subprocess
import sys


REPOS = [
    "EvoLinkAI/awesome-gpt-image-2-API-and-Prompts",
    "freestylefly/awesome-gpt-image-2",
    "YouMind-OpenLab/awesome-gpt-image-2",
]


def configure_stdout() -> None:
    """Keep emoji / multilingual GitHub descriptions printable on Windows."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def run(cmd: list[str]) -> str:
    result = subprocess.run(
        cmd,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return result.stdout


def repo_info(repo: str) -> dict:
    raw = run(
        [
            "gh",
            "repo",
            "view",
            repo,
            "--json",
            "nameWithOwner,description,stargazerCount,updatedAt,url",
        ]
    )
    return json.loads(raw)


def top_contents(repo: str) -> list[str]:
    raw = run(
        [
            "gh",
            "api",
            f"repos/{repo}/contents",
            "--jq",
            ".[] | [.type,.name,.path] | @tsv",
        ]
    )
    return [line.strip() for line in raw.splitlines() if line.strip()]


def main() -> None:
    configure_stdout()
    print("# \u53c2\u8003\u4ed3\u5e93\u6458\u8981")
    print()
    for repo in REPOS:
        info = repo_info(repo)
        print(f"## {info['nameWithOwner']}")
        print()
        print(f"- URL: {info['url']}")
        print(f"- Stars: {info['stargazerCount']}")
        print(f"- Updated: {info['updatedAt']}")
        print(f"- Description: {info.get('description') or ''}")
        print()
        print("### Top-level contents")
        print()
        for item in top_contents(repo)[:40]:
            print(f"- {item}")
        print()


if __name__ == "__main__":
    main()
