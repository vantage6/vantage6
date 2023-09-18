export const routePaths = {
  login: '/login',
  start: '/start',
  home: '/',
  adminHome: '/admin',
  organization: '/admin/organization',
  collaborations: '/admin/collaborations',
  collaboration: '/admin/collaborations',
  task: '/task/read',
  taskCreate: '/task/create',
  tasks: '/task'
};

export const routerConfig = {
  login: 'login',
  start: 'start',
  home: '',
  admin: 'admin',
  adminHome: '',
  organization: 'organization',
  collaborations: 'collaborations',
  collaboration: 'collaborations/:id',
  task: 'task/read/:id',
  taskCreate: 'task/create',
  tasks: 'task'
};
