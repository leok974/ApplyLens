// Debug script for browser console
// Run this on https://applylens.app/web/search

// 1. Show which bundle is loaded
console.log('📦 Loaded bundles:',
  [...document.scripts]
    .filter(s => s.src.includes('index-'))
    .map(s => s.src)
);

// 2. Intercept fetch calls to log all URLs
(function(){
  const orig = fetch;
  window.fetch = async function(input, init){
    const url = typeof input === 'string' ? input : input.url;
    console.info('[FETCH]', url, init?.method || 'GET');
    return orig.apply(this, arguments);
  };
})();

console.log('✅ Fetch interceptor installed. Now perform a search and watch for [FETCH] logs.');
console.log('Expected: [FETCH] https://applylens.app/api/search?q=... GET');
console.log('❌ BAD if you see: [FETCH] https://applylens.app/web/search/...');
