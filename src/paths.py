# -*- coding: utf-8 -*-
"""Point d'indirection UNIQUE pour tous les chemins de DONNÉES du dépôt.

Pourquoi ce module existe. Inventaire mesuré le 2026-09-09 : **57 chemins de données écrits en
DUR dans 26 fichiers**, 16 constantes de module, et **une seule** variable d'environnement liée aux
données (`HOF_PATH`). Conséquence directe : héberger les données ailleurs — un NAS, un autre disque,
une autre machine — demandait d'éditer 26 fichiers. Le stockage était une propriété du CODE, alors
que c'est une propriété du DÉPLOIEMENT.

TROIS RACINES, et elles sont séparées pour une raison MESURÉE
------------------------------------------------------------
    AGAGI_DATA_ROOT     défaut "data"     -- artefacts FROIDS : génomes, Hall of Fame, états d'agents
    AGAGI_RESULTS_ROOT  défaut "results"  -- sorties de mesure (les .json sont versionnés dans git)
    AGAGI_DB_ROOT       défaut = DATA_ROOT -- bases VIVANTES (KuzuDB, graphe d'expériences)

`AGAGI_DB_ROOT` est distincte, et ce n'est pas de la symétrie décorative. Répartition mesurée des
3,0 Go de `data/` : **`kuzu_graph.db` pèse 2 674 Mo à lui seul (89 %)**, `agent_states/` 305 Mo, le
reste ~15 Mo. La base est VIVANTE et ce dépôt a déjà dû construire un mécanisme de bail
(`tools/jobs/`) à cause de la contention qu'elle produit — la mettre sur un partage réseau ajouterait
latence et risque de corruption à l'endroit précis où le dépôt a déjà mal. Le froid part sur le NAS,
la base reste sur disque rapide et se SAUVEGARDE vers le NAS.

Les défauts reproduisent EXACTEMENT les chemins actuels : sans variable d'environnement, ce module
est bit-identique à l'existant. Une migration se fait donc en posant trois variables, sans toucher
au code.

⚠️ CE MODULE NE LÈVE PAS À L'IMPORT, et c'est délibéré. Le 2026-09-08, un module posait `HOF_PATH`
au niveau module : tout script qui l'importait, même pour un helper sans rapport, voyait ensuite
`load_champion_genome()` échouer sur « HoF vide » — un diagnostic qui envoie chercher la cause à
l'opposé (classe E5, registre). Ici, rien ne s'exécute à l'import ; `assert_roots_exist()` est
explicite, et c'est à l'appelant de la poser où il veut échouer.
"""
import os

__all__ = [
    "data_root", "results_root", "db_root",
    "hall_of_fame", "agent_states", "epoch_states", "genomes", "data_file",
    "results_file", "kuzu_graph", "experiment_graph", "db_file",
    "assert_roots_exist", "describe",
]

_DEFAUTS = {"AGAGI_DATA_ROOT": "data", "AGAGI_RESULTS_ROOT": "results"}


def _racine(var, defaut):
    """Lu à CHAQUE appel, jamais figé à l'import : un test qui monkeypatche l'environnement doit
    pouvoir agir, et un runner qui pose la variable avant d'appeler doit être entendu."""
    v = os.environ.get(var)
    return v if v else defaut


def data_root():
    """Racine des artefacts FROIDS (génomes, Hall of Fame, états d'agents). Candidate au NAS."""
    return _racine("AGAGI_DATA_ROOT", _DEFAUTS["AGAGI_DATA_ROOT"])


def results_root():
    """Racine des sorties de mesure. Les `.json` y sont versionnés dans git (l'évidence que les
    records citent) ; le reste — logs, .npy — ne l'est pas et peut vivre sur le NAS."""
    return _racine("AGAGI_RESULTS_ROOT", _DEFAUTS["AGAGI_RESULTS_ROOT"])


def db_root():
    """Racine des bases VIVANTES. Défaut : la racine des données, pour rester bit-identique — mais
    séparable, et c'est tout l'intérêt : le froid part sur le NAS, la base reste locale."""
    return _racine("AGAGI_DB_ROOT", data_root())


