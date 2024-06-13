import { NameDescription } from './base.model';

export enum VisualizationType {
  Table = 'table',
  Histogram = 'histogram',
  Line = 'line'
}

// TODO should these schema's be moved to a separate JSON file? Which also allows for translations?
// Which maybe can also be shared with the backend?
const VISUALIZATION_SCHEMA_BASE = {
  location: {
    type: 'array',
    items: {
      type: 'string'
    },
    description: 'Location of the data to be visualized in the algorithm results',
    example: 'Set to "data,A" if your data is located in "results["data"]["A"]". If empty, the entire results object will be used'
  }
};

export const TABLE_VISUALIZATION_SCHEMA = Object.assign({}, VISUALIZATION_SCHEMA_BASE, {
  columns: {
    type: 'array',
    items: {
      type: 'string'
    },
    description: 'Columns to be displayed in the table',
    example: 'Enter "A,B,C" if you want to display columns A, B and C in the table. If empty, all columns will be displayed'
  }
});

export const HISTOGRAM_VISUALIZATION_SCHEMA = Object.assign({}, VISUALIZATION_SCHEMA_BASE);

export const LINE_VISUALIZATION_SCHEMA = Object.assign({}, VISUALIZATION_SCHEMA_BASE, {
  x: {
    type: 'string',
    description: 'Column to be displayed on the x-axis',
    example: 'Enter "A" if you want to display column A on the x-axis'
  },
  y: {
    type: 'string',
    description: 'Column to be displayed on the y-axis',
    example: 'Enter "B" if you want to display column B on the y-axis'
  },
  y_axis_min: {
    type: 'number',
    description: 'Minimum value of the y-axis',
    example: 'Enter 0 if you want to start the y-axis at 0'
  },
  y_axis_max: {
    type: 'number',
    description: 'Maximum value of the y-axis',
    example: 'Enter 100 if you want to end the y-axis at 100'
  }
});

interface VisualizationSchemaBase {
  // defines the type of keys and values that these schemas contain
  [key: string]: string[] | string | number | undefined;
  // location is a shared property of all visualization schemas. It signals where the
  // data to be visualized is located in the algorithm results
  location: string[];
}
export interface TableVisualizationSchema extends VisualizationSchemaBase {
  columns: string[];
}

export type HistogramVisualizationSchema = VisualizationSchemaBase;

export interface LineVisualizationSchema extends VisualizationSchemaBase {
  x: string;
  y: string;
}

export type VisualizationSchema = TableVisualizationSchema | HistogramVisualizationSchema | LineVisualizationSchema;

export interface Visualization {
  id: number;
  name: string;
  description?: string;
  type: VisualizationType;
  schema: VisualizationSchema;
}

export interface VisualizationForm extends NameDescription {
  type: VisualizationType;
  schema: VisualizationSchema;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function getVisualizationSchema(visType: VisualizationType): any {
  switch (visType) {
    case VisualizationType.Table:
      return TABLE_VISUALIZATION_SCHEMA;
    case VisualizationType.Histogram:
      return HISTOGRAM_VISUALIZATION_SCHEMA;
    case VisualizationType.Line:
      return LINE_VISUALIZATION_SCHEMA;
  }
}
