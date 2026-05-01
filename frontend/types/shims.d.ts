declare namespace JSX {
  interface IntrinsicElements {
    [elemName: string]: any;
  }
  interface IntrinsicAttributes {
    key?: string | number;
  }
  interface Element {}
  interface ElementChildrenAttribute {
    children: {};
  }
}

declare module "react" {
  export type ReactNode = any;
  export type ReactElement = any;
  export type FormEvent<T = any> = any;
  export type RefObject<T> = { current: T | null };
  export interface ButtonHTMLAttributes<T> {
    className?: string;
    children?: ReactNode;
    onClick?: (event: any) => void;
    disabled?: boolean;
    type?: "button" | "submit" | "reset";
  }
  export interface InputHTMLAttributes<T> {
    className?: string;
    value?: string;
    placeholder?: string;
    type?: string;
    onChange?: (event: any) => void;
  }
  export interface HTMLAttributes<T> {
    className?: string;
    children?: ReactNode;
    onClick?: (event: any) => void;
  }
  export function useState<T>(
    initial: T,
  ): [T, (value: T | ((previous: T) => T)) => void];
  export function useEffect(
    effect: () => void | (() => void),
    deps?: any[],
  ): void;
  export function useMemo<T>(factory: () => T, deps: any[]): T;
  export function useRef<T>(initial: T | null): { current: T | null };
  export function useCallback<T extends (...args: any[]) => any>(
    callback: T,
    deps: any[],
  ): T;
  export function createElement(...args: any[]): any;
  export const Fragment: any;
}

declare module "react/jsx-runtime" {
  export const jsx: any;
  export const jsxs: any;
  export const Fragment: any;
}

declare module "next/link" {
  import type { ReactNode } from "react";
  export default function Link(props: {
    href: string;
    className?: string;
    children?: ReactNode;
    onClick?: () => void;
  }): any;
}

declare module "next/navigation" {
  export function redirect(url: string): never;
  export function useRouter(): { push: (url: string) => void };
  export function useParams<T extends Record<string, string | string[]>>(): T;
}

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

declare module "@tanstack/react-query" {
  import type { ReactNode } from "react";
  export class QueryClient {}
  export function QueryClientProvider(props: {
    client: QueryClient;
    children?: ReactNode;
  }): any;
}

declare module "zustand" {
  export function create<T>(): any;
}

declare module "zustand/middleware" {
  export function persist<T>(initializer: any, options: any): any;
}

declare module "swr" {
  export default function useSWR(
    key: any,
    fetcher: any,
  ): { data: any; error: any; mutate: any };
}

declare module "@tiptap/react" {
  import type { ReactNode } from "react";
  export function useEditor(options: any): any;
  export function EditorContent(props: {
    editor: any;
    children?: ReactNode;
  }): any;
}

declare module "@tiptap/starter-kit" {
  const StarterKit: any;
  export default StarterKit;
}

declare module "@tiptap/extension-placeholder" {
  const Placeholder: any;
  export default Placeholder;
}

declare module "dompurify" {
  const DOMPurify: { sanitize: (input: string) => string };
  export default DOMPurify;
}

declare module "*.css" {
  const content: string;
  export default content;
}
