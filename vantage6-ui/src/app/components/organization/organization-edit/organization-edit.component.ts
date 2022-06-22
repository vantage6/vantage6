import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import {
  EMPTY_ORGANIZATION,
  getEmptyOrganization,
  Organization,
} from 'src/app/interfaces/organization';

import { ApiOrganizationService } from 'src/app/services/api/api-organization.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { ResType } from 'src/app/shared/enum';
import { UtilsService } from 'src/app/services/common/utils.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { BaseEditComponent } from 'src/app/components/base/base-edit/base-edit.component';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { FileService } from 'src/app/services/common/file.service';

@Component({
  selector: 'app-organization-edit',
  templateUrl: './organization-edit.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    './organization-edit.component.scss',
  ],
})
export class OrganizationEditComponent
  extends BaseEditComponent
  implements OnInit
{
  organization: Organization = getEmptyOrganization();
  public_key_file: File | null = null;
  delete_public_key: boolean = false;

  constructor(
    protected router: Router,
    protected activatedRoute: ActivatedRoute,
    protected orgApiService: ApiOrganizationService,
    protected orgDataService: OrgDataService,
    protected modalService: ModalService,
    protected utilsService: UtilsService,
    public userPermission: UserPermissionService,
    private fileService: FileService
  ) {
    super(
      router,
      activatedRoute,
      userPermission,
      utilsService,
      orgApiService,
      orgDataService,
      modalService
    );
  }

  async init(): Promise<void> {
    // subscribe to id parameter in route to change edited organization if
    // required
    this.activatedRoute.paramMap.subscribe((params) => {
      let id = this.utilsService.getId(params, ResType.ORGANIZATION);
      if (id === EMPTY_ORGANIZATION.id) {
        return; // cannot get organization
      }
      this.setupEdit(id);
    });
  }

  async setupEdit(id: number) {
    let org = await this.orgDataService.get(id);
    if (org) {
      this.organization = org;
    }
  }

  setupCreate(): void {
    // nothing has to be done here for organizations - just implementing
    // abstract base function
  }

  async save(): Promise<void> {
    if (this.delete_public_key) {
      this.organization.public_key = null;
    }
    const new_public_key = await this.readUploadedFile();
    if (new_public_key) {
      this.organization.public_key = new_public_key;
    }
    let org_json = await super.save(this.organization, false);
    this.router.navigate([`/organization/${org_json.id}`]);
  }

  uploadPublicKey($event: any): void {
    this.public_key_file = this.fileService.uploadFile($event);
  }

  uploadPublicKeyText(): string {
    return this.organization.public_key
      ? 'Upload new public key:'
      : 'Upload public key:';
  }

  async readUploadedFile(): Promise<string | undefined> {
    if (this.public_key_file) {
      return await this.fileService.readFile(this.public_key_file as File);
    } else {
      return undefined;
    }
  }
}