def _sous(racine, *parties):
    r"""Joint avec `/`, JAMAIS avec `os.path.join`.

    ⚠️ Corrigé le 2026-09-09, une heure après avoir écrit ce module. `os.path.join` produit
    `data\hall_of_fame.pkl` sous Windows, là où les 47 littéraux du dépôt écrivent
    `data/hall_of_fame.pkl`. La garantie « bit-identique sans variable d'environnement » annoncée en
    tête était donc FAUSSE sur cette plateforme — et c'est un test PRÉ-EXISTANT qui comparait la
    constante à son littéral (`tests/test_famine_pipeline_wiring.py`) qui l'a montré, pas moi. Le `/`
    fonctionne pour toutes les entrées-sorties Windows ; ce qui casse, c'est la COMPARAISON de
    chaînes, et elle est réelle."""
    return "/".join([racine.rstrip("/\\")] + [str(x).strip("/\\") for x in parties if str(x)])


# --- artefacts FROIDS -----------------------------------------------------------------------------
def hall_of_fame(variante=None):
    """`data/hall_of_fame.pkl` par défaut. `variante="famine"` -> `hall_of_fame_famine.pkl`,
    `variante="famine_s43"` -> `hall_of_fame_famine_s43.pkl`. 25 des 57 sites mesurés visaient
    cette famille : c'est la plus rentable à rebrancher."""
    nom = "hall_of_fame.pkl" if not variante else "hall_of_fame_%s.pkl" % variante
    return _sous(data_root(), nom)


def agent_states(*parties):
    return _sous(data_root(), "agent_states", *parties)


def epoch_states(*parties):
    return _sous(data_root(), "epoch_states", *parties)


def genomes(*parties):
    return _sous(data_root(), "genomes", *parties)


def data_file(*parties):
    """Échappatoire pour un artefact froid sans accesseur dédié. Préférer un accesseur NOMMÉ : un
    nom dit ce qu'est la donnée, un chemin ne dit que où elle est aujourd'hui."""
    return _sous(data_root(), *parties)


# --- sorties de mesure ----------------------------------------------------------------------------
def results_file(*parties):
    return _sous(results_root(), *parties)


# --- bases VIVANTES -------------------------------------------------------------------------------
def kuzu_graph():
    """La base de 2,7 Go. Reste sur disque rapide (cf. l'en-tête) ; se sauvegarde vers le NAS."""
    return _sous(db_root(), "kuzu_graph.db")


def experiment_graph():
    return _sous(db_root(), "experiment_graph.db")


def db_file(*parties):
    return _sous(db_root(), *parties)


# --- vérification EXPLICITE, jamais à l'import ----------------------------------------------------
def assert_roots_exist(*, data=True, results=False, db=False):
    """Vérifie que les racines demandées EXISTENT, et lève en NOMMANT la variable d'environnement.

    À appeler explicitement, au début d'un runner. Raison mesurée : une racine mal configurée se
    manifeste sinon très loin de sa cause — le 2026-09-08, un `HOF_PATH` pointant sur un fichier
    absent produisait « HoF vide : évoluer d'abord », c'est-à-dire un diagnostic qui envoie chercher
    le problème à l'opposé. Une racine absente doit se dire À L'ENDROIT où elle est absente."""
    manquantes = []
    for actif, var, valeur in ((data, "AGAGI_DATA_ROOT", data_root()),
                               (results, "AGAGI_RESULTS_ROOT", results_root()),
                               (db, "AGAGI_DB_ROOT", db_root())):
        if actif and not os.path.isdir(valeur):
            manquantes.append("%s -> %r" % (var, valeur))
    if manquantes:
        raise RuntimeError(
            "racine(s) de données INTROUVABLE(S) : %s. Ce n'est PAS un jeu de données vide -- ne pas "
            "le lire comme tel. Vérifier la ou les variables d'environnement nommées ci-dessus (un "
            "montage NAS non monté, un chemin d'une autre machine)." % " ; ".join(manquantes))
    return True


def describe():
    """Les trois racines effectives et leur origine (défaut ou variable). Pour l'imprimer en tête
    d'un run : une mesure faite sur la mauvaise racine ne doit pas pouvoir passer inaperçue."""
    out = {}
    for var, valeur in (("AGAGI_DATA_ROOT", data_root()),
                        ("AGAGI_RESULTS_ROOT", results_root()),
                        ("AGAGI_DB_ROOT", db_root())):
        out[var] = {"valeur": valeur, "origine": "environnement" if os.environ.get(var) else "defaut",
                    "existe": os.path.isdir(valeur)}
    return out
