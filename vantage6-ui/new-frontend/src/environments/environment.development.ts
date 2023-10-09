let env: any = {
  production: false,
  server_url: 'http://localhost:5000',
  api_path: '/api',
  version: '0.0.0',
  algorithm_server_url: 'http://localhost:3002'
};

env.api_url = `${env['server_url']}${env['api_path']}`;

export const environment = env;
