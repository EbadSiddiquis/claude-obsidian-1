#!/usr/bin/env python3
"""query.py - the Graph-RAG traversal demo: start from a control (or node), walk the authority
graph across sovereigns, and emit the citation-pinned bundle an LLM needs to generate a spec/WSP.

This is the step plain vector RAG cannot do: the FDIC pass-through <-> SEC custody-ban <-> FinCEN
AML joins are EDGES, found by traversal, not by embedding similarity.

USAGE
  python3 query.py --control oracle_custody_qualified_third_party
  python3 query.py --node cfr-17-227.303 --hops 2
  python3 query.py --control oracle_custody_qualified_third_party --json   # feed to an LLM prompt
"""
import argparse
import json
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "oracle.db")


def expand(con, seed_ids, hops=2):
    """BFS along all edge types from the seed nodes; returns (nodes, edges) touched."""
    seen, frontier, hit_edges = set(seed_ids), set(seed_ids), []
    for _ in range(hops):
        if not frontier:
            break
        q = ",".join("?" * len(frontier))
        rows = con.execute(
            f"SELECT src, dst, rel, note FROM edges WHERE src IN ({q}) OR dst IN ({q})",
            list(frontier) * 2).fetchall()
        nxt = set()
        for src, dst, rel, note in rows:
            if (src, dst, rel) not in [(e[0], e[1], e[2]) for e in hit_edges]:
                hit_edges.append((src, dst, rel, note))
            for n in (src, dst):
                if n not in seen:
                    seen.add(n)
                    nxt.add(n)
        frontier = nxt
    q = ",".join("?" * len(seen))
    nodes = con.execute(
        f"SELECT id, tier, sovereign, citation, title, pinned_version FROM nodes WHERE id IN ({q})",
        list(seen)).fetchall()
    return nodes, hit_edges


def main():
    ap = argparse.ArgumentParser(description="Traverse the authority graph from a control or node.")
    ap.add_argument("--control")
    ap.add_argument("--node")
    ap.add_argument("--hops", type=int, default=2)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if not args.control and not args.node:
        ap.error("give --control or --node")

    con = sqlite3.connect(DB)
    ctrl = None
    if args.control:
        row = con.execute("SELECT id, obligation, sovereign, severity, state FROM controls WHERE id=?",
                          (args.control,)).fetchone()
        if not row:
            raise SystemExit(f"no control '{args.control}'")
        ctrl = {"id": row[0], "obligation": row[1], "sovereign": row[2], "severity": row[3], "state": row[4]}
        seeds = [r[0] for r in con.execute(
            "SELECT node_id FROM control_authorities WHERE control_id=?", (args.control,))]
    else:
        seeds = [args.node]

    nodes, edges = expand(con, seeds, args.hops)
    wsps = []
    if ctrl:
        wsps = [{"id": r[0], "status": r[1], "supervised_by": r[2]} for r in con.execute(
            "SELECT id, status, supervised_by FROM wsp_procedures WHERE control_id=?", (ctrl["id"],))]

    if args.json:
        print(json.dumps({
            "control": ctrl,
            "authority_bundle": [{"id": n[0], "tier": n[1], "sovereign": n[2], "citation": n[3],
                                  "title": n[4], "pinned_version": n[5]} for n in nodes],
            "edges": [{"src": e[0], "dst": e[1], "rel": e[2], "why": e[3]} for e in edges],
            "wsp_procedures": wsps,
            "discipline": "Outputs generated from this bundle are CANDIDATES pending principal "
                          "adoption; nothing here is a legal conclusion."}, indent=2))
        return

    if ctrl:
        print(f"CONTROL {ctrl['id']}  [{ctrl['sovereign']}] ({ctrl['severity']}, state={ctrl['state']})")
        print(f"  {ctrl['obligation']}\n")
    print(f"AUTHORITY BUNDLE ({len(nodes)} nodes, {args.hops}-hop expansion from {len(seeds)} seed(s)):")
    by_sov = {}
    for n in sorted(nodes, key=lambda x: (x[2], x[3])):
        by_sov.setdefault(n[2], []).append(n)
    for sov, ns in by_sov.items():
        print(f"  [{sov}]")
        for n in ns:
            print(f"    {n[3]:20} @{n[5]}  (tier {n[1]})  {(n[4] or '')[:58]}")
    print(f"\nCROSS-SOVEREIGN EDGES ({len(edges)}):")
    for src, dst, rel, note in edges:
        print(f"  {src} --{rel}--> {dst}")
        print(f"      {note}")
    if wsps:
        print(f"\nWSP PROCEDURES: " + ", ".join(f"{w['id']} [{w['status']}]" for w in wsps))
    print("\nThis bundle assembles authority; it draws no conclusion. Generated outputs are "
          "candidates pending principal adoption.")


if __name__ == "__main__":
    main()
