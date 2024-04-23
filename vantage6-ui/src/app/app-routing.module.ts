import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { routePaths, routerConfig } from './routes';
import { LoginComponent } from './pages/auth/login/login.component';
import { LayoutLoginComponent } from './layouts/layout-login/layout-login.component';
import { LayoutDefaultComponent } from './layouts/layout-default/layout-default.component';
import { HomeComponent } from './pages/home/home.component';
import { authenticationGuard } from './guards/authentication.guard';
import { OrganizationReadComponent } from './pages/organization/read/organization-read.component';
import { TaskCreateComponent } from './pages/task/create/task-create.component';
import { StartComponent } from './pages/start/start.component';
import { TaskListComponent } from './pages/task/list/task-list.component';
import { TaskReadComponent } from './pages/task/read/task-read.component';
import { CollaborationReadComponent } from './pages/collaboration/read/collaboration-read.component';
import { CollaborationListComponent } from './pages/collaboration/list/collaboration-list.component';
import { UserListComponent } from './pages/user/list/user-list.component';
import { UserReadComponent } from './pages/user/read/user-read.component';
import { OrganizationCreateComponent } from './pages/organization/create/organization-create.component';
import { CollaborationCreateComponent } from './pages/collaboration/create/collaboration-create.component';
import { UserCreateComponent } from './pages/user/create/user-create.component';
import { OrganizationListComponent } from './pages/organization/list/organization-list.component';
import { NodeReadComponent } from './pages/node/read/node-read.component';
import { OrganizationEditComponent } from './pages/organization/edit/organization-edit.component';
import { CollaborationEditComponent } from './pages/collaboration/edit/collaboration-edit.component';
import { UserEditComponent } from './pages/user/edit/user-edit.component';
import { ChangePasswordComponent } from './pages/auth/change-password/change-password.component';
import { chosenCollaborationGuard } from './guards/chosenCollaboration.guard';
import { TemplateTaskCreateComponent } from './pages/template-task/create/template-task-create.component';
import { RoleListComponent } from './pages/role/list/role-list.component';
import { RoleReadComponent } from './pages/role/read/role-read.component';
import { RoleCreateComponent } from './pages/role/create/role-create.component';
import { SetupMfaComponent } from './pages/auth/setup-mfa/setup-mfa.component';
import { MfaCodeComponent } from './pages/auth/mfa-code/mfa-code.component';
import { MfaLostComponent } from './pages/auth/mfa-lost/mfa-lost.component';
import { MfaRecoverComponent } from './pages/auth/mfa-recover/mfa-recover.component';
import { PasswordLostComponent } from './pages/auth/password-lost/password-lost.component';
import { PasswordRecoverComponent } from './pages/auth/password-recover/password-recover.component';
import { AddAlgoStoreComponent } from './pages/collaboration/add-algo-store/add-algo-store.component';
import { StudyReadComponent } from './pages/collaboration/study/read/study-read.component';
import { StudyCreateComponent } from './pages/collaboration/study/create/study-create.component';
import { StudyEditComponent } from './pages/collaboration/study/edit/study-edit.component';
import { AlgorithmListComponent } from './pages/algorithm/list/algorithm-list.component';
import { AlgorithmReadOnlyComponent } from './pages/algorithm/read-only/algorithm-read-only.component';
import { AlgorithmStoreListComponent } from './pages/algorithm-stores/list/algorithm-store-list.component';
import { AlgorithmStoreReadComponent } from './pages/algorithm-stores/read/algorithm-store-read.component';
import { AlgorithmReadComponent } from './pages/algorithm/read/algorithm-read.component';
import { chosenStoreGuard } from './guards/chosenStore.guard';

