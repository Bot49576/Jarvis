import assert from 'node:assert/strict';
import { chooseAcknowledgement } from './dashboard/acknowledgements.js';

assert.equal(chooseAcknowledgement('Hallo JARVIS'), null);
assert.equal(chooseAcknowledgement('Bist du online?'), null);
assert.equal(chooseAcknowledgement('Was ist zwei plus zwei?'), null);
assert.equal(chooseAcknowledgement('Wie heißt du?'), null);
assert.equal(chooseAcknowledgement('Merk dir: Mein Lieblingsspiel ist Minecraft.'), null);
assert.equal(chooseAcknowledgement('/memory'), null);

assert.match(chooseAcknowledgement('Weißt du noch, wie mein Freund heißt?', { randomValue: 0 }), /Speicher/);
assert.match(chooseAcknowledgement('Prüfe bitte die Datenbank.', { randomValue: 0 }), /Datenbanken/);
assert.match(chooseAcknowledgement('Werte bitte diese Statistik aus.', { randomValue: 0 }), /Daten/);
assert.match(chooseAcknowledgement('Welche Filme laufen heute im Kino?', { randomValue: 0 }), /aktuellen Informationen/);
assert.match(chooseAcknowledgement('Prüfe den Render-Fehler im Server.', { randomValue: 0 }), /Zustand/);
assert.match(chooseAcknowledgement('', { hasFiles: true, randomValue: 0 }), /Datei/);
assert.match(chooseAcknowledgement('Analysiere diese Möglichkeiten gründlich.', { randomValue: 0 }), /Moment/);

const first = chooseAcknowledgement('Recherchiere das aktuelle Wetter.', { randomValue: 0 });
const second = chooseAcknowledgement('Recherchiere das aktuelle Wetter.', { randomValue: 0, previous: first });
assert.notEqual(second, first);

console.log('14 Kurzrückmeldungs-Tests bestanden.');
