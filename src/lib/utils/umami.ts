/**
 * Umami's tracker starts with `if (!document.currentScript) return`. A
 * normal `<script src>` added after parse (e.g. from Svelte `<svelte:head>`)
 * runs with `currentScript === null`, so tracking never starts. Fetching the
 * tracker and assigning it to `script.textContent` keeps `currentScript`
 * pointing at that element while it runs, so `data-*` attributes work.
 *
 * Note: a strict CSP without `'unsafe-inline'` may block inline execution; in
 * that case set CONTENT_SECURITY_POLICY to allow the tracker (see backend
 * security_headers) or use a nonce-based policy with server-injected HTML.
 */
export async function injectUmami(umami: {
	website_id?: string;
	script_url?: string;
	host_url?: string;
}): Promise<void> {
	if (!umami?.website_id || typeof document === 'undefined') return;
	if (document.querySelector('script[data-openwebui-umami]')) return;

	const scriptUrl = umami.script_url || 'https://cdn.umami.is/script.js';
	let apiOrigin = (umami.host_url || '').replace(/\/$/, '');
	if (!apiOrigin) {
		try {
			apiOrigin = new URL(scriptUrl).origin;
		} catch {
			apiOrigin = 'https://cdn.umami.is';
		}
	}

	let code: string;
	try {
		const res = await fetch(scriptUrl, { credentials: 'omit' });
		if (!res.ok) return;
		code = await res.text();
	} catch {
		return;
	}

	const s = document.createElement('script');
	s.setAttribute('data-openwebui-umami', '1');
	s.setAttribute('data-website-id', umami.website_id);
	s.setAttribute('data-host-url', apiOrigin);
	s.textContent = code;
	document.head.appendChild(s);
}
