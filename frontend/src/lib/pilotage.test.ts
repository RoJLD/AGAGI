import { describe, expect, test } from "vitest";
import {
  flotteAveugleSur,
  formatAge,
  lignesDuBloc,
  lireFlotte,
  mesure,
  messageIndisponible,
  NON_MESURE,
  vscodeHref,
} from "./pilotage";

// Lignes RECOPIÉES des gabarits de tools/pm/pilotage.py et backend/app/services/pilotage_service.py.
const AVEUGLE = [
  "flotte : BOARD.json introuvable (ou JSON illisible) à C:/x/data/pm/BOARD.json -- tick PM jamais passé",
  "backlog : docs/roadmap/PRIORITES_ET_DETTES.md introuvable",
  "graphe de records : results/records_graph.json introuvable",
  "portes_agi : bloc refusé par le modèle de la route (1 erreur) -- servi à null, le reste de la roadmap reste servi",
  "portes : tools/hooks/pre-commit illisible",
  "compteurs du PM : ROLES_COUNTS.json introuvable (ou JSON illisible) à C:/x/data/pm/ROLES_COUNTS.json",
  "frais=1 accepté SANS mesure de charge -- recalcul lancé à l'aveugle",
];

describe("lignesDuBloc — chaque bloc null retrouve SA raison", () => {
  test("portes ne capte pas portes_agi (même préfixe de mot)", () => {
    expect(lignesDuBloc(AVEUGLE, "portes")).toEqual(["portes : tools/hooks/pre-commit illisible"]);
    expect(lignesDuBloc(AVEUGLE, "portes_agi")).toEqual([AVEUGLE[2], AVEUGLE[3]]);
  });

  test("charge réunit ses deux causes : la flotte ET les compteurs", () => {
    expect(lignesDuBloc(AVEUGLE, "charge")).toEqual([AVEUGLE[0], AVEUGLE[5]]);
  });

  test("roadmap : backlog et refus du modèle", () => {
    const l = [...AVEUGLE, "roadmap : bloc refusé par le modèle de la route (x) -- servi à null"];
    expect(lignesDuBloc(l, "roadmap")).toEqual([AVEUGLE[1], l[l.length - 1]]);
  });

  test("une ligne GLOBALE (mode dégradé, racine suspecte) explique tous les blocs", () => {
    const l = ["pilotage: ImportError: tools.pm indisponible", "racine résolue suspecte : /tmp ne porte ni …"];
    for (const b of ["flotte", "roadmap", "portes", "charge", "portes_agi"] as const) {
      expect(lignesDuBloc(l, b)).toEqual(l);
    }
  });

  test("la ligne flotte recopiée du board (« flotte: ») est rangée sous flotte", () => {
    expect(lignesDuBloc(["flotte: bails (tools/jobs)"], "flotte")).toEqual(["flotte: bails (tools/jobs)"]);
  });
});

