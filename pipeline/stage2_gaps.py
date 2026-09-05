"""Stage 2 — content gaps from Surfer's Content Planner export.

Reads a Surfer Content Planner CSV and emits a ranked cluster list for stage 1's
primed extraction prompt.

Note on the export's real shape (observed, not assumed):
  - The header declares 9 columns but every data row carries 7. The trailing
    "Relative difficulty" / "Relative Cluster Difficulty" columns are always absent.
  - There is NO status/covered/gap column and no existing-URL column. Surfer's
    Content Planner does not flag gaps, so "gap" has to be derived here rather
    than read off a field.
  - Cluster-level figures repeat on every row of the cluster.
"""

from __future__ import annotations

import csv
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

# Clusters at or above this difficulty are unwinnable for a site with no authority.
MAX_VIABLE_DIFFICULTY = 65
# A single keyword owning this share of cluster volume means the cluster is really
# one head term with debris attached, not a topic.
HEAD_TERM_DOMINANCE = 0.6
# Head terms this large are national-brand territory regardless of difficulty.
HEAD_TERM_VOLUME = 50_000
# Share of cluster volume that must sit on ICP-relevant keywords. On the real export
# every legitimate cluster scores >= 0.88 and the noise scores <= 0.29, so anywhere in
# that gap works. Set just above the noise: "manager software" is accounting software
# but reads as 0.29 relevant, because "account manager software" is not "accounting".
MIN_ICP_RELEVANCE = 0.30

# Seeded from the DNA's own fields, plus the adjacent vocabulary a buyer uses for the
# same subject. Substring match, so "productschool" and "products" both hit "product".
ADJACENT_TERMS = {"pm", "roadmap", "kpi", "activation", "retention", "onboarding", "backlog"}

# Terms that prove a keyword belongs to a different subject entirely. These are the
# clusters that survive every metric filter: "manager software" is accounting software,
# "maturity phase" is macOS Stage Manager, "product snippet" is schema markup.
OFF_DOMAIN_TERMS = {
    "accounting", "schema", "snippet", "macbook", "mac os", "macos", "stage manager",
    "udacity", "contentsquare", "french", "restaurant",
}


@dataclass
class Cluster:
    name: str
    keywords: list[dict] = field(default_factory=list)
    volume: int = 0
    traffic: int = 0
    avg_difficulty: int = 0

    @property
    def capture_rate(self) -> float:
        """Share of cluster volume the site already captures. Low = unclaimed."""
        return self.traffic / self.volume if self.volume else 0.0

    @property
    def top_keyword(self) -> dict:
        return max(self.keywords, key=lambda k: k["volume"])

    @property
    def dominance(self) -> float:
        return self.top_keyword["volume"] / self.volume if self.volume else 0.0

    def icp_relevance(self, terms: set[str]) -> float:
        """Volume-weighted share of the cluster sitting on ICP-relevant keywords."""
        if not self.volume:
            return 0.0
        relevant = sum(k["volume"] for k in self.keywords if _is_relevant(k["keyword"], terms))
        return relevant / self.volume

    def flags(self, terms: set[str]) -> list[str]:
        out = []
        if self.avg_difficulty >= MAX_VIABLE_DIFFICULTY:
            out.append("too-difficult")
        if self.dominance >= HEAD_TERM_DOMINANCE and self.top_keyword["volume"] >= HEAD_TERM_VOLUME:
            out.append("head-term")
        if self.capture_rate >= 0.5:
            out.append("already-captured")
        if self.icp_relevance(terms) < MIN_ICP_RELEVANCE:
            out.append("off-icp")
        return out

    def opportunity(self, terms: set[str]) -> float:
        """Unclaimed, winnable volume. Higher is better. 0 for anything flagged."""
        if self.flags(terms):
            return 0.0
        winnable = max(0.0, (100 - self.avg_difficulty) / 100)
        unclaimed = 1.0 - min(self.capture_rate, 1.0)
        return round(math.log10(self.volume + 1) * winnable * unclaimed, 3)


def _int(value: str) -> int:
    return int(value) if value.strip().isdigit() else 0


def _is_relevant(keyword: str, terms: set[str]) -> bool:
    kw = keyword.lower()
    if any(bad in kw for bad in OFF_DOMAIN_TERMS):
        return False
    return any(term in kw for term in terms)


