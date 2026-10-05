// Service worker de Miamm : rappels (Web Push) et ouverture hors ligne de la dernière version de la page.
const CACHE = "miamm-v1";
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));

// La page : réseau d'abord, la copie gardée sinon (l'app s'ouvre même sans connexion).
self.addEventListener("fetch", e => {
  if (e.request.mode !== "navigate") return;
  e.respondWith(fetch(e.request).then(r => {
    const copie = r.clone(); caches.open(CACHE).then(c => c.put("/", copie)); return r;
  }).catch(() => caches.match("/")));
});

// Le rappel arrive sans contenu : on lit le texte du jour sur le serveur.
self.addEventListener("push", e => e.waitUntil((async () => {
  let r = { titre: "Miamm", texte: "Un rappel t'attend dans l'app." };
  try { const x = await fetch("/api/rappel", { cache: "no-store" }); if (x.ok) r = await x.json(); } catch (err) {}
  await self.registration.showNotification(r.titre, { body: r.texte, icon: "/icone-192.png", badge: "/icone-192.png", tag: "miamm-" + (r.date || "") });
})()));

self.addEventListener("notificationclick", e => {
  e.notification.close();
  e.waitUntil(self.clients.matchAll({ type: "window" }).then(l => l.length ? l[0].focus() : self.clients.openWindow("/")));
});
