let env: any = {
  production: true,
  server_url:
    (window as { [key: string]: any })['env']['server_url'] ||
    'https://cotopaxi.vantage6.ai',
  api_path: (window as { [key: string]: any })['env']['api_path'] || '',
};

env['api_url'] =
  (window as { [key: string]: any })['env']['api_url'] ||
  `${env['server_url']}${env['api_path']}`;
export const environment = env;
