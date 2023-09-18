import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CollaborationListComponent } from './collaboration-list.component';

describe('CollaborationListComponent', () => {
  let component: CollaborationListComponent;
  let fixture: ComponentFixture<CollaborationListComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [CollaborationListComponent]
    });
    fixture = TestBed.createComponent(CollaborationListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
