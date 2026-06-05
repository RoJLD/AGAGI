from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Sequence

import matplotlib.pyplot as plt
from src.seed_ai.mutation import Genome

try:
    import graphviz
except ImportError:  # pragma: no cover
    graphviz = None


def save_experiment_history_csv(
    gate_name: str,
    fitness_history: Sequence[float],
    accuracy_history: Sequence[float],
    size_history: Sequence[int] | None = None,
    output_dir: Path | str = Path("./results"),
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / f"{gate_name.lower()}_history.csv"
    fieldnames = ["generation", "fitness", "accuracy"]
    if size_history is not None:
        fieldnames.append("size")

    with csv_path.open(mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for generation, fitness, accuracy in zip(range(1, len(fitness_history) + 1), fitness_history, accuracy_history):
            row = {
                "generation": generation,
                "fitness": fitness,
                "accuracy": accuracy,
            }
            if size_history is not None:
                row["size"] = size_history[generation - 1]
            writer.writerow(row)

    return csv_path


def save_experiment_history_json(
    gate_name: str,
    fitness_history: Sequence[float],
    accuracy_history: Sequence[float],
    size_history: Sequence[int] | None = None,
    output_dir: Path | str = Path("./results"),
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    history = {
        "generation": list(range(1, len(fitness_history) + 1)),
        "fitness": list(fitness_history),
        "accuracy": list(accuracy_history),
    }
    if size_history is not None:
        history["size"] = list(size_history)

    json_path = output_dir / f"{gate_name.lower()}_history.json"
    json_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    return json_path


def describe_genome_topology(genome: Genome) -> str:
    n_nodes = genome.num_nodes
    inputs = list(range(genome.num_inputs))
    outputs = list(range(n_nodes - genome.num_outputs, n_nodes))
    edges = [
        (int(i), int(j), float(genome.W[i, j]))
        for i in range(n_nodes)
        for j in range(n_nodes)
        if genome.W[i, j] != 0.0
    ]

    lines = [
        f"Nombre de nœuds : {n_nodes}",
        f"Entrées : {inputs}",
        f"Sorties : {outputs}",
        f"Nombre de connexions actives : {len(edges)}",
        f"Densité de connexions : {len(edges) / max(1, n_nodes * (n_nodes - 1) / 2):.4f}",
        "",
        "Connexions (source → cible, poids) :",
    ]

    for source, target, weight in edges:
        lines.append(f" - {source} -> {target} : {weight:.4f}")

    return "\n".join(lines)


def save_genome_topology_txt(
    gate_name: str,
    genome: Genome,
    output_dir: Path | str = Path("./results"),
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    txt_path = output_dir / f"{gate_name.lower()}_topology.txt"
    txt_path.write_text(describe_genome_topology(genome), encoding="utf-8")
    return txt_path


def save_genome_topology_edge_list_csv(
    gate_name: str,
    genome: Genome,
    output_dir: Path | str = Path("./results"),
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / f"{gate_name.lower()}_topology_edges.csv"
    fieldnames = ["source", "target", "weight"]
    with csv_path.open(mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(genome.num_nodes):
            for j in range(genome.num_nodes):
                if genome.W[i, j] != 0.0:
                    writer.writerow({
                        "source": i,
                        "target": j,
                        "weight": float(genome.W[i, j]),
                    })
    return csv_path


def compute_genome_layers(genome: Genome) -> dict[int, int]:
    layers = {node_id: 0 for node_id in range(genome.num_inputs)}
    n_nodes = genome.num_nodes

    for node_id in range(genome.num_inputs, n_nodes):
        parent_layers = [
            layers[parent_id]
            for parent_id in range(node_id)
            if genome.W[parent_id, node_id] != 0.0
        ]
        layers[node_id] = min(parent_layers) + 1 if parent_layers else 0

    return layers


def save_genome_graphviz_dot(
    gate_name: str,
    genome: Genome,
    output_dir: Path | str = Path("./results"),
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    dot_path = output_dir / f"{gate_name.lower()}_topology.dot"
    layers = compute_genome_layers(genome)
    max_layer = max(layers.values()) if layers else 0
    lines = [
        "digraph G {",
        "    rankdir=LR;",
        "    ranksep=1.0;",
        "    nodesep=0.8;",
        "    splines=true;",
        "    node [fontsize=10, style=filled, fillcolor=white];",
    ]

    n_nodes = genome.num_nodes
    for node_id in range(n_nodes):
        if node_id < genome.num_inputs:
            shape = "box"
            label = f"I{node_id}"
            if genome.num_inputs > 2 and node_id == genome.num_inputs - 1:
                label = "B"
            color = "darkgreen"
        elif node_id >= n_nodes - genome.num_outputs:
            shape = "box"
            output_index = node_id - (n_nodes - genome.num_outputs)
            label = f"O{output_index}"
            color = "darkred"
        else:
            shape = "ellipse"
            label = f"H{node_id}"
            color = "gray"

        lines.append(
            f"    {node_id} [label=\"{label}\", shape={shape}, color={color}, penwidth=2.0];"
        )

    for layer in range(max_layer + 1):
        layer_nodes = [node_id for node_id, layer_id in layers.items() if layer_id == layer]
        if not layer_nodes:
            continue
        lines.append(f"    subgraph cluster_layer_{layer} {{")
        lines.append("        rank=same;")
        for node_id in layer_nodes:
            lines.append(f"        {node_id};")
        lines.append("    }")

    for i in range(n_nodes):
        for j in range(n_nodes):
            weight = float(genome.W[i, j])
            if weight == 0.0:
                continue
            label = f"{weight:.3f}"
            penwidth = max(1.0, min(4.0, abs(weight) * 2.0))
            color = "blue" if weight > 0 else "red"
            lines.append(
                f"    {i} -> {j} [label=\"{label}\", color={color}, penwidth={penwidth:.1f}];"
            )

    lines.append("}")
    dot_path.write_text("\n".join(lines), encoding="utf-8")
    return dot_path


def genome_to_json(genome: Genome) -> dict:
    nodes = []
    links = []
    n_nodes = genome.num_nodes

    for node_id in range(n_nodes):
        if node_id < genome.num_inputs:
            node_type = "input"
            label = f"I{node_id}"
            if genome.num_inputs > 2 and node_id == genome.num_inputs - 1:
                label = "B"
        elif node_id >= n_nodes - genome.num_outputs:
            node_type = "output"
            output_index = node_id - (n_nodes - genome.num_outputs)
            label = f"O{output_index}"
        else:
            node_type = "hidden"
            label = f"H{node_id}"

        nodes.append({
            "id": node_id,
            "label": label,
            "type": node_type,
        })

    for i in range(n_nodes):
        for j in range(n_nodes):
            weight = float(genome.W[i, j])
            if weight == 0.0:
                continue
            links.append({
                "source": i,
                "target": j,
                "weight": weight,
            })

    return {"nodes": nodes, "links": links}


def save_genome_graph_json(
    gate_name: str,
    genome: Genome,
    output_dir: Path | str = Path("./results"),
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    graph_json = genome_to_json(genome)
    json_path = output_dir / f"{gate_name.lower()}_topology.json"
    json_path.write_text(json.dumps(graph_json, indent=2), encoding="utf-8")
    return json_path


def save_genome_interactive_html(
    gate_name: str,
    genome: Genome,
    output_dir: Path | str = Path("./results"),
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    graph_json = genome_to_json(genome)
    html_path = output_dir / f"{gate_name.lower()}_interactive_topology.html"
    html_lines = [
        "<!DOCTYPE html>",
        "<html lang=\"fr\">",
        "<head>",
        "  <meta charset=\"utf-8\">",
        "  <title>" + gate_name + " interactive topology</title>",
        "  <style>",
        "    body { margin: 0; font-family: Arial, sans-serif; background: #f7f7f7; }",
        "    header { padding: 1rem; background: #222; color: white; }",
        "    #graph { width: 100vw; height: calc(100vh - 80px); }",
        "    .node circle { stroke: #333; stroke-width: 1.5px; }",
        "    .node text { font-size: 12px; pointer-events: none; fill: #111; }",
        "    .link { stroke-opacity: 0.7; }",
        "    .tooltip { position: absolute; padding: 0.4rem 0.6rem; border-radius: 4px; background: rgba(0,0,0,0.75); color: white; font-size: 12px; pointer-events: none; display: none; }",
        "  </style>",
        "</head>",
        "<body>",
        "  <header><h1>" + gate_name + " topology interactive</h1></header>",
        "  <div id=\"graph\"></div>",
        "  <div class=\"tooltip\" id=\"tooltip\"></div>",
        "  <script src=\"https://d3js.org/d3.v7.min.js\"></script>",
        "  <script>",
        "    const graph = " + json.dumps(graph_json) + ";",
        "    const width = window.innerWidth;",
        "    const height = window.innerHeight - 80;",
        "    const color = d => d.type === 'input' ? '#1f77b4' : d.type === 'output' ? '#d62728' : '#7f7f7f';",
        "    const svg = d3.select('#graph').append('svg').attr('width', width).attr('height', height);",
        "",
        "    const defs = svg.append('defs');",
        "    defs.append('marker')",
        "      .attr('id', 'arrow')",
        "      .attr('viewBox', '0 -5 10 10')",
        "      .attr('refX', 18)",
        "      .attr('refY', 0)",
        "      .attr('markerWidth', 6)",
        "      .attr('markerHeight', 6)",
        "      .attr('orient', 'auto')",
        "      .append('path')",
        "      .attr('d', 'M0,-5L10,0L0,5')",
        "      .attr('fill', '#999');",
        "",
        "    const maxWeight = d3.max(graph.links, d => Math.abs(d.weight)) || 1;",
        "    const link = svg.append('g')",
        "      .attr('stroke', '#999')",
        "      .selectAll('line')",
        "      .data(graph.links)",
        "      .join('line')",
        "      .attr('class', 'link')",
        "      .attr('stroke-width', d => Math.max(1, Math.abs(d.weight) / maxWeight * 5))",
        "      .attr('stroke', d => d.weight > 0 ? '#1f77b4' : '#d62728')",
        "      .attr('marker-end', 'url(#arrow)');",
        "",
        "    const node = svg.append('g')",
        "      .selectAll('g')",
        "      .data(graph.nodes)",
        "      .join('g')",
        "      .attr('class', 'node')",
        "      .call(d3.drag()",
        "        .on('start', dragstarted)",
        "        .on('drag', dragged)",
        "        .on('end', dragended));",
        "",
        "    node.append('circle')",
        "      .attr('r', 18)",
        "      .attr('fill', color);",
        "",
        "    node.append('text')",
        "      .attr('dy', 4)",
        "      .attr('x', 0)",
        "      .attr('text-anchor', 'middle')",
        "      .text(d => d.label);",
        "",
        "    node.append('title')",
        "      .text(d => `${d.label} (${d.type})`);",
        "",
        "    const tooltip = d3.select('#tooltip');",
        "",
        "    node.on('mouseover', (event, d) => {",
        "      tooltip.style('display', 'block');",
        "      tooltip.html(`${d.label} — ${d.type}`);",
        "    }).on('mousemove', (event) => {",
        "      tooltip.style('left', `${event.pageX + 12}px`).style('top', `${event.pageY + 12}px`);",
        "    }).on('mouseout', () => {",
        "      tooltip.style('display', 'none');",
        "    });",
        "",
        "    const simulation = d3.forceSimulation(graph.nodes)",
        "      .force('link', d3.forceLink(graph.links).id(d => d.id).distance(140).strength(1))",
        "      .force('charge', d3.forceManyBody().strength(-600))",
        "      .force('center', d3.forceCenter(width / 2, height / 2))",
        "      .force('collision', d3.forceCollide().radius(28));",
        "",
        "    simulation.on('tick', () => {",
        "      link",
        "        .attr('x1', d => d.source.x)",
        "        .attr('y1', d => d.source.y)",
        "        .attr('x2', d => d.target.x)",
        "        .attr('y2', d => d.target.y);",
        "",
        "      node.attr('transform', d => `translate(${d.x},${d.y})`);",
        "    });",
        "",
        "    function dragstarted(event, d) {",
        "      if (!event.active) simulation.alphaTarget(0.3).restart();",
        "      d.fx = d.x;",
        "      d.fy = d.y;",
        "    }",
        "",
        "    function dragged(event, d) {",
        "      d.fx = event.x;",
        "      d.fy = event.y;",
        "    }",
        "",
        "    function dragended(event, d) {",
        "      if (!event.active) simulation.alphaTarget(0);",
        "      d.fx = null;",
        "      d.fy = null;",
        "    }",
        "",
        "    window.addEventListener('resize', () => {",
        "      const newWidth = window.innerWidth;",
        "      const newHeight = window.innerHeight - 80;",
        "      svg.attr('width', newWidth).attr('height', newHeight);",
        "      simulation.force('center', d3.forceCenter(newWidth / 2, newHeight / 2));",
        "      simulation.alpha(0.3).restart();",
        "    });",
        "  </script>",
        "</body>",
        "</html>",
    ]
    html = "\n".join(html_lines)
    html_path.write_text(html, encoding="utf-8")
    return html_path


def save_experiment_dashboard_html(
    gate_name: str,
    genome: Genome,
    fitness_history: Sequence[float],
    accuracy_history: Sequence[float],
    size_history: Sequence[int] | None,
    output_dir: Path | str = Path("./results"),
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    graph_json = genome_to_json(genome)
    history = {
        "generation": list(range(1, len(fitness_history) + 1)),
        "fitness": list(fitness_history),
        "accuracy": list(accuracy_history),
        "size": list(size_history) if size_history is not None else None,
    }

    html_path = output_dir / f"{gate_name.lower()}_dashboard.html"
    html_lines = [
        "<!DOCTYPE html>",
        "<html lang=\"fr\">",
        "<head>",
        "  <meta charset=\"utf-8\">",
        "  <title>" + gate_name + " experiment dashboard</title>",
        "  <style>",
        "    body { margin: 0; font-family: Arial, sans-serif; background: #f5f7fa; }",
        "    header { padding: 1rem; background: #1e293b; color: white; }",
        "    #container { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; padding: 1rem; }",
        "    #graph, #metrics { background: white; border-radius: 12px; box-shadow: 0 10px 30px rgba(15,23,42,0.08); padding: 1rem; }",
        "    h2 { margin-top: 0; font-size: 1.1rem; }",
        "    svg { width: 100%; height: 100%; }",
        "    .tooltip { position: absolute; pointer-events: none; background: rgba(15,23,42,0.88); color: #fff; padding: 0.4rem 0.6rem; border-radius: 6px; font-size: 12px; display: none; }",
        "  </style>",
        "</head>",
        "<body>",
        "  <header><h1>" + gate_name + " dashboard</h1></header>",
        "  <div id=\"container\">",
        "    <section id=\"graph\">",
        "      <h2>Topologie du modèle</h2>",
        "      <div id=\"graph-canvas\"></div>",
        "    </section>",
        "    <section id=\"metrics\">",
        "      <h2>Historique de l'évolution</h2>",
        "      <svg id=\"metrics-canvas\" width=\"100%\" height=\"420\"></svg>",
        "    </section>",
        "  </div>",
        "  <div class=\"tooltip\" id=\"tooltip\"></div>",
        "  <script src=\"https://d3js.org/d3.v7.min.js\"></script>",
        "  <script>",
        "    const graph = " + json.dumps(graph_json) + ";",
        "    const history = " + json.dumps(history) + ";",
        "    const color = d => d.type === 'input' ? '#0f766e' : d.type === 'output' ? '#be123c' : '#334155';",
        "    const width = document.body.clientWidth / 2 - 50;",
        "    const height = 520;",
        "    const svg = d3.select('#graph-canvas').append('svg').attr('width', width).attr('height', height);",
        "    const node = svg.append('g').selectAll('g').data(graph.nodes).join('g').attr('class', 'node');",
        "    node.append('circle').attr('r', 16).attr('fill', color);",
        "    node.append('text').attr('dy', 4).attr('x', 0).attr('text-anchor', 'middle').text(d => d.label).attr('font-size', 11).attr('fill', '#111');",
        "    const link = svg.append('g').selectAll('line').data(graph.links).join('line').attr('stroke', d => d.weight > 0 ? '#0f766e' : '#be123c').attr('stroke-width', d => Math.max(1, Math.abs(d.weight) * 2));",
        "    const simulation = d3.forceSimulation(graph.nodes).force('link', d3.forceLink(graph.links).id(d => d.id).distance(120).strength(1)).force('charge', d3.forceManyBody().strength(-400)).force('center', d3.forceCenter(width / 2, height / 2)).force('collision', d3.forceCollide().radius(28));",
        "    simulation.on('tick', () => { link.attr('x1', d => d.source.x).attr('y1', d => d.source.y).attr('x2', d => d.target.x).attr('y2', d => d.target.y); node.attr('transform', d => `translate(${d.x},${d.y})`); });",
        "    const tooltip = d3.select('#tooltip');",
        "    node.on('mouseover', (event, d) => { tooltip.style('display', 'block').style('left', (event.pageX + 10) + 'px').style('top', (event.pageY + 10) + 'px').text(d.label + ' (' + d.type + ')'); }).on('mouseout', () => tooltip.style('display', 'none'));",
        "    const metricsSvg = d3.select('#metrics-canvas');",
        "    const margin = { top: 30, right: 50, bottom: 50, left: 50 };",
        "    const chartWidth = parseInt(metricsSvg.style('width')) - margin.left - margin.right;",
        "    const chartHeight = parseInt(metricsSvg.attr('height')) - margin.top - margin.bottom;",
        "    const chart = metricsSvg.append('g').attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');",
        "    const x = d3.scaleLinear().domain([1, d3.max(history.generation)]).range([0, chartWidth]);",
        "    const y = d3.scaleLinear().domain([0, 1]).range([chartHeight, 0]);",
        "    chart.append('g').attr('transform', 'translate(0,' + chartHeight + ')').call(d3.axisBottom(x).ticks(8).tickFormat(d3.format('d')));",
        "    chart.append('g').call(d3.axisLeft(y));",
        "    const fitnessLine = d3.line().x((d, i) => x(history.generation[i])).y((d, i) => y(history.fitness[i]));",
        "    const accuracyLine = d3.line().x((d, i) => x(history.generation[i])).y((d, i) => y(history.accuracy[i]));",
        "    chart.append('path').datum(history.fitness).attr('fill', 'none').attr('stroke', '#0f766e').attr('stroke-width', 2).attr('d', fitnessLine);",
        "    chart.append('path').datum(history.accuracy).attr('fill', 'none').attr('stroke', '#be123c').attr('stroke-width', 2).attr('d', accuracyLine);",
        "    chart.append('text').attr('x', 10).attr('y', -8).attr('fill', '#0f766e').text('Fitness');",
        "    chart.append('text').attr('x', 80).attr('y', -8).attr('fill', '#be123c').text('Précision');",
        "    if (history.size) { const sizeY = d3.scaleLinear().domain([d3.min(history.size), d3.max(history.size)]).range([chartHeight, 0]); chart.append('g').attr('transform', 'translate(' + chartWidth + ',0)').call(d3.axisRight(sizeY)); const sizeLine = d3.line().x((d, i) => x(history.generation[i])).y((d, i) => sizeY(history.size[i])); chart.append('path').datum(history.size).attr('fill', 'none').attr('stroke', '#444444').attr('stroke-width', 2).attr('stroke-dasharray', '4 4').attr('d', sizeLine); chart.append('text').attr('x', chartWidth - 40).attr('y', -8).attr('fill', '#444444').text('Taille'); }",
        "  </script>",
        "</body>",
        "</html>",
    ]
    html = "\n".join(html_lines)
    html_path.write_text(html, encoding="utf-8")
    return html_path


def save_experiments_dashboard_html(
    experiments: Sequence[dict],
    output_dir: Path | str = Path("./results"),
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    html_path = output_dir / "experiments_dashboard.html"
    html_lines = [
        "<!DOCTYPE html>",
        "<html lang=\"fr\">",
        "<head>",
        "  <meta charset=\"utf-8\">",
        "  <title>AGIseed Evolution Dashboard</title>",
        "  <style>",
        "    body { margin: 0; font-family: Inter, system-ui, sans-serif; background: #f3f4f6; color: #0f172a; }",
        "    header { padding: 1rem 1.5rem; background: #0f172a; color: white; }",
        "    header h1 { margin: 0; font-size: 1.6rem; }",
        "    #toolbar { display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; margin: 1rem 1.5rem; }",
        "    #toolbar select, #toolbar button, #toolbar input { font-size: 0.95rem; padding: 0.75rem 1rem; border-radius: 0.75rem; border: 1px solid #cbd5e1; }",
        "    #tab-bar { display: flex; gap: 0.5rem; margin-bottom: 0.75rem; }",
        "    .tab-button { background: #e2e8f0; color: #0f172a; border: none; cursor: pointer; border-radius: 0.75rem; padding: 0.75rem 1rem; transition: background 0.2s ease; }",
        "    .tab-button.active { background: #0f172a; color: white; }",
        "    #main { display: grid; grid-template-columns: 1fr; gap: 1rem; padding: 0 1.5rem 1.5rem; }",
        "    .panel { background: white; border-radius: 1rem; box-shadow: 0 20px 60px rgba(15,23,42,0.08); padding: 1rem; }",
        "    .panel h2 { margin-top: 0; font-size: 1.1rem; }",
        "    .tab-section { display: none; }",
        "    .tab-section.active { display: block; }",
        "    #chart svg, #comparison-svg { width: 100%; height: 360px; }",
        "    #graph-canvas { width: 100%; height: 420px; }",
        "    .legend { display: flex; gap: 1rem; flex-wrap: wrap; margin-top: 0.75rem; }",
        "    .legend span { display: inline-flex; align-items: center; gap: 0.5rem; }",
        "    .legend .dot { width: 0.85rem; height: 0.85rem; border-radius: 999px; display: inline-block; }",
        "    #status { margin-top: 0.75rem; font-size: 0.95rem; color: #334155; }",
        "    #comparison-legend { margin-top: 0.75rem; display: flex; flex-wrap: wrap; gap: 0.75rem; }",
        "    #comparison-legend span { font-size: 0.9rem; display: flex; align-items: center; gap: 0.5rem; }",
        "    #comparison-legend .dot { width: 0.95rem; height: 0.95rem; }",
        "    .compare-line { opacity: 0.45; transition: opacity 0.2s ease; }",
        "    .compare-line.active { opacity: 1; stroke-width: 3; }",
        "    #academy-content { line-height: 1.6; }",
        "    #academy-content h3 { margin-top: 1.25rem; }",
        "    .tooltip { position: absolute; pointer-events: none; background: rgba(15,23,42,0.9); color: white; padding: 0.5rem 0.75rem; border-radius: 0.75rem; font-size: 0.85rem; display: none; }",
        "  </style>",
        "</head>",
        "<body>",
        "  <header><h1>AGIseed Dashboard d'évolution</h1></header>",
        "  <div id=\"toolbar\">",
        "    <div id=\"tab-bar\">",
        "      <button type=\"button\" class=\"tab-button active\" data-tab=\"evolution\">Évolution</button>",
        "      <button type=\"button\" class=\"tab-button\" data-tab=\"comparison\">Comparaison</button>",
        "      <button type=\"button\" class=\"tab-button\" data-tab=\"academy\">Academy</button>",
        "    </div>",
        "    <label for=\"gate-select\">Choisir une porte :</label>",
        "    <select id=\"gate-select\"></select>",
        "    <button id=\"play-pause\">Play</button>",
        "    <label for=\"generation-range\">Génération :</label>",
        "    <input id=\"generation-range\" type=\"range\" min=\"1\" max=\"1\" value=\"1\">",
        "    <span id=\"generation-label\">1</span>",
        "    <label for=\"comparison-metric\">Comparer :</label>",
        "    <select id=\"comparison-metric\"><option value=\"fitness\">Fitness</option><option value=\"accuracy\">Précision</option></select>",
        "  </div>",
        "  <div id=\"main\">",
        "    <section class=\"panel tab-section active\" id=\"evolution\">",
        "      <h2>Évolution dynamique</h2>",
        "      <svg></svg>",
        "      <div class=\"legend\">",
        "        <span><span class=\"dot\" style=\"background:#0f766e\"></span> Fitness</span>",
        "        <span><span class=\"dot\" style=\"background:#be123c\"></span> Précision</span>",
        "        <span><span class=\"dot\" style=\"background:#334155\"></span> Taille</span>",
        "      </div>",
        "      <div id=\"status\"></div>",
        "    </section>",
        "    <section class=\"panel tab-section\" id=\"topology\">",
        "      <h2>Topologie du meilleur modèle</h2>",
        "      <div id=\"graph-canvas\"></div>",
        "    </section>",
        "    <section class=\"panel tab-section\" id=\"comparison\">",
        "      <h2>Comparaison entre portes</h2>",
        "      <svg id=\"comparison-svg\"></svg>",
        "      <div id=\"comparison-legend\"></div>",
        "    </section>",
        "    <section class=\"panel tab-section\" id=\"academy\">",
        "      <h2>Academy : Pourquoi ces évolutions ?</h2>",
        "      <div id=\"academy-content\">",
        "        <p>Ce dashboard est conçu pour rendre l'évolution du modèle visible, compréhensible et analysable.</p>",
        "        <h3>Pourquoi ajouter cette visualisation ?</h3>",
        "        <ul>",
        "          <li>Pour suivre l'émergence de la topologie et comprendre comment la mutation transforme le réseau.</li>",
        "          <li>Pour comparer les portes logiques sur leur fitness, précision et taille, et détecter les tendances d'optimisation.</li>",
        "          <li>Pour justifier les choix d'évolution par des preuves visuelles, pas seulement des scores numériques.</li>",
        "        </ul>",
        "        <h3>Pourquoi ce modèle évolue-t-il ?</h3>",
        "        <ul>",
        "          <li>Nous rajoutons des nœuds et connexions quand ils améliorent la fonction, mais nous évaluons aussi la complexité.</li>",
        "          <li>La pénalité de taille empêche l'explosion de la topologie et préserve la simplicité émergente.</li>",
        "          <li>La topologie est une représentation concrète du compromis entre expressivité et efficience.</li>",
        "        </ul>",
        "        <h3>Pourquoi ces ajouts au dashboard ?</h3>",
        "        <ul>",
        "          <li>CSV/JSON : pour analyser l'évolution à froid et conserver un historique exploitable.</li>",
        "          <li>Graphviz + D3 : pour inspecter à la fois la structure statique (DOT/SVG) et la dynamique interactive.</li>",
        "          <li>Onglet Academy : pour garder une trace des justifications techniques et faire du projet un outil pédagogique.</li>",
        "        </ul>",
        "        <h3>Journal des versions</h3>",
        "        <ol id=\"academy-version-history\">",
        "          <li>V1.0 — Mise en place du runner d'évolution de portes et sauvegarde CSV/JSON.</li>",
        "          <li>V1.1 — Ajout des exports Graphviz et de topologie textuelle.</li>",
        "          <li>V1.2 — Ajout de la page D3 interactive pour inspecter les graphes.</li>",
        "          <li>V1.3 — Ajout du dashboard global multi-porte avec comparaison.</li>",
        "          <li>V1.4 — Ajout de l'onglet Academy avec timeline et justification des évolutions.</li>",
        "        </ol>",
        "        <h3>Timeline des évolutions</h3>",
        "        <ol id=\"academy-timeline\"></ol>",
        "        <h3>Ce que nous voulons apprendre</h3>",
        "        <ul>",
        "          <li>Comment un réseau émerge de mutations et de sélections successives.</li>",
        "          <li>Pourquoi certaines portes convergent plus vite que d'autres et comment la topologie influe sur cela.</li>",
        "          <li>Comment le modèle se développe sans perdre de vue l'interprétabilité.</li>",
        "        </ul>",
        "      </div>",
        "    </section>",
        "  </div>",
        "  <div class=\"tooltip\" id=\"tooltip\"></div>",
        "  <script src=\"https://d3js.org/d3.v7.min.js\"></script>",
        "  <script>",
        "    const experiments = " + json.dumps(experiments) + ";",
        "    const gateSelect = document.getElementById('gate-select');",
        "    const playPause = document.getElementById('play-pause');",
        "    const generationRange = document.getElementById('generation-range');",
        "    const generationLabel = document.getElementById('generation-label');",
        "    const status = document.getElementById('status');",
        "    const comparisonMetric = document.getElementById('comparison-metric');",
        "    const tooltip = d3.select('#tooltip');",
        "    let activeIndex = 0;",
        "    let playing = false;",
        "    let timer = null;",
        "    experiments.forEach((experiment, index) => {",
        "      const option = document.createElement('option');",
        "      option.value = index;",
        "      option.textContent = experiment.gate;",
        "      gateSelect.appendChild(option);",
        "    });",
        "    const svg = d3.select('#chart svg');",
        "    const width = document.getElementById('chart').clientWidth - 70;",
        "    const height = 360;",
        "    const margin = { top: 30, right: 60, bottom: 40, left: 50 };",
        "    const chart = svg.append('g').attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');",
        "    const chartWidth = width - margin.left - margin.right;",
        "    const chartHeight = height - margin.top - margin.bottom;",
        "    const xScale = d3.scaleLinear().range([0, chartWidth]);",
        "    const yScale = d3.scaleLinear().range([chartHeight, 0]).domain([0, 1]);",
        "    const xAxis = chart.append('g').attr('transform', 'translate(0,' + chartHeight + ')');",
        "    const yAxis = chart.append('g');",
        "    const lineFitness = d3.line().x((d, i) => xScale(i + 1)).y(d => yScale(d));",
        "    const lineAccuracy = d3.line().x((d, i) => xScale(i + 1)).y(d => yScale(d));",
        "    const lineSize = d3.line().x((d, i) => xScale(i + 1)).y(d => yScale(d));",
        "    const pathFitness = chart.append('path').attr('fill', 'none').attr('stroke', '#0f766e').attr('stroke-width', 2);",
        "    const pathAccuracy = chart.append('path').attr('fill', 'none').attr('stroke', '#be123c').attr('stroke-width', 2);",
        "    const pathSize = chart.append('path').attr('fill', 'none').attr('stroke', '#334155').attr('stroke-width', 2).attr('stroke-dasharray', '6 4');",
        "    const currentLine = chart.append('line').attr('stroke', '#0f172a').attr('stroke-width', 1).attr('stroke-dasharray', '4 3');",
        "    const currentLabel = chart.append('text').attr('fill', '#0f172a').attr('font-size', 12).attr('text-anchor', 'start');",
        "    const topologySvg = d3.select('#graph-canvas').append('svg').attr('width', '100%').attr('height', '100%');",
        "    const topologyGroup = topologySvg.append('g');",
        "    const comparisonSvg = d3.select('#comparison-svg');",
        "    const comparisonMargin = { top: 30, right: 50, bottom: 40, left: 50 };",
        "    const comparisonWidth = Math.max(640, document.getElementById('chart').clientWidth) - comparisonMargin.left - comparisonMargin.right;",
        "    const comparisonHeight = 360 - comparisonMargin.top - comparisonMargin.bottom;",
        "    const comparisonChart = comparisonSvg.append('g').attr('transform', 'translate(' + comparisonMargin.left + ',' + comparisonMargin.top + ')');",
        "    const comparisonX = d3.scaleLinear().range([0, comparisonWidth]);",
        "    const comparisonY = d3.scaleLinear().range([comparisonHeight, 0]).domain([0, 1]);",
        "    const comparisonXAxis = comparisonChart.append('g').attr('transform', 'translate(0,' + comparisonHeight + ')');",
        "    const comparisonYAxis = comparisonChart.append('g');",
        "    const lineComparison = d3.line().x((d, i) => comparisonX(i + 1)).y(d => comparisonY(d));",
        "    const comparisonPathGroup = comparisonChart.append('g');",
        "    const comparisonLegend = d3.select('#comparison-legend');",
        "    function updateComparison(metric) {",
        "      const currentComparisonWidth = Math.max(640, document.getElementById('comparison').clientWidth) - comparisonMargin.left - comparisonMargin.right;",
        "      comparisonX.range([0, currentComparisonWidth]);",
        "      const maxGen = d3.max(experiments, exp => exp.history.generation.length);",
        "      comparisonX.domain([1, maxGen]);",
        "      comparisonYAxis.call(d3.axisLeft(comparisonY));",
        "      comparisonXAxis.call(d3.axisBottom(comparisonX).ticks(Math.min(maxGen, 10)).tickFormat(d3.format('d')));",
        "      const lines = comparisonPathGroup.selectAll('path').data(experiments);",
        "      lines.join('path')",
        "        .attr('class', d => d.gate === experiments[activeIndex].gate ? 'compare-line active' : 'compare-line')",
        "        .attr('fill', 'none')",
        "        .attr('stroke', (d, i) => d3.schemeTableau10[i % 10])",
        "        .attr('stroke-width', d => d.gate === experiments[activeIndex].gate ? 3 : 2)",
        "        .attr('d', d => lineComparison(d.history[metric] || []));",
        "      updateComparisonLegend(metric);",
        "    }",
        "    function updateComparisonLegend(metric) {",
        "      comparisonLegend.selectAll('*').remove();",
        "      experiments.forEach((experiment, index) => {",
        "        const item = comparisonLegend.append('span');",
        "        item.append('span').attr('class', 'dot').style('background', d3.schemeTableau10[index % 10]);",
        "        item.append('span').text(experiment.gate + ' — ' + metric);",
        "      });",
        "    }",
        "    function showTab(tabName) {",
        "      document.querySelectorAll('.tab-section').forEach(section => {",
        "        section.classList.toggle('active', section.id === tabName);",
        "      });",
        "      if (tabName === 'comparison') {",
        "        updateComparison(comparisonMetric.value);",
        "      }",
        "      if (tabName === 'academy') {",
        "        renderAcademyTimeline();",
        "      }",
        "    }",
        "    function updateExperiment(index) {",
        "      activeIndex = index;",
        "      const experiment = experiments[index];",
        "      const history = experiment.history;",
        "      const maxGen = history.generation.length;",
        "      generationRange.max = maxGen;",
        "      if (+generationRange.value > maxGen) generationRange.value = maxGen;",
        "      const generation = +generationRange.value;",
        "      generationLabel.textContent = generation;",
        "      xScale.domain([1, maxGen]);",
        "      xAxis.call(d3.axisBottom(xScale).ticks(Math.min(maxGen, 10)).tickFormat(d3.format('d')));",
        "      yAxis.call(d3.axisLeft(yScale));",
        "      pathFitness.datum(history.fitness).attr('d', lineFitness);",
        "      pathAccuracy.datum(history.accuracy).attr('d', lineAccuracy);",
        "      if (history.size) {",
        "        const sizeNormalized = history.size.map(d => (d - d3.min(history.size)) / Math.max(1, d3.max(history.size) - d3.min(history.size)));",
        "        pathSize.datum(sizeNormalized).attr('d', lineSize).style('opacity', 1);",
        "      } else { pathSize.style('opacity', 0); }",
        "      const xPos = xScale(generation);",
        "      currentLine.attr('x1', xPos).attr('y1', 0).attr('x2', xPos).attr('y2', chartHeight);",
        "      currentLabel.attr('x', xPos + 6).attr('y', 14).text('Gen ' + generation);",
        "      status.textContent = 'Porte : ' + experiment.gate + ' · Fitness = ' + history.fitness[generation - 1].toFixed(3) + ' · Précision = ' + history.accuracy[generation - 1].toFixed(3) + (history.size ? ' · Taille = ' + history.size[generation - 1] : '');",
        "      renderTopology(experiment.graph);",
        "      updateComparison(comparisonMetric.value);",
        "    }",
        "    function renderTopology(graph) {",
        "      topologyGroup.selectAll('*').remove();",
        "      const g = topologyGroup;",
        "      const width = document.getElementById('graph-canvas').clientWidth;",
        "      const height = document.getElementById('graph-canvas').clientHeight;",
        "      const simulation = d3.forceSimulation(graph.nodes)",
        "        .force('link', d3.forceLink(graph.links).id(d => d.id).distance(120).strength(1))",
        "        .force('charge', d3.forceManyBody().strength(-260))",
        "        .force('center', d3.forceCenter(width / 2, height / 2))",
        "        .force('collision', d3.forceCollide().radius(24));",
        "      const link = g.append('g').selectAll('line').data(graph.links).join('line').attr('stroke', d => d.weight > 0 ? '#0f766e' : '#be123c').attr('stroke-width', d => Math.max(1.5, Math.abs(d.weight) * 1.8));",
        "      const node = g.append('g').selectAll('g').data(graph.nodes).join('g').call(d3.drag().on('start', dragstarted).on('drag', dragged).on('end', dragended));",
        "      node.append('circle').attr('r', 18).attr('fill', d => d.type === 'input' ? '#0f766e' : d.type === 'output' ? '#be123c' : '#64748b');",
        "      node.append('text').attr('text-anchor', 'middle').attr('dy', 4).attr('font-size', 11).attr('fill', '#fff').text(d => d.label);",
        "      node.on('mouseover', (event, d) => { tooltip.style('display', 'block').style('left', (event.pageX + 10) + 'px').style('top', (event.pageY + 10) + 'px').text(d.label + ' (' + d.type + ')'); }).on('mouseout', () => tooltip.style('display', 'none'));",
        "      simulation.on('tick', () => {",
        "        link.attr('x1', d => d.source.x).attr('y1', d => d.source.y).attr('x2', d => d.target.x).attr('y2', d => d.target.y);",
        "        node.attr('transform', d => 'translate(' + d.x + ',' + d.y + ')');",
        "      }).on('end', () => { simulation.alphaTarget(0); });",
        "      function dragstarted(event, d) { if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }",
        "      function dragged(event, d) { d.fx = event.x; d.fy = event.y; }",
        "      function dragended(event, d) { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; }",
        "    }",
        "    function startPlay() { playing = true; playPause.textContent = 'Pause'; timer = setInterval(() => { const max = +generationRange.max; const next = Math.min(max, +generationRange.value + 1); generationRange.value = next; generationLabel.textContent = next; updateExperiment(activeIndex); if (next === max) stopPlay(); }, 900); }",
        "    function renderAcademyTimeline() {",
        "      const timeline = document.getElementById('academy-timeline');",
        "      timeline.innerHTML = '';",
        "      experiments.forEach((experiment, index) => {",
        "        const bestGen = experiment.history.fitness.indexOf(Math.max(...experiment.history.fitness)) + 1;",
        "        const finalAcc = experiment.history.accuracy.slice(-1)[0];",
        "        const item = document.createElement('li');",
        "        item.textContent = experiment.gate + ' : meilleure fitness à la génération ' + bestGen + ', précision finale ' + finalAcc.toFixed(3) + '.';",
        "        timeline.appendChild(item);",
        "      });",
        "      const milestone = document.createElement('li');",
        "      milestone.textContent = 'Dashboard Academy actif : documentation pédagogique des évolutions et des choix de design.';",
        "      timeline.appendChild(milestone);",
        "    }",
        "    function stopPlay() { playing = false; playPause.textContent = 'Play'; clearInterval(timer); timer = null; }",
        "    playPause.addEventListener('click', () => { if (playing) stopPlay(); else startPlay(); });",
        "    gateSelect.addEventListener('change', event => updateExperiment(+event.target.value));",
        "    document.getElementById('comparison-metric').addEventListener('change', event => updateComparison(event.target.value));",
        "    document.querySelectorAll('.tab-button').forEach(button => {",
        "      button.addEventListener('click', () => {",
        "        document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));",
        "        button.classList.add('active');",
        "        showTab(button.dataset.tab);",
        "      });",
        "    });",
        "    generationRange.addEventListener('input', () => { generationLabel.textContent = generationRange.value; updateExperiment(activeIndex); });",
        "    updateExperiment(0);",
        "    updateComparison('fitness');",
        "    window.addEventListener('resize', () => { updateExperiment(activeIndex); updateComparison(document.getElementById('comparison-metric').value); });",
        "  </script>",
        "</body>",
        "</html>",
    ]
    html = "\n".join(html_lines)
    html_path.write_text(html, encoding="utf-8")
    return html_path


def save_genome_graphviz_svg(
    gate_name: str,
    genome: Genome,
    output_dir: Path | str = Path("./results"),
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    dot_path = save_genome_graphviz_dot(gate_name, genome, output_dir)
    svg_path = output_dir / f"{gate_name.lower()}_topology.svg"

    if graphviz is None:
        return dot_path

    try:
        dot = graphviz.Source(dot_path.read_text(encoding="utf-8"), format="svg")
        dot.render(filename=f"{gate_name.lower()}_topology", directory=output_dir, cleanup=False)
        return svg_path
    except graphviz.backend.ExecutableNotFound:
        return dot_path
    except Exception:
        return dot_path


def save_genome_graphviz_html(
    gate_name: str,
    genome: Genome,
    output_dir: Path | str = Path("./results"),
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    svg_path = save_genome_graphviz_svg(gate_name, genome, output_dir)
    html_path = output_dir / f"{gate_name.lower()}_topology.html"

    if svg_path.suffix == ".svg" and svg_path.exists():
        svg_content = svg_path.read_text(encoding="utf-8")
        html = (
            "<!DOCTYPE html>\n"
            "<html lang=\"fr\">\n"
            "<head>\n"
            "  <meta charset=\"utf-8\">\n"
            f"  <title>{gate_name} topology</title>\n"
            "  <style>body{margin:0;padding:0;} .svg-container{width:100vw;height:100vh;overflow:auto;} </style>\n"
            "</head>\n"
            "<body>\n"
            f"  <h1 style=\"font-family:sans-serif;margin:0.5rem 1rem\">{gate_name} topology</h1>\n"
            "  <div class=\"svg-container\">\n"
            f"    {svg_content}\n"
            "  </div>\n"
            "</body>\n"
            "</html>\n"
        )
    else:
        dot_path = output_dir / f"{gate_name.lower()}_topology.dot"
        html = (
            "<!DOCTYPE html>\n"
            "<html lang=\"fr\">\n"
            "<head>\n"
            "  <meta charset=\"utf-8\">\n"
            f"  <title>{gate_name} topology</title>\n"
            "</head>\n"
            "<body>\n"
            f"  <h1>{gate_name} topology</h1>\n"
            "  <p>Graphviz n'est pas installé ou le rendu SVG n'a pas pu être généré.</p>\n"
            f"  <p>Ouvrez le fichier DOT ici : <a href=\"{dot_path.name}\">{dot_path.name}</a></p>\n"
            "</body>\n"
            "</html>\n"
        )

    html_path.write_text(html, encoding="utf-8")
    return html_path


def render_genome_graphviz(
    gate_name: str,
    genome: Genome,
    output_dir: Path | str = Path("./results"),
    fmt: str = "png",
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    dot_path = save_genome_graphviz_dot(gate_name, genome, output_dir)
    rendered_path = output_dir / f"{gate_name.lower()}_topology.{fmt}"

    if graphviz is None:
        return dot_path

    try:
        dot = graphviz.Source(dot_path.read_text(encoding="utf-8"), format=fmt)
        dot.render(filename=f"{gate_name.lower()}_topology", directory=output_dir, cleanup=False)
        return rendered_path
    except graphviz.backend.ExecutableNotFound:
        return dot_path
    except Exception:
        return dot_path


def plot_evolution_curve(
    gate_name: str,
    fitness_history: Sequence[float],
    accuracy_history: Sequence[float],
    size_history: Sequence[int] | None = None,
    output_dir: Path | str = Path("./results"),
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    generations = list(range(1, len(fitness_history) + 1))
    figure, ax1 = plt.subplots(figsize=(10, 6))

    ax1.plot(generations, fitness_history, label="Meilleure fitness", color="tab:blue", marker="o")
    ax1.plot(generations, accuracy_history, label="Précision", color="tab:green", marker="x")
    ax1.set_xlabel("Génération")
    ax1.set_ylabel("Fitness / Précision")
    ax1.grid(True, linestyle="--", alpha=0.3)

    handles, labels = ax1.get_legend_handles_labels()

    if size_history is not None:
        ax2 = ax1.twinx()
        ax2.plot(generations, size_history, label="Taille du génome", color="tab:red", linestyle="--", marker="s")
        ax2.set_ylabel("Taille du génome")
        handles2, labels2 = ax2.get_legend_handles_labels()
        handles += handles2
        labels += labels2

    ax1.legend(handles, labels, loc="upper left")
    figure.suptitle(f"Évolution de la solution pour {gate_name}")
    figure.tight_layout()

    image_path = output_dir / f"{gate_name.lower()}_evolution.png"
    figure.savefig(image_path, dpi=150)
    plt.close(figure)

    return image_path
