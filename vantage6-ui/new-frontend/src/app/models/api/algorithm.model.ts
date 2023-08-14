export interface Algorithm {
  id: number;
  name: string;
  functions: Function[];
}

export interface Function {
  name: string;
  is_central: boolean;
}
