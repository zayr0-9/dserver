import { useEffect, useRef } from 'react';

/**
 * useInfiniteScroll
 *
 * @param {Function} callback - function to call when sentinel is intersected (e.g. loadMore)
 * @param {boolean} hasMore - whether more data is available
 * @param {boolean} isLoading - whether a load is in progress
 * @param {number} [rootMargin=0] - margin around the root. Increase if you want to load earlier (e.g. "200px")
 */

function useInfiniteScroll(
  callback,
  hasMore,
  containerRef,
  isLoading,
  rootMargin = '250px'
) {
  const sentinelRef = useRef(null);

  useEffect(() => {
    if (!hasMore) return; // If there's no more data, don't set up observer
    if (isLoading) return; // If we're already loading, don't trigger again

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          console.log('intersection detected');
          callback();
        }
      },
      {
        root: null, //containerRef?.current || null, // or pass a specific scrollable container
        rootMargin, // how far from the bottom to trigger
        threshold: 0.1, // trigger when sentinel is 10% in view
      }
    );

    const sentinel = sentinelRef.current;
    if (sentinel) observer.observe(sentinel);

    return () => {
      if (sentinel) observer.unobserve(sentinel);
    };
  }, [callback, hasMore, isLoading, rootMargin]);

  return sentinelRef;
}

export default useInfiniteScroll;
