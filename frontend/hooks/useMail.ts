import useSWR from "swr";

import { api } from "@/lib/api";

export function useFolders() {
  return useSWR("folders", api.mail.folders);
}

export function useMail(folder: string, page: number) {
  return useSWR(["mail", folder, page], () => api.mail.list(folder, page));
}
