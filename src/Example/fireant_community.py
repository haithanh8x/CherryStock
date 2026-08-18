"""
FireAnt Community collector for CherryStock.

Basis:
    GET https://restv2.fireant.vn/posts
        ?symbol=MWG
        &type=0
        &offset=0
        &limit=30

Authentication:
    Authorization: Bearer <token>

Recommended usage on PowerShell:
    $env:FIREANT_TOKEN="YOUR_FIREANT_ACCESS_TOKEN"
    python fireant_community.py --symbol MWG

Outputs:
    MWG_posts_raw.json
    MWG_posts.csv

Install:
    pip install requests pandas
"""

from __future__ import annotations

import argparse
import html
import json
import os
import time
from pathlib import Path
from typing import Any

import requests

try:
    import pandas as pd
except ImportError:
    pd = None


BASE_URL = "https://restv2.fireant.vn"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-GB,en;q=0.9,en-US;q=0.8,vi;q=0.7,ru;q=0.6",
    "Origin": "https://fireant.vn",
    "Referer": "https://fireant.vn/",
    "Sec-CH-UA": '"Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
}


class FireAntCommunityError(RuntimeError):
    pass


class FireAntCommunityClient:
    def __init__(
        self,
        token: str | None = None,
        *,
        timeout: float = 30.0,
        sleep_between_requests: float = 0.2,
    ) -> None:
        token = token or os.getenv("FIREANT_TOKEN")
        if not token:
            raise FireAntCommunityError(
                "Missing FireAnt token.\n"
                "PowerShell:\n"
                '  $env:FIREANT_TOKEN="YOUR_TOKEN"'
            )

        token = token.strip()
        if token.lower().startswith("bearer "):
            token = token[7:].strip()

        self.timeout = timeout
        self.sleep_between_requests = sleep_between_requests

        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.session.headers["Authorization"] = f"Bearer {token}"

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "FireAntCommunityClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{BASE_URL}{path}"

        r = self.session.get(
            url,
            params=params,
            timeout=self.timeout,
        )

        if r.status_code >= 400:
            raise FireAntCommunityError(
                f"HTTP {r.status_code}: {r.url}\n"
                f"Response: {r.text[:1500]}"
            )

        try:
            return r.json()
        except ValueError as exc:
            raise FireAntCommunityError(
                f"Invalid JSON from {r.url}: {r.text[:1000]}"
            ) from exc

    def get_posts(
        self,
        symbol: str,
        *,
        post_type: int = 0,
        offset: int = 0,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        """
        Get one page of FireAnt community posts for a symbol.
        """
        data = self._get(
            "/posts",
            {
                "symbol": symbol.upper(),
                "type": int(post_type),
                "offset": int(offset),
                "limit": int(limit),
            },
        )

        if not isinstance(data, list):
            raise FireAntCommunityError(
                f"Unexpected posts response type: {type(data).__name__}"
            )

        return data

    def get_all_posts(
        self,
        symbol: str,
        *,
        post_type: int = 0,
        page_size: int = 100,
        max_posts: int | None = None,
        max_pages: int | None = None,
        verbose: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Retrieve all available posts through offset/limit pagination.

        Stops when:
        - API returns no rows
        - API returns fewer than page_size rows
        - max_posts is reached
        - max_pages is reached
        """
        symbol = symbol.upper()
        result: list[dict[str, Any]] = []
        seen_ids: set[Any] = set()

        offset = 0
        page_no = 0

        while True:
            if max_pages is not None and page_no >= max_pages:
                break

            rows = self.get_posts(
                symbol,
                post_type=post_type,
                offset=offset,
                limit=page_size,
            )

            page_no += 1

            added = 0

            for row in rows:
                post_id = (
                    row.get("postID")
                    or row.get("postId")
                    or row.get("id")
                )

                # If FireAnt exposes an id, deduplicate by it.
                if post_id is not None:
                    if post_id in seen_ids:
                        continue
                    seen_ids.add(post_id)

                result.append(row)
                added += 1

                if max_posts is not None and len(result) >= max_posts:
                    break

            if verbose:
                print(
                    f"[{symbol}] "
                    f"page={page_no:<4} "
                    f"offset={offset:<7} "
                    f"returned={len(rows):<4} "
                    f"added={added:<4} "
                    f"total={len(result)}"
                )

            if max_posts is not None and len(result) >= max_posts:
                result = result[:max_posts]
                break

            if not rows:
                break

            if len(rows) < page_size:
                break

            offset += page_size

            if self.sleep_between_requests:
                time.sleep(self.sleep_between_requests)

        return result


def _get_first(post: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in post and post[name] is not None:
            return post[name]
    return None


def extract_tagged_symbols(post: dict[str, Any]) -> list[str]:
    tagged = post.get("taggedSymbols")

    if not isinstance(tagged, list):
        return []

    symbols: list[str] = []

    for item in tagged:
        if isinstance(item, dict):
            symbol = (
                item.get("symbol")
                or item.get("code")
                or item.get("ticker")
            )
        elif isinstance(item, str):
            symbol = item
        else:
            symbol = None

        if symbol:
            symbol = str(symbol).upper()
            if symbol not in symbols:
                symbols.append(symbol)

    return symbols


def extract_author(post: dict[str, Any]) -> dict[str, Any]:
    """
    FireAnt post schemas may evolve. Preserve common author/user shapes.
    """
    author = (
        post.get("user")
        or post.get("author")
        or post.get("individual")
        or post.get("createdBy")
    )

    if not isinstance(author, dict):
        return {
            "author_id": None,
            "author_name": None,
            "author_username": None,
        }

    return {
        "author_id": _get_first(
            author,
            "userID",
            "userId",
            "individualID",
            "individualId",
            "id",
        ),
        "author_name": _get_first(
            author,
            "displayName",
            "fullName",
            "name",
        ),
        "author_username": _get_first(
            author,
            "username",
            "userName",
            "screenName",
        ),
    }


def normalize_content(post: dict[str, Any]) -> str | None:
    """
    Prefer originalContent because the captured response shows:
      content         -> HTML entities
      originalContent -> decoded Vietnamese text
    """
    original = post.get("originalContent")
    if isinstance(original, str) and original.strip():
        return original.strip()

    content = post.get("content")
    if isinstance(content, str) and content.strip():
        return html.unescape(content).strip()

    return None


def flatten_post(
    post: dict[str, Any],
    *,
    requested_symbol: str | None = None,
) -> dict[str, Any]:
    tagged_symbols = extract_tagged_symbols(post)
    author = extract_author(post)

    record: dict[str, Any] = {
        "post_id": _get_first(
            post,
            "postID",
            "postId",
            "id",
        ),
        "requested_symbol": (
            requested_symbol.upper()
            if requested_symbol
            else None
        ),
        "date": post.get("date"),
        "language": post.get("language"),

        # Main NLP field:
        "content": normalize_content(post),

        # Keep the original API variants too:
        "content_html": post.get("content"),
        "original_content": post.get("originalContent"),

        "sentiment_fireant": post.get("sentiment"),
        "is_ai_generated": post.get("isAIGenerated"),
        "is_expert_idea": post.get("isExpertIdea"),
        "is_top": post.get("isTop"),
        "approved": post.get("approved"),
        "priority": post.get("priority"),

        "total_likes": post.get("totalLikes"),
        "total_replies": post.get("totalReplies"),
        "total_shares": post.get("totalShares"),
        "liked": post.get("liked"),

        "has_image": post.get("hasImage"),
        "has_file": post.get("hasFile"),
        "has_video": bool(post.get("videoUrl")),
        "video_url": post.get("videoUrl"),
        "video_thumbnail_url": post.get("videoThumbnailUrl"),

        "link": post.get("link"),
        "link_title": post.get("linkTitle"),
        "link_description": post.get("linkDescription"),

        "post_group": post.get("postGroup"),
        "post_source": post.get("postSource"),
        "post_source_url": post.get("postSourceUrl"),
        "is_source_content_full": post.get("isSourceContentFull"),

        "reply_to_post_id": post.get("replyToPostID"),
        "refer_to_post_id": post.get("referToPostID"),

        "tagged_symbols": ",".join(tagged_symbols),
        "tagged_symbols_count": len(tagged_symbols),

        **author,

        # Reserved columns for CherryStock sentiment pipeline:
        "sentiment_cherrystock": None,
        "sentiment_score": None,
    }

    return record


def to_dataframe(
    posts: list[dict[str, Any]],
    *,
    requested_symbol: str | None = None,
):
    if pd is None:
        raise RuntimeError(
            "pandas is not installed.\n"
            "Run: pip install pandas"
        )

    rows = [
        flatten_post(
            post,
            requested_symbol=requested_symbol,
        )
        for post in posts
    ]

    df = pd.DataFrame(rows)

    if not df.empty and "date" in df.columns:
        # Preserve raw timezone-aware ISO in JSON, but pandas can parse it for sorting.
        parsed = pd.to_datetime(df["date"], errors="coerce", utc=True)
        df = (
            df.assign(_date_sort=parsed)
            .sort_values("_date_sort", ascending=False)
            .drop(columns="_date_sort")
            .reset_index(drop=True)
        )

    return df


def build_daily_activity(
    df,
):
    """
    Aggregate FireAnt community activity by date.

    This does NOT infer bullish/bearish mapping from FireAnt sentiment values;
    we keep sentiment_fireant raw until its encoding is verified.
    """
    if pd is None:
        raise RuntimeError("pandas is required")

    if df.empty:
        return pd.DataFrame()

    temp = df.copy()
    temp["_date"] = pd.to_datetime(
        temp["date"],
        errors="coerce",
    ).dt.date

    daily = (
        temp.groupby("_date", dropna=True)
        .agg(
            posts=("post_id", "count"),
            likes=("total_likes", "sum"),
            replies=("total_replies", "sum"),
            shares=("total_shares", "sum"),
            ai_generated_posts=("is_ai_generated", "sum"),
            expert_ideas=("is_expert_idea", "sum"),
        )
        .reset_index()
        .rename(columns={"_date": "date"})
        .sort_values("date")
        .reset_index(drop=True)
    )

    return daily


def save_outputs(
    symbol: str,
    posts: list[dict[str, Any]],
    *,
    output_dir: str | Path = ".",
) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    symbol = symbol.upper()

    raw_json = output_dir / f"{symbol}_posts_raw.json"
    raw_json.write_text(
        json.dumps(
            posts,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    print(f"Saved: {raw_json}")

    if pd is not None:
        df = to_dataframe(
            posts,
            requested_symbol=symbol,
        )

        csv_path = output_dir / f"{symbol}_posts.csv"
        df.to_csv(
            csv_path,
            index=False,
            encoding="utf-8-sig",
        )

        daily = build_daily_activity(df)
        daily_path = output_dir / f"{symbol}_community_daily.csv"
        daily.to_csv(
            daily_path,
            index=False,
            encoding="utf-8-sig",
        )

        print(f"Saved: {csv_path}")
        print(f"Saved: {daily_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect FireAnt community posts for one stock symbol."
    )

    parser.add_argument(
        "--symbol",
        default="MWG",
        help="Ticker symbol. Default: MWG",
    )

    parser.add_argument(
        "--type",
        dest="post_type",
        type=int,
        default=0,
        help="FireAnt post type. Captured Community request used type=0.",
    )

    parser.add_argument(
        "--page-size",
        type=int,
        default=100,
        help="Posts requested per page. Default: 100",
    )

    parser.add_argument(
        "--max-posts",
        type=int,
        default=None,
        help="Optional safety cap. Default: unlimited until API is exhausted.",
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional maximum number of API pages.",
    )

    parser.add_argument(
        "--output-dir",
        default=".",
        help="Output directory. Default: current directory.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    symbol = args.symbol.upper()

    with FireAntCommunityClient() as fireant:
        posts = fireant.get_all_posts(
            symbol,
            post_type=args.post_type,
            page_size=args.page_size,
            max_posts=args.max_posts,
            max_pages=args.max_pages,
        )

    print(f"\nTotal posts collected for {symbol}: {len(posts)}")

    if posts:
        flat = flatten_post(
            posts[0],
            requested_symbol=symbol,
        )

        print("\nNewest post preview:")
        print("Date   :", flat.get("date"))
        print("Author :", flat.get("author_name"))
        print("Likes  :", flat.get("total_likes"))
        print("Replies:", flat.get("total_replies"))
        print(
            "Tagged :",
            flat.get("tagged_symbols"),
        )
        print(
            "Content:",
            (flat.get("content") or "")[:500],
        )

    save_outputs(
        symbol,
        posts,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()