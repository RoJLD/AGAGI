export const meta = {
  name: 'refutateur',
  description: 'Revue adversariale a sondes propres d un record ou d une pre-inscription : temoins ANONYMES, plancher MECANIQUE puis JUGE calibre, enfin 10 prompts figes (docs/REF/REF-REVUE-ADVERSARIALE.md). Le bareme vit en Python (tools/refutateur_temoins.py) : ce script ne juge rien. Tout score de phase temoins voyage avec son PLANCHER DE FAUSSES RETROUVAILLES. Un defaut connu non retrouve rend la revue NULLE : rien ne s ecrit.',
  phases: [
    { title: 'Racine', detail: 'racine ABSOLUE du depot, validee avant toute autre phase' },
    { title: 'Temoins', detail: 'relecture AVEUGLE de fichiers anonymes : ni nom, ni genre, ni attendu' },
    { title: 'Aiguillage', detail: 'quels fichiers le juge doit juger : le no-op ne lui parvient pas' },
    { title: 'Juge', detail: 'etage 2 : calibre sur cinq textes a reponse connue, sinon INDECIDABLE' },
    { title: 'Verification', detail: 'etage 1 + verdict par le CLI python ; chemins DECLARES, plancher publie' },
    { title: 'Revue', detail: 'P1..P10, un contexte par prompt, sondes obligatoires et LANCEES' },
    { title: 'Consolidation', detail: 'docs/reviews/<date>-<slug>.md, selon docs/reviews/README.md' },
  ],
}

// args = { target: 'docs/EDR/X.md' | 'docs/preregistrations/Y.json', kind: 'record'|'prereg', today: 'AAAA-MM-JJ',
//          fichiers: ['<dir>/temoin-1.md', ...],   // CHEMINS SEULS : ni nom de temoin, ni genre, ni attendu
//          travail: '<scratchpad>/refutateur' }    // ou le verificateur ecrit les critiques
//
// Le roster gele (tools/refutateur_temoins.json) fait foi et n'est JAMAIS passe par l'appelant.
// Ce script ne contient AUCUN bareme : il fait lancer le CLI python, dont les codes de sortie sont
// 0 (retrouve) / 1 (revue NULLE) / 2 (indecidable). Il ne construit aucun monde et ne prend aucun bail.
// ⚠ RACINE ABSOLUE. Tous les prompts employaient des chemins RELATIFS, donc dependaient du repertoire
// courant dont les agents heritent -- un etat ambiant NON DECLARE. Mesure du 2026-09-24 : un agent a
// lance le CLI depuis l'arbre principal, ou le module n'existe pas, et n'a rapporte qu'EXIT=2. Sans la
// sortie brute rendue par l'aiguillage, la cause aurait ete cherchee une troisieme fois a l'aveugle.
let racine = args.racine || '.'
const REF = 'docs/REF/REF-REVUE-ADVERSARIALE.md'
const ROSTER = 'tools/refutateur_temoins.json'
const PROMPTS = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9', 'P10']
const CRITIQUES = {
  type: 'object',
  properties: { critiques: { type: 'array', items: { type: 'object', properties: {
    prompt: { type: 'string' }, constat: { type: 'string' }, sonde: { type: 'string' }, preuve: { type: 'string' },
    classe: { type: 'string' }, verdict: { type: 'string' } },
    required: ['prompt', 'constat', 'sonde', 'preuve', 'classe', 'verdict'] } } },
  required: ['critiques'],
}
const JUGEMENTS = {
  type: 'object',
  properties: {
    calibration: { type: 'object', additionalProperties: { type: 'string' } },
    jugements: { type: 'object', additionalProperties: { type: 'string' } },
  },
  required: ['calibration', 'jugements'],
}
// ⚠ LE NO-OP MESURE, IL NE FAIT PAS BARRAGE. Son `statut` vaut MESURE et son `n_recevables` est le
// PLANCHER mesure sur un record cru sain : il voyage avec le score, jamais a cote. Une revue qui a
// retrouve trois defauts reels ne se jette plus parce que ce plancher est haut -- c'etait supprimer la
// mesure au lieu de la publier (1er Step 4 complet, 2026-09-24 : 6 critiques recevables sur le no-op,
// dont une confirmee contre les donnees). Seuls les temoins a DEFAUT font barriere.
const VERIFICATION = {
  type: 'object',
  properties: {
    // P2.133 : la DECISION de refus est un BOOLEEN ; raison n'en porte que le motif, lu seulement si refuse.
    refuse: { type: 'boolean' },
    raison: { type: 'string' },
    plancher: { type: 'string' },
    plancher_noop: { type: 'string' },
    resultats: { type: 'object', additionalProperties: { type: 'object', properties: {
      statut: { type: 'string' }, code: { type: 'number' }, n_recevables: { type: 'number' },
      fichier_critiques: { type: 'string' }, commande: { type: 'string' } },
      required: ['statut', 'code', 'n_recevables', 'fichier_critiques', 'commande'] } },
  },
  required: ['refuse', 'resultats', 'plancher', 'plancher_noop'],
}

