import { useEffect } from "react";

export function useInfiniteScroll(
  target: { current: HTMLElement | null },
  onLoadMore: () => void,
) {
  useEffect(() => {
    const node = target.current;
    if (!node) {
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      if (entries[0]?.isIntersecting) {
        onLoadMore();
      }
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [target, onLoadMore]);
}
