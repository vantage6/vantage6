import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PermissionsMatrixStoreComponent } from './permissions-matrix-store.component';

describe('PermissionsMatrixStoreComponent', () => {
  let component: PermissionsMatrixStoreComponent;
  let fixture: ComponentFixture<PermissionsMatrixStoreComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PermissionsMatrixStoreComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(PermissionsMatrixStoreComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
