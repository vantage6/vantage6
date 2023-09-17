import { ComponentFixture, TestBed } from '@angular/core/testing';

import { OrganizationReadComponent } from './organization-read.component';

describe('OrganizationReadComponent', () => {
  let component: OrganizationReadComponent;
  let fixture: ComponentFixture<OrganizationReadComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [OrganizationReadComponent]
    });
    fixture = TestBed.createComponent(OrganizationReadComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
