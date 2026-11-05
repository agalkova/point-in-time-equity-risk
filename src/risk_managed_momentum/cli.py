from __future__ import annotations

import argparse


def parse_no_arguments(description: str) -> None:
    """Provide standard help and reject unexpected arguments for a no-argument command."""
    argparse.ArgumentParser(description=description).parse_args()
