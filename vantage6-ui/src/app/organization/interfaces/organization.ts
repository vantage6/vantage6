export interface Organization {
  id: number;
  name: string;
  address1: string;
  address2: string;
  zipcode: string;
  country: string;
  domain: string;
  public_key: string;
  is_being_created?: boolean;
}

export const EMPTY_ORGANIZATION = {
  id: -1,
  name: '',
  address1: '',
  address2: '',
  zipcode: '',
  country: '',
  domain: '',
  public_key: '',
};
