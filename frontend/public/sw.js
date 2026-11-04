const CACHE = "mikuy-shell-v1";
const BUILD_ASSETS = [];
const PUBLIC = [
  ...BUILD_ASSETS,
  "/",
  "/offline.html",
  "/manifest.webmanifest",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/logo.png",
  "/icons/logo-dark.png",
  "/icons/logo-light.png",
  "/fonts/Nunito-variable.ttf",
  "/reference-art/plate.webp",
  "/reference-art/recipe-1.webp",
  "/reference-art/recipe-2.webp",
  "/reference-art/recipe-3.webp",
];
self.addEventListener("install", (event) =>
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.addAll(PUBLIC))
      .then(() => self.skipWaiting()),
  ),
);
self.addEventListener("activate", (event) =>
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((k) => k.startsWith("mikuy-shell-") && k !== CACHE)
            .map((k) => caches.delete(k)),
        ),
      )
      .then(() => self.clients.claim()),
  ),
);
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (
    event.request.method !== "GET" ||
    url.origin !== self.location.origin ||
    url.pathname.startsWith("/api")
  )
    return;
  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request).catch(() =>
        caches.match("/").then((r) => r || caches.match("/offline.html")),
      ),
    );
    return;
  }
  if (PUBLIC.includes(url.pathname) || url.pathname.startsWith("/assets/")) {
    // Static public resources may be precached without the module Origin header.
    event.respondWith(
      caches.match(event.request, { ignoreVary: true }).then(
        (cached) =>
          cached ||
          fetch(event.request).then((response) => {
            if (response.ok) {
              const clone = response.clone();
              caches
                .open(CACHE)
                .then((cache) => cache.put(event.request, clone));
            }
            return response;
          }),
      ),
    );
  }
});
