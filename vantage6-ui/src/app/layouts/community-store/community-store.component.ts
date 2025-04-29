import {Component} from '@angular/core';
import {MatProgressSpinner} from "@angular/material/progress-spinner";
import {MatToolbar} from "@angular/material/toolbar";
import {routePaths} from 'src/app/routes';
import {RouterLink, RouterOutlet} from "@angular/router";

@Component({
    selector: 'app-community-store',
    templateUrl: './community-store.component.html',
    imports: [
        MatProgressSpinner,
        MatToolbar,
        RouterOutlet,
        RouterLink,


    ],
    styleUrl: './community-store.component.scss'
})
export class CommunityStoreComponent  {

    protected readonly routes = routePaths;
    protected readonly routePaths = routePaths;
}
