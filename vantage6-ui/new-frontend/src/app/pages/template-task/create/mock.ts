export const mockDataQualityTemplateTask = {
  image: 'harbor2.vantage6.ai/starter/utils',
  function: 'fetch_static_file',
  collaboration: 2,
  fixed: { name: 'Quality check', databases: [] },
  variable: [
    'organizations',
    'description',
    {
      functions: {
        arguments: ['file_name']
      }
    }
  ],
  allow_data_extend: false,
  allow_data_filter: false
};

export const mockDataAllTemplateTask = {
  image: 'harbor2.vantage6.ai/starter/crosstab',
  function: 'dct',
  collaboration: 2,
  fixed: {
    name: 'Name',
    description: 'Description'
    //  databases: [{ name: 'default' }]
  },
  variable: [
    //'name',
    'organizations',
    //'description',
    {
      functions: {
        arguments: ['file_name']
      }
    }
  ],
  allow_data_extend: false,
  allow_data_filter: false
};