const routes: Routes = [
  {
    path: 'auth',
    component: LayoutLoginComponent,
    children: [
      {
        path: routerConfig.login,
        component: LoginComponent
      },
      {
        path: routerConfig.passwordLost,
        component: PasswordLostComponent
      },
      {
        path: routerConfig.passwordRecover,
        component: PasswordRecoverComponent
      },
      {
        path: routerConfig.mfaCode,
        component: MfaCodeComponent
      },
      {
        path: routerConfig.setupMFA,
        component: SetupMfaComponent
      },
      {
        path: routerConfig.mfaLost,
        component: MfaLostComponent
      },
      {
        path: routerConfig.mfaRecover,
        component: MfaRecoverComponent
      }
    ]
  },
  {
    path: '',
    component: LayoutDefaultComponent,
    data: { crumb: ['home.title', routePaths.home] },
    children: [
      {
        path: routerConfig.home,
        component: HomeComponent,
        canActivate: [authenticationGuard(), chosenCollaborationGuard()]
      },
      {
        path: routerConfig.passwordChange,
        component: ChangePasswordComponent,
        canActivate: [authenticationGuard()]
      }
    ]
  },
  {
    path: routerConfig.analyze,
    component: LayoutDefaultComponent,
    data: { crumb: ['links.title', routePaths.analyzeHome] },
    children: [
      {
        path: routerConfig.analyzeHome,
        component: HomeComponent
      },
      {
        path: routerConfig.start,
        component: StartComponent,
        canActivate: [authenticationGuard()]
      },
      {
        path: routerConfig.tasks,
        component: TaskListComponent,
        canActivate: [authenticationGuard(), chosenCollaborationGuard()],
        data: {
          crumbs: [['task-list.title']]
        }
      },
      {
        path: routerConfig.taskCreate,
        component: TaskCreateComponent,
        canActivate: [authenticationGuard(), chosenCollaborationGuard()],
        data: {
          crumbs: [['task-list.title', routePaths.tasks], ['task-create.title']]
        }
      },
      {
        path: routerConfig.taskCreateRepeat,
        component: TaskCreateComponent,
        canActivate: [authenticationGuard(), chosenCollaborationGuard()],
        data: {
          crumbs: [['task-list.title', routePaths.tasks], ['task-create.title']]
        }
      },
      {
        path: routerConfig.task,
        component: TaskReadComponent,
        canActivate: [authenticationGuard(), chosenCollaborationGuard()],
        data: {
          crumbs: [['task-list.title', routePaths.tasks], ['task-read.title']]
        }
      },
      {
        path: routerConfig.algorithms,
        component: AlgorithmListComponent,
        canActivate: [authenticationGuard(), chosenCollaborationGuard()],
        data: {
          crumbs: [['algorithm-list.title']]
        }
      },
      {
        path: routerConfig.algorithm,
        component: AlgorithmReadOnlyComponent,
        canActivate: [authenticationGuard(), chosenCollaborationGuard()],
        data: {
          crumbs: [['algorithm-list.title', routePaths.algorithms], ['algorithm-read.crumb-title']]
        }
      },
      {
        path: routerConfig.templateTaskCreate,
        component: TemplateTaskCreateComponent,
        canActivate: [authenticationGuard(), chosenCollaborationGuard()]
      }
    ]
  },
  {
    path: routerConfig.admin,
    component: LayoutDefaultComponent,
    data: { crumb: ['home.title', routePaths.adminHome] },
    children: [
      {
        path: routerConfig.adminHome,
        component: CollaborationListComponent,
        canActivate: [authenticationGuard()]
      },
      {
        path: routerConfig.organizations,
        component: OrganizationListComponent,
        canActivate: [authenticationGuard()],
        data: {
          crumbs: [['organization-list.title']]
        }
      },
      {
        path: routerConfig.organizationCreate,
        component: OrganizationCreateComponent,
        canActivate: [authenticationGuard()],
        data: {
          crumbs: [['organization-list.title', routePaths.organizations], ['organization-create.title']]
        }
      },
      {
        path: routerConfig.organizationEdit,
        component: OrganizationEditComponent,
        canActivate: [authenticationGuard()],
        data: {
          crumbs: [['organization-list.title', routePaths.organizations], ['organization-read.title']]
        }
      },
      {
        path: routerConfig.organization,
        component: OrganizationReadComponent,
        canActivate: [authenticationGuard()],
        data: {
          crumbs: [['organization-list.title', routePaths.organizations], ['organization-read.title']]
        }
      },
      {
        path: routerConfig.collaborations,
        component: CollaborationListComponent,
        canActivate: [authenticationGuard()],
        data: {
          crumbs: [['collaboration-list.title']]
        }
      },
      {
        path: routerConfig.collaborationCreate,
        component: CollaborationCreateComponent,
        canActivate: [authenticationGuard()],
        data: {
          crumbs: [['collaboration-list.title', routePaths.collaborations], ['collaboration-create.title']]
        }
      },
      {
        path: routerConfig.collaborationEdit,
        component: CollaborationEditComponent,
        canActivate: [authenticationGuard()],
        data: {
          crumbs: [['collaboration-list.title', routePaths.collaborations], ['collaboration-read.title']]
        }
      },
      {
        path: routerConfig.collaboration,
        component: CollaborationReadComponent,
        canActivate: [authenticationGuard()],
        data: {
          crumbs: [['collaboration-list.title', routePaths.collaborations], ['collaboration-read.title']]
        }
      },
      {
        path: routerConfig.algorithmStoreAdd,
        component: AddAlgoStoreComponent,
        canActivate: [authenticationGuard()],
        data: {
          crumbs: [
            ['collaboration-list.title', routePaths.collaborations],
            // TODO this crumb is not complete: it should include the collaboration for which
            // the algorithm store is being added, but not sure how to get its ID here
            // ['collaboration-read.title', Router().url.split('/').pop() || ''],
            ['algorithm-store-add.title']
          ]
        }
      },
      {
        path: routerConfig.roles,
        component: RoleListComponent,
        canActivate: [authenticationGuard()],
        data: {
          crumbs: [['role-list.title']]
        }
      },
      {
        path: routerConfig.roleCreate,
        component: RoleCreateComponent,
        canActivate: [authenticationGuard()],
        data: {
          crumbs: [['role-list.title', routePaths.roles], ['role-create.title']]
        }
      },
      {
        path: routerConfig.role,
        component: RoleReadComponent,
        canActivate: [authenticationGuard()],
        data: {
          crumbs: [['role-list.title', routePaths.roles], ['role-read.title']]
        }
      },
      {
        path: routerConfig.users,
        component: UserListComponent,
        canActivate: [authenticationGuard()],
        data: {
          crumbs: [['user-list.title']]
        }
      },
      {
        path: routerConfig.userCreate,
        component: UserCreateComponent,
        canActivate: [authenticationGuard()],
        data: {
          crumbs: [['user-list.title', routePaths.users], ['user-create.title']]
        }
      },
      {
        path: routerConfig.userEdit,
        component: UserEditComponent,
        canActivate: [authenticationGuard()],
        data: {
          crumbs: [['user-list.title', routePaths.users], ['user-read.title']]
        }
      },
      {
        path: routerConfig.user,
        component: UserReadComponent,
        canActivate: [authenticationGuard()],
        data: {
          crumbs: [['user-list.title', routePaths.users], ['user-read.title']]
        }
      },
      {
        path: routerConfig.nodes,
        component: NodeReadComponent,
        canActivate: [authenticationGuard()],
        data: {
          crumbs: [['node-read.title']]
        }
      },
      {
        path: routerConfig.study,
        component: StudyReadComponent,
        canActivate: [authenticationGuard()],
        data: {
          crumbs: [['collaboration-list.title', routePaths.collaborations], ['collaboration-read.title']]
        }
      },
      {
        path: routerConfig.studyCreate,
        component: StudyCreateComponent,
        canActivate: [authenticationGuard()],
        data: {
          crumbs: [['collaboration-list.title', routePaths.collaborations], ['collaboration-read.title']]
        }
      },
      {
        path: routerConfig.studyEdit,
        component: StudyEditComponent,
        canActivate: [authenticationGuard()],
        data: {
          crumbs: [['collaboration-list.title', routePaths.collaborations], ['collaboration-read.title']]
        }
      }
    ]
  },
  {
    path: routerConfig.storeBase,
    component: LayoutDefaultComponent,
    data: { crumb: ['home.title', routePaths.storeHome] },
    children: [
      {
        path: routerConfig.storeHome,
        component: AlgorithmStoreListComponent,
        canActivate: [authenticationGuard()]
      },
      {
        path: routerConfig.stores,
        component: AlgorithmStoreListComponent,
        canActivate: [authenticationGuard()],
        data: {
          crumbs: [['algorithm-store-list.title']]
        }
      },
      {
        path: routerConfig.store,
        component: AlgorithmStoreReadComponent,
        canActivate: [authenticationGuard(), chosenStoreGuard()],
        data: {
          crumbs: [['algorithm-store-list.title', routePaths.stores], ['algorithm-store-read.title']]
        }
      },
      {
        path: routerConfig.algorithmManage,
        component: AlgorithmReadComponent,
        canActivate: [authenticationGuard(), chosenStoreGuard()],
        data: {
          crumbs: [
            ['algorithm-store-list.title', routePaths.stores],
            ['algorithm-store-read.title', routePaths.store],
            ['resources.algorithm']
          ]
        }
      }
    ]
  }
];

@NgModule({
  imports: [RouterModule.forRoot(routes, { bindToComponentInputs: true, useHash: true })],
  exports: [RouterModule]
})
export class AppRoutingModule {}
