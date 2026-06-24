"""
Foldseek REST API client for structural similarity search.

Submits a PDB file to the public Foldseek server and returns structural
homologs from PDB and/or AlphaFold databases.

Can be used standalone:
  python foldseek_search.py protein.pdb --databases pdb100 afdb-swissprot

Or imported as a module (does NOT require the esmfold conda env — only stdlib + requests).
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Optional

import ssl

import requests
from requests.adapters import HTTPAdapter

logger = logging.getLogger(__name__)


def _make_session() -> requests.Session:
    """Return a requests Session with TLS 1.2 fallback for Python 3.8 compatibility."""
    session = requests.Session()
    try:
        from urllib3.util.ssl_ import create_urllib3_context

        class _TLS12Adapter(HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                ctx = create_urllib3_context()
                ctx.minimum_version = ssl.TLSVersion.TLSv1_2
                ctx.maximum_version = ssl.TLSVersion.TLSv1_2
                kwargs["ssl_context"] = ctx
                super().init_poolmanager(*args, **kwargs)

        session.mount("https://", _TLS12Adapter())
    except Exception:
        pass  # fall through to default SSL handling
    return session


_SESSION: Optional[requests.Session] = None


def _get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = _make_session()
    return _SESSION

# ── Constants ────────────────────────────────────────────────────────────────

FOLDSEEK_API    = "https://search.foldseek.com/api"
POLL_INTERVAL   = 5    # seconds between status polls
DEFAULT_TIMEOUT = 120  # max seconds to wait for results
DEFAULT_TOP_N   = 10

# Databases exposed on the public Foldseek server
AVAILABLE_DATABASES: dict[str, str] = {
    "pdb100":          "PDB 实验结构（全库）",
    "afdb50":          "AlphaFold DB（50% 冗余去除）",
    "afdb-swissprot":  "AlphaFold SwissProt（功能注释完善）",
    "afdb-proteome":   "AlphaFold 全蛋白质组",
    "cath50":          "CATH 结构域数据库",
}
DEFAULT_DATABASES = ["pdb100", "afdb-swissprot"]


# ── Internal helpers ─────────────────────────────────────────────────────────

def _submit(pdb_path: str, databases: list[str], mode: str) -> str:
    """POST PDB to Foldseek. Returns ticket ID."""
    url  = f"{FOLDSEEK_API}/ticket"
    form = [("mode", mode)] + [("database[]", db) for db in databases]
    with open(pdb_path, "rb") as fh:
        files = {"q": (Path(pdb_path).name, fh, "chemical/x-pdb")}
        resp = _get_session().post(url, data=form, files=files, timeout=60)
    resp.raise_for_status()
    ticket_id = resp.json()["id"]
    logger.info(f"Foldseek ticket: {ticket_id}")
    return ticket_id


def _wait(ticket_id: str, timeout: int) -> None:
    """Poll until COMPLETE or timeout."""
    url      = f"{FOLDSEEK_API}/ticket/{ticket_id}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp   = _get_session().get(url, timeout=15)
        resp.raise_for_status()
        status = resp.json().get("status", "UNKNOWN")
        if status == "COMPLETE":
            return
        if status == "ERROR":
            raise RuntimeError("Foldseek server reported an error for this search")
        logger.debug(f"Foldseek status: {status}, waiting {POLL_INTERVAL}s...")
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"Foldseek search did not complete within {timeout}s")


def _fetch(ticket_id: str) -> dict:
    """Fetch results page 0."""
    url  = f"{FOLDSEEK_API}/result/{ticket_id}/0"
    resp = _get_session().get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _split_target(raw_target: str) -> tuple[str, str]:
    """
    Foldseek embeds the protein name inside the target field for afdb entries:
      "AF-Q8ZKW4-F1-model_v6 Aspartate--ammonia ligase"
    Split on the first space: (target_id, embedded_description).
    For PDB entries like "4YGS_A" there is no embedded description.
    """
    parts = raw_target.split(" ", 1)
    return parts[0], parts[1] if len(parts) > 1 else ""


def _parse_hits(raw: dict, top_n: int) -> list[dict]:
    """Flatten raw Foldseek response into a sorted hit list."""
    hits: list[dict] = []
    for db_result in raw.get("results", []):
        db_name = db_result.get("db", "unknown")
        for alignment_list in db_result.get("alignments", []):
            for hit in alignment_list:
                evalue = hit.get("eval") or hit.get("evalue")

                # seqId is returned as 0–100 percentage; normalize to 0–1
                raw_seqid = float(hit.get("seqId", 0))
                seq_id = round(raw_seqid / 100 if raw_seqid > 1 else raw_seqid, 4)

                # target may embed protein name: split into ID + description
                target_id, embedded_desc = _split_target(hit.get("target", ""))
                description = (hit.get("description") or embedded_desc or "").strip()

                hits.append({
                    "target":      target_id,
                    "database":    db_name,
                    "prob":        round(float(hit.get("prob", 0)), 4),
                    "evalue":      float(evalue) if evalue is not None else None,
                    "seq_id":      seq_id,
                    "aln_length":  hit.get("alnLength"),
                    "q_start":     hit.get("qStartPos"),
                    "q_end":       hit.get("qEndPos"),
                    "description": description,
                    "taxon":       (hit.get("taxName") or "").strip(),
                    "tax_id":      hit.get("taxId"),
                })

    hits.sort(key=lambda h: h["prob"], reverse=True)
    return hits[:top_n]


# ── Public API ───────────────────────────────────────────────────────────────

def search(
    pdb_path: str,
    databases: Optional[list[str]] = None,
    top_n: int = DEFAULT_TOP_N,
    mode: str = "3diaa",
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """
    Run structural similarity search via the Foldseek public server.

    Args:
        pdb_path:   Path to a PDB file (predicted or experimental).
        databases:  Foldseek databases to search (default: pdb100 + afdb-swissprot).
        top_n:      Maximum hits to return across all databases.
        mode:       "3diaa" (structure+sequence, recommended) or "tmscore".
        timeout:    Seconds to wait for server results (default 120).

    Returns:
        {
          "ticket_id": str,
          "databases": list[str],
          "total_hits": int,
          "top_hits": list[dict],   # sorted by prob descending
        }

    Raises:
        requests.HTTPError:  HTTP-level error from the server.
        TimeoutError:        Server did not finish within `timeout` seconds.
        RuntimeError:        Server-side search error.
    """
    if databases is None:
        databases = DEFAULT_DATABASES

    logger.info(f"Foldseek search: {pdb_path} → {databases}")
    ticket_id = _submit(pdb_path, databases, mode)
    _wait(ticket_id, timeout)
    raw  = _fetch(ticket_id)
    hits = _parse_hits(raw, top_n)

    return {
        "ticket_id":  ticket_id,
        "databases":  databases,
        "total_hits": len(hits),
        "top_hits":   hits,
    }


# ── CLI ──────────────────────────────────────────────────────────────────────

def _cli() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(
        description="Foldseek structural similarity search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\nAvailable databases:\n"
               + "\n".join(f"  {k:20s} {v}" for k, v in AVAILABLE_DATABASES.items()),
    )
    parser.add_argument("pdb", help="Path to PDB file")
    parser.add_argument(
        "--databases", "-d", nargs="+", default=DEFAULT_DATABASES,
        metavar="DB", help=f"Databases to search (default: {' '.join(DEFAULT_DATABASES)})",
    )
    parser.add_argument("--top", "-n", type=int, default=DEFAULT_TOP_N,
                        help=f"Number of top hits to show (default: {DEFAULT_TOP_N})")
    parser.add_argument("--mode", default="3diaa", choices=["3diaa", "tmscore"],
                        help="Search mode (default: 3diaa)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"Max seconds to wait (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    result = search(
        pdb_path=args.pdb,
        databases=args.databases,
        top_n=args.top,
        mode=args.mode,
        timeout=args.timeout,
    )

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(f"\n[OK] Foldseek search complete — {result['total_hits']} hits")
    print(f"  Ticket: {result['ticket_id']}")
    print(f"  {'Rank':<5} {'Target':<22} {'DB':<18} {'Prob':>6} {'E-val':>10} {'SeqID%':>7}  Description")
    print("  " + "-" * 95)
    for i, h in enumerate(result["top_hits"], 1):
        eval_s = f"{h['evalue']:.1e}" if h["evalue"] is not None else "  —"
        desc   = h["description"][:40] + ("…" if len(h["description"]) > 40 else "")
        seqid  = h["seq_id"] * 100  # display as percentage
        print(f"  {i:<5} {h['target']:<22} {h['database']:<18} "
              f"{h['prob']:>6.4f} {eval_s:>10} {seqid:>6.1f}%  {desc}")


if __name__ == "__main__":
    _cli()
