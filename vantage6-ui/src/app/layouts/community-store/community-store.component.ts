import {Component, OnInit} from '@angular/core';
import {NgIf} from "@angular/common";
import {AlgorithmStore} from "../../models/api/algorithmStore.model";
import {environment} from "../../../environments/environment";
import {AlgorithmService} from "../../services/algorithm.service";
import {PageHeaderComponent} from "../../components/page-header/page-header.component";
import {MatCard, MatCardContent} from "@angular/material/card";
import {MatProgressSpinner} from "@angular/material/progress-spinner";
import {TranslatePipe} from "@ngx-translate/core";
import {Algorithm} from "../../models/api/algorithm.model";

import {
    AlgorithmTableComponent
} from "../../components/algorithm/algorithm-table/algorithm-table.component";

@Component({
    selector: 'app-community-store',
    templateUrl: './community-store.component.html',
    imports: [
        NgIf,
        PageHeaderComponent,
        MatCard,
        MatCardContent,
        MatProgressSpinner,
        TranslatePipe,
        AlgorithmTableComponent
    ],
    styleUrl: './community-store.component.scss'
})
export class CommunityStoreComponent implements OnInit {
    isLoading = true;
    algorithms: Algorithm[] = [];
    algorithmStore: AlgorithmStore = this.getCommunityStore();

    constructor(
        private algorithmService: AlgorithmService,
    ) {
    }

    async ngOnInit(): Promise<void> {
        this.algorithms = await this.algorithmService.getAlgorithmsForAlgorithmStore(this.algorithmStore);
        console.log(this.algorithms)
        this.isLoading = false;
    }


    getCommunityStore(): AlgorithmStore {
        return {
            id: -1, name: "community store",
            url: environment.community_store_url,
            collaborations: [],
            all_collaborations: true
        }
    }

}