function consigne(cible, ids) {
  return `Tu es le REFUTATEUR. Lis ${racine}/${REF} et applique EXACTEMENT les prompts ${ids.join(', ')} a la cible ${cible}.
Un prompt marque DELEGUE est UNE LIGNE : lance la porte nommee, recopie son verdict, arrete-toi. Un prompt marque JUGE
demande de lire, de compter ou de rejouer. Chaque critique porte sa SONDE (commande rejouable, que tu as LANCEE), sa PREUVE
et son CONSTAT, une classe (Ex du registre ou "aucune") et un verdict parmi confirme / non confirme / hors perimetre.
Trois conditions MECANIQUES ecartent une critique avant toute lecture de fond : verdict confirme ; PREUVE de forme
verifiable (fichier:ligne, ou commande avec sortie chiffree, ou valeur opposee a une autre -- "aucune" n'en est pas une) ;
et CONSTAT qui n'est pas une RECOPIE (aucune fenetre de huit mots consecutifs reprise mot pour mot du fichier relu).
Ne construis aucun monde, ne lance aucune simulation. Reponds en francais, <= 40 lignes.`
}

phase('Racine')
// Une garde qui REFUSE au demarrage si le module n'est pas trouvable a la racine annoncee. Le script
// n'a pas d'acces disque : un agent la derive et la fait VALIDER par le CLI, dont le code fait foi.
const RACINE = {
  type: 'object',
  properties: { racine: { type: 'string' }, code: { type: 'number' },
                commande: { type: 'string' }, sortie_brute: { type: 'string' } },
  required: ['racine', 'code', 'commande', 'sortie_brute'],
}
const ancrage = await agent(`Determine la racine ABSOLUE du depot AGAGI et verifie que le Refutateur y est utilisable.
1. Lance: git rev-parse --show-toplevel   (depuis le repertoire du script${args.racine ? `, ou prends ${args.racine}` : ''})
2. Avec ce chemin ABSOLU R, lance: PYTHONIOENCODING=utf-8 python R/tools/refutateur_temoins.py --racine-valide R
3. Rends \`racine\` = R, \`code\` = le code de sortie de l'etape 2 (0 = utilisable, 2 = non),
   \`commande\` = la ligne EXACTE de l'etape 2, \`sortie_brute\` = sa sortie COMPLETE telle quelle.
N'invente aucun chemin et ne corrige rien : si ca echoue, rends le code et la sortie.`,
  { label: 'racine', phase: 'Racine', schema: RACINE })
if (!ancrage || ancrage.code !== 0 || !ancrage.racine) {
  log(`revue NULLE : racine-invalide -- le module n'est pas trouvable a la racine annoncee`)
  log(`  commande lancee : ${(ancrage && ancrage.commande) || '(non rendue)'}`)
  log(`  sortie brute lue : ${(ancrage && ancrage.sortie_brute) || '(non rendue)'}`)
  return { statut: 'NUL', raison: 'racine-invalide', cible: args.target,
           racine: { annoncee: ancrage && ancrage.racine, code: ancrage && ancrage.code,
                     commande: ancrage && ancrage.commande,
                     sortie_brute: ancrage && ancrage.sortie_brute } }
}
racine = ancrage.racine
log(`racine validee : ${racine}`)

