"""Cliquet : toute statistique LUE par une fonction de competence doit etre ECRITE par le moteur actif.

CLASSE D'ERREUR E16 (registre) -- "metrique nommee pour un mecanisme MORT". Distincte de E3 :
la metrique n'est PAS degeneree, elle varie normalement. Le defaut est que son terme DOMINANT est
alimente par une statistique que rien n'incremente, si bien que toute sa variation vient d'un terme
accessoire -- et se lit sous le nom du mecanisme mort.

Cas fondateur (2026-07-21) : `altars_solved` n'est incremente NULLE PART dans `src/worlds/`. Le bloc
de resolution existe seulement dans `world_0_soup.SoupWorldLegacyV13` (classe marquee "NE PLUS
UTILISER") et dans `src/environments/biosphere.py` (moteur pre-refactor). Il n'a jamais ete porte vers
`Biosphere3D`, dont heritent les CINQ mondes actifs. Consequences mesurees :
  - `gym_competence`        = _median_norm(altars_solved, 5.0)          -> identiquement 0.0
  - `industrial_competence` = 0.6 * <mort> + 0.4 * persist              -> plafonnee a 0.4
  - le barreau 2 du design de l'organe dreaming ("la competence-autels quitte le plancher",
    `industrial_competence > 0.15`) ne pouvait bouger QUE par la survie. Comme EDR-DREAM-001 a
    mesure que le reve augmente la survie de 77 %, le barreau aurait ete franchi et le franchissement
    attribue aux autels : un FAUX POSITIF arme.

Une garde de borne ne voit rien ici (aucun bras au plancher ni au plafond). Ce qui est detectable
l'est STATIQUEMENT : la stat est-elle ecrite ailleurs que dans son initialisation a 0 ?

Meme mecanique que les autres cliquets du depot : la dette legataire est GELEE, seule une NOUVELLE
stat morte fait echouer.
"""
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
_WORLDS = os.path.join(_ROOT, "src", "worlds")

# Stats lues par au moins une fonction de src/curriculum/competence.py.
STATS_LUES = ["age", "preys_eaten", "mammoth_kills", "spears_crafted", "altars_solved", "total_dreams"]

# Dette GELEE au 2026-07-21. Retirer une entree quand le mecanisme est repare -- jamais en ajouter
# sans un record qui l'explique.
MORTES_CONNUES = {"altars_solved"}


def _ecrite_dans_moteur_actif(stat: str) -> bool:
    """La stat est-elle ECRITE ailleurs que par son initialisation a 0, dans src/worlds/ ?

    Compte comme ecriture : `+= `, `= <autre chose que 0>`, ou passage a .get(...)+N.
    Ne compte PAS : la ligne d'initialisation `"stat": 0,` du dict d'agent -- c'est precisement ce
    qui rendait `altars_solved` invisible : la stat EXISTE, elle est initialisee, elle est lue, elle
    remonte dans les artefacts... et elle vaut zero pour toujours.
    """
    motif_ecriture = re.compile(
        r"""\[["']""" + re.escape(stat) + r"""["']\]\s*(\+=|=\s*(?!0\s*[,}\n]))"""
    )
    for nom in os.listdir(_WORLDS):
        if not nom.endswith(".py"):
            continue
        with open(os.path.join(_WORLDS, nom), encoding="utf-8") as fh:
            src = fh.read()
        # Ecarte les classes explicitement depreciees : une stat qui n'est vivante que dans du legacy
        # est morte pour tout ce qui tourne aujourd'hui.
        if "LEGACY" in src.upper():
            src = re.split(r"^class \w*Legacy\w*", src, flags=re.M)[0]
        if motif_ecriture.search(src):
            return True
    return False


def test_le_detecteur_voit_une_stat_vivante():
    """Controle POSITIF du detecteur lui-meme : sans lui, un motif regex casse rendrait TOUTES les
    stats 'mortes' et le test passerait en signalant une catastrophe imaginaire -- ou, si la dette
    gelee etait large, ne signalerait rien du tout. Le detecteur doit pouvoir dire OUI."""
    assert _ecrite_dans_moteur_actif("spears_crafted"), \
        "le detecteur ne voit plus une stat pourtant vivante -> motif casse"


def test_aucune_nouvelle_stat_morte():
    """Cliquet : la dette legataire est geleee, aucune NOUVELLE stat lue-mais-jamais-ecrite."""
    mortes = {s for s in STATS_LUES if not _ecrite_dans_moteur_actif(s)}
    nouvelles = mortes - MORTES_CONNUES
    assert not nouvelles, (
        f"stats lues par une fonction de competence mais JAMAIS ecrites par src/worlds/ : {nouvelles}. "
        "Une competence batie dessus portera le nom d'un mecanisme mort et variera par ses seuls "
        "termes accessoires (classe E16)."
    )


def test_la_dette_gelee_est_toujours_reelle():
    """L'inverse du cliquet : si une stat gelee redevient vivante, il faut la RETIRER de la dette,
    sinon le gel masque une reparation et la garde s'endort. Une dette qui ne peut plus etre
    invalidee n'est plus une dette, c'est un commentaire."""
    ressuscitees = {s for s in MORTES_CONNUES if _ecrite_dans_moteur_actif(s)}
    assert not ressuscitees, (
        f"{ressuscitees} est de nouveau ecrite par le moteur actif -> la retirer de MORTES_CONNUES "
        "et reexaminer les competences qui la lisent."
    )
