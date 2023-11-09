import { EnvironmentConfig } from 'src/app/models/application/enivronmentConfig.model';

const env: EnvironmentConfig = {
  production: false,
  server_url: 'https://test-petronas.azurewebsites.net',
  api_path: '',
  version: '0.0.0',
  algorithm_server_url: 'http://localhost:3002'
};

export const environment = env;