phase('Temoins')
const fichiers = args.fichiers || []
if (!fichiers.length) {
  log(`revue NULLE : aucun fichier de temoin fourni (lancer python ${racine}/tools/refutateur_temoins.py --extraire avant)`)
  return { statut: 'NUL', raison: 'temoins absents', cible: args.target }
}
// Relecture AVEUGLE : l'agent recoit un chemin anonyme, jamais le nom du temoin ni ce qu'il doit y trouver.
const relectures = await parallel(fichiers.map(f => () =>
  agent(consigne(f, PROMPTS), { label: `aveugle:${f.split(/[\\/]/).pop()}`, phase: 'Temoins', schema: CRITIQUES })
    .then(r => ({ fichier: f, critiques: (r && Array.isArray(r.critiques)) ? r.critiques : null }))))
const muettes = relectures.filter(r => !r || !r.critiques).length
if (muettes) {
  log(`revue NULLE : ${muettes} relecture(s) de temoin sans reponse`)
  return { statut: 'NUL', raison: 'relecture sans reponse', cible: args.target }
}

phase('Aiguillage')
// Le juge ne doit NI etre interroge sur le temoin sain, NI en recevoir la relecture : sinon il
// l'identifie par difference. Un agent qui ne juge rien et ne lit aucun temoin rend la liste des
// fichiers a juger.
//
// POURQUOI UN AGENT, et pas `args.fichiers_a_juger` : le roster GELE doit rester le seul a partitionner
// les temoins. Laisser l'appelant nommer les fichiers a juger lui rendrait le pouvoir qu'on lui a retire
// a la ronde 4 -- il pourrait tous les passer (le juge verrait le no-op) ou n'en passer qu'un. Le script
// n'a pas d'acces disque : quelqu'un doit lancer la commande. Cet agent est le privilege MINIMAL qui le
// permet, et depuis cette ronde sa sortie est RE-DERIVEE par le verificateur, qui refuse sur ecart :
// une fuite ne serait plus silencieuse.
//
// ⚠ PAS d'`effort: 'low'` ici (il y etait, et c'etait l'erreur) : cette phase decide ce que le juge voit,
// c'est une garde contre une fuite, pas une corvee. Son mode d'echec silencieux -- une liste vide -- a
// fait tomber toute la revue au 2e lancement reel.
const AIGUILLAGE = {
  type: 'object',
  properties: { fichiers: { type: 'array', items: { type: 'string' } },
                commande: { type: 'string' }, sortie_brute: { type: 'string' } },
  required: ['fichiers', 'commande', 'sortie_brute'],
}
const aiguillage = await agent(`Lance: PYTHONIOENCODING=utf-8 python ${racine}/tools/refutateur_temoins.py --questions-du-juge
Rends dans \`fichiers\` la liste des noms de fichier qu'elle imprime, telle quelle, sans rien y ajouter ni retirer ;
dans \`commande\` la ligne EXACTE que tu as lancee ; dans \`sortie_brute\` sa sortie COMPLETE, telle quelle.
Si la commande echoue ou n'imprime aucun fichier, rends \`fichiers\` vide ET la sortie brute : c'est elle qui dira
pourquoi. Tu ne juges rien et tu ne lis aucun de ces fichiers.`,
  { label: 'aiguillage', phase: 'Aiguillage', schema: AIGUILLAGE })
const aJuger = new Set((aiguillage && aiguillage.fichiers) || [])
const relecturesJugees = relectures.filter(r => aJuger.has(r.fichier.split(/[\\/]/).pop()))
// Deux pannes OPPOSEES, longtemps confondues sous un seul message : rien n'a ete relaye (TRANSPORT),
// ou rien n'a ete filtre (FUITE -- le juge verrait le temoin sain).
if (!relecturesJugees.length || relecturesJugees.length >= relectures.length) {
  const panne = relecturesJugees.length ? 'aiguillage-FUITE' : 'aiguillage-TRANSPORT'
  const detail = relecturesJugees.length
    ? `rien n'a ete filtre : le juge verrait les ${relectures.length} relectures, no-op compris`
    : `rien n'a ete relaye : ${aJuger.size} fichier(s) rendu(s) par l'aiguillage`
  log(`revue NULLE : ${panne} -- ${detail}`)
  log(`  commande lancee : ${(aiguillage && aiguillage.commande) || '(non rendue)'}`)
  log(`  sortie brute lue : ${(aiguillage && aiguillage.sortie_brute) || '(non rendue)'}`)
  return { statut: 'NUL', raison: panne, detail, cible: args.target,
           aiguillage: { commande: aiguillage && aiguillage.commande,
                         sortie_brute: aiguillage && aiguillage.sortie_brute,
                         fichiers: [...aJuger] } }
}

