import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const body = await request.json();
  const apiBase =
    (globalThis as { process?: { env?: Record<string, string | undefined> } })
      .process?.env?.NEXT_PUBLIC_API_URL ?? "";
  const backend = await fetch(`${apiBase}/api/auth/logout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await backend.json();
  const response = NextResponse.json(payload, { status: backend.status });
  response.cookies.set("access_token", "", {
    httpOnly: true,
    sameSite: "lax",
    secure: true,
    path: "/",
    maxAge: 0,
  });
  response.cookies.set("refresh_token", "", {
    httpOnly: true,
    sameSite: "lax",
    secure: true,
    path: "/",
    maxAge: 0,
  });
  return response;
}
