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
MIN_DIRECT_CONNECTION_CLEARANCE = 24.0
SHOWCASE_DESKTOP_AVAILABLE_WIDTH = 930.0
SHOWCASE_MIN_PROJECTED_CONTEXT_PX = 6.0
SHOWCASE_CONTEXT_SOURCE_FONT_PX = 9.0


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



def _component_rect(component: dict) -> tuple[float, float, float, float] | None:
    pos = component.get("pos")
    size = component.get("size")
    if (
        not isinstance(pos, list)
        or len(pos) != 2
        or not isinstance(size, list)
        or len(size) != 2
    ):
        return None
    try:
        x, y = float(pos[0]), float(pos[1])
        width, height = float(size[0]), float(size[1])
    except (TypeError, ValueError):
        return None
    return x, y, width, height


def _direct_connection_clearance(
    connection: dict,
    components_by_id: dict[str, dict],
) -> float | None:
    """Return endpoint-to-endpoint gap for an explicit straight cardinal connection.

    Archify showcase currently requires at least 24 px for a short direct connection.
    Only evaluate relationships whose geometry is unambiguous locally; automatic or
    routed/via relationships remain Archify's responsibility.
    """

    if connection.get("route") != "straight" or connection.get("via"):
        return None

    source = components_by_id.get(connection.get("from"))
    target = components_by_id.get(connection.get("to"))
    if source is None or target is None:
        return None

    source_rect = _component_rect(source)
    target_rect = _component_rect(target)
    if source_rect is None or target_rect is None:
        return None

    sx, sy, sw, sh = source_rect
    tx, ty, tw, th = target_rect
    from_side = connection.get("fromSide")
    to_side = connection.get("toSide")

    if from_side == "right" and to_side == "left":
        return tx - (sx + sw)
    if from_side == "left" and to_side == "right":
        return sx - (tx + tw)
    if from_side == "bottom" and to_side == "top":
        return ty - (sy + sh)
    if from_side == "top" and to_side == "bottom":
        return sy - (ty + th)
    return None


def _validate_showcase_readability_budget(source: dict, errors: list[str]) -> None:
    meta = source.get("meta", {})
    view_box = meta.get("viewBox") if isinstance(meta, dict) else None
    if not isinstance(view_box, list) or len(view_box) != 2:
        return
    try:
        view_box_width = float(view_box[0])
    except (TypeError, ValueError):
        return
    if view_box_width <= 0:
        return

    projected_context_px = (
        SHOWCASE_CONTEXT_SOURCE_FONT_PX
        * SHOWCASE_DESKTOP_AVAILABLE_WIDTH
        / view_box_width
    )
    if projected_context_px < SHOWCASE_MIN_PROJECTED_CONTEXT_PX:
        max_safe_width = (
            SHOWCASE_CONTEXT_SOURCE_FONT_PX
            * SHOWCASE_DESKTOP_AVAILABLE_WIDTH
            / SHOWCASE_MIN_PROJECTED_CONTEXT_PX
        )
        errors.append(
            "showcase desktop readability budget is too small: "
            f"viewBox width {view_box_width:g}px projects 9px context text to "
            f"{projected_context_px:.3f}px (< {SHOWCASE_MIN_PROJECTED_CONTEXT_PX:g}px). "
            f"Keep viewBox width <= {max_safe_width:g}px or split/compact the diagram."
        )

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

    _validate_showcase_readability_budget(source, errors)

    components = source.get("components")
    if not isinstance(components, list) or not components:
        errors.append("components must be a non-empty list")
        components = []

    component_ids: list[str] = []
    components_by_id: dict[str, dict] = {}
    for index, component in enumerate(components):
        if not isinstance(component, dict):
            errors.append(f"components[{index}] must be an object")
            continue
        component_id = component.get("id")
        if not isinstance(component_id, str) or not component_id.strip():
            errors.append(f"components[{index}].id must be a non-empty string")
            continue
        component_ids.append(component_id)
        components_by_id[component_id] = component

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

        if (
            connection.get("from") in component_id_set
            and connection.get("to") in component_id_set
        ):
            clearance = _direct_connection_clearance(connection, components_by_id)
            if (
                clearance is not None
                and clearance < MIN_DIRECT_CONNECTION_CLEARANCE
            ):
                label = connection.get("label") or (
                    f"{connection.get('from')} -> {connection.get('to')}"
                )
                errors.append(
                    f"connection {label!r} has only {clearance:g}px direct clearance; "
                    f"minimum is {MIN_DIRECT_CONNECTION_CLEARANCE:g}px. "
                    "Move the components farther apart before Archify showcase validation."
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
    print(f"  min explicit direct connection clearance: {MIN_DIRECT_CONNECTION_CLEARANCE:g}px")
    print(f"  showcase context readability budget: >= {SHOWCASE_MIN_PROJECTED_CONTEXT_PX:g}px projected")
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