describe("messageIndisponible — jamais un bloc vide muet", () => {
  test("reprend la ligne du backend", () => {
    expect(messageIndisponible(AVEUGLE, "portes", "Portes")).toBe(
      "Portes indisponible — portes : tools/hooks/pre-commit illisible",
    );
  });

  test("sans ligne publiée, l'absence de raison est DITE", () => {
    const m = messageIndisponible([], "flotte", "Flotte");
    expect(m).toMatch(/^Flotte indisponible/);
    expect(m).toMatch(/aucune ligne d'aveuglement/);
  });
});

describe("mesure / formatAge — « non mesuré », jamais 0", () => {
  test("null, undefined et non fini deviennent « non mesuré »", () => {
    expect(mesure(null)).toBe(NON_MESURE);
    expect(mesure(undefined)).toBe(NON_MESURE);
    expect(mesure(Number.NaN)).toBe(NON_MESURE);
    expect(mesure(0)).toBe("0"); // un zéro MESURÉ reste un zéro
    expect(formatAge(null)).toBe(NON_MESURE);
  });

  test("unités", () => {
    expect(formatAge(12)).toBe("12 s");
    expect(formatAge(600)).toBe("10 min");
    expect(formatAge(5.8 * 3600)).toBe("5,8 h");
    expect(formatAge(2 * 86400)).toBe("2 j");
  });
});

describe("vscodeHref — deux gabarits littéraux de la spec §3.3", () => {
  const racine = "C:/Users/robla/VScode_Project/AGAGI";

  test("entrée du backlog : chemin + ligne", () => {
    expect(vscodeHref(racine, "docs/roadmap/PRIORITES_ET_DETTES.md", 671)).toBe(
      "vscode://file/C:/Users/robla/VScode_Project/AGAGI/docs/roadmap/PRIORITES_ET_DETTES.md:671",
    );
  });

  test("chemin cité : SANS ligne quand elle est null", () => {
    expect(vscodeHref(racine, "tools/cost_guard.py", null)).toBe(
      "vscode://file/C:/Users/robla/VScode_Project/AGAGI/tools/cost_guard.py",
    );
  });

  test("un antislash n'atteint jamais le href (VS Code ne résout pas %5C)", () => {
    const h = vscodeHref("C:\\Users\\robla\\AGAGI\\", "tools\\a.py")!;
    expect(h).toBe("vscode://file/C:/Users/robla/AGAGI/tools/a.py");
    expect(h).not.toMatch(/%5C|\\/);
  });

  test("sans racine, pas de lien", () => {
    expect(vscodeHref(null, "tools/a.py")).toBeNull();
  });
});

describe("lireFlotte — lecture défensive d'un contrat qui n'est pas le nôtre", () => {
  test("lit sessions (compte Bash P2.118 compris), alertes, mortes et l'aveuglement du tableau", () => {
    const v = lireFlotte({
      sessions: [
        {
          name: "agagi-e2",
          branch: "feat/d1",
          claims: ["P2.114"],
          claims_inferes: ["P2.107"],
          files_touched: ["a", "b"],
          bash_ecritures_possibles: 2,
          bulletin: true,
          heartbeat_at: 100,
        },
      ],
      alertes: [{ id: "A1", cle: "A1:x", gravite: "alerte", message: "m", preuve: { f: 1 } }],
      sessions_mortes: ["agagi-00"],
      aveugle: ["backlog (chemins cités par les entrées)"],
    });
    expect(v.sessions?.items[0]).toEqual({
      nom: "agagi-e2",
      branche: "feat/d1",
      claims: ["P2.114"],
      inferes: ["P2.107"],
      fichiers: 2,
      bashEcritures: 2,
      bulletin: true,
      heartbeatAt: 100,
    });
    expect(v.alertes?.items[0].gravite).toBe("alerte");
    expect(v.mortes).toEqual(["agagi-00"]);
    expect(flotteAveugleSur(v, "backlog")).toBe(true);
    expect(flotteAveugleSur(v, "registre natif")).toBe(false);
  });

  test("clé absente -> null (« non publié »), jamais une liste vide ni un 0", () => {
    const v = lireFlotte({ sessions: [{ name: "s" }] });
    expect(v.sessions?.items[0]).toMatchObject({ claims: null, inferes: null, fichiers: null, bashEcritures: null });
    const w = lireFlotte({});
    expect(w.sessions).toBeNull();
    expect(w.alertes).toBeNull();
    expect(w.mortes).toBeNull();
    expect(w.aveugle).toEqual([]);
  });

  test("une entrée illisible est COMPTÉE, jamais retirée en silence", () => {
    const v = lireFlotte({ sessions: [{ name: "a" }, 42, null], alertes: [{ id: "A1" }] });
    expect(v.sessions?.items).toHaveLength(1);
    expect(v.sessions?.illisibles).toBe(2);
    expect(v.alertes?.items).toHaveLength(0);
    expect(v.alertes?.illisibles).toBe(1);
  });
});
