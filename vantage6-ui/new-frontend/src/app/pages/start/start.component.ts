import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { BaseCollaboration, CollaborationSortProperties, GetCollaborationParameters } from 'src/app/models/api/collaboration.model';
import { routePaths } from 'src/app/routes';
import { AuthService } from 'src/app/services/auth.service';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { CollaborationService } from 'src/app/services/collaboration.service';

@Component({
  selector: 'app-start',
  templateUrl: './start.component.html',
  styleUrls: ['./start.component.scss'],
  host: { '[class.card-container]': 'true' }
})
export class StartComponent implements OnInit {
  collaborations: BaseCollaboration[] = [];

  constructor(
    private router: Router,
    private collaborationService: CollaborationService,
    private chosenCollaborationService: ChosenCollaborationService,
    private authService: AuthService
  ) {}

  async ngOnInit() {
    let params: GetCollaborationParameters = {
      sort: CollaborationSortProperties.Name
    };
    let activeOrgId = this.authService.getActiveOrganizationID();
    if (activeOrgId) {
      params.organization_id = activeOrgId.toString();
    }
    this.collaborations = await this.collaborationService.getCollaborations(params);
  }

  handleCollaborationClick(collaboration: BaseCollaboration) {
    this.chosenCollaborationService.setCollaboration(collaboration.id.toString());
    this.router.navigate([routePaths.home]);
  }
}
