"""
Tests unitaires pour LUHumanExplainer et warmstart_spectral.
Conforme au Commandement 5 (Auditabilité & Transparence) et Commandement 7 (Validation).
"""

import pytest
import numpy as np

from src.metaprog.lu_human_explainer import LUHumanExplainer, LUExplanationReport
from src.metaprog.lu_auto_translator import MutualLatentTranslator, AutoTranslatorConfig
from src.metaprog.lu_dsl_semantic import LUSemanticParser


def test_lu_human_explainer_rich_statement():
    explainer = LUHumanExplainer()
    stmt = (
        "(Hunter:AGENT {name: 'PredatorAlpha'})-[TARGETS {prio: 0.95}]->(Prey:CONCEPT {speed: 1.5}) ; "
        "(Prey:CONCEPT)-[IS_A]->(Food:CONCEPT)"
    )
    report = explainer.explain_dsl_string(stmt)

    assert isinstance(report, LUExplanationReport)
    assert report.confidence_score > 0.90
    assert report.nodes_count == 3
    assert report.edges_count == 2
    assert "PredatorAlpha a pour cible prioritaire Prey" in report.human_text_fr
    assert "actively targets" in report.human_text_en
    assert "est une instance de Food" in report.human_text_fr


def test_lu_human_explainer_passive_or_empty():
    explainer = LUHumanExplainer()
    stmt = "(Night:STATE {darkness: 0.9}) ; (Cold:STATE)"
    report = explainer.explain_dsl_string(stmt)
    assert "Perception passive des concepts" in report.human_text_fr


def test_warmstart_spectral_high_dimension():
    """Vérifie que warmstart_spectral initialise immédiatement une fidélité élevée en D=64."""
    rng = np.random.RandomState(42)
    dim = 64
    n_anchors = 100

    z_a = rng.randn(n_anchors, dim)
    # Matrice de rotation orthogonale cible
    q, _ = np.linalg.qr(rng.randn(dim, dim))
    z_b = np.dot(z_a, q)

    cfg = AutoTranslatorConfig(dim_a=dim, dim_b=dim, seed=42)
    translator = MutualLatentTranslator(cfg)

    # Initialement aléatoire
    initial_fid = translator.compute_mutual_fidelity(z_a, z_b)

    # Application du warmstart spectral
    translator.warmstart_spectral(z_a, z_b)
    spectral_fid = translator.compute_mutual_fidelity(z_a, z_b)

    assert spectral_fid > initial_fid
    assert spectral_fid > 0.95, f"Le warmstart spectral en D=64 doit conférer > 0.95 de fidélité, obtenu {spectral_fid}"
