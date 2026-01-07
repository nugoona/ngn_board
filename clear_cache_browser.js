// 브라우저 콘솔에서 실행할 캐시 무효화 명령어

// 방법 1: cafe24_product_sales 캐시만 삭제
fetch('/data/cache/invalidate', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({pattern: 'cafe24_product_sales'})
})
.then(r => r.json())
.then(console.log)
.catch(console.error);

// 방법 2: 전체 캐시 삭제
fetch('/data/cache/invalidate', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({pattern: ''})
})
.then(r => r.json())
.then(console.log)
.catch(console.error);

