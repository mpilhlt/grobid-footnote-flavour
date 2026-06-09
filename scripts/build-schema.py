#!/usr/bin/env python3
"""
Flatten composable RNG schemas from schema/*.rng -> docs/schema/.

For each top-level schema in schema/ (not shared/):
  1. Flatten all <include> directives using rnginline.
  2. Check the flattened output for duplicate <define name="..."> values.
     Duplicates indicate that a shared element needs a filename-stem prefix.
  3. Optionally validate with jing if available on PATH.
  4. Write the result to docs/schema/ with an auto-generated header comment.
"""

import sys
from collections import Counter
from pathlib import Path

try:
    import rnginline
    from lxml import etree
except ImportError:
    print(
        "ERROR: rnginline and lxml are required. Install with:\n"
        "  uv sync --group dev",
        file=sys.stderr,
    )
    sys.exit(1)

REPO_ROOT = Path(__file__).parent.parent
SCHEMA_SRC = REPO_ROOT / "schema"
SCHEMA_OUT = REPO_ROOT / "docs" / "schema"

RNG_NS = "http://relaxng.org/ns/structure/1.0"
RNG_DEFINE_TAG = f"{{{RNG_NS}}}define"
RNG_DIV_TAG = f"{{{RNG_NS}}}div"

HEADER_TEMPLATE = (
    "<!-- AUTO-GENERATED — do not edit directly.\n"
    "     Source:      schema/{stem}.rng\n"
    "     Regenerate:  python scripts/build-schema.py -->\n"
)


def flatten(src: Path) -> etree._Element:
    """Inline all <include> elements and return the flattened XML element."""
    # rnginline._get_cwd() asserts the path ends with "/" which fails on Windows.
    # Pass the base URI explicitly so that code path is never reached.
    base_uri = src.parent.as_uri() + "/"
    inliner = rnginline.Inliner(default_base_uri=base_uri)
    root = inliner.inline(path=src, create_validator=False)
    remove_divs(root)
    return root


def remove_divs(parent: etree._Element) -> None:
    """Recursively replace <div> elements with their children in-place."""
    i = 0
    while i < len(parent):
        child = parent[i]
        if child.tag == RNG_DIV_TAG:
            # Splice children of <div> into parent at position i
            tail = child.tail  # text after the <div> closing tag
            children = list(child)
            parent.remove(child)
            for j, grandchild in enumerate(children):
                parent.insert(i + j, grandchild)
            # Preserve any tail text from the div itself
            if tail and children:
                children[-1].tail = (children[-1].tail or "") + tail
            # Don't advance i — re-check the same position (may be another div)
        else:
            remove_divs(child)
            i += 1


def check_duplicates(root: etree._Element, out_name: str) -> bool:
    """
    Report any <define name="..."> that appears more than once in the
    flattened grammar. Returns True if clean, False if duplicates found.
    """
    names = [
        el.get("name")
        for el in root.iter(RNG_DEFINE_TAG)
        if el.get("name")
    ]
    counts = Counter(names)
    dupes = {n: c for n, c in counts.items() if c > 1}

    if not dupes:
        return True

    print(f"ERROR: Duplicate define name(s) in docs/schema/{out_name}:", file=sys.stderr)
    for name, count in sorted(dupes.items()):
        print(f'  - "{name}" (appears {count} times)', file=sys.stderr)
    print(file=sys.stderr)
    print(
        "Duplicate define names must be namespaced using the filename-stem convention.\n"
        'For example, a <define name="note"> in shared/bibl-struct.rng should be\n'
        'renamed <define name="bibl-struct_note">.',
        file=sys.stderr,
    )
    return False


def validate_schema(path: Path) -> None:
    """Validate the generated schema using lxml's RelaxNG parser."""
    try:
        etree.RelaxNG(file=str(path))
    except etree.RelaxNGParseError as e:
        print(f"WARNING: RelaxNG parse error in {path.name}: {e}")


def serialize(root: etree._Element, stem: str) -> str:
    """Serialize the element tree to a string and prepend the auto-generated header."""
    xml_bytes = etree.tostring(
        root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
    )
    xml_text = xml_bytes.decode("utf-8")
    header = HEADER_TEMPLATE.format(stem=stem)
    # Insert header comment after the XML declaration
    if xml_text.startswith("<?xml"):
        end = xml_text.index("?>") + 2
        return xml_text[:end] + "\n" + header + xml_text[end:]
    return header + xml_text


def main() -> None:
    sources = sorted(SCHEMA_SRC.glob("*.rng"))
    if not sources:
        print("No *.rng files found in schema/", file=sys.stderr)
        sys.exit(1)

    errors = False
    for src in sources:
        out = SCHEMA_OUT / src.name
        print(f"  {src.name} -> docs/schema/{src.name}")

        root = flatten(src)

        if not check_duplicates(root, src.name):
            errors = True
            continue

        xml_text = serialize(root, src.stem)
        out.write_text(xml_text, encoding="utf-8")
        validate_schema(out)

    if errors:
        sys.exit(1)

    print("Done.")


if __name__ == "__main__":
    main()
