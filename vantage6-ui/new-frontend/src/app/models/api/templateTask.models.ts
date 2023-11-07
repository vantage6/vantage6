export interface TemplateTask {
  image: string;
  function: string;
  fixed: FixedTemplateTask;
  variable: Array<string | any>;
}

interface FixedTemplateTask {
  name?: string;
  description?: string;
  organizations?: string[];
  databases?: FixedDatabase[];
}

interface FixedDatabase {
  name: string;
  sheet?: string;
  query?: string;
}
