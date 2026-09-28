"""Recensement MESURÉ des tirages du RNG GLOBAL numpy, par SITE appelant (E34 v6, P2.132).

Question posée par Master 2 avant le sceau de la v6 : « combien de sites du RNG global le monde consomme après t1,
MESURÉ et non recensé » — un `grep np.random` compte des LIGNES DE CODE (42 dans `world_1_stoneage.py`), pas ce qui
TIRE dans le régime de la cellule. La bande de la v6 est faite de répliques du harnais publié réensemencées à t1 : si le
monde ne tirait rien après t1, ou se réensemençait lui-même, le réensemencement ne décorrélerait rien.

`RecensementTirages` enveloppe, le temps d'un bloc `with`, chaque fonction de module `numpy.random` qui tire dans le
générateur GLOBAL (celui de `np.random.seed`) : l'appel est compté sous le site appelant (`fichier:ligne`, relatif à la
racine du dépôt) puis délégué TEL QUEL — mêmes tirages, même ordre (no-op au bit, testé). `marquer(etiquette)` ouvre
la fenêtre « après » ; ce qui précède est compté à part. Les RÉENSEMENCEMENTS (`seed`, `set_state`,
`set_bit_generator`) sont comptés à part, par fenêtre : un monde qui se réensemence après t1 annulerait le
réensemencement de la bande, et doit se voir.

Périmètre DÉCLARÉ (ce qui n'est PAS vu, et le dire plutôt que compter 0) : un alias lié AVANT le bloc
(`from numpy.random import rand` — aucun dans `src/` ni `tools/` le 2026-09-29) ; un générateur PRIVÉ
(`np.random.RandomState(...)`, `default_rng`) ; l'appel direct de `np.random.mtrand._rand`. Le RNG torch et le module
`random` ne sont pas enveloppés : leur ÉTAT est comparé entre la marque et la sortie du bloc (changé / inchangé / None
si non mesurable) — une présence, pas un compte.
"""
import os
import random as _random
import sys

import numpy as np

_RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ECRITURES = ("seed", "set_state", "set_bit_generator")
_LECTURES = ("get_state", "get_bit_generator")
_TIRAGES_NON_LIES = ("ranf", "sample")          # fonctions de module qui tirent dans le global sans y être liées


def fonctions_globales():
    """Les noms de `numpy.random` enveloppés : (tirages, réensemencements). Tirages = toute fonction de module liée au
    RandomState global, sauf les lectures d'état, plus `ranf` et `sample` ; réensemencements = `_ECRITURES` présents."""
    glob = np.random.mtrand._rand
    tirages = [n for n in dir(np.random)
               if not n.startswith("_") and n not in _LECTURES + _ECRITURES
               and getattr(getattr(np.random, n, None), "__self__", None) is glob]
    tirages += [n for n in _TIRAGES_NON_LIES if callable(getattr(np.random, n, None))]
    ecritures = [n for n in _ECRITURES if callable(getattr(np.random, n, None))]
    return sorted(set(tirages)), ecritures


def _etat_torch():
    try:
        import torch
        return torch.get_rng_state().clone()
    except Exception:                                   # noqa: BLE001 — torch absent : non mesurable, jamais « inchangé »
        return None


def _meme_etat_torch(a, b):
    if a is None or b is None:
        return None
    import torch
    return bool(torch.equal(a, b))


class RecensementTirages:
    """Contexte : compte les tirages du RNG global numpy par site appelant, avant et après `marquer()`."""

    def __init__(self, racine=None):
        self.racine = os.path.abspath(racine or _RACINE)
        self.avant, self.apres = {}, {}
        self.reensemencements = {"avant": 0, "apres": 0}
        self.marque = None
        self.torch_change_apres = None
        self.py_random_change_apres = None
        self._originaux = {}
        self._actif = False
        self._torch_marque = self._py_marque = None

    def _site(self, frame):
        fichier = os.path.abspath(frame.f_code.co_filename)
        try:
            rel = os.path.relpath(fichier, self.racine)
        except ValueError:                              # autre lecteur (Windows) : hors dépôt
            rel = fichier
        if rel.startswith(".."):
            rel = fichier
        return f"{rel.replace(os.sep, '/')}:{frame.f_lineno}"

    def _envelopper(self, nom, f, ecriture):
        recensement = self

        def enveloppe(*args, **kwargs):
            fenetre = "apres" if recensement.marque is not None else "avant"
            if ecriture:
                recensement.reensemencements[fenetre] += 1
            else:
                d = recensement.apres if fenetre == "apres" else recensement.avant
                site = recensement._site(sys._getframe(1))
                d[site] = d.get(site, 0) + 1
            return f(*args, **kwargs)

        enveloppe.__wrapped__ = f
        enveloppe.__name__ = getattr(f, "__name__", nom)
        return enveloppe

    def __enter__(self):
        if self._actif:
            raise RuntimeError("RecensementTirages : déjà actif -- un recensement n'est pas réentrant")
        tirages, ecritures = fonctions_globales()
        for nom in tirages + ecritures:
            f = getattr(np.random, nom)
            self._originaux[nom] = f
            setattr(np.random, nom, self._envelopper(nom, f, nom in ecritures))
        self.perimetre = {"tirages": tirages, "reensemencements": ecritures}
        self._actif = True
        return self

    def marquer(self, etiquette):
        """Ouvre la fenêtre « après ». Une seule marque : une seconde LÈVE (la fenêtre ne se déplace pas en silence)."""
        if not self._actif:
            raise RuntimeError("RecensementTirages.marquer : hors du bloc `with`")
        if self.marque is not None:
            raise RuntimeError(f"RecensementTirages.marquer : déjà marqué ({self.marque!r}), refus de {etiquette!r}")
        self.marque = etiquette
        self._torch_marque = _etat_torch()
        self._py_marque = _random.getstate()

    def __exit__(self, *exc):
        for nom, f in self._originaux.items():
            setattr(np.random, nom, f)
        self._originaux = {}
        self._actif = False
        if self.marque is not None:
            self.torch_change_apres = (None if self._torch_marque is None
                                       else not _meme_etat_torch(self._torch_marque, _etat_torch()))
            self.py_random_change_apres = _random.getstate() != self._py_marque
        return False

    def resume(self):
        """Ce qui se publie : comptes par fenêtre, sites de la fenêtre « après » (triés), périmètre enveloppé."""
        return {"marque": self.marque,
                "tirages_avant": int(sum(self.avant.values())), "n_sites_avant": len(self.avant),
                "tirages_apres": (int(sum(self.apres.values())) if self.marque is not None else None),
                "n_sites_apres": (len(self.apres) if self.marque is not None else None),
                "sites_apres": ({k: self.apres[k] for k in sorted(self.apres)} if self.marque is not None else None),
                "reensemencements_avant": int(self.reensemencements["avant"]),
                "reensemencements_apres": (int(self.reensemencements["apres"]) if self.marque is not None else None),
                "torch_rng_change_apres": self.torch_change_apres,
                "py_random_change_apres": self.py_random_change_apres,
                "perimetre": getattr(self, "perimetre", None)}
