export interface TemplateTask {
  name: string;
  image: string;
  function: string;
  fixed?: FixedTemplateTask;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  variable?: Array<string | any>;
}

interface FixedTemplateTask {
  name?: string;
  description?: string;
  organizations?: string[];
  databases?: FixedDatabase[];
  arguments?: FixedArgument[];
}

interface FixedDatabase {
  name: string;
  sheet?: string;
  query?: string;
}

interface FixedArgument {
  name: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  value: any;
}
