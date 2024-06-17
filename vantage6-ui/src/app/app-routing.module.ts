import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { routePaths, routerConfig } from './routes';
import { LoginComponent } from './pages/auth/login/login.component';
import { LayoutLoginComponent } from './layouts/layout-login/layout-login.component';
import { LayoutDefaultComponent } from './layouts/layout-default/layout-default.component';
import { HomeComponent } from './pages/home/home.component';
import { authenticationGuard } from './guards/authentication.guard';
import { OrganizationReadComponent } from './pages/admin/organization/read/organization-read.component';
import { TaskCreateComponent } from './pages/analyze/task/create/task-create.component';
import { ChooseCollaborationComponent } from './pages/analyze/choose-collaboration/choose-collaboration';
import { TaskListComponent } from './pages/analyze/task/list/task-list.component';
import { TaskReadComponent } from './pages/analyze/task/read/task-read.component';
import { CollaborationReadComponent } from './pages/admin/collaboration/read/collaboration-read.component';
import { CollaborationListComponent } from './pages/admin/collaboration/list/collaboration-list.component';
import { UserListComponent } from './pages/admin/user/list/user-list.component';
import { UserReadComponent } from './pages/admin/user/read/user-read.component';
import { OrganizationCreateComponent } from './pages/admin/organization/create/organization-create.component';
import { CollaborationCreateComponent } from './pages/admin/collaboration/create/collaboration-create.component';
import { UserCreateComponent } from './pages/admin/user/create/user-create.component';
import { OrganizationListComponent } from './pages/admin/organization/list/organization-list.component';
import { NodeReadComponent } from './pages/admin/node/read/node-read.component';
import { OrganizationEditComponent } from './pages/admin/organization/edit/organization-edit.component';
import { CollaborationEditComponent } from './pages/admin/collaboration/edit/collaboration-edit.component';
import { UserEditComponent } from './pages/admin/user/edit/user-edit.component';
import { ChangePasswordComponent } from './pages/auth/change-password/change-password.component';
import { chosenCollaborationGuard } from './guards/chosenCollaboration.guard';
import { TemplateTaskCreateComponent } from './pages/analyze/template-task/create/template-task-create.component';
import { RoleListComponent } from './pages/admin/role/list/role-list.component';
import { RoleReadComponent } from './pages/admin/role/read/role-read.component';
import { RoleCreateComponent } from './pages/admin/role/create/role-create.component';
import { SetupMfaComponent } from './pages/auth/setup-mfa/setup-mfa.component';
import { MfaCodeComponent } from './pages/auth/mfa-code/mfa-code.component';
import { MfaLostComponent } from './pages/auth/mfa-lost/mfa-lost.component';
import { MfaRecoverComponent } from './pages/auth/mfa-recover/mfa-recover.component';
import { PasswordLostComponent } from './pages/auth/password-lost/password-lost.component';
import { PasswordRecoverComponent } from './pages/auth/password-recover/password-recover.component';
import { AddAlgoStoreComponent } from './pages/admin/collaboration/add-algo-store/add-algo-store.component';
import { StudyReadComponent } from './pages/admin/collaboration/study/read/study-read.component';
import { StudyCreateComponent } from './pages/admin/collaboration/study/create/study-create.component';
import { StudyEditComponent } from './pages/admin/collaboration/study/edit/study-edit.component';
import { AlgorithmListReadOnlyComponent } from './pages/analyze/algorithm/list/algorithm-list-read-only.component';
import { AlgorithmReadOnlyComponent } from './pages/analyze/algorithm/read-only/algorithm-read-only.component';
import { AlgorithmStoreListComponent } from './pages/store/algorithm-stores/list/algorithm-store-list.component';
import { AlgorithmStoreReadComponent } from './pages/store/algorithm-stores/read/algorithm-store-read.component';
import { AlgorithmReadComponent } from './pages/store/algorithm/read/algorithm-read.component';
import { chosenStoreGuard } from './guards/chosenStore.guard';
import { AlgorithmListComponent } from './pages/store/algorithm/list/algorithm-list.component';
import { AlgorithmCreateComponent } from './pages/store/algorithm/create/algorithm-create.component';
import { AlgorithmEditComponent } from './pages/store/algorithm/edit/algorithm-edit.component';
import { UploadPrivateKeyComponent } from './pages/analyze/choose-collaboration/upload-private-key/upload-private-key.component';
import { StoreUserListComponent } from './pages/store/user/list/store-user-list.component';
import { StoreUserReadComponent } from './pages/store/user/read/store-user-read.component';
import { StoreUserCreateComponent } from './pages/store/user/create/store-user-create.component';
import { StoreUserEditComponent } from './pages/store/user/edit/store-user-edit.component';

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
        canActivate: [authenticationGuard()]
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
        path: routerConfig.chooseCollaboration,
        component: ChooseCollaborationComponent,
        canActivate: [authenticationGuard()]
      },
      {
        path: routerConfig.keyUpload,
        component: UploadPrivateKeyComponent,
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
        component: AlgorithmListReadOnlyComponent,
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
          crumbs: [['algorithm-store-read.title']]
        }
      },
      {
        path: routerConfig.algorithmsManage,
        component: AlgorithmListComponent,
        canActivate: [authenticationGuard(), chosenStoreGuard()],
        data: {
          crumbs: [['algorithm-list.title']]
        }
      },
      {
        path: routerConfig.algorithmCreate,
        component: AlgorithmCreateComponent,
        canActivate: [authenticationGuard(), chosenStoreGuard()],
        data: {
          crumbs: [['algorithm-list.title', routePaths.algorithmsManage], ['algorithm-create.short-title']]
        }
      },
      {
        path: routerConfig.algorithmManage,
        component: AlgorithmReadComponent,
        canActivate: [authenticationGuard(), chosenStoreGuard()],
        data: {
          crumbs: [['algorithm-list.title', routePaths.algorithmsManage], ['resources.algorithm']]
        }
      },
      {
        path: routerConfig.algorithmEdit,
        component: AlgorithmEditComponent,
        canActivate: [authenticationGuard(), chosenStoreGuard()],
        data: {
          crumbs: [['algorithm-list.title', routePaths.algorithmsManage], ['resources.algorithm']]
        }
      },
      {
        path: routerConfig.storeUsers,
        component: StoreUserListComponent,
        canActivate: [authenticationGuard(), chosenStoreGuard()],
        data: {
          crumbs: [['user-list.title']]
        }
      },
      {
        path: routerConfig.storeUser,
        component: StoreUserReadComponent,
        canActivate: [authenticationGuard(), chosenStoreGuard()],
        data: {
          crumbs: [['user-list.title', routePaths.storeUsers], ['user-read.title']]
        }
      },
      {
        path: routerConfig.storeUserCreate,
        component: StoreUserCreateComponent,
        canActivate: [authenticationGuard(), chosenStoreGuard()],
        data: {
          crumbs: [['user-list.title', routePaths.storeUsers], ['user-create.title']]
        }
      },
      {
        path: routerConfig.storeUserEdit,
        component: StoreUserEditComponent,
        canActivate: [authenticationGuard(), chosenStoreGuard()],
        data: {
          crumbs: [['user-list.title', routePaths.storeUsers], ['user-read.title']]
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
