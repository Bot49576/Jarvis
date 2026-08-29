const GENERAL = [
  'Einen Moment, Sir. Ich prüfe das.',
  'Verstanden, Sir. Ich sehe mir das kurz an.',
  'Ich kümmere mich darum und melde mich gleich.',
  'Einen Augenblick, ich prüfe die Anfrage.',
  'Alles klar, Sir. Ich bin dran.',
  'Ich überprüfe das kurz und melde mich gleich bei Ihnen.',
  'Dafür brauche ich einen Moment, Sir.',
  'Sehr wohl, Sir. Ich arbeite daran.',
  'Verstanden. Ich bereite die Antwort vor.',
];

const SPECIAL = {
  memory: [
    'Dafür prüfe ich kurz meinen Speicher, einen Moment, Sir.',
    'Ich gleiche das kurz mit meinem Gedächtnis ab, Sir.',
  ],
  data: [
    'Ich prüfe kurz die verfügbaren Daten.',
    'Einen Moment, Sir. Ich werte die verfügbaren Daten aus.',
  ],
  database: [
    'Ich prüfe kurz meine Datenbanken.',
    'Einen Augenblick, Sir. Ich sehe in der Datenbank nach.',
  ],
  research: [
    'Ich rufe die aktuellen Informationen ab, einen Moment.',
    'Einen Moment, Sir. Ich gleiche die aktuellen Quellen ab.',
    'Ich recherchiere das kurz und melde mich mit dem Ergebnis.',
  ],
  technical: [
    'Ich überprüfe kurz den aktuellen Zustand.',
    'Einen Augenblick, Sir. Ich führe die technische Prüfung durch.',
    'Verstanden. Ich prüfe den Fehler und melde mich gleich.',
  ],
  file: [
    'Einen Moment, Sir. Ich prüfe die Datei.',
    'Verstanden. Ich sehe mir den Inhalt der Datei kurz an.',
  ],
};

const SIMPLE = /^(hallo(?: jarvis)?|hi(?: jarvis)?|hey(?: jarvis)?|guten (morgen|tag|abend)(?: jarvis)?|bist du (da|online)|jarvis[, ]*bist du da|wie geht es dir|wie geht['’]?s|danke|vielen dank|wer bist du|was kannst du)[.!? ]*$/i;
const MEMORY = /\b(erinnerst du|weißt du noch|weisst du noch|was weißt du über mich|was weisst du über mich|was habe ich dir|mein speicher|dein speicher|gedächtnis|memory)\b/i;
const DATABASE = /\b(datenbank|datenbanken|database|sql|neon[- ]?tabelle)\b/i;
const DATA = /\b(statistik|messwerte?|datensatz|daten auswerten|werte auswerten|verfügbare daten|zahlen vergleichen)\b/i;
const RESEARCH = /\b(recherchier\w*|suche (im|online|nach)|aktuell\w*|neueste\w*|heute|morgen|wetter|kinoprogramm|spielzeiten|öffnungszeiten|preise?|quellen?|internet)\b/i;
const TECHNICAL = /\b(fehler|error|log|protokoll|status|server|render|api|webhook|code|programm|funktioniert nicht|technisch|diagnose|prüfe .*(system|verbindung|dienst|zustand))\b/i;
const COMPLEX = /\b(analysier\w*|vergleich\w*|plane|erstelle|berechne|fasse zusammen|erklär\w*.*ausführlich|überprüf\w*|untersuch\w*|arbeite .* aus|liste .* auf)\b/i;
const FAST_COMMAND = /^\/(memory|reset|forgetall|voice)(\s|$)|^(merk dir|vergiss)\s*:/i;

function categoryFor(text, hasFiles) {
  const normalized = String(text || '').trim().replace(/\s+/g, ' ');
  if (hasFiles) return 'file';
  if (!normalized || FAST_COMMAND.test(normalized) || SIMPLE.test(normalized)) return null;
  if (MEMORY.test(normalized)) return 'memory';
  if (DATABASE.test(normalized)) return 'database';
  if (DATA.test(normalized)) return 'data';
  if (RESEARCH.test(normalized)) return 'research';
  if (TECHNICAL.test(normalized)) return 'technical';
  if (COMPLEX.test(normalized) || normalized.length >= 100) return 'general';
  return null;
}

export function chooseAcknowledgement(text, {
  hasFiles = false,
  randomValue = Math.random(),
  previous = '',
} = {}) {
  const category = categoryFor(text, hasFiles);
  if (!category) return null;
  const variants = category === 'general' ? GENERAL : SPECIAL[category];
  const safeRandom = Number.isFinite(randomValue) ? Math.max(0, Math.min(.999999, randomValue)) : 0;
  let index = Math.floor(safeRandom * variants.length);
  if (variants.length > 1 && variants[index] === previous) index = (index + 1) % variants.length;
  return variants[index];
}
