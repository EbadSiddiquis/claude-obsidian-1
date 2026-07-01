"""authority_registry.py - load the authority registry; resolve control authority_refs to nodes.

The registry (controls/authorities.json) holds the source-of-truth NODES; controls cite them by
id (the provenance edge). See docs/authority-model.md.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.join(os.path.dirname(HERE), "controls", "authorities.json")


def load_registry(path=REGISTRY):
    return {a["id"]: a for a in json.load(open(path, encoding="utf-8"))["authorities"]}


def resolve(refs, registry):
    """authority_refs -> [node]; silently drops unknown ids (use dangling() to detect them)."""
    return [registry[r] for r in (refs or []) if r in registry]


def dangling(refs, registry):
    return [r for r in (refs or []) if r not in registry]
