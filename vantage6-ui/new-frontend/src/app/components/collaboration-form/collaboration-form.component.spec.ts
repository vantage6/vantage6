import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CollaborationFormComponent } from './collaboration-form.component';

describe('CollaborationFormComponent', () => {
  let component: CollaborationFormComponent;
  let fixture: ComponentFixture<CollaborationFormComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [CollaborationFormComponent]
    });
    fixture = TestBed.createComponent(CollaborationFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
