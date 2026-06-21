// frontend/src/lib/push.ts — register SW, request permission, POST subscription.

const SUBSCRIBED_FLAG = "analytis_push_subscribed";
const ASKED_FLAG = "analytis_push_asked";

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const output = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i += 1) output[i] = rawData.charCodeAt(i);
  return output;
}

export function isPushSupported(): boolean {
  return (
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

export function isInstalledPwa(): boolean {
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    (window.navigator as { standalone?: boolean }).standalone === true
  );
}

export function hasBeenAsked(): boolean {
  return localStorage.getItem(ASKED_FLAG) === "true";
}

export function isSubscribed(): boolean {
  return localStorage.getItem(SUBSCRIBED_FLAG) === "true";
}

export function markAsked(): void {
  localStorage.setItem(ASKED_FLAG, "true");
}

export async function enablePush(): Promise<void> {
  if (!isPushSupported()) throw new Error("push not supported");

  const keyResp = await fetch("/v1/push/vapid-public-key");
  if (!keyResp.ok) throw new Error(`vapid-public-key failed: ${keyResp.status}`);
  const { public_key } = (await keyResp.json()) as { public_key: string };

  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    markAsked();
    throw new Error("permission denied");
  }

  const registration = await navigator.serviceWorker.register("/sw.js");
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(public_key),
  });

  const json = subscription.toJSON();
  const subResp = await fetch("/v1/push/subscribe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      endpoint: json.endpoint,
      p256dh: json.keys?.p256dh,
      auth: json.keys?.auth,
      user_agent: navigator.userAgent,
    }),
  });
  if (!subResp.ok) throw new Error(`subscribe failed: ${subResp.status}`);

  localStorage.setItem(SUBSCRIBED_FLAG, "true");
  markAsked();
}
