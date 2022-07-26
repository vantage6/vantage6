import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RoleViewSingleComponent } from './role-view-single.component';

describe('RoleViewSingleComponent', () => {
  let component: RoleViewSingleComponent;
  let fixture: ComponentFixture<RoleViewSingleComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ RoleViewSingleComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(RoleViewSingleComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