phase('Juge')
const travail = args.travail || `${fichiers[0].replace(/[\\/][^\\/]*$/, '')}-verification`
// Etage 2. Le juge ne voit JAMAIS le motif `attendu` : il recoit le defaut DECLARE en prose et des critiques.
// Il est d'abord confronte a ses cinq cas a reponse connue ; s'il les rate, l'instrument ne juge pas.
const juge = await agent(`Tu es le JUGE de la phase temoins. Ta seule question, pour chaque lot de critiques :
« ces critiques nomment-elles LE defaut decrit ? » -- OUI, NON, ou INDECIDABLE. Tu ne cherches AUCUN mot impose :
une decouverte formulee autrement reste une decouverte, et reciter un vocabulaire n'en est pas une.
1. Lance: PYTHONIOENCODING=utf-8 python ${racine}/tools/refutateur_temoins.py --cas-du-juge
   Cette commande rend des cas de calibration : une REF opaque, les temoins vises, et des critiques. Pour chacun, va
   chercher le champ \`defaut\` du temoin vise dans ${racine}/${ROSTER}, puis reponds OUI ou NON a la question ci-dessus.
   Rends ces reponses dans \`calibration\`, la cle etant la REF du cas, telle quelle.
2. Lance: PYTHONIOENCODING=utf-8 python ${racine}/tools/refutateur_temoins.py --questions-du-juge
   Elle donne, pour chaque fichier a juger, le DEFAUT a reconnaitre. Pour chaque relecture fournie plus bas, retrouve
   son fichier dans cette liste et rends dans \`jugements\` (cle = nom de base du fichier relu) OUI / NON / INDECIDABLE
   sur la meme question. Ne juge que les fichiers que cette commande nomme.
Relectures a juger (JSON) : ${JSON.stringify(relecturesJugees)}`,
  { label: 'juge', phase: 'Juge', schema: JUGEMENTS })

