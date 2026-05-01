declare module "next/server" {
  export class NextResponse extends Response {
    cookies: {
      set: (
        name: string,
        value: string,
        options?: {
          httpOnly?: boolean;
          sameSite?: "lax" | "strict" | "none";
          secure?: boolean;
          path?: string;
          maxAge?: number;
        },
      ) => void;
    };
    static json(body: unknown, init?: ResponseInit): NextResponse;
  }
}
