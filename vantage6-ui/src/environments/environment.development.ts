import { EnvironmentConfig } from 'src/app/models/application/enivronmentConfig.model';

const env: EnvironmentConfig = {
  production: false,
  // server_url: 'https://cotopaxi.vantage6.ai',
  // api_path: ''
  server_url: 'http://localhost:5000',
  api_path: '/api'
};

export const environment = env;