phase('Verification')
// Le script ne juge rien : un agent ecrit les critiques, lance le CLI, et DECLARE les chemins pour que le
// controleur relance lui-meme. Un agent qui rendrait code:0 sans rien lancer laisse une commande rejouable.
const verif = await agent(`Tu es le VERIFICATEUR. Tu ne juges RIEN : le bareme vit dans ${racine}/${ROSTER} et dans
${racine}/tools/refutateur_temoins.py.
Relectures, une par temoin (JSON) : ${JSON.stringify(relectures)}
Jugements rendus par le juge, cle = nom de base du fichier relu : ${JSON.stringify(juge && juge.jugements)}
1. Lis ${racine}/${ROSTER}. REFUSE (refuse: true, le motif dans raison, resultats vide) si les genres ne sont pas EXACTEMENT trois "defaut" et
   un "noop", si un nom ou un champ fichier est en double, ou si un temoin du roster n'a pas sa relecture ci-dessus.
2. RE-DERIVE l'aiguillage. Lance: PYTHONIOENCODING=utf-8 python ${racine}/tools/refutateur_temoins.py --questions-du-juge
   et compare la liste de fichiers qu'elle imprime a celle qui a servi a filtrer les relectures du juge :
   ${JSON.stringify([...aJuger])}. Si elles different, REFUSE avec la raison "aiguillage divergent" -- le juge a vu
   autre chose que ce que le roster gele prescrit, et cela peut etre une FUITE.
3. Verifie la CALIBRATION du juge. Lance:
   PYTHONIOENCODING=utf-8 python ${racine}/tools/refutateur_temoins.py --cas-du-juge-avec-reponses
   (vue RESERVEE au verificateur : le juge, lui, n'a recu que la question, sous une REF opaque). Chaque ligne y porte
   la REF puis le nom du cas : remappe par la REF les reponses du juge ${JSON.stringify(juge && juge.calibration)}
   et compare-les au champ juge. Si UNE seule differe, REFUSE avec la raison "juge non calibre" : un juge qui rate ses
   propres temoins ne juge pas.
4. Ecris la liste de critiques de chaque relecture, telle quelle, en JSON, dans
   ${travail}/critiques-<nom du temoin>.json (cree le repertoire). N'ajoute, ne retire, ne reformule AUCUNE critique.
5. Lance pour chacun, depuis la racine du depot, en reprenant le jugement du juge -- ses cles sont des NOMS DE BASE de
   fichiers, que le champ fichier du roster rattache a un temoin :
   PYTHONIOENCODING=utf-8 python ${racine}/tools/refutateur_temoins.py --verifier <nom> ${travail}/critiques-<nom>.json --extrait <chemin relu> --jugement <OUI|NON|INDECIDABLE>
   Le code de sortie fait foi et la premiere ligne imprimee donne le STATUT (RETROUVE / NULLE / INDECIDABLE /
   MESURE) ainsi que le nombre de critiques RECEVABLES. Ne reinterprete rien d'autre.
   Un temoin sans jugement du juge se lance SANS --jugement ; ne fabrique jamais un jugement absent.
   ⚠ Le temoin qui rend MESURE ne fait PAS barrage : il MESURE un plancher sur un record cru sain. Reporte son
   statut et son compte, n'en tire aucun echec.
6. Lance enfin: PYTHONIOENCODING=utf-8 python ${racine}/tools/refutateur_temoins.py --plancher <repertoire des temoins>
   et recopie sa premiere ligne, TELLE QUELLE, dans le champ plancher. Un score sans son plancher est interdit.
7. Compose \`plancher_noop\` : une ligne de la forme
   "plancher mesure sur <nom du temoin de genre noop> : N critiques recevables (seuil historique S)",
   avec le N et le S que l'etape 5 a imprimes pour ce temoin. Ce nombre voyage AVEC le score, jamais a cote.
8. Rends {refuse, raison, plancher, plancher_noop, resultats: {<nom>: {statut, code, n_recevables, fichier_critiques,
   commande}}}, ou le champ commande porte la ligne EXACTE de l'etape 5, pour qu'un tiers la relance.
   refuse est un BOOLEEN : true si tu as refuse a l'une des etapes 1 a 3, false sinon. raison porte le motif
   d'un refus et n'est LUE que si refuse vaut true : ne l'emploie jamais pour dire qu'il n'y a pas de refus.`,
  { label: 'verification', phase: 'Verification', schema: VERIFICATION })

const resultats = (verif && verif.resultats) || {}
// P2.133 (2026-09-26) : la decision de refus etait un TEXTE LIBRE, et quatre formes l'ont lue a tort comme un refus
// le meme soir -- deux guillemets (bfaea9c6, qui normalisait guillemets et espaces), « aucun » (wf_c3134d3f-8dd),
// « (vide) Pas de refus. Etape 1 : ... » (wf_f2e45bc7-b84), « (aucun refus) Roster conforme : ... »
// (wf_4c85e158-009). Une liste noire recommence a chaque synonyme : la
// DECISION est desormais le booleen refuse, le motif un champ separe raison, lu seulement si refuse vaut true. Un
// refus accompagne de resultats, ou un refuse absent ou non booleen, est un etat INCOHERENT NOMME -- jamais un nul
// de fond. Temoin : tests/sandbox/test_refutateur_workflow_refus.py (extrait lireRefus, l'execute sous node).
function lireRefus(v) {
  const n = Object.keys((v && v.resultats) || {}).length
  if (v && v.refuse === true) {
    const motif = typeof v.raison === 'string' ? v.raison.trim() : ''
    return n ? { etat: 'INCOHERENT', raison: 'refuse vaut true mais ' + n + ' resultat(s) rendus : un refus exige resultats VIDE' }
             : { etat: 'REFUS', raison: motif || 'refus sans raison donnee' }
  }
  if (v && v.refuse === false) return { etat: 'SANS_REFUS', raison: '' }
  return { etat: 'INCOHERENT', raison: 'champ refuse absent ou non booleen : ' + JSON.stringify(v ? v.refuse : null) }
}
const lecture = lireRefus(verif)
const refus = lecture.etat === 'REFUS' ? lecture.raison : ''
const plancherPublie = ((verif && verif.plancher) || '').trim()
const plancherNoop = ((verif && verif.plancher_noop) || '').trim()
if (lecture.etat === 'INCOHERENT') {
  log(`revue INCOHERENTE : ${lecture.raison}`)
  return { statut: 'INCOHERENT', raison: lecture.raison, temoins: resultats,
           plancher: plancherPublie, plancher_noop: plancherNoop, cible: args.target }
}
// Seuls les temoins a DEFAUT font barriere. Un statut MESURE est une mesure, pas un echec.
const rates = Object.entries(resultats)
  .filter(([, v]) => v.statut !== 'RETROUVE' && v.statut !== 'MESURE').map(([n]) => n)
