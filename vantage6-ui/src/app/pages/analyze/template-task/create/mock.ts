export const mockDataQualityTemplateTask = {
  name: 'Quality check',
  image: 'ghcr.io/vantage6/algorithm/starter-utils:latest',
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
  image: 'ghcr.io/vantage6/algorithm/starter-crosstab:latest',
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
