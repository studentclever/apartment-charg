/* Service worker for the apartment-charge offline app.
   Only registered over https / localhost (see registerSW() in the page). */
var CACHE = 'apartment-charge-v7';

var ASSETS = [
  './',
  './apartment-charge.html',
  './manifest.webmanifest',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/icon-maskable-192.png',
  './icons/icon-maskable-512.png',
  './icons/apple-touch-icon.png',
  './icons/favicon-32.png',
  './icons/favicon-16.png'
];

self.addEventListener('install', function(e){
  e.waitUntil((function(){
    return caches.open(CACHE).then(function(c){
      return Promise.all(ASSETS.map(function(u){
        return c.add(new Request(u, {cache:'reload'})).catch(function(){});
      }));
    }).then(function(){ return self.skipWaiting(); });
  })());
});

self.addEventListener('activate', function(e){
  e.waitUntil((function(){
    return caches.keys().then(function(keys){
      return Promise.all(keys.map(function(k){
        return k === CACHE ? null : caches.delete(k);
      }));
    }).then(function(){ return self.clients.claim(); });
  })());
});

self.addEventListener('fetch', function(e){
  var req = e.request;
  if(req.method !== 'GET') return;

  var url;
  try{ url = new URL(req.url); }catch(err){ return; }
  if(url.origin !== self.location.origin) return;

  // Navigations: try the network, fall back to the cached shell.
  if(req.mode === 'navigate'){
    e.respondWith(
      fetch(req).then(function(res){
        var copy = res.clone();
        caches.open(CACHE).then(function(c){ c.put('./apartment-charge.html', copy); });
        return res;
      }).catch(function(){
        return caches.match('./apartment-charge.html').then(function(hit){
          return hit || caches.match('./') || Response.error();
        });
      })
    );
    return;
  }

  // Everything else: cache-first.
  e.respondWith(
    caches.match(req).then(function(hit){
      if(hit) return hit;
      return fetch(req).then(function(res){
        if(res && res.status === 200 && res.type === 'basic'){
          var copy = res.clone();
          caches.open(CACHE).then(function(c){ c.put(req, copy); });
        }
        return res;
      }).catch(function(){
        return caches.match('./apartment-charge.html').then(function(fb){
          return fb || Response.error();
        });
      });
    })
  );
});
