export const meta = {
  name: 'refutateur',
  description: 'Revue adversariale a sondes propres d un record ou d une pre-inscription : temoins ANONYMES d abord, puis 10 prompts figes (docs/REF/REF-REVUE-ADVERSARIALE.md), un contexte par prompt, consolidation en docs/reviews/. Le bareme vit en Python (tools/refutateur_temoins.py) : ce script ne juge rien. Un defaut connu non retrouve rend la revue NULLE : rien ne s ecrit.',
  phases: [
    { title: 'Temoins', detail: 'relecture AVEUGLE de fichiers anonymes : ni nom, ni genre, ni attendu' },
    { title: 'Verification', detail: 'un seul agent : roster gele + CLI python, codes 0/1/2' },
    { title: 'Revue', detail: 'P1..P10, un contexte par prompt, sondes obligatoires et LANCEES' },
    { title: 'Consolidation', detail: 'docs/reviews/<date>-<slug>.md, selon docs/reviews/README.md' },
  ],
}

// args = { target: 'docs/EDR/X.md' | 'docs/preregistrations/Y.json', kind: 'record'|'prereg', today: 'AAAA-MM-JJ',
//          fichiers: ['<dir>/temoin-1.md', ...],   // CHEMINS SEULS : ni nom de temoin, ni genre, ni attendu
//          travail: '<scratchpad>/refutateur' }    // ou le verificateur ecrit les critiques
//
// Le roster gele (tools/refutateur_temoins.json) fait foi et n'est JAMAIS passe par l'appelant : sinon un
// appelant pourrait affaiblir un `attendu`, ne passer que le no-op, ou pointer ailleurs. Ce script ne
// contient AUCUN bareme : il fait lancer `python tools/refutateur_temoins.py --verifier`, dont les codes
// de sortie sont 0 (retrouve) / 1 (revue NULLE) / 2 (indecidable ou roster invalide).
// Ce workflow ne construit aucun monde et ne prend aucun bail : une revue est une lecture.
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
const VERIFICATION = {
  type: 'object',
  properties: {
    refus: { type: 'string' },
    resultats: { type: 'object', additionalProperties: { type: 'object', properties: {
      retrouve: { type: 'boolean' }, code: { type: 'number' }, fichier: { type: 'string' } },
      required: ['retrouve', 'code'] } },
  },
  required: ['resultats'],
}

function consigne(cible, ids) {
  return `Tu es le REFUTATEUR. Lis ${REF} et applique EXACTEMENT les prompts ${ids.join(', ')} a la cible ${cible}.
Un prompt marque DELEGUE est UNE LIGNE : lance la porte nommee, recopie son verdict, arrete-toi. Un prompt marque JUGE
demande de lire, de compter ou de rejouer. Chaque critique porte sa SONDE (commande rejouable, que tu as LANCEE), sa PREUVE
(fichier:ligne ou sortie de commande), une classe (Ex du registre ou "aucune") et un verdict parmi confirme / non confirme /
hors perimetre. Une critique sans sonde lancee est interdite. Le CONSTAT et la PREUVE portent ce que tu affirmes : une
critique dont le fond ne vit que dans la sonde ne dit rien. Ne construis aucun monde, ne lance aucune simulation.
Reponds en francais, <= 40 lignes.`
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

phase('Verification')
const travail = args.travail || `${fichiers[0].replace(/[\\/][^\\/]*$/, '')}-verification`
const verif = await agent(`Tu es le VERIFICATEUR de la phase temoins. Tu ne juges RIEN toi-meme : le bareme vit dans
${ROSTER} et dans tools/refutateur_temoins.py.
1. Lis ${ROSTER}. REFUSE (champ refus non vide, resultats vide) si les genres ne sont pas EXACTEMENT trois "defaut" et un
   "noop", ou si un nom ou un champ fichier est en double, ou si un temoin de genre defaut n'a pas de regex attendu.
2. Pour chaque relecture ci-dessous, retrouve le temoin dont le champ fichier du roster est le NOM DE BASE du chemin relu.
   REFUSE si un temoin du roster n'a pas sa relecture, ou si un chemin relu ne correspond a aucun temoin.
3. Ecris la liste de critiques de chaque relecture, telle quelle, en JSON, dans ${travail}/critiques-<nom du temoin>.json
   (cree le repertoire). N'ajoute, ne retire, ne reformule AUCUNE critique.
4. Lance pour chacun, depuis la racine du depot :
   PYTHONIOENCODING=utf-8 python tools/refutateur_temoins.py --verifier <nom du temoin> ${travail}/critiques-<nom>.json
   Le code de sortie fait foi : 0 = retrouve, 1 = revue NULLE, 2 = indecidable. Ne reinterprete pas la sortie texte.
5. Rends {refus, resultats: {<nom du temoin>: {retrouve, code, fichier}}}.
Relectures (JSON) : ${JSON.stringify(relectures)}`,
  { label: 'verification', phase: 'Verification', schema: VERIFICATION })

const resultats = (verif && verif.resultats) || {}
const refus = (verif && verif.refus || '').trim()
const rates = Object.entries(resultats).filter(([, v]) => !v.retrouve || v.code !== 0).map(([n]) => n)
if (refus || !Object.keys(resultats).length || rates.length) {
  log(`revue NULLE : ${refus || `temoins non retrouves ${rates.join(', ')}`}`)
  return { statut: 'NUL', raison: refus || 'temoin manque', temoins: resultats, cible: args.target }
}
log(`temoins retrouves : ${Object.keys(resultats).join(' ')}`)

phase('Revue')
const parPrompt = await pipeline(PROMPTS, id =>
  agent(consigne(args.target, [id]), { label: `revue:${id}`, phase: 'Revue', schema: CRITIQUES }))
const critiques = parPrompt.filter(Boolean).flatMap(r => r.critiques || []).filter(c => c.sonde && c.sonde.trim())

phase('Consolidation')
const slug = args.target.split('/').pop().replace(/\.(md|json)$/, '').slice(0, 60)
const sortie = `docs/reviews/${args.today}-${slug}.md`
const consolide = await agent(`Ecris le fichier ${sortie} (Write) selon docs/reviews/README.md : en-tete (cible ${args.target},
date ${args.today}, SHA courant via git rev-parse HEAD, resultat des TEMOINS : ${JSON.stringify(resultats)} — y compris le
plancher de fausses critiques rendu par le temoin de genre noop), puis une section par prompt P1..P10 avec Sonde / Constat /
Classe / Verdict, a partir de ces critiques (JSON) : ${JSON.stringify(critiques)}. N'invente AUCUNE critique et n'en retire
aucune. Ne modifie AUCUN autre fichier. Rends le chemin ecrit et le nombre de critiques confirmees.`,
  { label: 'consolidation', phase: 'Consolidation', effort: 'low' })
return { statut: 'ECRITE', fichier: sortie, n_critiques: critiques.length,
         n_confirmees: critiques.filter(c => (c.verdict || '').toLowerCase().startsWith('confirm')).length,
         temoins: resultats, note: consolide }
