export const meta = {
  name: 'refutateur',
  description: 'Revue adversariale a sondes propres d un record ou d une pre-inscription : temoins ANONYMES, plancher MECANIQUE puis JUGE calibre, enfin 10 prompts figes (docs/REF/REF-REVUE-ADVERSARIALE.md). Le bareme vit en Python (tools/refutateur_temoins.py) : ce script ne juge rien. Tout score de phase temoins voyage avec son PLANCHER DE FAUSSES RETROUVAILLES. Un defaut connu non retrouve rend la revue NULLE : rien ne s ecrit.',
  phases: [
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
const VERIFICATION = {
  type: 'object',
  properties: {
    refus: { type: 'string' },
    plancher: { type: 'string' },
    resultats: { type: 'object', additionalProperties: { type: 'object', properties: {
      retrouve: { type: 'boolean' }, code: { type: 'number' },
      fichier_critiques: { type: 'string' }, commande: { type: 'string' } },
      required: ['retrouve', 'code', 'fichier_critiques', 'commande'] } },
  },
  required: ['resultats', 'plancher'],
}

function consigne(cible, ids) {
  return `Tu es le REFUTATEUR. Lis ${REF} et applique EXACTEMENT les prompts ${ids.join(', ')} a la cible ${cible}.
Un prompt marque DELEGUE est UNE LIGNE : lance la porte nommee, recopie son verdict, arrete-toi. Un prompt marque JUGE
demande de lire, de compter ou de rejouer. Chaque critique porte sa SONDE (commande rejouable, que tu as LANCEE), sa PREUVE
et son CONSTAT, une classe (Ex du registre ou "aucune") et un verdict parmi confirme / non confirme / hors perimetre.
Trois conditions MECANIQUES ecartent une critique avant toute lecture de fond : verdict confirme ; PREUVE de forme
verifiable (fichier:ligne, ou commande avec sortie chiffree, ou valeur opposee a une autre -- "aucune" n'en est pas une) ;
et CONSTAT qui n'est pas une RECOPIE (aucune fenetre de huit mots consecutifs reprise mot pour mot du fichier relu).
Ne construis aucun monde, ne lance aucune simulation. Reponds en francais, <= 40 lignes.`
}

phase('Temoins')
const fichiers = args.fichiers || []
if (!fichiers.length) {
  log(`revue NULLE : aucun fichier de temoin fourni (lancer python tools/refutateur_temoins.py --extraire avant)`)
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
// ⚠️ PAS d'`effort: 'low'` ici (il y etait, et c'etait l'erreur) : cette phase decide ce que le juge voit,
// c'est une garde contre une fuite, pas une corvee. Son mode d'echec silencieux -- une liste vide -- a
// fait tomber toute la revue au 2e lancement reel.
const AIGUILLAGE = {
  type: 'object',
  properties: { fichiers: { type: 'array', items: { type: 'string' } },
                commande: { type: 'string' }, sortie_brute: { type: 'string' } },
  required: ['fichiers', 'commande', 'sortie_brute'],
}
const aiguillage = await agent(`Lance: PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --questions-du-juge
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
1. Lance: PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --cas-du-juge
   Cette commande rend des cas de calibration : une REF opaque, les temoins vises, et des critiques. Pour chacun, va
   chercher le champ \`defaut\` du temoin vise dans ${ROSTER}, puis reponds OUI ou NON a la question ci-dessus.
   Rends ces reponses dans \`calibration\`, la cle etant la REF du cas, telle quelle.
2. Lance: PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --questions-du-juge
   Elle donne, pour chaque fichier a juger, le DEFAUT a reconnaitre. Pour chaque relecture fournie plus bas, retrouve
   son fichier dans cette liste et rends dans \`jugements\` (cle = nom de base du fichier relu) OUI / NON / INDECIDABLE
   sur la meme question. Ne juge que les fichiers que cette commande nomme.
Relectures a juger (JSON) : ${JSON.stringify(relecturesJugees)}`,
  { label: 'juge', phase: 'Juge', schema: JUGEMENTS })

phase('Verification')
// Le script ne juge rien : un agent ecrit les critiques, lance le CLI, et DECLARE les chemins pour que le
// controleur relance lui-meme. Un agent qui rendrait code:0 sans rien lancer laisse une commande rejouable.
const verif = await agent(`Tu es le VERIFICATEUR. Tu ne juges RIEN : le bareme vit dans ${ROSTER} et dans
tools/refutateur_temoins.py.
Relectures, une par temoin (JSON) : ${JSON.stringify(relectures)}
Jugements rendus par le juge, cle = nom de base du fichier relu : ${JSON.stringify(juge && juge.jugements)}
1. Lis ${ROSTER}. REFUSE (champ refus non vide, resultats vide) si les genres ne sont pas EXACTEMENT trois "defaut" et
   un "noop", si un nom ou un champ fichier est en double, ou si un temoin du roster n'a pas sa relecture ci-dessus.
2. RE-DERIVE l'aiguillage. Lance: PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --questions-du-juge
   et compare la liste de fichiers qu'elle imprime a celle qui a servi a filtrer les relectures du juge :
   ${JSON.stringify([...aJuger])}. Si elles different, REFUSE avec la raison "aiguillage divergent" -- le juge a vu
   autre chose que ce que le roster gele prescrit, et cela peut etre une FUITE.
3. Verifie la CALIBRATION du juge. Lance:
   PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --cas-du-juge-avec-reponses
   (vue RESERVEE au verificateur : le juge, lui, n'a recu que la question, sous une REF opaque). Chaque ligne y porte
   la REF puis le nom du cas : remappe par la REF les reponses du juge ${JSON.stringify(juge && juge.calibration)}
   et compare-les au champ juge. Si UNE seule differe, REFUSE avec la raison "juge non calibre" : un juge qui rate ses
   propres temoins ne juge pas.
4. Ecris la liste de critiques de chaque relecture, telle quelle, en JSON, dans
   ${travail}/critiques-<nom du temoin>.json (cree le repertoire). N'ajoute, ne retire, ne reformule AUCUNE critique.
5. Lance pour chacun, depuis la racine du depot, en reprenant le jugement du juge -- ses cles sont des NOMS DE BASE de
   fichiers, que le champ fichier du roster rattache a un temoin :
   PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier <nom> ${travail}/critiques-<nom>.json --extrait <chemin relu> --jugement <OUI|NON|INDECIDABLE>
   Le code de sortie fait foi : 0 = retrouve, 1 = revue NULLE, 2 = indecidable. Ne reinterprete pas la sortie texte.
   Un temoin sans jugement du juge se lance SANS --jugement ; ne fabrique jamais un jugement absent.
6. Lance enfin: PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --plancher <repertoire des temoins>
   et recopie sa premiere ligne, TELLE QUELLE, dans le champ plancher. Un score sans son plancher est interdit.
7. Rends {refus, plancher, resultats: {<nom>: {retrouve, code, fichier_critiques, commande}}}, ou le champ commande
   porte la ligne EXACTE que tu as lancee a l'etape 5, pour qu'un tiers la relance.`,
  { label: 'verification', phase: 'Verification', schema: VERIFICATION })

const resultats = (verif && verif.resultats) || {}
const refus = ((verif && verif.refus) || '').trim()
const plancherPublie = ((verif && verif.plancher) || '').trim()
const rates = Object.entries(resultats).filter(([, v]) => !v.retrouve || v.code !== 0).map(([n]) => n)
if (refus || !Object.keys(resultats).length || rates.length || !plancherPublie) {
  log(`revue NULLE : ${refus || (rates.length ? `temoins non retrouves ${rates.join(', ')}` : 'plancher non publie')}`)
  return { statut: 'NUL', raison: refus || 'temoin manque', temoins: resultats,
           plancher: plancherPublie, cible: args.target }
}
log(`temoins retrouves : ${Object.keys(resultats).join(' ')} — ${plancherPublie}`)

phase('Revue')
const parPrompt = await pipeline(PROMPTS, id =>
  agent(consigne(args.target, [id]), { label: `revue:${id}`, phase: 'Revue', schema: CRITIQUES }))
const critiques = parPrompt.filter(Boolean).flatMap(r => r.critiques || []).filter(c => c.sonde && c.sonde.trim())

phase('Consolidation')
const slug = args.target.split('/').pop().replace(/\.(md|json)$/, '').slice(0, 60)
const sortie = `docs/reviews/${args.today}-${slug}.md`
const consolide = await agent(`Ecris le fichier ${sortie} (Write) selon docs/reviews/README.md : en-tete (cible ${args.target},
date ${args.today}, SHA courant via git rev-parse HEAD, resultat des TEMOINS ${JSON.stringify(resultats)} ET, sur la meme
ligne, le PLANCHER DE FAUSSES RETROUVAILLES tel quel : "${plancherPublie}" -- un score sans son plancher est interdit),
puis une section par prompt P1..P10 avec Sonde / Constat / Classe / Verdict, a partir de ces critiques (JSON) :
${JSON.stringify(critiques)}. N'invente AUCUNE critique et n'en retire aucune. Ne modifie AUCUN autre fichier.
Rends le chemin ecrit et le nombre de critiques confirmees.`,
  { label: 'consolidation', phase: 'Consolidation', effort: 'low' })
return { statut: 'ECRITE', fichier: sortie, n_critiques: critiques.length,
         n_confirmees: critiques.filter(c => (c.verdict || '').toLowerCase().startsWith('confirm')).length,
         temoins: resultats, plancher: plancherPublie, note: consolide }
