import {Component, Input} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';
import {MatButtonModule} from '@angular/material/button';
import {MatTableModule} from '@angular/material/table';
import {Algorithm} from "../../../models/api/algorithm.model";
import {MatList, MatListItem} from "@angular/material/list";

@Component({
    selector: 'app-algorithm-table',
    templateUrl: './algorithm-table.component.html',
    styleUrl: './algorithm-table.component.scss',
    imports: [MatIconModule, MatButtonModule, MatTableModule, MatList, MatListItem]
})
export class AlgorithmTableComponent {
    @Input() algorithms: Algorithm[] = []
    columnsToDisplay = ['name', 'vantage6_version', 'submitted_at'];
    columnsToDisplayWithExpand = [...this.columnsToDisplay, 'expand'];
    expandedElement: Algorithm | null = null;

    /** Checks whether an element is expanded. */
    isExpanded(element: Algorithm) {
        return this.expandedElement === element;
    }

    /** Toggles the expanded state of an element. */
    toggle(element: Algorithm) {
        this.expandedElement = this.isExpanded(element) ? null : element;
    }

}
