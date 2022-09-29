export const environment = {
  production: true,
  api_url:
    (window as { [key: string]: any })['env']['api_url'] ||
    'https://petronas.vantage6.ai',
};