const mesures = Object.entries(resultats).filter(([, v]) => v.statut === 'MESURE')
// DISCRIMINATION : le record cru sain produit-il MOINS de critiques recevables que les defectueux ?
// Si non, l'instrument ne les distingue pas -- et ca se DIT, ca ne s'annule pas.
const nDefauts = Object.values(resultats)
  .filter(v => v.statut === 'RETROUVE').map(v => v.n_recevables).filter(n => typeof n === 'number')
const nNoop = mesures.length ? mesures[0][1].n_recevables : null
const discrimine = (nNoop === null || !nDefauts.length) ? null : nNoop < Math.min(...nDefauts)
if (refus || !Object.keys(resultats).length || rates.length || !plancherPublie || !plancherNoop) {
  log(`revue NULLE : ${refus || (rates.length ? `defauts non retrouves ${rates.join(', ')}` : 'plancher non publie')}`)
  return { statut: 'NUL', raison: refus || 'defaut manque', temoins: resultats,
           plancher: plancherPublie, plancher_noop: plancherNoop, cible: args.target }
}
log(`defauts retrouves : ${Object.keys(resultats).filter(n => resultats[n].statut === 'RETROUVE').join(' ')}`)
log(`  ${plancherPublie}`)
log(`  ${plancherNoop}`)
if (discrimine === false) {
  log(`  ⚠ INDISCRIMINANT : le record cru sain rend ${nNoop} critiques recevables, les defectueux au moins ${Math.min(...nDefauts)}`)
}

phase('Revue')
const parPrompt = await pipeline(PROMPTS, id =>
  agent(consigne(args.target, [id]), { label: `revue:${id}`, phase: 'Revue', schema: CRITIQUES }))
const critiques = parPrompt.filter(Boolean).flatMap(r => r.critiques || []).filter(c => c.sonde && c.sonde.trim())

phase('Consolidation')
const slug = args.target.split('/').pop().replace(/\.(md|json)$/, '').slice(0, 60)
const sortie = `docs/reviews/${args.today}-${slug}.md`
const consolide = await agent(`Ecris le fichier ${sortie} (Write) selon docs/reviews/README.md : en-tete (cible ${args.target},
date ${args.today}, SHA courant via git -C ${racine} rev-parse HEAD, resultat des TEMOINS ${JSON.stringify(resultats)} ET, sur les
memes lignes, LES DEUX PLANCHERS tels quels : "${plancherPublie}" et "${plancherNoop}"${
  discrimine === false ? `, suivis de "⚠ INDISCRIMINANT : le record cru sain rend autant de critiques recevables que les defectueux"` : ''
} -- un score sans ses planchers est interdit),
puis une section par prompt P1..P10 avec Sonde / Constat / Classe / Verdict, a partir de ces critiques (JSON) :
${JSON.stringify(critiques)}. N'invente AUCUNE critique et n'en retire aucune. Ne modifie AUCUN autre fichier.
Rends le chemin ecrit et le nombre de critiques confirmees.`,
  { label: 'consolidation', phase: 'Consolidation', effort: 'low' })
return { statut: 'ECRITE', fichier: sortie, n_critiques: critiques.length,
         n_confirmees: critiques.filter(c => (c.verdict || '').toLowerCase().startsWith('confirm')).length,
         temoins: resultats, plancher: plancherPublie, plancher_noop: plancherNoop,
         discrimine, racine, note: consolide }
