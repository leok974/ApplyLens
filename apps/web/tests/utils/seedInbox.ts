// apps/web/tests/utils/seedInbox.ts

/**
 * Extract CSRF token from Set-Cookie header or cookie string
 */
function extractCsrfToken(response: Response): string | null {
  const setCookie = response.headers.get('set-cookie');
  if (!setCookie) return null;

  // Parse csrf_token from Set-Cookie header
  const match = setCookie.match(/csrf_token=([^;]+)/);
  return match ? match[1] : null;
}

/**
 * Build Cookie header from Set-Cookie response
 */
function buildCookieHeader(response: Response): string {
  const setCookie = response.headers.get('set-cookie');
  if (!setCookie) return '';

  // Extract cookie name=value pairs
  const cookies = setCookie.split(',').map(c => {
    const match = c.trim().match(/^([^=]+)=([^;]+)/);
    return match ? `${match[1]}=${match[2]}` : '';
  }).filter(Boolean);

  return cookies.join('; ');
}

export async function seedInbox(baseUrl: string, count = 25) {
  // Get CSRF token from any endpoint (token is set in cookie by middleware)
  const csrfRes = await fetch(`${baseUrl}/ready`, {
    method: 'GET',
    credentials: 'include'
  });

  if (!csrfRes.ok) {
    throw new Error(`Failed to get CSRF token: ${csrfRes.status}`);
  }

  // Extract CSRF token from Set-Cookie header
  const token = extractCsrfToken(csrfRes);
  if (!token) {
    throw new Error('No CSRF token in response cookies');
  }

  // Build cookie header to pass to next request
  const cookieHeader = buildCookieHeader(csrfRes);

  console.log('Got CSRF token from cookie');

  // Call seed endpoint with CSRF token
  const seedUrl = `${baseUrl}/api/dev/seed-threads-simple`;
  console.log(`Calling seed endpoint: ${seedUrl}`);

  const seedRes = await fetch(seedUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': token,
      'Cookie': cookieHeader,  // Pass cookies manually
    },
    body: JSON.stringify({ count })
  });

  if (!seedRes.ok) {
    const body = await seedRes.text();
    throw new Error(`Seed failed: ${seedRes.status} ${body}`);
  }

  return await seedRes.json();
}
