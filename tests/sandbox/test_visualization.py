from pathlib import Path
import csv
import json
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.seed_ai.mutation import Genome
from src.visualization import (
    plot_evolution_curve,
    save_experiment_history_csv,
    save_experiment_history_json,
    save_experiment_dashboard_html,
    save_experiments_dashboard_html,
    save_genome_topology_txt,
    genome_to_json,
    save_genome_topology_edge_list_csv,
    save_genome_graphviz_dot,
    save_genome_graphviz_html,
    save_genome_graph_json,
    save_genome_interactive_html,
)


def test_plot_and_save_experiment_history(tmp_path: Path):
    fitness_history = [0.1, 0.25, 0.6, 0.85]
    accuracy_history = [0.0, 0.25, 0.5, 0.75]
    size_history = [4, 5, 6, 7]

    image_path = plot_evolution_curve(
        "TEST_GATE",
        fitness_history,
        accuracy_history,
        size_history,
        output_dir=tmp_path,
    )
    assert image_path.exists()
    assert image_path.suffix == ".png"

    csv_path = save_experiment_history_csv(
        "TEST_GATE",
        fitness_history,
        accuracy_history,
        size_history,
        output_dir=tmp_path,
    )
    assert csv_path.exists()
    contents = csv_path.read_text(encoding="utf-8")
    assert "generation" in contents.lower()
    assert "fitness" in contents.lower()
    assert "accuracy" in contents.lower()
    assert "size" in contents.lower()


def test_save_genome_topology(tmp_path: Path):
    matrix = [[0.0, 1.5, 0.0], [0.0, 0.0, -0.7], [0.0, 0.0, 0.0]]
    genome = Genome(
        W=np.array(matrix, dtype=np.float32),
        num_inputs=1,
        num_outputs=1,
    )

    topology_txt = save_genome_topology_txt("TEST_GATE", genome, output_dir=tmp_path)
    assert topology_txt.exists()
    text = topology_txt.read_text(encoding="utf-8")
    assert "Nombre de nœuds" in text
    assert "Entrées" in text
    assert "Sorties" in text
    assert "0 -> 1" in text

    topology_edges = save_genome_topology_edge_list_csv("TEST_GATE", genome, output_dir=tmp_path)
    assert topology_edges.exists()
    edge_contents = topology_edges.read_text(encoding="utf-8")
    assert "source" in edge_contents
    assert "target" in edge_contents
    assert "weight" in edge_contents
    assert "1.5" in edge_contents

    with topology_edges.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert any(
        row["source"] == "1" and row["target"] == "2" and abs(float(row["weight"]) + 0.7) < 1e-5
        for row in rows
    )


def test_save_genome_graphviz_dot(tmp_path: Path):
    matrix = [[0.0, 1.5, 0.0], [0.0, 0.0, -0.7], [0.0, 0.0, 0.0]]
    genome = Genome(
        W=np.array(matrix, dtype=np.float32),
        num_inputs=1,
        num_outputs=1,
    )

    from src.visualization import save_genome_graphviz_dot

    dot_path = save_genome_graphviz_dot("TEST_GATE", genome, output_dir=tmp_path)
    assert dot_path.exists()
    dot_text = dot_path.read_text(encoding="utf-8")
    assert "digraph G" in dot_text
    assert "0 -> 1" in dot_text
    assert "1 -> 2" in dot_text
    assert "label=\"1.500\"" in dot_text
    assert "color=red" in dot_text or "color=blue" in dot_text


def test_save_genome_graph_json_and_interactive_html(tmp_path: Path):
    matrix = [[0.0, 1.5, 0.0], [0.0, 0.0, -0.7], [0.0, 0.0, 0.0]]
    genome = Genome(
        W=np.array(matrix, dtype=np.float32),
        num_inputs=1,
        num_outputs=1,
    )

    json_path = save_genome_graph_json("TEST_GATE", genome, output_dir=tmp_path)
    assert json_path.exists()
    json_content = json_path.read_text(encoding="utf-8")
    assert '"nodes"' in json_content
    assert '"links"' in json_content

    html_path = save_genome_interactive_html("TEST_GATE", genome, output_dir=tmp_path)
    assert html_path.exists()
    html_text = html_path.read_text(encoding="utf-8")
    assert '<html' in html_text.lower()
    assert 'd3.v7.min.js' in html_text
    assert 'const graph = ' in html_text


