let env: any = {
  production: false,
  server_url: 'http://localhost:5000',
  api_path: ''
  version: '0.0.0'
};

env.api_url = `${env['server_url']}${env['api_path']}`;

export const environment = env;
