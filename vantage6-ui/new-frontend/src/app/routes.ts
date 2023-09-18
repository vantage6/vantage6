export const routePaths = {
  login: '/login',
  start: '/start',
  home: '/',
  adminHome: '/admin',
  organization: '/admin/organization',
  collaborations: '/admin/collaborations',
  collaboration: '/admin/collaborations',
  collaborationCreate: '/admin/collaborations/create',
  task: '/task',
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
  collaborationCreate: 'collaborations/create',
  collaboration: 'collaborations/:id',
  task: 'task/:id',
  taskCreate: 'task/create',
  tasks: 'task'
};
