import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const body = await request.json();
  const apiBase =
    ((globalThis as { process?: { env?: Record<string, string | undefined> } })
      .process?.env?.NEXT_PUBLIC_API_URL ?? "")
      .replace(/\/+$/, "")
      .replace(/\/api$/, "");
  const backend = await fetch(`${apiBase}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await backend.json();
  if (!backend.ok) {
    return NextResponse.json(payload, { status: backend.status });
  }
  const response = NextResponse.json(payload);
  response.cookies.set("access_token", payload.access_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: true,
    path: "/",
  });
  response.cookies.set("refresh_token", payload.refresh_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: true,
    path: "/",
  });
  return response;
}