def test_save_experiment_history_json_and_dashboard(tmp_path: Path):
    fitness_history = [0.12, 0.44, 0.76, 0.92]
    accuracy_history = [0.25, 0.5, 0.75, 1.0]
    size_history = [4, 5, 6, 7]

    json_path = save_experiment_history_json(
        "TEST_GATE",
        fitness_history,
        accuracy_history,
        size_history,
        output_dir=tmp_path,
    )
    assert json_path.exists()
    json_content = json.loads(json_path.read_text(encoding="utf-8"))
    assert json_content["generation"] == [1, 2, 3, 4]
    assert json_content["fitness"] == fitness_history
    assert json_content["accuracy"] == accuracy_history
    assert json_content["size"] == size_history

    matrix = [[0.0, 1.5, 0.0], [0.0, 0.0, -0.7], [0.0, 0.0, 0.0]]
    genome = Genome(
        W=np.array(matrix, dtype=np.float32),
        num_inputs=1,
        num_outputs=1,
    )
    dashboard_path = save_experiment_dashboard_html(
        "TEST_GATE",
        genome,
        fitness_history,
        accuracy_history,
        size_history,
        output_dir=tmp_path,
    )
    assert dashboard_path.exists()
    dashboard_text = dashboard_path.read_text(encoding="utf-8")
    assert '<html' in dashboard_text.lower()
    assert 'const graph = ' in dashboard_text
    assert 'const history = ' in dashboard_text
    assert 'Topologie du modèle' in dashboard_text
    assert 'Historique de l\'évolution' in dashboard_text


def test_save_experiments_dashboard_html(tmp_path: Path):
    matrix = [[0.0, 1.5, 0.0], [0.0, 0.0, -0.7], [0.0, 0.0, 0.0]]
    genome = Genome(
        W=np.array(matrix, dtype=np.float32),
        num_inputs=1,
        num_outputs=1,
    )

    experiments = [
        {
            "gate": "AND",
            "history": {
                "generation": [1, 2, 3],
                "fitness": [0.2, 0.5, 0.8],
                "accuracy": [0.0, 0.5, 1.0],
                "size": [3, 4, 5],
            },
            "graph": genome_to_json(genome),
        },
        {
            "gate": "OR",
            "history": {
                "generation": [1, 2, 3],
                "fitness": [0.1, 0.4, 0.9],
                "accuracy": [0.25, 0.75, 1.0],
                "size": [3, 4, 4],
            },
            "graph": genome_to_json(genome),
        },
    ]

    html_path = save_experiments_dashboard_html(experiments, output_dir=tmp_path)
    assert html_path.exists()
    html_text = html_path.read_text(encoding="utf-8")
    assert '<html' in html_text.lower()
    assert 'const experiments = ' in html_text
    assert 'and' in html_text.lower()
    assert 'or' in html_text.lower()
    assert 'comparison-metric' in html_text.lower()
    assert 'size' in html_text.lower()
    assert 'academy' in html_text.lower()
    assert 'showtab' in html_text.lower() or 'showTab' in html_text


def test_save_genome_graphviz_html(tmp_path: Path):
    matrix = [[0.0, 1.5, 0.0], [0.0, 0.0, -0.7], [0.0, 0.0, 0.0]]
    genome = Genome(
        W=np.array(matrix, dtype=np.float32),
        num_inputs=1,
        num_outputs=1,
    )

    html_path = save_genome_graphviz_html("TEST_GATE", genome, output_dir=tmp_path)
    assert html_path.exists()
    html_text = html_path.read_text(encoding="utf-8")
    assert "<html" in html_text.lower()
    assert "topology" in html_text.lower()
    assert "TEST_GATE" in html_text
