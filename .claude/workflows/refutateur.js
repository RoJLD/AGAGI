export const meta = {
  name: 'refutateur',
  description: 'Revue adversariale a sondes propres d un record ou d une pre-inscription : temoins ANONYMES, plancher MECANIQUE puis JUGE calibre, enfin 10 prompts figes (docs/REF/REF-REVUE-ADVERSARIALE.md). Le bareme vit en Python (tools/refutateur_temoins.py) : ce script ne juge rien. Tout score de phase temoins voyage avec son PLANCHER DE FAUSSES RETROUVAILLES. Un defaut connu non retrouve rend la revue NULLE : rien ne s ecrit.',
  phases: [
    { title: 'Temoins', detail: 'relecture AVEUGLE de fichiers anonymes : ni nom, ni genre, ni attendu' },
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
2. Pour chaque relecture ci-dessous, identifie le temoin par le champ \`fichier\` du roster (nom de base du chemin relu),
   et rends dans \`jugements\` (cle = nom du temoin) OUI / NON / INDECIDABLE sur la meme question, a partir du champ
   \`defaut\` de CE temoin. Pour un temoin de genre noop, rends INDECIDABLE : il n'a pas de defaut a nommer.
Relectures (JSON) : ${JSON.stringify(relectures)}`, { label: 'juge', phase: 'Juge', schema: JUGEMENTS })

phase('Verification')
// Le script ne juge rien : un agent ecrit les critiques, lance le CLI, et DECLARE les chemins pour que le
// controleur relance lui-meme. Un agent qui rendrait code:0 sans rien lancer laisse une commande rejouable.
const verif = await agent(`Tu es le VERIFICATEUR. Tu ne juges RIEN : le bareme vit dans ${ROSTER} et dans
tools/refutateur_temoins.py.
1. Lis ${ROSTER}. REFUSE (champ refus non vide, resultats vide) si les genres ne sont pas EXACTEMENT trois "defaut" et
   un "noop", si un nom ou un champ fichier est en double, ou si un temoin du roster n'a pas sa relecture ci-dessous.
2. Verifie la CALIBRATION du juge. Lance:
   PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --cas-du-juge-avec-reponses
   (vue RESERVEE au verificateur : le juge, lui, n'a recu que la question, sous une REF opaque). Chaque ligne y porte
   la REF puis le nom du cas : remappe par la REF les reponses du juge ${JSON.stringify(juge && juge.calibration)}
   et compare-les au champ juge. Si UNE seule differe, REFUSE avec la raison "juge non calibre" : un juge qui rate ses
   propres temoins ne juge pas.
3. Ecris la liste de critiques de chaque relecture, telle quelle, en JSON, dans
   ${travail}/critiques-<nom du temoin>.json (cree le repertoire). N'ajoute, ne retire, ne reformule AUCUNE critique.
4. Lance pour chacun, depuis la racine du depot, en reprenant le jugement du juge
   (${JSON.stringify(juge && juge.jugements)}) :
   PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier <nom> ${travail}/critiques-<nom>.json --extrait <chemin relu> --jugement <OUI|NON|INDECIDABLE>
   Le code de sortie fait foi : 0 = retrouve, 1 = revue NULLE, 2 = indecidable. Ne reinterprete pas la sortie texte.
   Pour un temoin de genre noop, ne passe PAS --jugement.
5. Lance enfin: PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --plancher <repertoire des temoins>
   et recopie sa premiere ligne, TELLE QUELLE, dans le champ plancher. Un score sans son plancher est interdit.
6. Rends {refus, plancher, resultats: {<nom>: {retrouve, code, fichier_critiques, commande}}}, ou le champ commande
   porte la ligne EXACTE que tu as lancee a l'etape 4, pour qu'un tiers la relance.`,
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
