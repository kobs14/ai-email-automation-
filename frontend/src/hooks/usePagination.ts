import { useState, useCallback } from 'react';

interface UsePaginationOptions {
  initialPage?: number;
  initialPerPage?: number;
}

export function usePagination({ initialPage = 1, initialPerPage = 20 }: UsePaginationOptions = {}) {
  const [page, setPage] = useState(initialPage);
  const [perPage] = useState(initialPerPage);

  const goToPage = useCallback((newPage: number) => {
    setPage(Math.max(1, newPage));
  }, []);

  const resetPage = useCallback(() => {
    setPage(1);
  }, []);

  return { page, perPage, goToPage, resetPage };
}
