import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormControl, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { NodeCreate } from 'src/app/models/api/node.model';
import { BaseOrganization } from 'src/app/models/api/organization.model';
import { routePaths } from 'src/app/routes';
import { CollaborationService } from 'src/app/services/collaboration.service';
import { NodeService } from 'src/app/services/node.service';
import { OrganizationService } from 'src/app/services/organization.service';

@Component({
  selector: 'app-collaboration-create',
  templateUrl: './collaboration-create.component.html',
  styleUrls: ['./collaboration-create.component.scss'],
  host: { '[class.card-container]': 'true' }
})
export class CollaborationCreateComponent implements OnInit {
  routes = routePaths;

  form = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    encrypted: false,
    organization_ids: [[] as number[], [Validators.required]]
  });
  registerNodes = new FormControl(false);
  isLoading = true;
  isSubmitting = false;
  organizations: BaseOrganization[] = [];

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private organizationService: OrganizationService,
    private collaborationService: CollaborationService,
    private nodeService: NodeService
  ) {}

  ngOnInit(): void {
    this.initData();
  }

  async handleSubmit() {
    if (this.form.valid) {
      this.isSubmitting = true;

      const collaboration = await this.collaborationService.createCollaboration(this.form.getRawValue());
      if (collaboration?.id) {
        if (this.registerNodes.value) {
          this.form.value.organization_ids?.forEach(async (organizationID: number) => {
            this.nodeService.createNode(collaboration, organizationID);
          });
        }
        this.router.navigate([routePaths.collaborations]);
      } else {
        this.isSubmitting = false;
      }
    }
  }

  private async initData(): Promise<void> {
    this.organizations = await this.organizationService.getOrganizations();
    this.isLoading = false;
  }
}
