export const meta = {
  name: 'refutateur',
  description: 'Revue adversariale a sondes propres d un record ou d une pre-inscription : temoins geles d abord, puis 10 prompts figes (docs/REF/REF-REVUE-ADVERSARIALE.md), un contexte par prompt, consolidation en docs/reviews/. Un defaut connu non retrouve rend la revue NULLE : rien ne s ecrit.',
  phases: [
    { title: 'Temoins', detail: '3 defauts connus + 1 no-op : un manque -> revue NULLE' },
    { title: 'Revue', detail: 'P1..P10, un contexte par prompt, sondes obligatoires et LANCEES' },
    { title: 'Consolidation', detail: 'docs/reviews/<date>-<slug>.md, selon docs/reviews/README.md' },
  ],
}

// args = { target: 'docs/EDR/X.md' | 'docs/preregistrations/Y.json', kind: 'record'|'prereg', today: 'AAAA-MM-JJ',
//          temoins: [{nom, genre, attendu, fichier}] }
// Les champs des temoins viennent de tools/refutateur_temoins.json (via --extraire) : le script ne les invente pas.
// Ce workflow ne construit AUCUN monde et ne prend AUCUN bail : une revue est une lecture.
const REF = 'docs/REF/REF-REVUE-ADVERSARIALE.md'
const PROMPTS = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9', 'P10']
const CRITIQUES = {
  type: 'object',
  properties: { critiques: { type: 'array', items: { type: 'object', properties: {
    prompt: { type: 'string' }, constat: { type: 'string' }, sonde: { type: 'string' }, preuve: { type: 'string' },
    classe: { type: 'string' }, verdict: { type: 'string' } },
    required: ['prompt', 'constat', 'sonde', 'preuve', 'classe', 'verdict'] } } },
  required: ['critiques'],
}

function consigne(cible, ids) {
  return `Tu es le REFUTATEUR. Lis ${REF} et applique EXACTEMENT les prompts ${ids.join(', ')} a la cible ${cible}.
Un prompt marque DELEGUE est UNE LIGNE : lance la porte nommee, recopie son verdict, arrete-toi. Un prompt marque JUGE
demande de lire, de compter ou de rejouer. Chaque critique porte sa SONDE (commande rejouable, que tu as LANCEE), sa PREUVE
(fichier:ligne ou sortie de commande), une classe (Ex du registre ou "aucune") et un verdict parmi confirme / non confirme /
hors perimetre. Une critique sans sonde lancee est interdite. Ne construis aucun monde, ne lance aucune simulation.
Reponds en francais, <= 40 lignes.`
}

// Un agent qui n'a RIEN rendu (r nul, pas de tableau) n'est pas une revue silencieuse : c'est une absence
// de mesure. La confondre avec « zero critique » ferait passer le temoin no-op sur du vide.
function retrouve(temoin, r) {
  if (!r || !Array.isArray(r.critiques)) return false
  const critiques = r.critiques
  if (temoin.genre === 'noop') {
    return critiques.filter(c => (c.verdict || '').toLowerCase().startsWith('confirm')).length <= 1
  }
  if (!temoin.attendu) return false // un temoin a defaut sans regex ne peut pas discriminer
  return new RegExp(temoin.attendu, 'i').test(JSON.stringify(critiques))
}

phase('Temoins')
const temoins = args.temoins || []
if (!temoins.length) {
  log('revue NULLE : aucun temoin fourni (lancer tools/refutateur_temoins.py --extraire avant)')
  return { statut: 'NUL', raison: 'temoins absents', cible: args.target }
}
const verdictsTemoins = await parallel(temoins.map(t => () =>
  agent(consigne(t.fichier, PROMPTS), { label: `temoin:${t.nom}`, phase: 'Temoins', schema: CRITIQUES })
    .then(r => {
      const crit = (r && Array.isArray(r.critiques)) ? r.critiques : null
      return { nom: t.nom, genre: t.genre, ok: retrouve(t, r), n: crit ? crit.length : null }
    })))
const rendus = verdictsTemoins.filter(Boolean)
const manques = rendus.filter(v => !v.ok).map(v => v.nom)
if (manques.length || rendus.length < temoins.length) {
  log(`revue NULLE : temoins non retrouves ${manques.join(', ') || '(agents sans reponse)'}`)
  return { statut: 'NUL', temoins: verdictsTemoins, cible: args.target }
}
log(`temoins retrouves : ${rendus.map(v => `${v.nom}(${v.n})`).join(' ')}`)

phase('Revue')
const parPrompt = await pipeline(PROMPTS, id =>
  agent(consigne(args.target, [id]), { label: `revue:${id}`, phase: 'Revue', schema: CRITIQUES }))
const critiques = parPrompt.filter(Boolean).flatMap(r => r.critiques || []).filter(c => c.sonde && c.sonde.trim())

phase('Consolidation')
const slug = args.target.split('/').pop().replace(/\.(md|json)$/, '').slice(0, 60)
const sortie = `docs/reviews/${args.today}-${slug}.md`
const consolide = await agent(`Ecris le fichier ${sortie} (Write) selon docs/reviews/README.md : en-tete (cible ${args.target},
date ${args.today}, SHA courant via git rev-parse HEAD, resultat des TEMOINS : ${JSON.stringify(rendus)} — y compris le
plancher de fausses critiques rendu par le temoin no-op), puis une section par prompt P1..P10 avec Sonde / Constat / Classe /
Verdict, a partir de ces critiques (JSON) : ${JSON.stringify(critiques)}. N'invente AUCUNE critique et n'en retire aucune.
Ne modifie AUCUN autre fichier. Rends le chemin ecrit et le nombre de critiques confirmees.`,
  { label: 'consolidation', phase: 'Consolidation', effort: 'low' })
return { statut: 'ECRITE', fichier: sortie, n_critiques: critiques.length,
         n_confirmees: critiques.filter(c => (c.verdict || '').toLowerCase().startsWith('confirm')).length,
         temoins: rendus, note: consolide }
