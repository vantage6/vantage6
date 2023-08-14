import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { Collaboration } from 'src/app/models/api/Collaboration.model';
import { routePaths } from 'src/app/routes';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { CollaborationService } from 'src/app/services/collaboration.service';

@Component({
  selector: 'app-start',
  templateUrl: './start.component.html',
  styleUrls: ['./start.component.scss'],
  host: { '[class.card-container]': 'true' }
})
export class StartComponent implements OnInit {
  collaborations: Collaboration[] = [];

  constructor(
    private router: Router,
    private collaborationService: CollaborationService,
    private chosenCollaborationService: ChosenCollaborationService
  ) {}

  async ngOnInit() {
    this.collaborations = await this.collaborationService.getCollaborations();
  }

  handleCollaborationClick(collaboration: Collaboration) {
    this.chosenCollaborationService.setCollaboration(collaboration);
    this.router.navigate([routePaths.home]);
  }
}
