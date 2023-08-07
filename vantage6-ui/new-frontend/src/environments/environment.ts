let env: any = {
  production: true,
  server_url: (window as any).env?.server_url || 'https://petronas.vantage6.ai',
  api_path: (window as any).env?.api_path || ''
};

env.api_url = (window as any).env?.api_url || `${env.server_url}${env.api_path}`;
export const environment = env;