def icp_terms(dna_path: Path) -> set[str]:
    """Derive the ICP vocabulary from the DNA fields Surfer returns.

    This is why stage 4 (DNA) has to run before stage 2 — the metric filters below
    cannot tell an on-topic cluster from an off-topic one without knowing the subject.
    """
    dna = json.loads(dna_path.read_text())
    seed = " ".join(
        dna.get(field, "")
        for field in ("products_services", "topics_to_cover", "customer_profile")
    ).lower()
    # Singularize crudely so "services"/"managers" collapse onto their stems.
    words = {w.rstrip("s") for w in re.findall(r"[a-z]{3,}", seed)}
    stop = {"and", "the", "for", "possibly", "unknown", "inactive", "presence", "online"}
    return (words - stop) | ADJACENT_TERMS


def parse(csv_path: Path, terms: set[str]) -> list[Cluster]:
    with csv_path.open(newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.reader(fh) if r]

    clusters: dict[str, Cluster] = {}
    for row in rows[1:]:
        # Rows are short relative to the header; pad rather than unpack positionally.
        row = row + [""] * (7 - len(row))
        name, keyword, volume, cluster_volume, cluster_traffic, difficulty, avg_difficulty = row[:7]

        cluster = clusters.setdefault(name, Cluster(name=name))
        cluster.volume = _int(cluster_volume)
        cluster.traffic = _int(cluster_traffic)
        cluster.avg_difficulty = _int(avg_difficulty)
        cluster.keywords.append(
            {"keyword": keyword, "volume": _int(volume), "difficulty": _int(difficulty)}
        )

    return sorted(clusters.values(), key=lambda c: c.opportunity(terms), reverse=True)


def to_gaps(clusters: list[Cluster], terms: set[str], keywords_per_cluster: int = 8) -> dict:
    """Shape stage 1's prompt consumes. Rejected clusters are kept, with a reason —
    dropping them silently makes a bad filter impossible to debug."""
    viable, rejected = [], []
    for cluster in clusters:
        entry = {
            "cluster": cluster.name,
            "opportunity": cluster.opportunity(terms),
            "icp_relevance": round(cluster.icp_relevance(terms), 3),
            "volume": cluster.volume,
            "traffic": cluster.traffic,
            "avg_difficulty": cluster.avg_difficulty,
            "capture_rate": round(cluster.capture_rate, 3),
            "keywords": [
                {"keyword": k["keyword"], "volume": k["volume"], "difficulty": k["difficulty"]}
                for k in sorted(cluster.keywords, key=lambda k: -k["volume"])[:keywords_per_cluster]
            ],
        }
        if cluster.flags(terms):
            rejected.append({**entry, "rejected_for": cluster.flags(terms)})
        else:
            viable.append(entry)

    return {
        "source": "surferseo-content-planner",
        "derived_gap_flag": True,  # Surfer ships no gap column; these are computed here.
        "viable": viable,
        "rejected": rejected,
    }


if __name__ == "__main__":
    import sys

    path = Path(sys.argv[1]) if len(sys.argv) > 1 else next(
        Path(__file__).parent.parent.glob("data/fixtures/surfer-content-planner-*.csv")
    )
    terms = icp_terms(path.parent / "site_dna.json")
    clusters = parse(path, terms)
    gaps = to_gaps(clusters, terms)

    print(f"icp terms: {' '.join(sorted(terms))}\n")
    print(f"{'cluster':<42}{'opp':>7}{'icp':>6}{'vol':>9}{'traf':>8}{'diff':>6}  flags")
    for cluster in clusters:
        print(
            f"{cluster.name[:41]:<42}{cluster.opportunity(terms):>7}"
            f"{cluster.icp_relevance(terms):>6.2f}{cluster.volume:>9}"
            f"{cluster.traffic:>8}{cluster.avg_difficulty:>6}  {','.join(cluster.flags(terms))}"
        )
    print(f"\nviable: {len(gaps['viable'])}   rejected: {len(gaps['rejected'])}")

    out = path.parent / "gaps.json"
    out.write_text(json.dumps(gaps, indent=2))
    print(f"wrote {out}")
