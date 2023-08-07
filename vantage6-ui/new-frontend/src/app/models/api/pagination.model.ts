export interface Pagination<T> {
  data: T[];
  links: Links;
}

interface Links {
  first: string;
  last: string;
  self: string;
}
