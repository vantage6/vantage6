import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StoreRoleListComponent } from './store-role-list.component';

describe('StoreRoleListComponent', () => {
  let component: StoreRoleListComponent;
  let fixture: ComponentFixture<StoreRoleListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [StoreRoleListComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(StoreRoleListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
