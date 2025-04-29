import {Component} from '@angular/core';
import {PageHeaderComponent} from "src/app/components/page-header/page-header.component";
import {MatProgressSpinner} from "@angular/material/progress-spinner";
import {MatToolbar, MatToolbarRow} from "@angular/material/toolbar";
import {routePaths} from 'src/app/routes';
import {RouterLink, RouterOutlet} from "@angular/router";

@Component({
    selector: 'app-community-store',
    templateUrl: './community-store.component.html',
    imports: [
        PageHeaderComponent,
        MatProgressSpinner,
        MatToolbar,
        MatToolbarRow,
        RouterOutlet,
        RouterLink,
    ],
    styleUrl: './community-store.component.scss'
})
export class CommunityStoreComponent  {

    protected readonly routes = routePaths;
    protected readonly routePaths = routePaths;
}
