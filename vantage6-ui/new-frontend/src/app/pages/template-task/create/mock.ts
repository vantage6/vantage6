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
  image: 'harbor2.vantage6.ai/starter/utils',
  function: 'fetch_static_file',
  collaboration: 2,
  fixed: { name: 'Name', description: 'Description' },
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
