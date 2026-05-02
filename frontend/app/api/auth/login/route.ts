import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const body = await request.json();
  const apiBase = (
    (globalThis as { process?: { env?: Record<string, string | undefined> } })
      .process?.env?.NEXT_PUBLIC_API_URL ?? ""
  )
    .replace(/\/+$/, "")
    .replace(/\/api$/, "");
  const backend = await fetch(`${apiBase}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const raw = await backend.text();
  let payload: unknown = raw;
  try {
    payload = raw ? JSON.parse(raw) : {};
  } catch {
    payload = raw || { detail: "Unexpected response from backend" };
  }

  if (!backend.ok) {
    const errorBody =
      typeof payload === "object" && payload !== null
        ? payload
        : { detail: String(payload) };
    return NextResponse.json(errorBody, { status: backend.status });
  }

  const isSecure =
    request.headers.get("x-forwarded-proto") === "https" ||
    new URL(request.url).protocol === "https:";
  const response = NextResponse.json(payload);
  if (
    typeof payload === "object" &&
    payload !== null &&
    "access_token" in payload &&
    "refresh_token" in payload
  ) {
    const tokens = payload as { access_token: string; refresh_token: string };
    response.cookies.set("access_token", tokens.access_token, {
      httpOnly: true,
      sameSite: "lax",
      secure: isSecure,
      path: "/",
    });
    response.cookies.set("refresh_token", tokens.refresh_token, {
      httpOnly: true,
      sameSite: "lax",
      secure: isSecure,
      path: "/",
    });
  }
  return response;
}
