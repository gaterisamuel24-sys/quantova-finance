// Leaving the app for a payment provider's hosted page.

/** The only places the app will send the browser to for payments. */
const PAYMENT_HOSTS = ["https://checkout.stripe.com/", "https://billing.stripe.com/"];

/**
 * Whether a URL is a payment page we expect. The server builds these URLs, but checking
 * here as well means a bug or a tampered response can never redirect users elsewhere.
 */
export function isPaymentPageUrl(url: string): boolean {
  return PAYMENT_HOSTS.some((prefix) => url.startsWith(prefix));
}

/** Send the browser to a provider-hosted payment page. Kept separate so tests can replace it. */
export function goToPaymentPage(url: string): void {
  if (!isPaymentPageUrl(url)) throw new Error("Unexpected payment page address.");
  window.location.assign(url);
}
