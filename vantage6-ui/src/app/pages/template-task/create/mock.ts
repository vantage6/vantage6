export const mockDataQualityTemplateTask = {
  name: 'Quality check',
  image: 'harbor2.vantage6.ai/starter/utils',
  function: 'fetch_static_file',
  collaboration: 2,
  fixed: { name: 'Quality check', databases: [] },
  variable: [
    'organizations',
    {
      functions: {
        arguments: ['file_name']
      }
    }
  ],
  allow_data_extend: false,
  allow_data_filter: false
};

export const mockDataCrossTabTemplateTask = {
  name: 'Cross tabulation',
  image: 'harbor2.vantage6.ai/starter/crosstab',
  function: 'dct',
  collaboration: 2,
  fixed: {
    name: 'Name',
    description: 'Description',
    organizations: ['2'],
    //  databases: [{ name: 'default' }]
    arguments: [{ name: 'group_by_columns', value: 'test column' }]
  },
  variable: [
    'name'
    // 'organizations',
    // 'description'
  ],
  allow_data_extend: false,
  allow_data_filter: false
};
