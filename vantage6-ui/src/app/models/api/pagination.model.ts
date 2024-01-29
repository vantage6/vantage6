export interface Pagination<T> {
  data: T[];
  links: PaginationLinks;
}

export interface PaginationLinks {
  first: string;
  last: string;
  self: string;
  total: number;
}
