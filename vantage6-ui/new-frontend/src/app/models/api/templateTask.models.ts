export interface TemplateTask {
  image: string;
  function: string;
  fixed: FixedTemplateTask;
  variable: Array<string | any>;
}

interface FixedTemplateTask {
  name?: string;
  databases?: string[];
}
