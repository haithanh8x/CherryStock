#!/usr/bin/env python3
"""CherryStock preflight checks for Archify architecture sources.

This catches repository-owned invariants before invoking Archify so common schema and
navigation mistakes fail fast with concise diagnostics. Archify remains the authority
for its full schema, geometry and showcase composition validation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MAX_COMPONENT_SOURCES = 3


def fail(errors: list[str]) -> int:
    print("CherryStock Archify preflight: FAIL")
    for index, error in enumerate(errors, start=1):
        print(f"  {index}. {error}")
    return 1


def load_json(path: Path, label: str, errors: list[str]) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"{label} not found: {path}")
        return None
    except json.JSONDecodeError as exc:
        errors.append(f"{label} is invalid JSON: {path} ({exc})")
        return None
    if not isinstance(value, dict):
        errors.append(f"{label} root must be a JSON object: {path}")
        return None
    return value


def validate(
    input_path: Path,
    repo_root: Path,
    output_path: Path | None,
    navigation_config: Path | None,
) -> int:
    errors: list[str] = []
    source = load_json(input_path, "Archify source", errors)
    if source is None:
        return fail(errors)

    if source.get("diagram_type") != "architecture":
        errors.append(
            f"diagram_type must be 'architecture', got {source.get('diagram_type')!r}"
        )

    components = source.get("components")
    if not isinstance(components, list) or not components:
        errors.append("components must be a non-empty list")
        components = []

    component_ids: list[str] = []
    for index, component in enumerate(components):
        if not isinstance(component, dict):
            errors.append(f"components[{index}] must be an object")
            continue
        component_id = component.get("id")
        if not isinstance(component_id, str) or not component_id.strip():
            errors.append(f"components[{index}].id must be a non-empty string")
            continue
        component_ids.append(component_id)

        sources = component.get("sources", [])
        if sources is None:
            sources = []
        if not isinstance(sources, list):
            errors.append(f"component '{component_id}': sources must be a list")
            continue
        if len(sources) > MAX_COMPONENT_SOURCES:
            errors.append(
                f"component '{component_id}': sources has {len(sources)} items; "
                f"Archify architecture schema allows at most {MAX_COMPONENT_SOURCES}. "
                "Keep drill-down/navigation in cherrystock-archify-navigation.json."
            )

        for source_index, item in enumerate(sources):
            if not isinstance(item, dict):
                errors.append(
                    f"component '{component_id}': sources[{source_index}] must be an object"
                )
                continue
            path_value = item.get("path")
            label_value = str(item.get("label", ""))
            if not isinstance(path_value, str) or not path_value.strip():
                errors.append(
                    f"component '{component_id}': sources[{source_index}].path is required"
                )
                continue
            normalized = path_value.replace("\\", "/")
            if normalized.lower().endswith(".html") or "drill-down" in label_value.lower():
                errors.append(
                    f"component '{component_id}': source '{path_value}' looks like presentation/navigation. "
                    "Archify component.sources is evidence only; use the navigation config for drill-down."
                )
            resolved_source = (repo_root / Path(normalized)).resolve()
            if not resolved_source.is_file():
                errors.append(
                    f"component '{component_id}': source path does not exist: {path_value}"
                )

    duplicates = sorted({value for value in component_ids if component_ids.count(value) > 1})
    if duplicates:
        errors.append(f"duplicate component id(s): {', '.join(duplicates)}")

    component_id_set = set(component_ids)
    connections = source.get("connections", [])
    if not isinstance(connections, list):
        errors.append("connections must be a list")
        connections = []
    for index, connection in enumerate(connections):
        if not isinstance(connection, dict):
            errors.append(f"connections[{index}] must be an object")
            continue
        for endpoint in ("from", "to"):
            value = connection.get(endpoint)
            if value not in component_id_set:
                errors.append(
                    f"connections[{index}].{endpoint} references unknown component id: {value!r}"
                )

    if navigation_config is not None:
        navigation = load_json(navigation_config, "Navigation config", errors)
        if navigation is not None:
            pages = navigation.get("pages", {})
            if not isinstance(pages, dict):
                errors.append("navigation config pages must be an object")
                pages = {}

            if output_path is not None:
                page_name = output_path.name
                page_config = pages.get(page_name)
                if page_config is None:
                    print(
                        f"CherryStock Archify preflight: navigation has no mapping for {page_name}; navigation step will skip."
                    )
                elif not isinstance(page_config, dict):
                    errors.append(f"navigation page config for {page_name} must be an object")
                else:
                    nodes = page_config.get("nodes", {})
                    if nodes is None:
                        nodes = {}
                    if not isinstance(nodes, dict):
                        errors.append(f"navigation nodes for {page_name} must be an object")
                    else:
                        unknown_nodes = sorted(set(nodes) - component_id_set)
                        if unknown_nodes:
                            errors.append(
                                f"navigation for {page_name} references unknown node id(s): "
                                + ", ".join(unknown_nodes)
                            )
                        for node_id, node_cfg in nodes.items():
                            if not isinstance(node_cfg, dict):
                                errors.append(
                                    f"navigation node '{node_id}' for {page_name} must be an object"
                                )
                                continue
                            target = node_cfg.get("target")
                            if not isinstance(target, str) or not target.strip():
                                errors.append(
                                    f"navigation node '{node_id}' for {page_name} requires target"
                                )

                    back = page_config.get("back")
                    if back is not None:
                        if not isinstance(back, dict) or not isinstance(back.get("target"), str):
                            errors.append(
                                f"navigation back config for {page_name} requires a string target"
                            )

    if errors:
        return fail(errors)

    print("CherryStock Archify preflight: PASS")
    print(f"  components: {len(component_ids)}")
    print(f"  connections: {len(connections)}")
    print(f"  max component sources: {MAX_COMPONENT_SOURCES}")
    if output_path is not None:
        print(f"  output: {output_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight CherryStock Archify architecture source")
    parser.add_argument("input", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--navigation-config", type=Path, default=None)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    input_path = args.input if args.input.is_absolute() else (repo_root / args.input)
    output_path = None
    if args.output is not None:
        output_path = args.output if args.output.is_absolute() else (repo_root / args.output)
    navigation_config = None
    if args.navigation_config is not None:
        navigation_config = (
            args.navigation_config
            if args.navigation_config.is_absolute()
            else (repo_root / args.navigation_config)
        )

    return validate(
        input_path.resolve(),
        repo_root,
        output_path.resolve() if output_path else None,
        navigation_config.resolve() if navigation_config else None,
    )


if __name__ == "__main__":
    sys.exit(main())
