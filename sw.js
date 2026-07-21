// GourmetAI Service Worker
self.addEventListener('install', (event) => {
    console.log('👷 Service Worker kuruluyor...');
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    console.log('🚀 Service Worker aktif!');
});

self.addEventListener('fetch', (event) => {
    // Çevrimdışı/ağ istekleri için standart geçiş
    event.respondWith(fetch(event.request));
});